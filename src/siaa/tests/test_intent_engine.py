import sys
import os
import numpy as np
import pickle
import re
from collections import Counter

# Ajusta o path para enxergar a raiz do projeto e importar módulos se necessário
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def pre_process(text):
    """Função de limpeza idêntica à do treino para o Pickle funcionar."""
    if not isinstance(text, str): return ""
    text = text.lower()
    # Isola a interrogação para o modelo tratá-la como um token (palavra)
    text = re.sub(r'(\?)', r' \1', text)
    # Remove caracteres especiais mas mantém letras, números e o ?
    text = re.sub(r'[^a-z0-9\s\?]', '', text)
    return text

def run_test_suite(model, samples, name):
    """Executa uma base de teste e retorna métricas de acerto e confiança."""
    print(f"\n🚀 --- TESTE {name} --- 🚀")
    print(f"{'FRASE':<38} | {'PREVISÃO':<15} | {'CONF':<6} | {'MARGEM':<6} | STATUS")
    print("-" * 105)

    correct = 0
    confidences = []
    
    for phrase, expected in samples:
        # O modelo (pipeline) aplica o pre_process automaticamente
        probs = model.predict_proba([phrase])[0]
        sorted_idx = np.argsort(probs)[::-1]
        
        intent = model.classes_[sorted_idx[0]]
        intent2 = model.classes_[sorted_idx[1]]
        confidence = probs[sorted_idx[0]]
        margin = confidence - probs[sorted_idx[1]]
        confidences.append(confidence)

        if expected:
            if intent == expected:
                status = "✅ OK"
                if margin < 0.20: status += " ⚠️ (Instável)"
                correct += 1
            else:
                status = f"❌ ERRADO (Era: {expected})"
        else:
            # Avaliação de frases que marcamos como ambíguas (None)
            status = f"❓ DÚVIDA: {intent} vs {intent2}" if margin < 0.25 else f"⚠️ CHUTOU: {intent}"

        print(f"{phrase[:38]:<38} | {intent:<15} | {confidence:.2f}  | {margin:.2f}  | {status}")

    total_supervised = len([s for s in samples if s[1] is not None])
    acc = (correct / total_supervised * 100) if total_supervised > 0 else 0
    avg_conf = np.mean(confidences) if confidences else 0
    
    return acc, avg_conf

def run_test():
    model_path = "core/svm_intent_model.pkl"
    if not os.path.exists(model_path):
        print("❌ Erro: Modelo não encontrado em core/svm_intent_model.pkl. Treine primeiro!")
        return

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # ===============================
    # 🏁 BASE 1 — CONTEXTUAL (Dataset Original)
    # ===============================
    base1 = [
        ("anota ai q gastei 50 no posto", "FINANCE_ADD"), ("paguei 120 na farmacia hj cedo", "FINANCE_ADD"),
        ("mais 30 de uber", "FINANCE_ADD"), ("50 no mercado", "FINANCE_ADD"),
        ("gastei 300 no cartao ontem", "FINANCE_ADD"), ("pix de 200 pro joao", "FINANCE_ADD"),
        ("quanto eu ja torrei esse mes?", "FINANCE_LIST"), ("resumo financeiro da semana", "FINANCE_LIST"),
        ("apaga aquele gasto de 30 conto", "FINANCE_REM"), ("remove o pagamento da luz", "FINANCE_REM"),
        ("marca uma call as 15h", "AGENDA_ADD"), ("agenda medico amanha 10h", "AGENDA_ADD"),
        ("o que eu tenho hoje?", "AGENDA_LIST"), ("tenho reuniao hj?", "AGENDA_LIST"),
        ("desmarca a reuniao de hj", "AGENDA_REM"), ("vai chover hj?", "WEATHER"),
        ("o que eu te falei ontem?", "MEMORY_SEARCH"), ("oi tudo bem?", "CHAT")
    ]

    # ===============================
    # 🏁 BASE 2 — GENERALIZAÇÃO (Linguagem Rápida)
    # ===============================
    base2 = [
        ("médico amanhã as 10", "AGENDA_ADD"), ("dentista sexta 09:00", "AGENDA_ADD"),
        ("o que eu tenho pra hoje?", "AGENDA_LIST"), ("desmarca o médico", "AGENDA_REM"),
        ("uber 45 reais", "FINANCE_ADD"), ("ifood 32,90", "FINANCE_ADD"),
        ("quanto já gastei hoje?", "FINANCE_LIST"), ("remove o gasto do uber", "FINANCE_REM"),
        ("previsão do tempo agora", "WEATHER"), ("quem é você?", "CHAT")
    ]

    # ===============================
    # 🏁 BASE 3 — COMPLEXIDADE / STRESS
    # ===============================
    base3 = [
        ("hj as 20h tem fut", "AGENDA_ADD"), ("paguei a marmita 25", "FINANCE_ADD"),
        ("limpa meus gastos de hj", "FINANCE_REM"), ("vê se vai chover no feriado", "WEATHER"),
        ("marmita 25 reais", "FINANCE_ADD"), ("niver do pai domingo", "AGENDA_ADD"),
        ("historico de ontem", "MEMORY_SEARCH"), ("tu ta ligado em q?", "CHAT"),
        ("anota 50", None), ("marca 200", None) # Ambíguas
    ]

    # ===============================
    # 🏁 BASE 4 — TESTE DO SINAL (Interrogação)
    # ===============================
    base4 = [
        ("reunião amanhã", "AGENDA_ADD"), ("reunião amanhã?", "AGENDA_LIST"),
        ("gasto no mercado", "FINANCE_ADD"), ("gasto no mercado?", "FINANCE_LIST"),
        ("aula de inglês hoje", "AGENDA_ADD"), ("aula de inglês hoje?", "AGENDA_LIST"),
        ("pix de 50", "FINANCE_ADD"), ("pix de 50?", "FINANCE_LIST")
    ]

    # Execução e Coleta de Resultados
    r1_acc, r1_conf = run_test_suite(model, base1, "BASE 1 (CONTEXTO)")
    r2_acc, r2_conf = run_test_suite(model, base2, "BASE 2 (RAPIDA)")
    r3_acc, r3_conf = run_test_suite(model, base3, "BASE 3 (STRESS)")
    r4_acc, r4_conf = run_test_suite(model, base4, "BASE 4 (SINAL ?)")

    # Relatório Comparativo Final
    print("\n" + "="*50)
    print(f"📊 RELATÓRIO FINAL DE PERFORMANCE")
    print("="*50)
    print(f"BASE 1 -> Precisão: {r1_acc:>5.1f}% | Confiança: {r1_conf:.2f}")
    print(f"BASE 2 -> Precisão: {r2_acc:>5.1f}% | Confiança: {r2_conf:.2f}")
    print(f"BASE 3 -> Precisão: {r3_acc:>5.1f}% | Confiança: {r3_conf:.2f}")
    print(f"BASE 4 -> Precisão: {r4_acc:>5.1f}% | Confiança: {r4_conf:.2f}")
    print("="*50)
    
    if r4_acc < 100:
        print("💡 DICA: A Base 4 falhou. Verifique se o TfidfVectorizer no train_svm.py está com o token_pattern correto.")
    else:
        print("🔥 SUCESSO: O modelo diferencia Adicionar de Listar pelo sinal '?'!")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_test()