import asyncio
import time
from loguru import logger
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.proxy import Proxy
from app.controllers.proxy_controller import ProxyController
from app.config import settings
from app.database import AsyncSessionLocal


async def validate_single(proxy: Proxy) -> tuple[bool, float]:
    """
    Tenta conectar ao proxy e mede latência.
    Retorna (sucesso, latency_ms).
    """
    proxy_url = proxy.url
    start = time.monotonic()
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=settings.PROXY_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(
                settings.PROXY_TEST_URL,
                proxy=proxy_url,
            ) as resp:
                if resp.status == 200:
                    latency_ms = (time.monotonic() - start) * 1000
                    return True, round(latency_ms, 1)
    except Exception:
        pass
    return False, 0.0


async def validate_all_proxies():
    """
    Job: valida todos os proxies ativos no banco.
    Roda com concorrência limitada.
    """
    logger.info("🔍 Iniciando validação de proxies...")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Proxy).where(Proxy.is_active == True))
        proxies = result.scalars().all()

    logger.info(f"   {len(proxies)} proxies para validar")

    sem = asyncio.Semaphore(settings.MAX_CONCURRENT_VALIDATIONS)

    async def _validate_with_sem(proxy: Proxy):
        async with sem:
            ok, latency = await validate_single(proxy)
            async with AsyncSessionLocal() as db:
                if ok:
                    await ProxyController.mark_validated(db, proxy.id, latency)
                    logger.debug(f"  ✅ {proxy.host}:{proxy.port} — {latency}ms")
                else:
                    await ProxyController.mark_failed(db, proxy.id)
                    logger.debug(f"  ❌ {proxy.host}:{proxy.port} — falhou")

    await asyncio.gather(*[_validate_with_sem(p) for p in proxies])
    logger.info("✅ Validação concluída.")
