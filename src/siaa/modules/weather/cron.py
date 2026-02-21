from framework.base_cron import BaseCron
from modules.weather.web import WeatherWeb


class WeatherCron(BaseCron):
    """
    Envia previsão do tempo toda manhã às 7h.
    """

    def get_schedule(self) -> dict:
        return {"trigger": "cron", "hour": 7, "minute": 0}

    async def run(self, chat_id: str):
        if not self.bot_send:
            return

        web    = WeatherWeb(self.mem.config)
        report = web.format_forecast("hoje")
        msg    = f"☀️ *Bom dia! Previsão do tempo:*\n\n{report}"

        await self.bot_send(chat_id=chat_id, text=msg, parse_mode="Markdown")
