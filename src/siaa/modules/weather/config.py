MODULE_NAME = "weather"

INTENTS = ["WEATHER"]

INTENT_DESCRIPTIONS = {
    "WEATHER": "Consulta de previsão do tempo, clima, chuva ou temperatura",
}

HAS_CRON = True   # cron de previsão matinal
HAS_WEB  = True   # consome open-meteo API
