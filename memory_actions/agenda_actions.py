from .base_actions import BaseActions
from .shared_utils import tokenize
from datetime import datetime
import re

class AgendaActions(BaseActions):
    def __init__(self, db_path):
        schema = "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, title TEXT, keywords TEXT, content TEXT"
        super().__init__(db_path, "agenda", schema)

    def extract_and_prepare(self, message, llm_func):
        try:
            prompt = (
                f"Extraia os dados do compromisso: '{message}'. Use o formato:\n"
                f"EVENTO: (nome do compromisso)\n"
                f"DATA: (DD/MM/AAAA ou 'HOJE')\n"
                f"Resposta:"
            )
            res = llm_func(prompt, fast=True)
            
            e_match = re.search(r"EVENTO:\s*(.*)", res)
            d_match = re.search(r"DATA:\s*([\d/]+|HOJE)", res, re.IGNORECASE)

            extracted_date = d_match.group(1) if d_match else "HOJE"
            final_date = datetime.now().strftime("%d/%m/%Y") if "HOJE" in extracted_date.upper() else extracted_date
            title = e_match.group(1).strip() if e_match else message[:40]

            return {
                "date": final_date,
                "time": datetime.now().strftime("%H:%M"),
                "title": title,
                "keywords": ",".join(tokenize(title)),
                "content": message
            }
        except Exception as e:
            print(f"❌ Erro AgendaActions: {e}")
            return {"title": message, "date": datetime.now().strftime("%d/%m/%Y")}