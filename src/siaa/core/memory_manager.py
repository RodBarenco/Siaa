import os
import json
import re
import requests

from core.situational_context import get_situational_context

class MemoryManager:
    """
    Gerencia a infraestrutura de memória, configuração e comunicação com a IA (Ollama).
    """

    def __init__(self):
        # Definição de caminhos (Prioriza ambiente Docker)
        self.data_dir     = os.getenv("SIAA_DATA_DIR", "/siaa-data")
        self.contexts_dir = os.path.join(self.data_dir, "contexts")
        self.db_path      = os.path.join(self.data_dir, "siaa.db")
        self.config_path  = os.path.join(self.data_dir, "config.json")
        
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

    def _load_config(self) -> dict:
        """Carrega o config.json ou cria um padrão se não existir."""
        if not os.path.exists(self.config_path):
            default = {
                "bot_info": {"name": "Siaa", "user_name": "Usuário", "version": "1.0.0"},
                "ollama": {
                    "url": "http://siaa-ollama:11434", 
                    "model_main": "granite3.3:2b"
                },
                "memory_limits": {
                    "actual_context_chars": 500,
                    "broader_context_chars": 600,
                    "sql_search_limit": 3
                }
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2, ensure_ascii=False)
            return default

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_files(self):
        """Garante que os ficheiros de texto da memória existam."""
        for fname in self.layers.values():
            path = os.path.join(self.contexts_dir, fname)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f: f.write("")

    def get_context(self) -> str:
        """Lê as camadas de memória para injetar no prompt."""
        ctx = ""
        for key, fname in self.layers.items():
            path = os.path.join(self.contexts_dir, fname)
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            ctx += f"\n[{key.upper()}_MEMORY]\n{content}\n"
            except Exception as e:
                print(f"⚠️ Erro ao ler memória {key}: {e}")
        return ctx

    def _llm(self, prompt: str, fast: bool = False) -> str:
        """
        Envia o pedido ao Ollama. 
        Auto-corrige o endpoint para evitar o Erro 405.
        """
        # 1. Resolução do Modelo
        model = os.getenv(
            "OLLAMA_MODEL_FAST" if fast else "OLLAMA_MODEL_CHAT",
            self.config.get("ollama", {}).get("model_main", "granite3.3:2b")
        )
        
        # 2. Resolução da URL (Garante /api/generate)
        base_url = os.getenv("OLLAMA_URL", self.config.get("ollama", {}).get("url", "http://siaa-ollama:11434"))
        if not base_url.endswith("/api/generate"):
            url = f"{base_url.rstrip('/')}/api/generate"
        else:
            url = base_url

        # 3. Injeção de Contexto Situacional (Data/Hora)
        situational = get_situational_context()
        full_prompt = f"{situational}\n{prompt}"

        try:
            print(f"📡 [LLM CALL] URL: {url} | Modelo: {model}")
            
            r = requests.post(
                url,
                json={
                    "model":  model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "stop": ["\nUsuário:", f"\n{self.bot_name}:", "\nUser:"]
                    },
                },
                timeout=180, # Timeout estendido para nuvens mais lentas
            )
            r.raise_for_status()
            res = r.json().get("response", "")
            
            # Limpeza de tags de raciocínio (deepseek/granite think tags)
            res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
            return res

        except requests.exceptions.ConnectionError:
            print(f"❌ ERRO DE CONEXÃO: Não foi possível alcançar o Ollama em {url}")
            return "Estou com dificuldades em conectar ao meu servidor de inteligência."
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ ERRO HTTP {r.status_code}: {e}")
            return "Tive um erro de comunicação técnica (HTTP)."
            
        except Exception as e:
            print(f"❌ ERRO NO LLM: {type(e).__name__}: {e}")
            return "Estou processando informações..."

    def save_memory(self, intent: str, msg: str, reply: str):
        """Delega ao módulo chat a gravação da interação."""
        try:
            from modules.chat.actions import ChatActions
            ChatActions(self.db_path).save_interaction(
                intent, msg, reply, self._llm, self.config, self.contexts_dir
            )
        except Exception as e:
            print(f"⚠️ Falha ao salvar memória: {e}")

    def search_long_term(self, query: str):
        """Busca no histórico SQL."""
        try:
            from modules.chat.actions import ChatActions
            return ChatActions(self.db_path).search_memory(
                query, self.config["memory_limits"]["sql_search_limit"]
            )
        except Exception: return None

    def run_maintenance(self):
        """Atualiza a memória de longo prazo."""
        try:
            from modules.chat.actions import ChatActions
            ChatActions(self.db_path).update_broader(
                self._llm, self.config, self.contexts_dir
            )
        except Exception as e:
            print(f"⚠️ Falha na manutenção de memória: {e}")