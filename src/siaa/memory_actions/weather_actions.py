import requests
from datetime import datetime, timedelta

class WeatherActions:
    def __init__(self, config):
        self.lat = config["location"]["latitude"]
        self.lon = config["location"]["longitude"]
        
        # Tabela expandida para evitar "None" em chuvas fortes
        self._wmo_codes = {
            0: "☀️ Limpo", 1: "🌤️ Quase limpo", 2: "⛅ Parcial. nublado", 3: "☁️ Nublado", 
            45: "🌫️ Neblina", 48: "🌫️ Névoa", 51: "🌦️ Garoa leve", 53: "🌦️ Garoa", 
            55: "🌦️ Garoa forte", 61: "🌧️ Chuva leve", 63: "🌧️ Chuva", 65: "🌧️ Chuva forte", 
            80: "🌦️ Pancadas", 81: "🌦️ Pancadas fortes", 82: "⛈️ Chuva torrencial", 
            95: "⛈️ Tempestade", 96: "⛈️ Tempestade c/ granizo", 99: "⛈️ Tempestade forte"
        }

    def _parse_time_intent(self, message: str) -> str:
        """Descobre qual dia o usuário quer saber."""
        msg = message.lower()
        if any(w in msg for w in ["amanhã", "amanha"]): return "amanha"
        if any(w in msg for w in ["fds", "fim de semana", "final de semana"]): return "fds"
        
        dias_semana = {
            "segunda": 0, "terça": 1, "terca": 1, "quarta": 2, 
            "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6
        }
        for dia, idx in dias_semana.items():
            if dia in msg: return f"dia_{idx}"
                
        return "hoje" # Fallback padrão

    def get_forecast(self, message: str):
        try:
            # Pede a previsão horária (hourly) E diária de 7 dias (daily)
            url = (f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
                   f"&current_weather=true&hourly=temperature_2m,weathercode"
                   f"&daily=weathercode,temperature_2m_max,temperature_2m_min"
                   f"&timezone=America%2FSao_Paulo")
            
            data = requests.get(url, timeout=10).json()
            curr = data["current_weather"]
            hourly = data["hourly"]
            daily = data["daily"]
            
            # Função auxiliar para extrair horário específico de um dia
            def get_h(date_str, h):
                target = f"{date_str}T{h:02d}:00"
                try:
                    idx = hourly["time"].index(target)
                    temp = hourly['temperature_2m'][idx]
                    cond = self._wmo_codes.get(hourly['weathercode'][idx], '—')
                    return f"{temp}°C, {cond}"
                except: return "—"

            intent = self._parse_time_intent(message)
            hoje_date = datetime.now()
            hoje_str = hoje_date.strftime("%Y-%m-%d")

            # ===================================================
            # 1. HOJE (Com inteligência de horário)
            # ===================================================
            if intent == "hoje":
                if hoje_date.hour >= 20: # Passou das 20h (8 da noite)
                    amanha_date = hoje_date + timedelta(days=1)
                    amanha_str = amanha_date.strftime("%Y-%m-%d")
                    
                    max_am = daily["temperature_2m_max"][1] # [1] é sempre amanhã
                    min_am = daily["temperature_2m_min"][1]
                    cond_am = self._wmo_codes.get(daily["weathercode"][1], '—')
                    
                    return (f"🌙 **Boa noite!** Agora faz {curr['temperature']}°C.\n\n"
                            f"📅 **Previsão para Amanhã:**\n"
                            f"{cond_am} | 🌡️ Máx {max_am}°C / Mín {min_am}°C\n"
                            f"🌅 Manhã (9h): {get_h(amanha_str, 9)}\n"
                            f"☀️ Tarde (15h): {get_h(amanha_str, 15)}")
                else:
                    max_hj = daily["temperature_2m_max"][0] # [0] é sempre hoje
                    min_hj = daily["temperature_2m_min"][0]
                    
                    return (f"🌡️ **Agora:** {curr['temperature']}°C ({self._wmo_codes.get(curr['weathercode'], '—')})\n"
                            f"📊 **Hoje:** Máx {max_hj}°C | Mín {min_hj}°C\n\n"
                            f"🌅 **Manhã:** {get_h(hoje_str, 9)}\n"
                            f"☀️ **Tarde:** {get_h(hoje_str, 15)}\n"
                            f"🌙 **Noite:** {get_h(hoje_str, 21)}")

            # ===================================================
            # 2. AMANHÃ
            # ===================================================
            elif intent == "amanha":
                amanha_date = hoje_date + timedelta(days=1)
                amanha_str = amanha_date.strftime("%Y-%m-%d")
                max_am = daily["temperature_2m_max"][1]
                min_am = daily["temperature_2m_min"][1]
                cond_am = self._wmo_codes.get(daily["weathercode"][1], '—')
                
                return (f"📅 **Amanhã ({amanha_date.strftime('%d/%m')}):** {cond_am}\n"
                        f"🌡️ Máx {max_am}°C | Mín {min_am}°C\n\n"
                        f"🌅 **Manhã (9h):** {get_h(amanha_str, 9)}\n"
                        f"☀️ **Tarde (15h):** {get_h(amanha_str, 15)}\n"
                        f"🌙 **Noite (21h):** {get_h(amanha_str, 21)}")

            # ===================================================
            # 3. FINAL DE SEMANA
            # ===================================================
            elif intent == "fds":
                res = "🏖️ **Previsão para o Final de Semana:**\n\n"
                found = False
                for i, d_str in enumerate(daily["time"]):
                    d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                    # 5 = Sábado, 6 = Domingo
                    if d_obj.weekday() in [5, 6]:
                        found = True
                        nome = "Sábado" if d_obj.weekday() == 5 else "Domingo"
                        max_t = daily["temperature_2m_max"][i]
                        min_t = daily["temperature_2m_min"][i]
                        cond = self._wmo_codes.get(daily["weathercode"][i], '—')
                        res += f"**{nome} ({d_obj.strftime('%d/%m')}):**\n{cond} | 🌡️ {max_t}°C / {min_t}°C\n\n"
                
                return res.strip() if found else "❌ O fim de semana ainda está longe para prever."

            # ===================================================
            # 4. DIA ESPECÍFICO (ex: "quarta")
            # ===================================================
            elif intent.startswith("dia_"):
                alvo_weekday = int(intent.split("_")[1])
                nomes_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                
                for i, d_str in enumerate(daily["time"]):
                    d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                    if d_obj.weekday() == alvo_weekday and i > 0: # > 0 ignora se o dia for hoje
                        max_t = daily["temperature_2m_max"][i]
                        min_t = daily["temperature_2m_min"][i]
                        cond = self._wmo_codes.get(daily["weathercode"][i], '—')
                        
                        return (f"📅 **{nomes_dias[alvo_weekday]} ({d_obj.strftime('%d/%m')}):**\n"
                                f"{cond} | 🌡️ Máx {max_t}°C / Mín {min_t}°C\n\n"
                                f"🌅 Manhã: {get_h(d_str, 9)}\n"
                                f"☀️ Tarde: {get_h(d_str, 15)}\n"
                                f"🌙 Noite: {get_h(d_str, 21)}")
                
                return f"❌ Não tenho a previsão para {nomes_dias[alvo_weekday]} ainda (limite de 7 dias)."

        except Exception as e:
            print(f"Erro no clima: {e}")
            return "❌ Desculpe, os servidores de clima estão fora do ar."