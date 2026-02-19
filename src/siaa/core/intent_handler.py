import pickle
import os
import numpy as np
import re

# Precisamos definir a função aqui para o Pickle carregar corretamente no contexto do App
def pre_process(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'(\?)', r' \1', text)
    text = re.sub(r'[^a-z0-9\s\?]', '', text)
    return text

class IntentHandler:
    def __init__(self, memory):
        self.mem = memory
        self.model = self._load_model()

    def _load_model(self):
        model_path = "core/svm_intent_model.pkl"
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                # O pre_process precisa estar no escopo global deste arquivo
                return pickle.load(f)
        return None

    def classify(self, message: str) -> str:
        if not self.model: return "CHAT"
        
        # O pre_process é aplicado automaticamente pelo TfidfVectorizer do Pipeline
        probs = self.model.predict_proba([message])[0]
        sorted_idx = np.argsort(probs)[::-1]
        
        intent = self.model.classes_[sorted_idx[0]]
        intent2 = self.model.classes_[sorted_idx[1]]
        
        confidence = probs[sorted_idx[0]]
        margin = confidence - probs[sorted_idx[1]]

        print(f"🎯 SVM: {intent} (Conf: {confidence:.2f} | Margem: {margin:.2f})")

        # Lógica de Dúvida / Margem Apertada
        if margin <= 0.20:
            return f"DUVIDA|{intent}|{intent2}"

        if confidence > 0.40:
            return intent

        return "CHAT"