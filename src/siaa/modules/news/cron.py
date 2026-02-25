"""
modules/news/cron.py

Envia o digest de notícias do dia todo dia de manhã.

Config em: <SIAA_DATA_DIR>/contexts/cron-jobs/news.json
    {
      "enabled": true,
      "schedule": {"hour": 8, "minute": 0},
      "settings": {
        "locale": "pt-BR",
        "country": "BR",
        "max_items": 10
      }
    }
"""

from framework.base_cron import BaseCron
from modules.news.web import NewsWeb


class NewsCron(BaseCron):
    """
    Busca as principais notícias do dia e envia via Telegram.
    Roda uma vez por dia no horário configurado (padrão: 08:00).
    """

    def get_schedule(self) -> dict:
        schedule = self._cron_schedule()
        hour   = schedule.get("hour", 8)
        minute = schedule.get("minute", 0)
        return {"trigger": "cron", "hour": hour, "minute": minute}

    async def run(self, chat_id: str):
        if not self.bot_send:
            return

        if not self.is_enabled():
            print(f"⏸️  [NewsCron] Desabilitado na config — pulando.")
            return

        print(f"📰 [NewsCron] Buscando notícias para chat_id={chat_id}")

        settings = self._cron_config().get("settings", {})
        web      = NewsWeb(settings)
        items    = web.fetch()
        msg      = web.format_digest(items or [])

        await self.bot_send(chat_id=chat_id, text=msg, parse_mode="MarkdownV2")
        print(f"✅ [NewsCron] Digest enviado — {len(items) if items else 0} notícias")
