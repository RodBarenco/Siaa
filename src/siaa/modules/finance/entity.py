from framework.base_entity import BaseEntity
from modules.finance.actions import FinanceActions


class FinanceEntity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = FinanceActions(memory.db_path)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            # 1. CONFIRMAÇÃO DE REMOÇÃO
            if intent == "CONFIRMATION" and self.mem.pending_action:
                if self.mem.pending_action.get("type") == "DELETE_CONFIRM":
                    if any(w in message.lower() for w in ["sim", "pode", "vrau", "confirmar", "bora", "ok"]):
                        self.actions.delete(self.mem.pending_action["ids"])
                        self.mem.pending_action = None
                        return "🗑️ Lançamento removido com sucesso!", True
                    self.mem.pending_action = None
                    return "👍 Operação cancelada.", True

            # 2. SELEÇÃO
            if intent == "SELECTION_RESPONSE" and self.mem.pending_action:
                ids = self.actions.parse_selection(
                    message, self.mem.pending_action["items"]
                )
                if not ids:
                    self.mem.pending_action = None
                    return "👍 Operação cancelada.", True
                self.mem.pending_action = {
                    "domain": "FINANCE", "type": "DELETE_CONFIRM", "ids": ids
                }
                return f"Selecionei {len(ids)} item(ns). Confirmar remoção? (Sim/Não)", False

            # 3. ADICIONAR
            if intent == "FINANCE_ADD":
                data = self.actions.extract_and_prepare(message, self.mem._llm)
                if data.get("amount", 0) <= 0:
                    return "❓ Não identifiquei o valor. Pode repetir com o valor?", True
                if self.actions.insert(data):
                    return (
                        f"💰 Salvo: *{data['desc']}* — R$ {data['amount']:.2f} "
                        f"em {data['date']}"
                    ), True
                return "❌ Erro ao salvar.", True

            # 4. REMOVER
            if intent == "FINANCE_REM":
                results = self.actions.search_multiple(
                    message, ["desc", "keywords", "content"]
                )
                if not results:
                    ultimos = self.actions.list_all(limit=5)
                    if not ultimos:
                        return "📭 Não há lançamentos.", True
                    lista = "\n".join(
                        [f"{i+1}. {r['desc']} — R$ {r['amount']:.2f} ({r['date']})"
                         for i, r in enumerate(ultimos)]
                    )
                    self.mem.pending_action = {
                        "domain": "FINANCE", "type": "SELECTION", "items": ultimos
                    }
                    return f"Não encontrei isso. Qual remover?\n{lista}", False

                if len(results) == 1:
                    self.mem.pending_action = {
                        "domain": "FINANCE", "type": "DELETE_CONFIRM",
                        "ids": [results[0]["id"]]
                    }
                    return (
                        f"❓ Encontrei: *{results[0]['desc']}* "
                        f"R$ {results[0]['amount']:.2f}. Remover? (Sim/Não)"
                    ), False

                lista = "\n".join(
                    [f"{i+1}. {r['desc']} — R$ {r['amount']:.2f} ({r['date']})"
                     for i, r in enumerate(results[:5])]
                )
                self.mem.pending_action = {
                    "domain": "FINANCE", "type": "SELECTION", "items": results[:5]
                }
                return f"Encontrei mais de um. Qual remover?\n{lista}", False

            # 5. LISTAR
            if intent == "FINANCE_LIST":
                total_mes = self.actions.get_total("month")
                items     = self.actions.list_all(limit=8)
                if not items:
                    return "📭 Nenhum gasto registrado.", True
                lista = "\n".join(
                    [f"• {r['date']} — {r['desc']}: R$ {r['amount']:.2f}"
                     for r in reversed(items)]
                )
                return (
                    f"💸 *Últimos gastos:*\n{lista}\n\n"
                    f"📊 Total no mês: R$ {total_mes:.2f}"
                ), True

            return "Desculpe, não entendi o que fazer com as finanças.", True

        except Exception as e:
            print(f"❌ FinanceEntity: {e}")
            self.mem.pending_action = None
            return "Tive um problema com as finanças. Pode repetir?", True
