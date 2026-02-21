from core.intent_handler import IntentHandler
from core.module_loader import load_entities

class CynbotAgent:
    def __init__(self, memory):
        self.mem = memory
        self.handler = IntentHandler(memory)
        self.entities = load_entities(memory)
        
        # Log para debug: vamos ver exatamente como os módulos foram carregados
        if self.entities:
            print(f"📦 Módulos carregados no Agente: {list(self.entities.keys())}")

    def process(self, message: str, history: str) -> tuple:
        try:
            intent = self.handler.classify(message)
            reply, close = self._execute(intent, message, history)
            return intent, reply, close
        except Exception as e:
            print(f"🔥 Erro Agente: {e}")
            return ("ERROR", "Erro no processamento.", True)

    def _execute(self, intent: str, message: str, history: str) -> tuple:
        # 1. Dúvidas do SVM
        if intent.startswith("DUVIDA|"):
            parts = intent.split("|")
            self.mem.pending_action = {"domain": "DECISION", "options": [parts[1], parts[2]], "original_msg": message}
            return f"Fiquei na dúvida... 🤔\n1️⃣ {parts[1]}\n2️⃣ {parts[2]}", False

        # 2. Roteamento Inteligente (A CORREÇÃO ESTÁ AQUI)
        # Se a intent é 'CHAT', prefix é 'chat'
        prefix = intent.split('_')[0].lower()
        
        # Tenta achar o módulo: 
        # 1. Pelo prefixo (chat)
        # 2. Pelo prefixo em maiúsculo (CHAT)
        # 3. Fallback forçado para o chat se nada funcionar
        entity = self.entities.get(prefix) or \
                 self.entities.get(prefix.upper()) or \
                 self.entities.get("chat") or \
                 self.entities.get("CHAT")

        if not entity:
            return "Desculpe, módulo não encontrado no sistema.", True

        return entity.run(message, intent, history)