import re
from .base import BaseEntity
from memory_actions.finance_actions import FinanceActions
from user_interactions.messages import BotMessages

class FinanceEntity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = FinanceActions(memory.db_path)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            # 1. CONFIRMAÇÃO FINAL
            if intent == "CONFIRMATION" and self.mem.pending_action:
                if self.mem.pending_action.get("type") == "DELETE_CONFIRM":
                    if any(w in message.lower() for w in ["sim", "pode", "vrau", "confirmar", "bora", "ok"]):
                        ids = self.mem.pending_action["ids"]
                        self.actions.delete(ids)
                        self.mem.pending_action = None # Libera fluxo
                        return BotMessages.SUCCESS_REM, True
                    
                    self.mem.pending_action = None # Cancela e libera fluxo
                    return BotMessages.CANCEL_REM, True

            # 2. PROCESSAR SELEÇÃO
            if intent == "SELECTION_RESPONSE" and self.mem.pending_action:
                items = self.mem.pending_action["items"]
                ids_escolhidos = self.actions.parse_selection(message, items)
                
                if not ids_escolhidos:
                    self.mem.pending_action = None
                    return BotMessages.CANCEL_REM, True

                self.mem.pending_action = {
                    "domain": "FINANCE", "type": "DELETE_CONFIRM", "ids": ids_escolhidos
                }
                qtd = len(ids_escolhidos)
                return f"Você selecionou {qtd} item(ns). Tem certeza que deseja apagar? (Sim/Não)", False

            # 3. ADICIONAR
            if intent == "FINANCE_ADD":
                data = self.actions.extract_and_prepare(message, self.mem._llm)
                if data.get("amount", 0) <= 0: return BotMessages.VAL_REQUIRED, True
                
                if self.actions.insert(data):
                    return BotMessages.SUCCESS_FINANCE_ADD.format(**data), True
                return "Erro ao salvar no banco.", True

            # 4. REMOVER
            if intent == "FINANCE_REM":
                resultados = self.actions.search_multiple(message, ["desc", "keywords", "content"])
                is_plural = self.actions.check_plural(message)

                if not resultados:
                    ultimos = self.actions.list_all(limit=5)
                    if not ultimos: return BotMessages.SUCCESS_LIST_EMPTY, True
                    res = "Não encontrei isso. Quer apagar algo da sua lista? (Ex: 1, 2 ou todos)\n\n"
                    for i, item in enumerate(ultimos):
                        res += f"{i+1}️⃣ {item['desc']} (R$ {item['amount']:.2f})\n"
                    self.mem.pending_action = {"domain": "FINANCE", "type": "SELECTION", "items": ultimos}
                    return res, False

                if len(resultados) > 1 or is_plural:
                    res = "Encontrei estes registros. Quais quer apagar? (Ex: 1, 2 ou todos)\n\n"
                    for i, item in enumerate(resultados):
                        res += f"{i+1}️⃣ {item['desc']} (R$ {item['amount']:.2f})\n"
                    self.mem.pending_action = {"domain": "FINANCE", "type": "SELECTION", "items": resultados}
                    return res, False
                else:
                    target = resultados[0]
                    self.mem.pending_action = {"domain": "FINANCE", "type": "DELETE_CONFIRM", "ids": [target["id"]]}
                    return BotMessages.CONFIRM_FINANCE_REM.format(**target), False

            # 5. LISTAR
            if intent == "FINANCE_LIST":
                items = self.actions.list_all()
                if not items: return BotMessages.SUCCESS_LIST_EMPTY, True
                res = "💰 **Financeiro:**\n" + "\n".join([f"• {i['desc']} (R$ {i['amount']:.2f})" for i in items])
                return res, True

            return BotMessages.ERROR_GENERIC, False

        except Exception as e:
            print(f"❌ Erro em FinanceEntity: {e}")
            self.mem.pending_action = None # GARANTE O RESET DO FLUXO
            return "Tive um problema técnico no financeiro e reiniciei meu estado.", True