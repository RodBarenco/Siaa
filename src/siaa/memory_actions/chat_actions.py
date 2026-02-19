import os
import sqlite3
from datetime import datetime

from .base_actions import BaseActions


class ChatActions(BaseActions):
    def __init__(self, db_path):
        schema = (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "date TEXT, time TEXT, intent TEXT, content TEXT"
        )
        super().__init__(db_path, "long_term", schema)

    # ------------------------------------------------------------------
    # Salva interação e atualiza actual_context.txt
    # contexts_dir: caminho completo da pasta de contextos
    # ------------------------------------------------------------------

    def save_interaction(self, intent, msg, reply, llm_func, config, contexts_dir):
        # 1. Log bruto no SQL
        self.insert({
            "date":    datetime.now().strftime("%Y-%m-%d"),
            "time":    datetime.now().strftime("%H:%M"),
            "intent":  intent,
            "content": f"U: {msg} | B: {reply}",
        })

        # 2. Filtro de relevância — ignora respostas automáticas de erro
        if any(w in reply.lower() for w in ["cancelado", "não encontrei", "erro", "repetir"]):
            return

        path  = os.path.join(contexts_dir, "actual_context.txt")
        limit = config["memory_limits"]["actual_context_chars"]

        # 3. Lê conteúdo acumulado
        current = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                current = f.read().strip()

        # 4. Extrai fato principal
        day        = datetime.now().strftime("%d/%m")
        fact_prompt = (
            f"Resuma o fato mais importante (clima, compromissos, preferências) "
            f"desta conversa em 1 frase curta começando com [{day}]: "
            f"U:{msg} B:{reply}"
        )
        new_fact = llm_func(fact_prompt, fast=True).strip()

        # 5. Acumula e compacta se necessário
        updated = f"{current}\n{new_fact}".strip()
        if len(updated) > limit:
            compact_prompt = (
                f"Condense estas memórias mantendo datas e fatos essenciais "
                f"para caber em {limit} caracteres:\n{updated}"
            )
            updated = llm_func(compact_prompt, fast=True)[:limit]

        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)

    # ------------------------------------------------------------------
    # Consolida broader_context.txt a partir do histórico SQL
    # ------------------------------------------------------------------

    def update_broader(self, llm_func, config, contexts_dir):
        limit = config["memory_limits"]["broader_context_chars"]
        items = self.list_all(limit=50)
        if not items:
            return

        raw_text = " ".join([i["content"] for i in items])
        prompt   = (
            f"Com base no histórico abaixo, crie uma lista de fatos conhecidos "
            f"sobre o usuário em tópicos curtos (max {limit} chars):\n{raw_text}"
        )
        topics = llm_func(prompt, fast=True)

        with open(os.path.join(contexts_dir, "broader_context.txt"), "w", encoding="utf-8") as f:
            f.write(topics[:limit])

    # ------------------------------------------------------------------
    # Busca no histórico SQL
    # ------------------------------------------------------------------

    def search_memory(self, query: str, limit: int):
        with sqlite3.connect(self.db_path) as c:
            rows = c.execute(
                "SELECT content FROM long_term "
                "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return "\n".join([r[0] for r in rows]) if rows else None