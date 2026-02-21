"""
train_svm.py — Treina o modelo SVM de intenções.

Lê automaticamente os training.json de todos os módulos em modules/
e usa o intent_dataset.json do volume de dados como base adicional.

Uso:
    python train_svm.py
"""

import os
import re
import json
import pickle

from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer


# ------------------------------------------------------------------
# Pre-process (deve ser idêntico ao do intent_handler.py)
# ------------------------------------------------------------------
def pre_process(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"(\?)", r" \1", text)
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text


# ------------------------------------------------------------------
# Coleta de dados de treinamento
# ------------------------------------------------------------------
def collect_training_data() -> tuple[list[str], list[str]]:
    texts, labels = [], []
    modules_dir   = os.path.join(os.path.dirname(__file__), "modules")

    print("📂 Varrendo módulos...")
    for module_name in sorted(os.listdir(modules_dir)):
        training_path = os.path.join(modules_dir, module_name, "training.json")
        if not os.path.exists(training_path):
            continue

        with open(training_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for intent, examples in data.items():
            for example in examples:
                if example.strip():
                    texts.append(example)
                    labels.append(intent)
                    count += 1

        print(f"  ✅ {module_name}: {count} exemplos")

    # Dataset extra do volume de dados (legado + manual)
    data_dir     = os.getenv("SIAA_DATA_DIR", "volumes/siaa-data")
    dataset_path = os.path.join(data_dir, "intent_dataset.json")
    if os.path.exists(dataset_path):
        with open(dataset_path, "r", encoding="utf-8") as f:
            extra = json.load(f)
        count = 0
        for intent, examples in extra.items():
            for example in examples:
                if example.strip():
                    texts.append(example)
                    labels.append(intent)
                    count += 1
        print(f"  📦 intent_dataset.json (legado): {count} exemplos")

    return texts, labels


# ------------------------------------------------------------------
# Treinamento
# ------------------------------------------------------------------
def train():
    print("\n🚀 ——— TREINAMENTO SVM SIAA ———\n")

    texts, labels = collect_training_data()

    if len(set(labels)) < 2:
        print("❌ Precisa de pelo menos 2 classes para treinar.")
        return

    print(f"\n📊 Total: {len(texts)} exemplos | {len(set(labels))} classes")
    print(f"   Classes: {sorted(set(labels))}\n")

    # AQUI ESTÁ A MÁGICA:
    # Usamos o SVC com kernel linear e probability=True. 
    # Ele contorna o bug do CalibratedClassifierCV na v1.3.0 e mantém a eficiência!
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            preprocessor=pre_process,
            ngram_range=(1, 2),
            min_df=1,
        )),
        ("clf", SVC(kernel="linear", probability=True, random_state=42)),
    ])

    pipeline.fit(texts, labels)

    model_path = os.path.join("core", "svm_intent_model.pkl")
    os.makedirs("core", exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"✅ Modelo salvo em: {model_path}")
    print("\n🎯 Teste rápido:")

    test_phrases = [
        ("agenda medico amanha 10h", "AGENDA_ADD"),
        ("quanto gastei esse mês?", "FINANCE_LIST"),
        ("vai chover hoje?", "WEATHER"),
        ("oi tudo bem?", "CHAT"),
        ("o que falamos ontem?", "MEMORY_SEARCH"),
    ]
    acertos = 0
    for phrase, expected in test_phrases:
        probs      = pipeline.predict_proba([phrase])[0]
        predicted  = pipeline.classes_[probs.argmax()]
        ok         = "✅" if predicted == expected else "❌"
        acertos   += predicted == expected
        print(f"  {ok} '{phrase}' → {predicted} (esperado: {expected})")

    print(f"\n🏆 Acurácia no teste rápido: {acertos}/{len(test_phrases)}")


if __name__ == "__main__":
    train()