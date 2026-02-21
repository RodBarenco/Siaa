import time

from core.intent_handler import IntentHandler
from core.module_loader import load_entities


class CynbotAgent:
    def __init__(self, memory):
        self.mem = memory
        self.handler = IntentHandler(memory)
        self.entities = load_entities(memory)

        if self.entities:
            print(f"📦 Módulos carregados no Agente: {list(self.entities.keys())}")

    def process(self, message: str, history: str, set_status=None) -> tuple:
        """
        set_status: callable(str) opcional — atualiza o status no Telegram
                    em tempo real conforme o processamento avança.
                    Chamado de thread síncrona, thread-safe via run_coroutine_threadsafe.
        """
        def _status(text: str):
            if set_status:
                set_status(text)

        try:
            # "💬 Lendo mensagem..." já foi setado pelo app.py antes de chamar process.
            # Damos 0.5s pra ele ser visto antes de mudar.
            time.sleep(0.5)

            # Fase 1 — SVM classifica a intenção (ms)
            _status("🧠 Pensando...")
            time.sleep(0.8)  # mínimo visível antes do SVM retornar e ir pro próximo
            intent = self.handler.classify(message)

            # Fase 2 — executa o módulo (pode chamar LLM, API, etc.)
            _status("✍️ Escrevendo...")
            reply, close = self._execute(intent, message, history)

            return intent, reply, close

        except Exception as e:
            print(f"🔥 Erro Agente: {e}")
            self.mem.pending_action = None
            return ("ERROR", "Erro no processamento.", True)

    def _execute(self, intent: str, message: str, history: str) -> tuple:

        # ------------------------------------------------------------------
        # 1. DÚVIDA DO SVM
        # ------------------------------------------------------------------
        if intent.startswith("DUVIDA|"):
            parts = intent.split("|")
            opt1, opt2 = parts[1], parts[2]
            self.mem.pending_action = {
                "domain":       "DECISION",
                "options":      [opt1, opt2],
                "original_msg": message,
            }
            reply = (
                f"Fiquei na dúvida sobre o que você quis dizer 🤔\n\n"
                f"1 - {opt1}\n"
                f"2 - {opt2}\n\n"
                f"Responda 1 ou 2, ou outra coisa para cancelar."
            )
            return reply, False

        # ------------------------------------------------------------------
        # 2. RESPOSTA DO USUÁRIO À DÚVIDA
        # ------------------------------------------------------------------
        if (
            self.mem.pending_action
            and self.mem.pending_action.get("domain") == "DECISION"
        ):
            opts         = self.mem.pending_action["options"]
            original_msg = self.mem.pending_action["original_msg"]
            self.mem.pending_action = None

            stripped = message.strip()
            if stripped.startswith("1"):
                chosen_intent = opts[0]
            elif stripped.startswith("2"):
                chosen_intent = opts[1]
            else:
                return "Ok, cancelei. Pode repetir o que queria fazer!", True

            return self._execute(chosen_intent, original_msg, history)

        # ------------------------------------------------------------------
        # 3. ROTEAMENTO PARA O MÓDULO CORRETO
        # ------------------------------------------------------------------
        prefix = intent.split("_")[0].lower()

        entity = (
            self.entities.get(prefix)
            or self.entities.get(prefix.upper())
            or self.entities.get("chat")
            or self.entities.get("CHAT")
        )

        if not entity:
            return "Desculpe, módulo não encontrado no sistema.", True

        return entity.run(message, intent, history)