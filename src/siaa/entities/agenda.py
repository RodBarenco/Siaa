from .base import BaseEntity
from memory_actions.agenda_actions import AgendaActions
from user_interactions.messages import BotMessages

class AgendaEntity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = AgendaActions(memory.db_path)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            # 1. CONFIRMAÇÃO FINAL
            if intent == "CONFIRMATION" and self.mem.pending_action:
                if self.mem.pending_action.get("type") == "DELETE_CONFIRM":
                    if any(w in message.lower() for w in ["sim", "pode", "vrau", "confirmar", "bora", "ok"]):
                        self.actions.delete(self.mem.pending_action["ids"])
                        self.mem.pending_action = None
                        return BotMessages.SUCCESS_REM, True
                    
                    self.mem.pending_action = None
                    return BotMessages.CANCEL_REM, True

            # 2. SELEÇÃO
            if intent == "SELECTION_RESPONSE" and self.mem.pending_action:
                ids = self.actions.parse_selection(message, self.mem.pending_action["items"])
                if not ids:
                    self.mem.pending_action = None
                    return BotMessages.CANCEL_REM, True

                self.mem.pending_action = {"domain": "AGENDA", "type": "DELETE_CONFIRM", "ids": ids}
                return f"Selecionei {len(ids)} item(ns). Confirmar deleção? (Sim/Não)", False

            # 3. ADICIONAR
            if intent == "AGENDA_ADD":
                data = self.actions.extract_and_prepare(message, self.mem._llm)
                if self.actions.insert(data):
                    return f"✅ Agendado: {data['title']} para {data['date']}", True
                return "Falha ao salvar compromisso.", True

            # 4. REMOVER
            if intent == "AGENDA_REM":
                resultados = self.actions.search_multiple(message, ["title", "content"])
                if not resultados:
                    proximos = self.actions.list_all(limit=5)
                    if not proximos: return "Agenda vazia.", True
                    res = "Não achei. Quer apagar um destes?\n\n"
                    for i, item in enumerate(proximos):
                        res += f"{i+1}️⃣ {item['date']}: {item['title']}\n"
                    self.mem.pending_action = {"domain": "AGENDA", "type": "SELECTION", "items": proximos}
                    return res, False

                if len(resultados) > 1 or self.actions.check_plural(message):
                    res = "Qual destes deseja remover?\n\n"
                    for i, item in enumerate(resultados):
                        res += f"{i+1}️⃣ {item['date']}: {item['title']}\n"
                    self.mem.pending_action = {"domain": "AGENDA", "type": "SELECTION", "items": resultados}
                    return res, False
                else:
                    target = resultados[0]
                    self.mem.pending_action = {"domain": "AGENDA", "type": "DELETE_CONFIRM", "ids": [target["id"]]}
                    return f"Achei: {target['title']}. Apagar? (Sim/Não)", False

            # 5. LISTAR
            if intent == "AGENDA_LIST":
                items = self.actions.list_all()
                if not items: return "Nenhum compromisso.", True
                res = "🗓️ **Agenda:**\n" + "\n".join([f"• {i['date']}: {i['title']}" for i in items])
                return res, True

            return BotMessages.ERROR_GENERIC, False

        except Exception as e:
            print(f"🔥 Erro em AgendaEntity: {e}")
            self.mem.pending_action = None # RESET SEGURO
            return "Erro técnico na agenda. Pode tentar de novo?", True