"""
tests/test_intent_engine.py

Roda a suíte de testes do modelo SVM de intenções.
Execute a partir da raiz src/siaa/:
    python3 tests/test_intent_engine.py
"""

import sys
import os
import numpy as np
import pickle
import re

# Garante que src/siaa/ está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def pre_process(text: str) -> str:
    """Idêntica ao train_svm.py e intent_handler.py para o Pickle funcionar."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"(\?)", r" \1", text)
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text


def run_test_suite(model, samples, name):
    print(f"\n🚀 --- TESTE {name} --- 🚀")
    print(f"{'FRASE':<38} | {'PREVISÃO':<15} | {'CONF':<6} | {'MARGEM':<6} | STATUS")
    print("-" * 105)

    correct = 0
    confidences = []

    for phrase, expected in samples:
        probs      = model.predict_proba([phrase])[0]
        sorted_idx = np.argsort(probs)[::-1]

        intent     = model.classes_[sorted_idx[0]]
        intent2    = model.classes_[sorted_idx[1]]
        confidence = probs[sorted_idx[0]]
        margin     = confidence - probs[sorted_idx[1]]
        confidences.append(confidence)

        if expected is not None:
            if intent == expected:
                status = "✅ OK"
                if margin < 0.20:
                    status += " ⚠️ (Instável)"
                correct += 1
            else:
                status = f"❌ ERRADO (Era: {expected})"
        else:
            status = (
                f"❓ DÚVIDA: {intent} vs {intent2}"
                if margin < 0.25
                else f"⚠️  CHUTOU: {intent}"
            )

        print(f"{phrase[:38]:<38} | {intent:<15} | {confidence:.2f}  | {margin:.2f}  | {status}")

    total_supervised = len([s for s in samples if s[1] is not None])
    acc      = (correct / total_supervised * 100) if total_supervised > 0 else 0
    avg_conf = float(np.mean(confidences)) if confidences else 0.0
    return acc, avg_conf


def run_test():
    model_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "core", "svm_intent_model.pkl")
    )

    if not os.path.exists(model_path):
        print(f"❌ Modelo não encontrado em: {model_path}")
        print("   Rode primeiro: python3 train_svm.py")
        return

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    print(f"✅ Modelo carregado: {model_path}")
    print(f"🏷️  Classes: {sorted(model.classes_)}")

    # ===================================================
    # BASE 1 — CONTEXTUAL
    # ===================================================
    base1 = [
        ("anota ai q gastei 50 no posto",    "FINANCE_ADD"),
        ("paguei 120 na farmacia hj cedo",   "FINANCE_ADD"),
        ("mais 30 de uber",                  "FINANCE_ADD"),
        ("50 no mercado",                    "FINANCE_ADD"),
        ("gastei 300 no cartao ontem",       "FINANCE_ADD"),
        ("pix de 200 pro joao",              "FINANCE_ADD"),
        ("quanto eu ja torrei esse mes?",    "FINANCE_LIST"),
        ("resumo financeiro da semana",      "FINANCE_LIST"),
        ("apaga aquele gasto de 30 conto",   "FINANCE_REM"),
        ("remove o pagamento da luz",        "FINANCE_REM"),
        ("marca uma call as 15h",            "AGENDA_ADD"),
        ("agenda medico amanha 10h",         "AGENDA_ADD"),
        ("o que eu tenho hoje?",             "AGENDA_LIST"),
        ("tenho reuniao hj?",                "AGENDA_LIST"),
        ("desmarca a reuniao de hj",         "AGENDA_REM"),
        ("vai chover hj?",                   "WEATHER"),
        ("o que eu te falei ontem?",         "MEMORY_SEARCH"),
        ("oi tudo bem?",                     "CHAT"),
    ]

    # ===================================================
    # BASE 2 — GENERALIZAÇÃO
    # ===================================================
    base2 = [
        ("médico amanhã as 10",          "AGENDA_ADD"),
        ("dentista sexta 09:00",         "AGENDA_ADD"),
        ("o que eu tenho pra hoje?",     "AGENDA_LIST"),
        ("desmarca o médico",            "AGENDA_REM"),
        ("uber 45 reais",                "FINANCE_ADD"),
        ("ifood 32,90",                  "FINANCE_ADD"),
        ("quanto já gastei hoje?",       "FINANCE_LIST"),
        ("remove o gasto do uber",       "FINANCE_REM"),
        ("previsão do tempo agora",      "WEATHER"),
        ("quem é você?",                 "CHAT"),
    ]

    # ===================================================
    # BASE 3 — STRESS
    # ===================================================
    base3 = [
        ("hj as 20h tem fut",            "AGENDA_ADD"),
        ("paguei a marmita 25",          "FINANCE_ADD"),
        ("limpa meus gastos de hj",      "FINANCE_REM"),
        ("vê se vai chover no feriado",  "WEATHER"),
        ("marmita 25 reais",             "FINANCE_ADD"),
        ("niver do pai domingo",         "AGENDA_ADD"),
        ("historico de ontem",           "MEMORY_SEARCH"),
        ("tu ta ligado em q?",           "CHAT"),
        ("anota 50",                     None),  # ambígua
        ("marca 200",                    None),  # ambígua
    ]

    # ===================================================
    # BASE 4 — SINAL DE INTERROGAÇÃO
    # ===================================================
    base4 = [
        ("reunião amanhã",       "AGENDA_ADD"),
        ("reunião amanhã?",      "AGENDA_LIST"),
        ("gasto no mercado",     "FINANCE_ADD"),
        ("gasto no mercado?",    "FINANCE_LIST"),
        ("aula de inglês hoje",  "AGENDA_ADD"),
        ("aula de inglês hoje?", "AGENDA_LIST"),
        ("pix de 50",            "FINANCE_ADD"),
        ("pix de 50?",           "FINANCE_LIST"),
    ]

    r1_acc, r1_conf = run_test_suite(model, base1, "BASE 1 (CONTEXTO)")
    r2_acc, r2_conf = run_test_suite(model, base2, "BASE 2 (RAPIDA)")
    r3_acc, r3_conf = run_test_suite(model, base3, "BASE 3 (STRESS)")
    r4_acc, r4_conf = run_test_suite(model, base4, "BASE 4 (SINAL ?)")

    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL DE PERFORMANCE")
    print("=" * 50)
    print(f"BASE 1 -> Precisão: {r1_acc:>5.1f}% | Confiança: {r1_conf:.2f}")
    print(f"BASE 2 -> Precisão: {r2_acc:>5.1f}% | Confiança: {r2_conf:.2f}")
    print(f"BASE 3 -> Precisão: {r3_acc:>5.1f}% | Confiança: {r3_conf:.2f}")
    print(f"BASE 4 -> Precisão: {r4_acc:>5.1f}% | Confiança: {r4_conf:.2f}")
    print("=" * 50)

    if r4_acc < 100:
        print("💡 DICA: Base 4 falhou — verifique o token_pattern do TfidfVectorizer no train_svm.py")
    else:
        print("🔥 SUCESSO: Modelo diferencia ADD de LIST pelo sinal '?'!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    run_test()