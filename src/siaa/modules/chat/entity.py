from framework.base_entity import BaseEntity


class ChatEntity(BaseEntity):
    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            contexto = self.mem.get_context()
            prompt = (
                f"Abaixo está o histórico de uma conversa. "
                f"Responda APENAS com a sua próxima fala.\n"
                f"Não use prefixos como '{self.mem.bot_name}:' ou '{self.mem.user_name}:'.\n\n"
                f"[CONTEXTO SOBRE VOCÊ]\n{contexto}\n\n"
                f"[HISTÓRICO]\n{history[-300:]}\n\n"
                f"Mensagem atual do usuário: {message}\n"
                f"Sua resposta direta:"
            )
            reply = self.mem._llm(prompt)

            # Remove prefixos que o modelo pode gerar mesmo com instrução
            for prefix in [
                f"{self.mem.user_name}:", "Usuário:", "User:",
                f"{self.mem.bot_name}:", "Bot:",
            ]:
                if reply.startswith(prefix):
                    reply = reply[len(prefix):].strip()

            return reply.strip() or "Pode repetir?", False

        except Exception as e:
            print(f"❌ ChatEntity: {e}")
            self.mem.pending_action = None
            return "Tive um problema ao pensar na resposta. Pode falar de novo?", True
