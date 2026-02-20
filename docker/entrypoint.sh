#!/bin/bash
# =============================================================
# SIAA — Entrypoint
# Executa no boot do container:
#   1. Garante que o dataset está disponível
#   2. Treina o SVM se o modelo não existir
#   3. Inicia o bot
# =============================================================
set -e

echo "============================================="
echo "🤖 SIAA — Iniciando container..."
echo "============================================="

DATA_DIR="${SIAA_DATA_DIR:-/siaa-data}"
MODEL_PATH="core/svm_intent_model.pkl"
DATASET_PATH="${DATA_DIR}/intent_dataset.json"

# -------------------------------------------------------
# 1. Verifica dataset
# -------------------------------------------------------
if [ ! -f "$DATASET_PATH" ]; then
    echo "⚠️  Dataset não encontrado em $DATASET_PATH"
    echo "   O volume siaa-data não está montado corretamente."
    echo "   Verifique o docker-compose.yml e tente novamente."
    exit 1
fi

echo "✅ Dataset encontrado: $DATASET_PATH"

# -------------------------------------------------------
# 2. Treina SVM se o modelo não existir ou se forçado
# -------------------------------------------------------
if [ ! -f "$MODEL_PATH" ] || [ "${FORCE_TRAIN:-false}" = "true" ]; then
    echo "⏳ Modelo SVM não encontrado. Treinando agora..."
    python train_svm.py
    echo "✅ Modelo SVM treinado com sucesso!"
else
    echo "✅ Modelo SVM já existe. Pulando treinamento."
    echo "   (Para retreinar, defina FORCE_TRAIN=true)"
fi

# -------------------------------------------------------
# 3. Verifica variáveis obrigatórias
# -------------------------------------------------------
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ ERRO: TELEGRAM_TOKEN não configurado!"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "❌ ERRO: TELEGRAM_CHAT_ID não configurado!"
    exit 1
fi

if [ -z "$OLLAMA_URL" ]; then
    echo "⚠️  OLLAMA_URL não definida. Usando padrão: http://ollama:11434/api/generate"
fi

echo "============================================="
echo "🚀 Iniciando o bot..."
echo "============================================="

exec python app.py
