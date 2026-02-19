from .base_actions import BaseActions
from .shared_utils import tokenize
from datetime import datetime
import re

class FinanceActions(BaseActions):
    def __init__(self, db_path):
        schema = "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, amount REAL, desc TEXT, keywords TEXT, content TEXT"
        super().__init__(db_path, "finance", schema)

    def extract_and_prepare(self, message, llm_func):
        try:
            # 1. Extração estruturada via LLM
            prompt = (
                f"Analise a mensagem: '{message}'. Extraia os dados seguindo este formato EXATO:\n"
                f"VALOR: (apenas números, use ponto para decimal)\n"
                f"TITULO: (máximo 4 palavras)\n"
                f"DATA: (DD/MM/AAAA ou 'HOJE')\n"
                f"Resposta:"
            )
            res = llm_func(prompt, fast=True)
            
            # 2. Parsing dos resultados
            v_match = re.search(r"VALOR:\s*([\d.,]+)", res)
            t_match = re.search(r"TITULO:\s*(.*)", res)
            d_match = re.search(r"DATA:\s*([\d/]+|HOJE)", res, re.IGNORECASE)

            # Limpeza do Valor
            amount_str = v_match.group(1).replace(',', '.') if v_match else "0"
            amount = float(re.sub(r"[^\d.]", "", amount_str))

            # Limpeza da Data
            extracted_date = d_match.group(1) if d_match else "HOJE"
            if "HOJE" in extracted_date.upper():
                final_date = datetime.now().strftime("%d/%m/%Y")
            else:
                final_date = extracted_date

            desc = t_match.group(1).strip() if t_match else message[:30]
            
            return {
                "date": final_date,
                "time": datetime.now().strftime("%H:%M"),
                "amount": amount,
                "desc": desc,
                "keywords": ",".join(tokenize(desc)),
                "content": message
            }
        except Exception as e:
            print(f"❌ Erro FinanceActions: {e}")
            return {"amount": 0, "desc": message, "date": datetime.now().strftime("%d/%m/%Y")}