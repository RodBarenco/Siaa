import re
from datetime import datetime

from framework.base_entity import BaseEntity
from modules.finance.actions import FinanceActions


def _extract_date_from_message(message: str) -> str | None:
    """
    Tenta extrair uma data da mensagem.
    Suporta: 'hoje', 'ontem', 'DD/MM', 'DD/MM/AAAA', 'dia DD'
    Retorna string no formato DD/MM/AAAA ou None.
    """
    msg = message.lower()
    now = datetime.now()

    if "hoje" in msg:
        return now.strftime("%d/%m/%Y")

    if "ontem" in msg:
        from datetime import timedelta
        return (now - timedelta(days=1)).strftime("%d/%m/%Y")

    # DD/MM/AAAA
    m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", message)
    if m:
        return m.group(1)

    # DD/MM (assume ano atual)
    m = re.search(r"\b(\d{2}/\d{2})\b", message)
    if m:
        return f"{m.group(1)}/{now.year}"

    # "dia DD" (assume mês/ano atual)
    m = re.search(r"\bdia\s+(\d{1,2})\b", msg)
    if m:
        day = m.group(1).zfill(2)
        return f"{day}/{now.strftime('%m/%Y')}"

    return None


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
                target_date = _extract_date_from_message(message)

                # --- Consulta por data específica ---
                if target_date:
                    items = self.actions.list_by_date(target_date)
                    total = self.actions.get_total_by_date(target_date)

                    label = "Hoje" if target_date == datetime.now().strftime("%d/%m/%Y") else target_date

                    if not items:
                        return f"📭 Nenhum gasto registrado em *{label}*.", True

                    lista = "\n".join(
                        [f"• {r['time']} — {r['desc']}: R$ {r['amount']:.2f}"
                         for r in items]
                    )
                    return (
                        f"💸 *Gastos de {label}:*\n{lista}\n\n"
                        f"📊 Total do dia: R$ {total:.2f}"
                    ), True

                # --- Consulta geral (últimos lançamentos + total do mês) ---
                total_mes  = self.actions.get_total("month")
                total_hoje = self.actions.get_total("today")
                items      = self.actions.list_all(limit=8)

                if not items:
                    return "📭 Nenhum gasto registrado.", True

                lista = "\n".join(
                    [f"• {r['date']} — {r['desc']}: R$ {r['amount']:.2f}"
                     for r in reversed(items)]
                )
                total_listado = sum(r["amount"] for r in items)

                return (
                    f"💸 *Últimos {len(items)} lançamentos:*\n{lista}\n\n"
                    f"─────────────────\n"
                    f"💵 Soma desta lista: R$ {total_listado:.2f}\n"
                    f"📅 Total hoje: R$ {total_hoje:.2f}\n"
                    f"📊 Total no mês: R$ {total_mes:.2f}"
                ), True

            return "Desculpe, não entendi o que fazer com as finanças.", True

        except Exception as e:
            print(f"❌ FinanceEntity: {e}")
            self.mem.pending_action = None
            return "Tive um problema com as finanças. Pode repetir?", True