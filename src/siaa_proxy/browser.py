"""
Serviço de navegador serverless (Playwright).
Usado pelo Siaa para acessar sites via proxy.

Instale os browsers após instalar o pacote:
    playwright install chromium
"""
from typing import Optional
from loguru import logger
from app.config import settings


async def browse_url(
    url: str,
    proxy_url: Optional[str] = None,
    extract: str = "text",  # "text" | "html" | "screenshot"
    wait_for: Optional[str] = None,  # CSS selector para aguardar
) -> dict:
    """
    Acessa uma URL usando Playwright com proxy opcional.

    Args:
        url: URL a acessar
        proxy_url: URL do proxy ex: "http://host:port"
        extract: o que extrair da página
        wait_for: seletor CSS para aguardar antes de extrair

    Returns:
        dict com { success, url, content, error }
    """
    try:
        from playwright.async_api import async_playwright

        proxy_config = None
        if proxy_url:
            proxy_config = {"server": proxy_url}

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=settings.BROWSER_HEADLESS,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            context = await browser.new_context(
                proxy=proxy_config,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )

            page = await context.new_page()
            page.set_default_timeout(settings.BROWSER_TIMEOUT_MS)

            await page.goto(url, wait_until="domcontentloaded")

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=settings.BROWSER_TIMEOUT_MS)

            content = None
            if extract == "text":
                content = await page.inner_text("body")
            elif extract == "html":
                content = await page.content()
            elif extract == "screenshot":
                content = await page.screenshot(type="png", full_page=True)
                content = content.hex()  # bytes -> hex string para serialização

            await browser.close()

            return {
                "success": True,
                "url": page.url,  # URL final (após redirects)
                "content": content,
                "error": None,
            }

    except Exception as e:
        logger.error(f"Erro no browser para {url}: {e}")
        return {
            "success": False,
            "url": url,
            "content": None,
            "error": str(e),
        }
