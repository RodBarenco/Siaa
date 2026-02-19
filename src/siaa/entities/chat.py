from .base import BaseEntity

class ChatEntity(BaseEntity):
    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            contexto = self.mem.get_context()
            prompt = (
                f"Abaixo está o histórico de uma conversa. Responda APENAS com a sua próxima fala.\n"
                f"Não use prefixos como '{self.mem.bot_name}:' ou '{self.mem.user_name}:'.\n\n"
                f"[CONTEXTO SOBRE VOCÊ]\n{contexto}\n\n"
                f"[HISTÓRICO]\n{history[-300:]}\n\n"
                f"Mensagem atual do usuário: {message}\n"
                f"Sua resposta direta:"
            )
            reply = self.mem._llm(prompt)
            
            # Limpeza bruta baseada nos nomes do seu config.json
            prefixes = [f"{self.mem.user_name}:", "Usuário:", "User:", f"{self.mem.bot_name}:", "Bot:", "Cynbot:"]
            for p in prefixes:
                if p in reply:
                    reply = reply.split(p)[-1] if p in [f"{self.mem.bot_name}:", "Bot:"] else reply.split(p)[0]
            
            return reply.strip(), False
        except Exception as e:
            self.mem.pending_action = None
            return "Tive um problema ao pensar na resposta. Pode falar de novo?", True