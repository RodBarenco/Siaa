"""
Treina o modelo SVM de classificação de intenções do Siaa.

Lê o dataset de:   $SIAA_DATA_DIR/intent_dataset.json
Salva o modelo em: core/svm_intent_model.pkl

Uso:
    python train_svm.py                    # usa SIAA_DATA_DIR do ambiente
    FORCE_TRAIN=true python train_svm.py   # força novo treino
"""
import json
import pickle
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from dotenv import load_dotenv

load_dotenv()


def pre_process(text):
    """Limpeza de texto — preserva '?' como token isolado."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Isola a interrogação: "hoje?" → "hoje ?"
    text = re.sub(r"(\?)", r" \1", text)
    # Remove lixo, mantém letras, números e '?'
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text


def train_intent_model():
    # -------------------------------------------------------
    # Paths — corrigidos para usar SIAA_DATA_DIR
    # -------------------------------------------------------
    data_dir    = os.getenv("SIAA_DATA_DIR", "volumes/siaa-data")
    data_path   = os.path.join(data_dir, "intent_dataset.json")
    model_dir   = "core"
    model_path  = os.path.join(model_dir, "svm_intent_model.pkl")

    # -------------------------------------------------------
    # Validações
    # -------------------------------------------------------
    if not os.path.exists(data_path):
        print(f"❌ Dataset não encontrado em: {data_path}")
        print(f"   Defina SIAA_DATA_DIR corretamente no .env")
        return False

    print(f"📂 Dataset: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    X, y = [], []
    for intent, phrases in data.items():
        for phrase in phrases:
            X.append(phrase)
            y.append(intent)

    if len(X) < 10:
        print("❌ Dataset muito pequeno para treino confiável.")
        return False

    print(f"📊 Total de exemplos: {len(X)} | Intenções: {len(data)}")

    # -------------------------------------------------------
    # Pipeline: TF-IDF → SVM
    # token_pattern aceita palavras OU '?' isolado
    # -------------------------------------------------------
    vectorizer = TfidfVectorizer(
        preprocessor=pre_process,
        token_pattern=r"(?u)\b\w+\b|\?"
    )
    model = make_pipeline(
        vectorizer,
        SVC(kernel="linear", probability=True)
    )

    print("⏳ Treinando modelo SVM...")
    model.fit(X, y)

    os.makedirs(model_dir, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Modelo salvo em: {model_path}")
    return True


if __name__ == "__main__":
    success = train_intent_model()
    exit(0 if success else 1)
