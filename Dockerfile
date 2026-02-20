# =============================================================
# SIAA — Dockerfile (Versão Final de Produção)
# Target: Oracle Cloud Free Tier — ARM64 Ampere A1
# Compatível também com AMD64 (Pop!_OS / Dev Local)
# =============================================================
FROM python:3.11-slim

LABEL maintainer="siaa-bot"
LABEL description="Siaa — Scaffoldable IA Assistant"

# Evita perguntas durante a instalação de pacotes
ARG DEBIAN_FRONTEND=noninteractive

# 1. Instalação de dependências do sistema
#   ffmpeg          : Necessário para processar áudio (Whisper)
#   curl            : Usado para o Healthcheck
#   build-essential : Compilador C++ para pacotes de Machine Learning
#   python3-dev     : Cabeçalhos do Python para compilação
#   libffi-dev      : Necessário para criptografia/segurança
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Preparação do ambiente Python
# Copiamos primeiro apenas o requirements para aproveitar o cache do Docker
COPY src/siaa/requirements.txt .

# A) Atualiza ferramentas base e fixa o setuptools numa versão que contém o 'pkg_resources'
RUN pip install --no-cache-dir --upgrade pip "setuptools<70" wheel

# B) Instala o Whisper sem isolamento de build para garantir que ele usa o setuptools acima
#    Isso resolve o erro "ModuleNotFoundError: No module named 'pkg_resources'"
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

# C) Instala as restantes dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# 3. Importação do código e configuração final
# Copia todo o conteúdo da pasta src/siaa para o diretório de trabalho (/app)
COPY src/siaa/ .

# Cria os diretórios necessários para a persistência de dados
RUN mkdir -p /siaa-data/contexts core

# 4. Verificação de Saúde (Healthcheck)
# O Docker verificará se o bot ainda está a correr a cada 60 segundos
HEALTHCHECK --interval=60s --timeout=10s --start-period=45s --retries=3 \
    CMD pgrep -f "python.*app.py" > /dev/null || exit 1

# 5. Configuração do Script de Entrada
# O entrypoint gere o treino automático do SVM e inicia o app.py
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]