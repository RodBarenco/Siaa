import sqlite3
import re
from .shared_utils import tokenize, is_plural

class BaseActions:
    def __init__(self, db_path, table_name, schema):
        self.db_path = db_path
        self.table = table_name
        try:
            self._ensure_table(schema)
        except Exception as e:
            print(f"❌ Erro ao criar tabela {table_name}: {e}")

    def _ensure_table(self, schema):
        with sqlite3.connect(self.db_path) as c:
            c.execute(f"CREATE TABLE IF NOT EXISTS {self.table} ({schema})")
            c.commit()

    def insert(self, data: dict) -> bool:
        """Insere dados dinamicamente no banco."""
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            values = tuple(data.values())
            query = f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders})"
            with sqlite3.connect(self.db_path) as c:
                c.execute(query, values)
                c.commit()
            return True
        except Exception as e:
            print(f"❌ Erro ao inserir em {self.table}: {e}")
            return False

    def delete(self, ids) -> bool:
        """Deleta registros por ID ou lista de IDs."""
        try:
            if not ids: return False
            with sqlite3.connect(self.db_path) as c:
                if isinstance(ids, (list, tuple)):
                    placeholders = ', '.join(['?'] * len(ids))
                    c.execute(f"DELETE FROM {self.table} WHERE id IN ({placeholders})", ids)
                else:
                    c.execute(f"DELETE FROM {self.table} WHERE id=?", (ids,))
                c.commit()
                return True
        except Exception as e:
            print(f"❌ Erro ao deletar em {self.table}: {e}")
            return False

    def list_all(self, order_by="id DESC", limit=10):
        try:
            query = f"SELECT * FROM {self.table} ORDER BY {order_by} LIMIT {limit}"
            with sqlite3.connect(self.db_path) as c:
                c.row_factory = sqlite3.Row
                return [dict(row) for row in c.execute(query).fetchall()]
        except Exception as e:
            print(f"❌ Erro ao listar {self.table}: {e}")
            return []

    def search_multiple(self, message, search_cols=["content"], limit=5):
        try:
            tokens = tokenize(message)
            if not tokens: return []
            
            with sqlite3.connect(self.db_path) as c:
                c.row_factory = sqlite3.Row
                rows = c.execute(f"SELECT * FROM {self.table}").fetchall()

            scored = []
            for row in rows:
                record = dict(row)
                score = 0
                text_to_scan = " ".join([str(record.get(col, "")).lower() for col in search_cols])
                for t in tokens:
                    if t in text_to_scan: score += 1
                if score > 0: scored.append((score, record))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored[:limit]]
        except Exception as e:
            print(f"❌ Erro na busca em {self.table}: {e}")
            return []

    def parse_selection(self, message: str, items: list) -> list:
        try:
            msg = message.lower()
            if any(w in msg for w in ["cancel", "nã", "nao", "nenhum", "esquece"]): return []
            
            if any(w in msg for w in ["todo", "tudo", "todos"]):
                nums = list(range(1, len(items) + 1))
            else:
                nums = [int(n) for n in re.findall(r'\d+', message)]

            ids = []
            for n in nums:
                idx = n - 1
                if 0 <= idx < len(items):
                    ids.append(items[idx]["id"])
            return ids
        except:
            return []

    def check_plural(self, message: str) -> bool:
        try: return is_plural(message)
        except: return False