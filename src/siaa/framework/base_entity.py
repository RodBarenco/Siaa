class BaseEntity:
    """
    Classe base para todas as entidades de módulos.
    Cada módulo em modules/<nome>/entity.py deve herdar desta classe
    e implementar o método run().
    """

    def __init__(self, memory):
        self.mem  = memory
        self.name = memory.bot_name
        self.user = memory.user_name

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        """
        Processa uma mensagem e retorna (reply: str, close_interaction: bool).
        close_interaction=True  → salva memória e fecha o turno
        close_interaction=False → mantém estado pendente (aguarda confirmação)
        """
        raise NotImplementedError(
            f"O módulo '{self.__class__.__name__}' deve implementar o método run()."
        )
