from datetime import datetime, timedelta

from framework.base_cron import BaseCron
from modules.agenda.actions import AgendaActions


class AgendaCron(BaseCron):
    """
    Verifica compromissos nas próximas 2 horas e envia alerta via Telegram.
    Roda a cada 30 minutos.
    """

    def get_schedule(self) -> dict:
        return {"trigger": "interval", "minutes": 30}

    async def run(self, chat_id: str):
        if not self.bot_send:
            return

        actions = AgendaActions(self.mem.db_path)
        items   = actions.list_all(limit=20)

        now      = datetime.now()
        alertas  = []

        for item in items:
            try:
                # Tenta parsear data/hora do compromisso
                dt_str = f"{item.get('date', '')} {item.get('time', '00:00')}"
                dt     = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                delta  = (dt - now).total_seconds() / 60  # em minutos

                # Alerta se estiver entre 5 e 120 minutos
                if 5 <= delta <= 120:
                    alertas.append(
                        f"⏰ *{item['title']}* em {int(delta)} min ({item['time']})"
                    )
            except Exception:
                continue

        if alertas:
            msg = "📅 *Lembretes próximos:*\n" + "\n".join(alertas)
            await self.bot_send(chat_id=chat_id, text=msg, parse_mode="Markdown")
