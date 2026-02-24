FROM python:3.12-slim

WORKDIR /app

COPY src/siaa_vault/requirements.txt .
COPY src/siaa_vault/ .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cria diretório para o banco SQLite
RUN mkdir -p /data

ENV DATABASE_URL=sqlite+aiosqlite:////data/siaa_vault.db

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
