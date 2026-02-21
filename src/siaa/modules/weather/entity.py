from framework.base_entity import BaseEntity
from modules.weather.web import WeatherWeb


class WeatherEntity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.web = WeatherWeb(memory.config)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        reply = self.web.format_forecast(message)
        return reply, True
