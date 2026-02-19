class BaseEntity:
    def __init__(self, memory):
        self.mem = memory
        self.name = memory.bot_name
        self.user = memory.user_name

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        # Deve retornar (reply, close) -> SEMPRE 2 VALORES
        raise NotImplementedError