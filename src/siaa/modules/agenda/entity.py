from framework.base_entity import BaseEntity
from modules.agenda.actions import AgendaActions


class AgendaEntity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = AgendaActions(memory.db_path)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            # 1. CONFIRMAÇÃO DE REMOÇÃO
            if intent == "CONFIRMATION" and self.mem.pending_action:
                if self.mem.pending_action.get("type") == "DELETE_CONFIRM":
                    if any(w in message.lower() for w in ["sim", "pode", "vrau", "confirmar", "bora", "ok"]):
                        self.actions.delete(self.mem.pending_action["ids"])
                        self.mem.pending_action = None
                        return "🗑️ Compromisso removido com sucesso!", True
                    self.mem.pending_action = None
                    return "👍 Operação cancelada.", True

            # 2. SELEÇÃO DE ITEM PARA REMOVER
            if intent == "SELECTION_RESPONSE" and self.mem.pending_action:
                ids = self.actions.parse_selection(
                    message, self.mem.pending_action["items"]
                )
                if not ids:
                    self.mem.pending_action = None
                    return "👍 Operação cancelada.", True
                self.mem.pending_action = {
                    "domain": "AGENDA", "type": "DELETE_CONFIRM", "ids": ids
                }
                return f"Selecionei {len(ids)} item(ns). Confirmar remoção? (Sim/Não)", False

            # 3. ADICIONAR
            if intent == "AGENDA_ADD":
                data = self.actions.extract_and_prepare(message, self.mem._llm)
                if self.actions.insert(data):
                    return f"✅ Agendado: *{data['title']}* para {data['date']}", True
                return "❌ Falha ao salvar compromisso.", True

            # 4. REMOVER
            if intent == "AGENDA_REM":
                results = self.actions.search_multiple(message, ["title", "content"])
                if not results:
                    proximos = self.actions.list_all(limit=5)
                    if not proximos:
                        return "📭 Agenda vazia.", True
                    lista = "\n".join(
                        [f"{i+1}. {r['title']} ({r['date']})" for i, r in enumerate(proximos)]
                    )
                    self.mem.pending_action = {
                        "domain": "AGENDA", "type": "SELECTION", "items": proximos
                    }
                    return f"Não encontrei esse compromisso. Qual deseja remover?\n{lista}", False

                if len(results) == 1:
                    self.mem.pending_action = {
                        "domain": "AGENDA", "type": "DELETE_CONFIRM", "ids": [results[0]["id"]]
                    }
                    return (
                        f"❓ Encontrei: *{results[0]['title']}* ({results[0]['date']}).\n"
                        f"Confirmar remoção? (Sim/Não)"
                    ), False

                lista = "\n".join(
                    [f"{i+1}. {r['title']} ({r['date']})" for i, r in enumerate(results[:5])]
                )
                self.mem.pending_action = {
                    "domain": "AGENDA", "type": "SELECTION", "items": results[:5]
                }
                return f"Encontrei mais de um. Qual remover?\n{lista}", False

            # 5. LISTAR
            if intent == "AGENDA_LIST":
                items = self.actions.list_all(limit=10)
                if not items:
                    return "📭 Agenda vazia.", True
                lista = "\n".join(
                    [f"• {r['date']} — {r['title']}" for r in reversed(items)]
                )
                return f"📅 *Seus compromissos:*\n{lista}", True

            return "Desculpe, não entendi o que fazer com a agenda.", True

        except Exception as e:
            print(f"❌ AgendaEntity: {e}")
            self.mem.pending_action = None
            return "Tive um problema com a agenda. Pode repetir?", True
