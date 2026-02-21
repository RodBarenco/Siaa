from typing import Optional
from loguru import logger
from app.config import settings


async def browse_url(
    url: str,
    proxy_url: Optional[str] = None,
    extract: str = "text",
    wait_for: Optional[str] = None,
) -> dict:
    try:
        from playwright.async_api import async_playwright
        proxy_config = {"server": proxy_url} if proxy_url else None

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=settings.BROWSER_HEADLESS,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
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
                content = (await page.screenshot(type="png", full_page=True)).hex()

            final_url = page.url
            await browser.close()
            return {"success": True, "url": final_url, "content": content, "error": None}

    except Exception as e:
        logger.error(f"Erro no browser para {url}: {e}")
        return {"success": False, "url": url, "content": None, "error": str(e)}
