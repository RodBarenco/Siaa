import re
from datetime import datetime

from framework.base_actions import BaseActions
from framework.shared_utils import tokenize


class FinanceActions(BaseActions):
    def __init__(self, db_path: str):
        schema = (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "date TEXT, time TEXT, amount REAL, "
            "desc TEXT, keywords TEXT, content TEXT"
        )
        super().__init__(db_path, "finance", schema)

    def extract_and_prepare(self, message: str, llm_func) -> dict:
        try:
            prompt = (
                f"Analise a mensagem e extraia os dados financeiros.\n"
                f"Responda SOMENTE neste formato (sem explicações):\n"
                f"VALOR: (apenas número, ponto para decimal)\n"
                f"TITULO: (máximo 4 palavras)\n"
                f"DATA: (DD/MM/AAAA ou 'HOJE')\n\n"
                f"Mensagem: '{message}'"
            )
            res = llm_func(prompt, fast=True)

            v_match = re.search(r"VALOR:\s*([\d.,]+)", res)
            t_match = re.search(r"TITULO:\s*(.*)", res)
            d_match = re.search(r"DATA:\s*([\d/]+|HOJE)", res, re.IGNORECASE)

            amount_str = v_match.group(1).replace(",", ".") if v_match else "0"
            amount     = float(re.sub(r"[^\d.]", "", amount_str))

            raw_date   = d_match.group(1) if d_match else "HOJE"
            final_date = (
                datetime.now().strftime("%d/%m/%Y")
                if "HOJE" in raw_date.upper()
                else raw_date
            )
            desc = t_match.group(1).strip() if t_match else message[:30]

            return {
                "date":     final_date,
                "time":     datetime.now().strftime("%H:%M"),
                "amount":   amount,
                "desc":     desc,
                "keywords": ",".join(tokenize(desc)),
                "content":  message,
            }
        except Exception as e:
            print(f"❌ FinanceActions.extract_and_prepare: {e}")
            return {
                "date": datetime.now().strftime("%d/%m/%Y"),
                "time": datetime.now().strftime("%H:%M"),
                "amount": 0,
                "desc": message[:30],
                "keywords": "",
                "content": message,
            }

    def get_total(self, period: str = "month") -> float:
        """Soma todos os gastos do período (today / week / month)."""
        import sqlite3
        from datetime import timedelta

        now = datetime.now()
        if period == "today":
            cutoff = now.strftime("%d/%m/%Y")
            query  = "SELECT SUM(amount) FROM finance WHERE date = ?"
            params = (cutoff,)
        elif period == "week":
            cutoff = (now - timedelta(days=7)).strftime("%d/%m/%Y")
            query  = "SELECT SUM(amount) FROM finance WHERE date >= ?"
            params = (cutoff,)
        else:  # month — filtra por mês/ano
            month_str = now.strftime("%m/%Y")
            query  = "SELECT SUM(amount) FROM finance WHERE date LIKE ?"
            params = (f"%/{month_str}",)

        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(query, params).fetchone()
            return result[0] or 0.0
        except Exception as e:
            print(f"❌ FinanceActions.get_total: {e}")
            return 0.0
