from datetime import datetime, timedelta
from framework.base_web import BaseWeb


_WMO_CODES = {
    0: "☀️ Limpo",         1: "🌤️ Quase limpo",      2: "⛅ Parcial. nublado",
    3: "☁️ Nublado",       45: "🌫️ Neblina",          48: "🌫️ Névoa",
    51: "🌦️ Garoa leve",  53: "🌦️ Garoa",            55: "🌦️ Garoa forte",
    61: "🌧️ Chuva leve",  63: "🌧️ Chuva",            65: "🌧️ Chuva forte",
    80: "🌦️ Pancadas",    81: "🌦️ Pancadas fortes",  82: "⛈️ Chuva torrencial",
    95: "⛈️ Tempestade",  96: "⛈️ Tempestade c/ granizo", 99: "⛈️ Tempestade forte",
}


class WeatherWeb(BaseWeb):
    def __init__(self, config: dict):
        self.lat = config["location"]["latitude"]
        self.lon = config["location"]["longitude"]

    def fetch(self, **kwargs) -> dict | None:
        url    = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude":   self.lat,
            "longitude":  self.lon,
            "current_weather": "true",
            "hourly":     "temperature_2m,weathercode",
            "daily":      "weathercode,temperature_2m_max,temperature_2m_min",
            "timezone":   "America/Sao_Paulo",
        }
        return self._get(url, params=params)

    # ------------------------------------------------------------------
    # Helpers de formatação
    # ------------------------------------------------------------------

    def code_to_str(self, code: int) -> str:
        return _WMO_CODES.get(code, "—")

    def parse_time_intent(self, message: str) -> str:
        msg = message.lower()
        if any(w in msg for w in ["amanhã", "amanha"]):
            return "amanha"
        if any(w in msg for w in ["fds", "fim de semana", "final de semana"]):
            return "fds"
        dias = {
            "segunda": 0, "terça": 1, "terca": 1, "quarta": 2,
            "quinta": 3,  "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6,
        }
        for dia, idx in dias.items():
            if dia in msg:
                return f"dia_{idx}"
        return "hoje"

    def format_forecast(self, message: str) -> str:
        """Monta a resposta formatada para o usuário."""
        data = self.fetch()
        if not data:
            return "❌ Não consegui acessar a previsão do tempo agora."

        hourly = data["hourly"]
        daily  = data["daily"]
        now    = datetime.now()
        intent = self.parse_time_intent(message)

        def get_hourly(date_str: str, hour: int) -> str:
            target = f"{date_str}T{hour:02d}:00"
            try:
                idx  = hourly["time"].index(target)
                temp = hourly["temperature_2m"][idx]
                cond = self.code_to_str(hourly["weathercode"][idx])
                return f"{temp}°C, {cond}"
            except Exception:
                return "—"

        hoje_str = now.strftime("%Y-%m-%d")

        if intent == "hoje":
            curr = data["current_weather"]
            h_idx = daily["time"].index(hoje_str) if hoje_str in daily["time"] else 0
            tmax  = daily["temperature_2m_max"][h_idx]
            tmin  = daily["temperature_2m_min"][h_idx]
            manha = get_hourly(hoje_str, 9)
            tarde = get_hourly(hoje_str, 15)
            noite = get_hourly(hoje_str, 20)
            return (
                f"🌍 *Previsão de hoje:*\n"
                f"Agora: {curr['temperature']}°C {self.code_to_str(int(curr['weathercode']))}\n"
                f"Máx/Mín: {tmax}°C / {tmin}°C\n"
                f"☀️ Manhã: {manha}\n"
                f"🕐 Tarde: {tarde}\n"
                f"🌙 Noite: {noite}"
            )

        if intent == "amanha":
            amanha_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            try:
                idx  = daily["time"].index(amanha_str)
                tmax = daily["temperature_2m_max"][idx]
                tmin = daily["temperature_2m_min"][idx]
                cond = self.code_to_str(daily["weathercode"][idx])
                manha = get_hourly(amanha_str, 9)
                tarde = get_hourly(amanha_str, 15)
            except Exception:
                return "❌ Não consegui dados de amanhã."
            return (
                f"🌍 *Previsão de amanhã:*\n"
                f"{cond} | {tmax}°C / {tmin}°C\n"
                f"☀️ Manhã: {manha}\n"
                f"🕐 Tarde: {tarde}"
            )

        if intent == "fds":
            lines = ["🌍 *Previsão do fim de semana:*"]
            for d in daily["time"]:
                dt = datetime.strptime(d, "%Y-%m-%d")
                if dt.weekday() in (5, 6) and dt >= now:
                    idx  = daily["time"].index(d)
                    dia  = "Sábado" if dt.weekday() == 5 else "Domingo"
                    cond = self.code_to_str(daily["weathercode"][idx])
                    tmax = daily["temperature_2m_max"][idx]
                    tmin = daily["temperature_2m_min"][idx]
                    lines.append(f"*{dia}*: {cond} | {tmax}°C / {tmin}°C")
            return "\n".join(lines) if len(lines) > 1 else "Sem dados do fim de semana."

        if intent.startswith("dia_"):
            target_wd = int(intent.split("_")[1])
            for d in daily["time"]:
                dt = datetime.strptime(d, "%Y-%m-%d")
                if dt.weekday() == target_wd and dt > now:
                    idx  = daily["time"].index(d)
                    cond = self.code_to_str(daily["weathercode"][idx])
                    tmax = daily["temperature_2m_max"][idx]
                    tmin = daily["temperature_2m_min"][idx]
                    dia  = dt.strftime("%d/%m")
                    return f"🌍 *Previsão {dia}:*\n{cond} | {tmax}°C / {tmin}°C"
            return "Sem dados para esse dia."

        return "❌ Não entendi qual dia você quer saber."
