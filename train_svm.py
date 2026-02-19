import json
import pickle
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline

def pre_process(text):
    """Limpeza de texto que preserva a interrogação como um token."""
    if not isinstance(text, str): return ""
    text = text.lower()
    # Isola a interrogação: "hoje?" -> "hoje ?"
    text = re.sub(r'(\?)', r' \1', text)
    # Remove lixo, mantém letras, números e o ?
    text = re.sub(r'[^a-z0-9\s\?]', '', text)
    return text

def train_intent_model():
    data_path = "data/intent_dataset.json"
    model_path = "core/svm_intent_model.pkl"

    if not os.path.exists(data_path):
        print("❌ Dataset não encontrado!")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    X, y = [], []
    for intent, phrases in data.items():
        for phrase in phrases:
            X.append(phrase)
            y.append(intent)

    # O segredo: token_pattern aceita palavras OU o símbolo ? isolado
    vectorizer = TfidfVectorizer(
        preprocessor=pre_process,
        token_pattern=r"(?u)\b\w+\b|\?"
    )

    # Pipeline: Vetorização -> Classificador SVM
    model = make_pipeline(vectorizer, SVC(kernel='linear', probability=True))
    
    print("⏳ Treinando modelo (Lógica de Interrogação Ativada)...")
    model.fit(X, y)

    os.makedirs("core", exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Sucesso! Modelo salvo em {model_path}")

if __name__ == "__main__":
    train_intent_model()