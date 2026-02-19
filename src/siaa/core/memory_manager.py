import os
import json
import requests
import re


class MemoryManager:
    def __init__(self):
        # -----------------------------------------------------------
        # Paths vêm de variáveis de ambiente — definidas no Docker
        # ou no .env local para desenvolvimento.
        #
        # Estrutura do volume mapeado (volumes/siaa-data → /siaa-data):
        #
        #   volumes/siaa-data/
        #     config.json
        #     siaa.db
        #     intent_dataset.json      ← usado pelo train_svm.py
        #     contexts/
        #       important_context.txt
        #       actual_context.txt
        #       broader_context.txt
        # -----------------------------------------------------------
        self.data_dir     = os.getenv("SIAA_DATA_DIR", "volumes/siaa-data")
        self.contexts_dir = os.path.join(self.data_dir, "contexts")
        self.db_path      = os.path.join(self.data_dir, "siaa.db")
        self.config_path  = os.path.join(self.data_dir, "config.json")
        self.dataset_path = os.path.join(self.data_dir, "intent_dataset.json")

        os.makedirs(self.contexts_dir, exist_ok=True)

        self.pending_action = None

        self.config    = self._load_config()
        self.bot_name  = self.config["bot_info"]["name"]
        self.user_name = self.config["bot_info"]["user_name"]

        self.layers = {
            "important": "important_context.txt",
            "actual":    "actual_context.txt",
            "broader":   "broader_context.txt",
        }
        self._init_files()

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            default = {
                "bot_info": {
                    "name":      "Siaa",
                    "user_name": "Usuário",
                    "version":   "0.1.0",
                },
                "location": {
                    "latitude":  "-22.9035",
                    "longitude": "-43.2096",
                },
                "memory_limits": {
                    "actual_context_chars":         500,
                    "broader_context_chars":         600,
                    "maintenance_frequency_days":     15,
                    "sql_search_limit":                3,
                },
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2, ensure_ascii=False)
            return default

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Arquivos de contexto
    # ------------------------------------------------------------------

    def _init_files(self):
        for fname in self.layers.values():
            path = os.path.join(self.contexts_dir, fname)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")

    def get_context(self) -> str:
        ctx = ""
        for key, fname in self.layers.items():
            path = os.path.join(self.contexts_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                ctx += f"\n[{key.upper()}_MEMORY]\n{content}\n"
        return ctx

    # ------------------------------------------------------------------
    # LLM (Ollama)
    # ------------------------------------------------------------------

    def _llm(self, prompt: str, fast: bool = False) -> str:
        model = os.getenv(
            "OLLAMA_MODEL_FAST" if fast else "OLLAMA_MODEL_CHAT",
            "granite3.1-dense:2b",
        )
        url = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
        try:
            r = requests.post(
                url,
                json={
                    "model":  model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "stop": [
                            "\nUsuário:", "\nUsuario:",
                            f"\n{self.bot_name}:",
                            "\nUser:", "[HISTÓRICO]",
                        ],
                    },
                },
                timeout=90,
            )
            res = r.json().get("response", "")
            res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
            return res
        except Exception:
            return "Estou processando informações..."

    # ------------------------------------------------------------------
    # Memória
    # ------------------------------------------------------------------

    def save_memory(self, intent: str, msg: str, reply: str):
        from memory_actions.chat_actions import ChatActions
        ChatActions(self.db_path).save_interaction(
            intent, msg, reply, self._llm, self.config, self.contexts_dir
        )

    def search_long_term(self, query: str):
        from memory_actions.chat_actions import ChatActions
        return ChatActions(self.db_path).search_memory(
            query, self.config["memory_limits"]["sql_search_limit"]
        )

    def run_maintenance(self):
        from memory_actions.chat_actions import ChatActions
        ChatActions(self.db_path).update_broader(
            self._llm, self.config, self.contexts_dir
        )