# Siaa Vault 🔐

Cofre de credenciais para os módulos do **Siaa** (Scaffoldable-IA-Assistant).
Armazena usuários, senhas, CPF, tokens e dados pessoais com criptografia Fernet (AES-128-CBC).

## Como funciona

```
Módulo (siaa-bot)
    │
    ├─ POST /auth/token  (client_id + client_secret)
    │       ↓ JWT válido por 15min
    │
    ├─ GET /secrets/enel-rj/all   [Bearer JWT]
    │       ↓ {"username": "...", "password": "...", "cpf": "..."}
    │
    └─ (JWT expira → renova automaticamente)
```

**Segurança em camadas:**
- Banco SQLite → valores cifrados com Fernet (ilegíveis sem `MASTER_KEY`)
- `MASTER_KEY` → só no `.env`, nunca no banco
- JWT → sessões curtas (15min), renovadas sob demanda
- Audit log → todo acesso registrado (quem, quando, IP)
- Namespaces → cada módulo acessa só o que precisa

## Estrutura

```
siaa-vault/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── vault_client.py   # Módulos registrados (siaa-bot, siaa-proxy...)
│   │   ├── secret.py         # Credenciais cifradas (namespace/key/value)
│   │   └── audit_log.py      # Log de todos os acessos
│   ├── controllers/
│   │   ├── secret_controller.py   # CRUD com encrypt/decrypt
│   │   └── client_controller.py   # Autenticação de módulos
│   ├── routes/
│   │   ├── auth_routes.py    # POST /auth/token
│   │   ├── secret_routes.py  # GET|PUT|DELETE /secrets/...
│   │   └── admin_routes.py   # /admin/* (senha de admin)
│   ├── services/
│   │   ├── crypto.py         # Fernet encrypt/decrypt
│   │   └── jwt_service.py    # Criação e validação de JWT
│   └── middlewares/
│       └── auth.py           # Bearer JWT + controle de namespace
├── siaa_vault_client.py      # SDK para usar no Siaa e módulos
├── requirements.txt
└── .env.example
```

## Setup

```bash
# 1. Instale dependências
pip install -r requirements.txt

# 2. Gere a MASTER_KEY (UMA VEZ — não perca!)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Gere o JWT_SECRET
openssl rand -hex 32

# 4. Configure o .env
cp .env.example .env
# Cole as chaves geradas no .env

# 5. Rode
python -m app.main
# Docs: http://localhost:8001/docs
```

## Uso — Admin

```bash
# Registrar o siaa-bot no vault
curl -X POST http://localhost:8001/admin/clients \
  -H "X-Admin-Password: sua-senha-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "siaa-bot",
    "client_secret": "secret-forte-aqui",
    "description": "Bot principal do Siaa",
    "allowed_namespaces": "enel-rj,boletos,dados-pessoais"
  }'

# Ver audit log
curl http://localhost:8001/admin/audit \
  -H "X-Admin-Password: sua-senha-admin"
```

## Uso — Módulos

```bash
# 1. Autenticar e pegar JWT
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"siaa-bot","client_secret":"secret-forte-aqui"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Guardar credenciais da conta de luz
curl -X PUT http://localhost:8001/secrets/enel-rj/username \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"namespace":"enel-rj","key":"username","value":"joao@email.com","secret_type":"credential"}'

curl -X PUT http://localhost:8001/secrets/enel-rj/cpf \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"namespace":"enel-rj","key":"cpf","value":"123.456.789-00","secret_type":"personal_data"}'

# 3. Buscar tudo de uma vez (o Siaa usa isso)
curl http://localhost:8001/secrets/enel-rj/all \
  -H "Authorization: Bearer $TOKEN"
# → {"username": "joao@email.com", "password": "...", "cpf": "123..."}
```

## Integração com o Siaa (Python SDK)

```python
from siaa_vault_client import VaultClient

vault = VaultClient(
    base_url="http://localhost:8001",
    client_id="siaa-bot",
    client_secret="secret-forte-aqui",
)

# O token é renovado automaticamente quando expira
creds = await vault.get_namespace("enel-rj")
# → {"username": "joao@email.com", "password": "senha", "cpf": "123..."}

# Usar com o proxy server para acessar o site da Enel
proxy = await proxy_client.get_best()
result = await browser.browse(
    url="https://www.enel.com.br/login",
    proxy_url=proxy["url"],
    credentials=creds,
)
```

## Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/auth/token` | client_id+secret | Abre sessão JWT |
| GET | `/secrets/namespaces` | JWT | Lista namespaces |
| GET | `/secrets/{ns}` | JWT | Lista chaves (sem valores) |
| GET | `/secrets/{ns}/all` | JWT | Todos os valores decifrados |
| GET | `/secrets/{ns}/{key}` | JWT | Um valor decifrado |
| PUT | `/secrets/{ns}/{key}` | JWT | Cria/atualiza segredo |
| DELETE | `/secrets/{ns}/{key}` | JWT | Remove segredo |
| POST | `/admin/clients` | Admin-Password | Registrar módulo |
| GET | `/admin/clients` | Admin-Password | Listar módulos |
| DELETE | `/admin/clients/{id}` | Admin-Password | Revogar módulo |
| GET | `/admin/audit` | Admin-Password | Ver audit log |

## ⚠️ Atenção na VPS Oracle

- **Nunca exponha o Vault para a internet** — use apenas na rede interna da VPS
- Bind em `127.0.0.1` se todos os módulos rodarem na mesma máquina
- Faça backup do `.env` (MASTER_KEY) em local seguro — se perder, perde os dados
- Considere usar `ufw` para bloquear a porta 8001 externamente
