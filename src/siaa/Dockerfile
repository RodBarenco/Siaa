# =============================================================
# SIAA — Dockerfile
# Target: Oracle Cloud Free Tier — ARM64 Ampere A1
# Compatível também com AMD64 (desenvolvimento local)
# Contexto de build: raiz do projeto (docker-compose passa context: .)
# =============================================================
FROM python:3.11-slim

LABEL maintainer="siaa-bot"
LABEL description="Siaa — Scaffoldable IA Assistant"

ARG DEBIAN_FRONTEND=noninteractive

# 1. Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Dependências Python
# Copia só o requirements primeiro para aproveitar cache do Docker
COPY src/siaa/requirements.txt .

# Fixa setuptools para evitar erro de pkg_resources no Whisper
RUN pip install --no-cache-dir --upgrade pip "setuptools<70" wheel

# Whisper precisa de no-build-isolation para usar o setuptools acima
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

# Restante das dependências
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia o código do siaa
COPY src/siaa/ .

# 4. Cria diretórios necessários
#    /siaa-data → montado pelo volume em runtime
#    core/      → montado pelo volume siaa-model (contém o .pkl do SVM)
RUN mkdir -p /siaa-data/contexts core

# 5. Entrypoint (treino automático do SVM + inicia app.py)
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]