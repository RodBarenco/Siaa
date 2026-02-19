import os
from datetime import datetime
from .base_actions import BaseActions

class ChatActions(BaseActions):
    def __init__(self, db_path):
        schema = "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, intent TEXT, content TEXT"
        super().__init__(db_path, "long_term", schema)

    def save_interaction(self, intent, msg, reply, llm_func, config, folder):
        # 1. Log Bruto no SQL
        self.insert({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "intent": intent,
            "content": f"U: {msg} | B: {reply}"
        })

        # 2. Filtro de Relevância: Ignora respostas automáticas de erro/cancelamento
        if any(w in reply.lower() for w in ["cancelado", "não encontrei", "erro", "repetir"]):
            return

        path = os.path.join(folder, "actual_context.txt")
        limit = config["memory_limits"]["actual_context_chars"]
        
        # 3. Lê o conteúdo acumulado
        current_content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                current_content = f.read().strip()

        # 4. Extrai o fato principal da conversa
        day = datetime.now().strftime("%d/%m")
        fact_prompt = f"Resuma o fato mais importante (clima, compromissos, preferências) desta conversa em 1 frase curta começando com [{day}]: U:{msg} B:{reply}"
        new_fact = llm_func(fact_prompt, fast=True).strip()

        # 5. Acumula e compacta se necessário
        updated_context = f"{current_content}\n{new_fact}".strip()

        if len(updated_context) > limit:
            compact_prompt = f"Condense estas memórias mantendo datas e fatos essenciais para caber em {limit} caracteres:\n{updated_context}"
            updated_context = llm_func(compact_prompt, fast=True)[:limit]

        with open(path, "w", encoding="utf-8") as f:
            f.write(updated_context)

    def update_broader(self, llm_func, config, folder):
        limit = config["memory_limits"]["broader_context_chars"]
        items = self.list_all(limit=50)
        if not items: return
        
        raw_text = " ".join([i['content'] for i in items])
        prompt = f"Com base no histórico abaixo, crie uma lista de fatos conhecidos sobre o usuário em tópicos curtos (max {limit} chars):\n{raw_text}"
        topics = llm_func(prompt, fast=True)
        
        with open(os.path.join(folder, "broader_context.txt"), "w", encoding="utf-8") as f:
            f.write(topics[:limit])

    def search_memory(self, query, limit):
        import sqlite3
        with sqlite3.connect(self.db_path) as c:
            rows = c.execute("SELECT content FROM long_term WHERE content LIKE ? ORDER BY id DESC LIMIT ?", 
                             (f"%{query}%", limit)).fetchall()
            return "\n".join([r[0] for r in rows]) if rows else None