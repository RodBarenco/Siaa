from .base import BaseEntity
from memory_actions.weather_actions import WeatherActions

class WeatherEntity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = WeatherActions(memory.config)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        print(f"🌍 Consultando Clima: LAT {self.actions.lat} | LON {self.actions.lon}")
        
        # Agora passamos a mensagem para o Action analisar as palavras-chave
        reply = self.actions.get_forecast(message)
        return reply, True