import asyncio
import time
from loguru import logger
import aiohttp
from sqlalchemy import select
from app.models.proxy import Proxy
from app.controllers.proxy_controller import ProxyController
from app.config import settings
from app.database import AsyncSessionLocal


async def validate_single(proxy: Proxy) -> tuple[bool, float]:
    proxy_url = proxy.url
    start = time.monotonic()
    try:
        connector = aiohttp.TCPConnector(ssl=True)
        timeout = aiohttp.ClientTimeout(total=settings.PROXY_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(settings.PROXY_TEST_URL, proxy=proxy_url) as resp:
                if resp.status == 200:
                    return True, round((time.monotonic() - start) * 1000, 1)
    except Exception:
        pass
    return False, 0.0


async def validate_all_proxies():
    logger.info("🔍 Iniciando validação de proxies...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Proxy).where(Proxy.is_active == True))
        proxies = result.scalars().all()

    logger.info(f"   {len(proxies)} proxies para validar")
    sem = asyncio.Semaphore(settings.MAX_CONCURRENT_VALIDATIONS)

    async def _validate(proxy: Proxy):
        async with sem:
            ok, latency = await validate_single(proxy)
            async with AsyncSessionLocal() as db:
                if ok:
                    await ProxyController.mark_validated(db, proxy.id, latency)
                else:
                    await ProxyController.mark_failed(db, proxy.id)

    await asyncio.gather(*[_validate(p) for p in proxies])
    logger.info("✅ Validação concluída.")
