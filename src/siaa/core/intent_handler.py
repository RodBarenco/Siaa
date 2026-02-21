import pickle
import os
import re
import numpy as np
from core.module_loader import load_intents

def pre_process(text: str) -> str:
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r"(\?)", r" \1", text)
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text

class IntentHandler:
    MODEL_PATH = "core/svm_intent_model.pkl"

    def __init__(self, memory):
        self.mem = memory
        self.model = self._load_model()
        self.valid_labels = set(load_intents())
        print(f"🏷️  SVM carregada com {len(self.valid_labels)} intenções.")

    def _load_model(self):
        if os.path.exists(self.MODEL_PATH):
            with open(self.MODEL_PATH, "rb") as f:
                return pickle.load(f)
        return None

    def classify(self, message: str) -> str:
        if not self.model: return "CHAT"
        
        probs = self.model.predict_proba([message])[0]
        sorted_idx = np.argsort(probs)[::-1]
        
        intent = self.model.classes_[sorted_idx[0]]
        confidence = float(probs[sorted_idx[0]])
        margin = float(confidence - probs[sorted_idx[1]])

        # LOG QUE VOCÊ QUER VER
        print(f"🎯 SVM: {intent} (conf={confidence:.2f} margin={margin:.2f})")

        if intent not in self.valid_labels: return "CHAT"
        if margin <= 0.20: return f"DUVIDA|{intent}|{self.model.classes_[sorted_idx[1]]}"
        if confidence > 0.40: return intent
        return "CHAT"