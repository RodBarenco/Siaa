from framework.base_entity import BaseEntity


class MemoryEntity(BaseEntity):
    def run(self, message: str, intent: str, history: str = "") -> tuple:
        results = self.mem.search_long_term(message)

        if not results:
            return (
                "Vasculhei meus registros antigos, mas não encontrei nada sobre isso.",
                True,
            )

        prompt = (
            f"O usuário quer saber algo do passado. "
            f"Encontrei estes registros:\n{results}\n\n"
            f"Responda de forma natural à pergunta: {message}"
        )
        reply = self.mem._llm(prompt)
        return reply, True
