# =============================================================
# SIAA-PROXY — Dockerfile
# Base fixada no Bookworm (Debian 12) para compatibilidade com Playwright
# =============================================================
FROM python:3.11-slim-bookworm

LABEL maintainer="siaa-proxy"
LABEL description="Siaa Proxy Server — gerenciador de proxies com Playwright"

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/siaa_proxy/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel
RUN pip install --no-cache-dir -r requirements.txt

# O parâmetro --with-deps agora vai funcionar perfeitamente no Bookworm
RUN playwright install chromium --with-deps

COPY src/siaa_proxy/ .

RUN mkdir -p /proxy-data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]