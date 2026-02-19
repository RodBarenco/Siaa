# Siaa Proxy Server 🤖

Servidor de gerenciamento de proxies para o **Siaa** — IA Bot com SVM + Granite LLM + Telegram.

## Estrutura

```
siaa-proxy/
├── app/
│   ├── main.py                  # Entrypoint FastAPI
│   ├── config.py                # Settings (.env)
│   ├── database.py              # SQLite + SQLAlchemy async
│   ├── models/
│   │   ├── proxy.py             # Model: Proxy (protocol, host, port, timestamps...)
│   │   └── token.py             # Model: APIToken
│   ├── controllers/
│   │   ├── proxy_controller.py  # CRUD + lógica de proxies
│   │   └── token_controller.py  # CRUD de tokens
│   ├── routes/
│   │   ├── proxy_routes.py      # GET /proxies, POST /proxies/browse ...
│   │   ├── token_routes.py      # POST /tokens ...
│   │   └── job_routes.py        # POST /jobs/fetch-proxies ...
│   ├── services/
│   │   ├── fetcher.py           # Scrapa listas públicas de proxy
│   │   ├── validator.py         # Valida proxies (latência, disponibilidade)
│   │   └── browser.py           # Playwright serverless (navegador headless)
│   ├── jobs/
│   │   └── scheduler.py         # APScheduler cron jobs
│   └── middlewares/
│       └── auth.py              # Autenticação via X-API-Token header
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
# 1. Instale dependências
pip install -r requirements.txt

# 2. Instale o Chromium para o Playwright
playwright install chromium

# 3. Configure o .env
cp .env.example .env
# Edite o SECRET_KEY e demais configs

# 4. Rode o servidor
python -m app.main
# ou
uvicorn app.main:app --reload
```

## Uso rápido

### 1. Criar um token
```bash
curl -X POST http://localhost:8000/tokens \
  -H "Content-Type: application/json" \
  -d '{"name": "siaa-bot", "expire_days": 30}'
```

### 2. Buscar proxies manualmente
```bash
curl -X POST http://localhost:8000/jobs/fetch-proxies \
  -H "X-API-Token: SEU_TOKEN"
```

### 3. Validar proxies
```bash
curl -X POST http://localhost:8000/jobs/validate-proxies \
  -H "X-API-Token: SEU_TOKEN"
```

### 4. Pegar o melhor proxy (para o Siaa usar)
```bash
curl http://localhost:8000/proxies/best \
  -H "X-API-Token: SEU_TOKEN"
```

### 5. Navegar em um site via proxy (Siaa → Playwright)
```bash
curl -X POST http://localhost:8000/proxies/browse \
  -H "X-API-Token: SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "use_proxy": true,
    "extract": "text"
  }'
```

## Integração com o Siaa (Python)

```python
import httpx

PROXY_SERVER = "http://localhost:8000"
TOKEN = "seu_token_aqui"
HEADERS = {"X-API-Token": TOKEN}

async def get_best_proxy():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PROXY_SERVER}/proxies/best", headers=HEADERS)
        return r.json()  # { protocol, host, port, ... }

async def browse(url: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{PROXY_SERVER}/proxies/browse",
            headers=HEADERS,
            json={"url": url, "use_proxy": True, "extract": "text"},
            timeout=60,
        )
        data = r.json()
        return data["content"] if data["success"] else ""
```

## Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/` | — | Health check |
| POST | `/tokens` | — | Criar token |
| GET | `/tokens` | — | Listar tokens |
| DELETE | `/tokens/{id}` | — | Revogar token |
| GET | `/proxies` | ✅ | Listar proxies |
| GET | `/proxies/best` | ✅ | Melhor proxy disponível |
| GET | `/proxies/stats` | ✅ | Estatísticas |
| POST | `/proxies` | ✅ | Adicionar proxy manual |
| DELETE | `/proxies/{id}` | ✅ | Remover proxy |
| POST | `/proxies/browse` | ✅ | Navegar via Playwright |
| POST | `/jobs/fetch-proxies` | ✅ | Trigger fetch manual |
| POST | `/jobs/validate-proxies` | ✅ | Trigger validação manual |

## Docs interativas
Acesse: `http://localhost:8000/docs`
