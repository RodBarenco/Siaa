#!/bin/bash

# Se FORCE_TRAIN for true, deleta o modelo velho antes de qualquer coisa
if [ "$FORCE_TRAIN" = "true" ]; then
    echo "⚠️ FORCE_TRAIN ativado. Eliminando modelo antigo..."
    rm -f /app/core/svm_intent_model.pkl
fi

# Se o modelo não existir (porque deletamos ou porque nunca existiu), treina.
if [ ! -f "/app/core/svm_intent_model.pkl" ]; then
    echo "⏳ Modelo não encontrado ou forçado. Treinando agora..."
    python3 train_svm.py
else
    echo "✅ Modelo SVM já existe. Pulando treinamento."
fi

# Inicia o bot
exec python3 -u app.py