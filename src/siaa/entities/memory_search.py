from .base import BaseEntity

class MemorySearchEntity(BaseEntity):
    def run(self, message: str, intent: str, history: str = "") -> tuple:
        # Busca no SQL
        results = self.mem.search_long_term(message)
        
        if not results:
            return "Vasculhei meus registros antigos, mas não encontrei detalhes sobre isso.", True
            
        prompt = (
            f"O usuário perguntou algo do passado. Encontrei estes registros no banco de dados:\n{results}\n"
            f"Responda ao usuário com base nisso: {message}"
        )
        reply = self.mem._llm(prompt)
        return reply, True