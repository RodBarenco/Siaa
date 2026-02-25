import re
from datetime import datetime, timedelta

from framework.base_entity import BaseEntity
from modules.agenda.actions import AgendaActions


def _extract_date_from_message(message: str) -> str | None:
    """
    Tenta extrair uma data da mensagem.
    Suporta: 'hoje', 'amanhã', 'ontem', 'DD/MM', 'DD/MM/AAAA', 'dia DD'
    Retorna string no formato DD/MM/AAAA ou None.
    """
    msg = message.lower()
    now = datetime.now()

    if "hoje" in msg:
        return now.strftime("%d/%m/%Y")

    if "amanhã" in msg or "amanha" in msg:
        return (now + timedelta(days=1)).strftime("%d/%m/%Y")

    if "ontem" in msg:
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
                    hora_str = f" às {data['time']}" if data.get("time") else ""
                    return f"✅ Agendado: *{data['title']}* para {data['date']}{hora_str}", True
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
                target_date = _extract_date_from_message(message)

                # --- Consulta por data específica ---
                if target_date:
                    items = self.actions.list_by_date(target_date)

                    now = datetime.now()
                    if target_date == now.strftime("%d/%m/%Y"):
                        label = "Hoje"
                    elif target_date == (now + __import__("datetime").timedelta(days=1)).strftime("%d/%m/%Y"):
                        label = "Amanhã"
                    else:
                        label = target_date

                    if not items:
                        return f"📭 Nenhum compromisso em *{label}*.", True

                    lista = "\n".join(
                        [f"• {r['time']} — {r['title']}" for r in items]
                    )
                    return f"📅 *Agenda de {label}:*\n{lista}", True

                # --- Consulta geral (próximos compromissos) ---
                items = self.actions.list_all(limit=10)
                if not items:
                    return "📭 Agenda vazia.", True
                lista = "\n".join(
                    [f"• {r['date']} {r['time']} — {r['title']}" for r in reversed(items)]
                )
                return f"📅 *Seus compromissos:*\n{lista}", True

            return "Desculpe, não entendi o que fazer com a agenda.", True

        except Exception as e:
            print(f"❌ AgendaEntity: {e}")
            self.mem.pending_action = None
            return "Tive um problema com a agenda. Pode repetir?", True