# =============================================================
# SIAA — Dockerfile (siaa-bot)
# Target: Oracle Cloud Free Tier — ARM64 Ampere A1
# Compatível também com AMD64 (desenvolvimento local)
# Contexto de build: raiz do projeto (docker-compose passa context: .)
#
# Nota: as credenciais e dados sensíveis do bot são gerenciados
# pelo siaa-vault (http://siaa-vault:8002) — não ficam nesta imagem.
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
COPY src/siaa/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip "setuptools<70" wheel

# Whisper precisa de no-build-isolation para usar o setuptools acima
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia o código do siaa
COPY src/siaa/ .

# 4. Cria diretórios necessários
#    /siaa-data → montado pelo volume em runtime
RUN mkdir -p /siaa-data/contexts core

# 5. Entrypoint
COPY src/siaa/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK --interval=60s --timeout=10s --start-period=45s --retries=3 \
    CMD pgrep -f "python.*app.py" > /dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
