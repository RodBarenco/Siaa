import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from app.controllers.proxy_controller import ProxyCreate, ProxyController
from app.database import AsyncSessionLocal

SOURCES = [
    {"name": "free-proxy-list.net", "url": "https://free-proxy-list.net/", "parser": "free_proxy_list"},
    {"name": "sslproxies.org",      "url": "https://www.sslproxies.org/",  "parser": "free_proxy_list"},
]


async def _fetch_html(url: str) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.text()
    except Exception as e:
        logger.warning(f"Erro ao buscar {url}: {e}")
    return None


def _parse_free_proxy_list(html: str, source_name: str) -> list[ProxyCreate]:
    proxies = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return proxies
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue
        try:
            proxies.append(ProxyCreate(
                protocol="https" if cols[6].text.strip().lower() == "yes" else "http",
                host=cols[0].text.strip(),
                port=int(cols[1].text.strip()),
                country=cols[2].text.strip().lower(),
                anonymity=cols[4].text.strip().lower(),
                source=source_name,
            ))
        except Exception:
            continue
    return proxies


PARSERS = {"free_proxy_list": _parse_free_proxy_list}


async def fetch_public_proxies():
    logger.info("🌐 Buscando proxies em listas públicas...")
    total_added = 0
    for source in SOURCES:
        html = await _fetch_html(source["url"])
        if not html:
            continue
        parser_fn = PARSERS.get(source["parser"])
        if not parser_fn:
            continue
        proxies = parser_fn(html, source["name"])
        logger.info(f"   {source['name']}: {len(proxies)} encontrados")
        if proxies:
            async with AsyncSessionLocal() as db:
                added = await ProxyController.bulk_upsert(db, proxies)
                total_added += added
    logger.info(f"✅ Total adicionados: {total_added}")
