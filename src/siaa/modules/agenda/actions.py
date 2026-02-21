import re
from datetime import datetime

from framework.base_actions import BaseActions
from framework.shared_utils import tokenize


class AgendaActions(BaseActions):
    def __init__(self, db_path: str):
        schema = (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "date TEXT, time TEXT, title TEXT, keywords TEXT, content TEXT"
        )
        super().__init__(db_path, "agenda", schema)

    def extract_and_prepare(self, message: str, llm_func) -> dict:
        try:
            prompt = (
                f"Extraia os dados do compromisso da mensagem abaixo.\n"
                f"Responda SOMENTE neste formato (sem explicações):\n"
                f"EVENTO: (nome do compromisso)\n"
                f"DATA: (DD/MM/AAAA ou 'HOJE')\n\n"
                f"Mensagem: '{message}'"
            )
            res = llm_func(prompt, fast=True)

            e_match = re.search(r"EVENTO:\s*(.*)", res)
            d_match = re.search(r"DATA:\s*([\d/]+|HOJE)", res, re.IGNORECASE)

            raw_date   = d_match.group(1) if d_match else "HOJE"
            final_date = (
                datetime.now().strftime("%d/%m/%Y")
                if "HOJE" in raw_date.upper()
                else raw_date
            )
            title = e_match.group(1).strip() if e_match else message[:40]

            return {
                "date":     final_date,
                "time":     datetime.now().strftime("%H:%M"),
                "title":    title,
                "keywords": ",".join(tokenize(title)),
                "content":  message,
            }
        except Exception as e:
            print(f"❌ AgendaActions.extract_and_prepare: {e}")
            return {
                "date":    datetime.now().strftime("%d/%m/%Y"),
                "time":    datetime.now().strftime("%H:%M"),
                "title":   message[:40],
                "keywords": "",
                "content": message,
            }
