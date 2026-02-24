# Siaa Vault 🔐

KV store cifrado por módulo para o ecossistema Siaa.
Cada módulo tem seu próprio namespace e guarda o que precisar — sem julgamento de conteúdo.

---

## Conceito

```
módulo-multas
  ├── renavan          → "ABC-1234"         (cifrado)
  ├── cpf              → "123.456.789-00"   (cifrado)
  ├── cookie_sessao    → "eyJhbGc..."       (cifrado)
  └── ultima_consulta  → "2024-01-15"       (cifrado)

módulo-enel
  ├── usuario          → "joao@email.com"   (cifrado)
  ├── senha            → "s3nha!"           (cifrado)
  ├── cpf              → "123.456.789-00"   (cifrado)
  └── token_api        → "Bearer xyz"       (cifrado)
```

O vault não interpreta o que é cada valor. O módulo define as chaves, salva o que precisa, e recupera quando quiser. Cada módulo só acessa seu próprio namespace.

---

## Arquitetura de Segurança

```
┌─────────────────────────────────────────────────────────────┐
│                        SIAA VAULT                           │
│                                                             │
│  MASTER_KEY (.env)  →  cifra todos os values no banco       │
│  JWT_SECRET (.env)  →  sessões curtas por módulo (15min)    │
│  INTERNAL_KEY (.env)→  token rotativo para acesso interno   │
│                                                             │
│  Banco SQLite  →  apenas values cifrados (inúteis sem key)  │
│  Audit log     →  todo acesso registrado (quem, quando, IP) │
└─────────────────────────────────────────────────────────────┘
```

---

## Estrutura

```
siaa_vault/
├── app/
│   ├── main.py                    # FastAPI + APScheduler
│   ├── config.py                  # Settings via .env
│   ├── database.py                # SQLAlchemy async
│   ├── models/
│   │   ├── vault_client.py        # Módulos registrados
│   │   ├── secret.py              # KV cifrado
│   │   ├── audit_log.py           # Log imutável de acessos
│   │   └── internal_token.py      # Tokens rotativos internos
│   ├── controllers/
│   │   ├── client_controller.py   # Auth + CRUD de módulos
│   │   └── secret_controller.py   # KV com encrypt/decrypt
│   ├── routes/
│   │   ├── auth_routes.py         # POST /auth/token
│   │   ├── secret_routes.py       # KV API
│   │   ├── admin_routes.py        # /admin/* (X-Admin-Password)
│   │   └── internal_routes.py     # /internal/* (token rotativo)
│   ├── services/
│   │   ├── crypto.py              # Fernet encrypt/decrypt
│   │   ├── jwt_service.py         # Criação/validação JWT
│   │   └── token_rotator.py       # APScheduler — rotação automática
│   └── middlewares/
│       └── auth.py                # Deps: JWT, Admin, Internal Token
├── siaa_vault_client.py           # SDK para os módulos
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/auth/token` | client_id + secret | JWT de sessão |
| GET | `/secrets/namespaces` | JWT | Namespaces acessíveis |
| GET | `/secrets/{ns}` | JWT | **Todos os valores** do namespace |
| GET | `/secrets/{ns}/keys` | JWT | Chaves sem valores |
| GET | `/secrets/{ns}/{key}` | JWT | Um valor |
| PUT | `/secrets/{ns}/{key}` | JWT | Salvar ou atualizar |
| DELETE | `/secrets/{ns}/{key}` | JWT | Remover uma chave |
| DELETE | `/secrets/{ns}` | JWT | Remover namespace inteiro |
| GET | `/internal/current-token` | X-Secret-Key | Token rotativo atual |
| POST | `/admin/clients` | X-Admin-Password | Registrar módulo |
| GET | `/admin/clients` | X-Admin-Password | Listar módulos |
| DELETE | `/admin/clients/{id}` | X-Admin-Password | Revogar módulo |
| GET | `/admin/audit` | X-Admin-Password | Log de auditoria |
| GET | `/health` | — | Status |

---

## Setup

```bash
# 1. Gere a MASTER_KEY (UMA VEZ — nunca mude depois)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Gere JWT_SECRET e INTERNAL_SECRET_KEY
openssl rand -hex 32
openssl rand -hex 32

# 3. Configure
cp .env.example .env
# cole as chaves geradas

# 4. Rode
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

---

## Uso — Registrar módulo (admin)

```bash
curl -X POST http://localhost:8002/admin/clients \
  -H "X-Admin-Password: sua-senha" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "modulo-multas",
    "description": "Consulta de multas via RENAVAN",
    "allowed_namespaces": "modulo-multas"
  }'
# → retorna client_secret gerado automaticamente — guarde!
```

---

## Uso — SDK nos módulos

```python
from siaa_vault_client import VaultClient

# O namespace é automaticamente o client_id do módulo
vault = VaultClient(
    base_url="http://siaa-vault:8002",
    client_id="modulo-multas",
    client_secret="...",
)

# --- Salvar qualquer coisa ---
await vault.set("renavan", "ABC-1234")
await vault.set("cpf", "123.456.789-00")
await vault.set("cookie_sessao", "eyJhbGc...", description="cookie do detran")
await vault.set("ultima_consulta", "2024-01-15")

# --- Ler tudo de uma vez (recomendado — uma request só) ---
dados = await vault.get_all()
# → {"renavan": "ABC-1234", "cpf": "123...", "cookie_sessao": "eyJ...", ...}

# Usar nos requests do scraper:
renavan = dados["renavan"]
cpf = dados["cpf"]
headers = {"Cookie": dados["cookie_sessao"]}

# --- Ler uma chave específica ---
renavan = await vault.get("renavan")

# --- Atualizar (cookie expirou, salva o novo) ---
await vault.set("cookie_sessao", novo_cookie)

# --- Remover ---
await vault.delete("cookie_sessao")

# --- Listar chaves (sem valores) ---
chaves = await vault.list_keys()
```

---

## Decisão de Design: tokens siaa↔proxy NÃO ficam aqui

Os tokens rotativos entre siaa-bot e siaa-proxy são segredos de infraestrutura gerenciados pelo próprio proxy. Colocá-los no vault criaria dependência circular: o bot precisaria do vault para falar com o proxy, mas o vault pode estar subindo. O modelo atual (proxy expõe `/internal/current-token` com `PROXY_SECRET_KEY` do `.env`) é mais resiliente e correto.

O vault cuida de **dados de módulos** — o que o usuário forneceu, o que o módulo descobriu, o que precisa persistir entre execuções.

---

## ⚠️ Atenção na VPS Oracle

- Nunca exponha o vault para a internet — apenas rede interna Docker
- Faça backup do `.env` (especialmente `MASTER_KEY`) em local absolutamente seguro
- Se perder a `MASTER_KEY`, todos os dados cifrados ficam inacessíveis para sempre
