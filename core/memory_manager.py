import os, json, requests, re

class MemoryManager:
    def __init__(self, folder="contexts"):
        self.folder = folder
        os.makedirs(self.folder, exist_ok=True)
        self.db_path = os.path.join(self.folder, "cynbot_data.db")
        self.config_path = "config.json"
        self.pending_action = None 
        
        self.config = self._load_config()
        self.bot_name = self.config["bot_info"]["name"]
        self.user_name = self.config["bot_info"]["user_name"]
        
        self.layers = {
            "important": "important_context.txt", 
            "actual": "actual_context.txt", 
            "broader": "broader_context.txt"
        }
        self._init_files()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            default = {
                "bot_info": {"name": "Cynbot", "user_name": "Usuário"}, 
                "location": {"latitude": "-22.9035", "longitude": "-43.2096"}, 
                "memory_limits": {
                    "actual_context_chars": 500, 
                    "broader_context_chars": 400, 
                    "sql_search_limit": 3
                }
            }
            with open(self.config_path, "w", encoding="utf-8") as f: 
                json.dump(default, f, indent=2)
            return default
        with open(self.config_path, "r", encoding="utf-8") as f: 
            return json.load(f)

    def _init_files(self):
        for f in self.layers.values():
            path = os.path.join(self.folder, f)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as file: file.write("")

    def _llm(self, prompt, fast=False):
            model = os.getenv("OLLAMA_MODEL_FAST" if fast else "OLLAMA_MODEL_CHAT", "granite-2b:latest")
            url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
            try:
                r = requests.post(url, json={
                    "model": model, "prompt": prompt, "stream": False,
                    "options": {
                        "temperature": 0.2, 
                        "stop": ["\nUsuário:", "\nUsuario:", f"\n{self.bot_name}:", "\nUser:", "[HISTÓRICO]"] 
                    }
                }, timeout=90)
                res = r.json().get("response", "")
                res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
                return res
            except: 
                return "Estou processando informações..."

    def get_context(self):
        ctx = ""
        for key, fname in self.layers.items():
            path = os.path.join(self.folder, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content: 
                    ctx += f"\n[{key.upper()}_MEMORY]\n{content}\n"
        return ctx

    def save_memory(self, intent, msg, reply):
        from memory_actions.chat_actions import ChatActions
        actions = ChatActions(self.db_path)
        actions.save_interaction(intent, msg, reply, self._llm, self.config, self.folder)

    def search_long_term(self, query):
        from memory_actions.chat_actions import ChatActions
        actions = ChatActions(self.db_path)
        return actions.search_memory(query, self.config["memory_limits"]["sql_search_limit"])
        
    def run_maintenance(self):
        from memory_actions.chat_actions import ChatActions
        actions = ChatActions(self.db_path)
        actions.update_broader(self._llm, self.config, self.folder)