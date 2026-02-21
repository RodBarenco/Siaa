from abc import ABC, abstractmethod


class BaseCron(ABC):
    """
    Base para tarefas agendadas (cron jobs) de módulos.
    Cada módulo que precisar de jobs periódicos cria um cron.py
    com uma classe que herda desta.

    O module_loader registra automaticamente os crons ativos
    e o scheduler do app.py os executa.

    Exemplo de uso em modules/agenda/cron.py:
        class AgendaCron(BaseCron):
            def get_schedule(self) -> dict:
                return {"trigger": "interval", "minutes": 30}

            async def run(self, bot, chat_id):
                # verifica compromissos próximos e envia alerta
                ...
    """

    def __init__(self, memory, bot_send_func=None):
        self.mem      = memory
        self.bot_send = bot_send_func  # função async para enviar msg no Telegram

    @abstractmethod
    def get_schedule(self) -> dict:
        """
        Retorna configuração do APScheduler.
        Ex: {"trigger": "interval", "minutes": 30}
            {"trigger": "cron", "hour": 8, "minute": 0}
        """
        raise NotImplementedError

    @abstractmethod
    async def run(self, chat_id: str):
        """Lógica principal do job. Chamada pelo scheduler."""
        raise NotImplementedError
