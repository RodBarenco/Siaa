from core.intent_handler import IntentHandler
from entities.agenda import AgendaEntity
from entities.finance import FinanceEntity
from entities.weather import WeatherEntity
from entities.memory_search import MemorySearchEntity
from entities.chat import ChatEntity

class CynbotAgent:
    def __init__(self, memory):
        self.mem = memory
        self.handler = IntentHandler(memory)
        self.entities = {
            "AGENDA": AgendaEntity(memory),
            "FINANCE": FinanceEntity(memory),
            "WEATHER": WeatherEntity(memory),
            "MEMORY_SEARCH": MemorySearchEntity(memory),
            "CHAT": ChatEntity(memory),
        }

    def process(self, message: str, history: str) -> tuple:
        """Coordena intenção e execução com proteção contra travamentos."""
        try:
            intent = self.get_intent(message, history)
            reply, close = self.execute(intent, message, history)
            return intent, reply, close
        except Exception as e:
            print(f"🔥 Erro Crítico no Agente: {e}")
            self.mem.pending_action = None # Reseta para não travar o bot
            return "ERROR", "Tive um problema técnico, mas já resetei meu sistema. Pode repetir?", True

    def get_intent(self, message: str, history: str) -> str:
        if self.mem.pending_action:
            # Se tem opções de dúvida do SVM
            if "options" in self.mem.pending_action:
                return "DECISION_RESPONSE"
            
            # Se o bot enviou uma lista e espera números (ou "todos")
            if self.mem.pending_action.get("type") == "SELECTION":
                return "SELECTION_RESPONSE"
            
            # Confirmação Simples ou Confirmação Final de Deleção
            return "CONFIRMATION"

        result = self.handler.classify(message)
        if result.startswith("DUVIDA|"):
            parts = result.split("|")
            self.mem.pending_action = {"domain": "DECISION", "options": [parts[1], parts[2]], "original_msg": message}
            return "DECISION_REQUIRED"
            
        return result

    def execute(self, intent: str, message: str, history: str) -> tuple:
        # Gerenciamento de Dúvidas do SVM
        if intent == "DECISION_REQUIRED":
            opts = self.mem.pending_action["options"]
            return f"Fiquei na dúvida... 🤔\n1️⃣ {opts[0]}\n2️⃣ {opts[1]}", False

        if intent == "DECISION_RESPONSE":
            opts = self.mem.pending_action["options"]
            original_msg = self.mem.pending_action["original_msg"]
            self.mem.pending_action = None 
            selected = opts[0] if "1" in message else (opts[1] if "2" in message else None)
            return self.execute(selected, original_msg, history) if selected else ("Cancelado.", True)

        # Roteamento de Estados Pendentes (Confirmação ou Seleção)
        if intent in ["CONFIRMATION", "SELECTION_RESPONSE"]:
            domain = self.mem.pending_action["domain"]
            # REPASSA A INTENÇÃO REAL (SELECTION_RESPONSE ou CONFIRMATION)
            return self.entities[domain].run(message, intent, history)

        # Fluxo Normal
        prefix = intent.split('_')[0]
        entity = self.entities.get(prefix, self.entities["CHAT"])
        return entity.run(message, intent, history)