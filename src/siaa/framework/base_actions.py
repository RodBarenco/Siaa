import sqlite3
import re
from framework.shared_utils import tokenize, is_plural


class BaseActions:
    """
    Camada de persistência base para módulos com banco SQLite.
    Cada módulo em modules/<nome>/actions.py herda desta classe.
    """

    def __init__(self, db_path: str, table_name: str, schema: str):
        self.db_path = db_path
        self.table   = table_name
        try:
            self._ensure_table(schema)
        except Exception as e:
            print(f"❌ Erro ao criar tabela '{table_name}': {e}")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _ensure_table(self, schema: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {self.table} ({schema})")
            conn.commit()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def insert(self, data: dict) -> bool:
        try:
            columns      = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values       = tuple(data.values())
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ Erro ao inserir em '{self.table}': {e}")
            return False

    def delete(self, ids) -> bool:
        try:
            if not ids:
                return False
            with sqlite3.connect(self.db_path) as conn:
                if isinstance(ids, (list, tuple)):
                    placeholders = ", ".join(["?"] * len(ids))
                    conn.execute(
                        f"DELETE FROM {self.table} WHERE id IN ({placeholders})", ids
                    )
                else:
                    conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (ids,))
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ Erro ao deletar em '{self.table}': {e}")
            return False

    def list_all(self, limit: int = 10) -> list[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"SELECT * FROM {self.table} ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"❌ Erro ao listar '{self.table}': {e}")
            return []

    # ------------------------------------------------------------------
    # Busca por keywords
    # ------------------------------------------------------------------

    def search_multiple(self, query: str, fields: list[str]) -> list[dict]:
        """
        Busca registros que contenham tokens da query nos campos indicados.
        Retorna lista ordenada por relevância (mais matches primeiro).
        """
        tokens = tokenize(query)
        if not tokens:
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"SELECT * FROM {self.table} ORDER BY id DESC LIMIT 50"
                ).fetchall()

            scored = []
            for row in rows:
                row_dict = dict(row)
                score    = 0
                combined = " ".join(
                    str(row_dict.get(f, "")).lower() for f in fields
                )
                for token in tokens:
                    if token in combined:
                        score += 1
                if score > 0:
                    scored.append((score, row_dict))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [r for _, r in scored]

        except Exception as e:
            print(f"❌ Erro na busca em '{self.table}': {e}")
            return []

    # ------------------------------------------------------------------
    # Helpers de interação
    # ------------------------------------------------------------------

    def check_plural(self, message: str) -> bool:
        return is_plural(message)

    def parse_selection(self, message: str, items: list[dict]) -> list:
        """
        Interpreta a resposta do usuário quando apresentado uma lista numerada.
        Ex: '1 e 3' → [items[0]['id'], items[2]['id']]
            'todos'  → todos os ids
        """
        msg = message.lower().strip()

        if any(w in msg for w in ["todos", "tudo", "todas"]):
            return [i["id"] for i in items]

        nums = re.findall(r"\d+", msg)
        ids  = []
        for n in nums:
            idx = int(n) - 1
            if 0 <= idx < len(items):
                ids.append(items[idx]["id"])
        return ids
