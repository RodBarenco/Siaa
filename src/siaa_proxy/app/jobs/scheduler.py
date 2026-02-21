from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from app.config import settings
from app.services.fetcher import fetch_public_proxies
from app.services.validator import validate_all_proxies

scheduler = AsyncIOScheduler()


def setup_jobs():
    scheduler.add_job(
        fetch_public_proxies,
        trigger=IntervalTrigger(minutes=settings.CRON_FETCH_PROXIES_MINUTES),
        id="fetch_proxies", name="Buscar proxies públicos",
        replace_existing=True, misfire_grace_time=60,
    )
    scheduler.add_job(
        validate_all_proxies,
        trigger=IntervalTrigger(minutes=settings.CRON_VALIDATE_PROXIES_MINUTES),
        id="validate_proxies", name="Validar proxies ativos",
        replace_existing=True, misfire_grace_time=60,
    )
    scheduler.start()
    logger.info(
        f"⏰ Jobs agendados:\n"
        f"   • fetch_proxies    → a cada {settings.CRON_FETCH_PROXIES_MINUTES}min\n"
        f"   • validate_proxies → a cada {settings.CRON_VALIDATE_PROXIES_MINUTES}min"
    )
