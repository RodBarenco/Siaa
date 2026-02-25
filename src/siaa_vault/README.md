# 🔐 Siaa-Vault — KV Store Cifrado por Módulo

[![Siaa-Bot](https://img.shields.io/badge/Siaa--Bot-stable-brightgreen?style=flat-square&logo=python)](../../)
[![Siaa-Proxy](https://img.shields.io/badge/Siaa--Proxy-active-blue?style=flat-square&logo=fastapi)](../siaa_proxy/)
[![Siaa-Vault](https://img.shields.io/badge/Siaa--Vault-active-blueviolet?style=flat-square&logo=fastapi)](.)

> Cofre de credenciais do ecossistema Siaa. Cada módulo tem seu próprio namespace cifrado — sem julgamento de conteúdo, sem acesso cruzado.

---

## 🧠 Conceito

```
módulo-multas
  ├── renavan          → "ABC-1234"         (cifrado)
  ├── cpf              → "123.456.789-00"   (cifrado)
  ├── cookie_sessao    → "eyJhbGc..."       (cifrado)
  └── ultima_consulta  → "2024-01-15"       (cifrado)

módulo-enel
  ├── usuario          → "joao@email.com"   (cifrado)
  ├── senha            → "s3nha!"           (cifrado)
  └── token_api        → "Bearer xyz"       (cifrado)
```

O vault não interpreta o que é cada valor. O módulo define as chaves, salva o que precisa e recupera quando quiser. Cada módulo só acessa seu próprio namespace.

---

## 🛡️ Arquitetura de Segurança

```
┌─────────────────────────────────────────────────────────────┐
│                        SIAA VAULT                           │
│                                                             │
│  MASTER_KEY (.env)   →  cifra todos os values no banco      │
│  JWT_SECRET (.env)   →  sessões curtas por módulo (15min)   │
│  INTERNAL_KEY (.env) →  token rotativo para acesso interno  │
│                                                             │
│  Banco SQLite  →  apenas values cifrados (inúteis sem key)  │
│  Audit log     →  todo acesso registrado (quem, quando, IP) │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Estrutura

```text
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
└── requirements.txt
```

---

## 📋 Endpoints

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/token` | client_id + secret | JWT de sessão (15min) |
| GET | `/secrets/{ns}` | JWT | Todos os valores do namespace |
| GET | `/secrets/{ns}/keys` | JWT | Chaves sem valores |
| GET | `/secrets/{ns}/{key}` | JWT | Um valor específico |
| PUT | `/secrets/{ns}/{key}` | JWT | Salvar ou atualizar |
| DELETE | `/secrets/{ns}/{key}` | JWT | Remover uma chave |
| DELETE | `/secrets/{ns}` | JWT | Remover namespace inteiro |
| GET | `/internal/current-token` | X-Secret-Key | Token rotativo atual |
| POST | `/admin/clients` | X-Admin-Password | Registrar módulo |
| GET | `/admin/clients` | X-Admin-Password | Listar módulos |
| DELETE | `/admin/clients/{id}` | X-Admin-Password | Revogar módulo |
| GET | `/admin/audit` | X-Admin-Password | Log de auditoria |
| GET | `/health` | — | Status |

### Gerenciar via Makefile

```bash
make vault-register ID=modulo-multas NS=modulo-multas DESC='Consulta de multas'
make vault-clients      # lista módulos registrados
make vault-audit        # log de auditoria (últimas 50 entradas)
```

---

## 🔧 Setup

```bash
# 1. Gere a MASTER_KEY (UMA VEZ — nunca mude depois)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Gere JWT_SECRET e INTERNAL_SECRET_KEY
openssl rand -hex 32
openssl rand -hex 32

# 3. Gere ADMIN_PASSWORD
openssl rand -hex 16
```

⚠️ Se perder a `MASTER_KEY`, todos os dados cifrados ficam inacessíveis permanentemente.

---

## 💻 SDK nos módulos

```python
from siaa_vault_client import VaultClient

vault = VaultClient(
    base_url="http://siaa-vault:8002",
    client_id="modulo-multas",
    client_secret="...",
)

# Salvar
await vault.set("renavan", "ABC-1234")
await vault.set("cookie_sessao", "eyJhbGc...", description="cookie do detran")

# Ler tudo de uma vez (recomendado — uma request só)
dados = await vault.get_all()
renavan = dados["renavan"]
headers = {"Cookie": dados["cookie_sessao"]}

# Ler uma chave específica
cpf = await vault.get("cpf")

# Atualizar (cookie expirou)
await vault.set("cookie_sessao", novo_cookie)

# Remover
await vault.delete("cookie_sessao")

# Listar chaves (sem valores)
chaves = await vault.list_keys()
```

---

## 📌 Decisão de Design

Os tokens rotativos entre siaa-bot e siaa-proxy **não ficam aqui** — são gerenciados pelo próprio proxy. Colocá-los no vault criaria dependência circular: o bot precisaria do vault para falar com o proxy, mas o vault pode ainda estar subindo. O vault cuida de **dados de módulos** — o que o usuário forneceu, o que o módulo descobriu, o que precisa persistir entre execuções.

---

## ⚠️ Atenção na VPS Oracle

- Nunca exponha o vault para a internet — apenas rede interna Docker
- Faça backup do `.env` (especialmente `MASTER_KEY`) em local seguro
- Se perder a `MASTER_KEY`, todos os dados cifrados ficam inacessíveis permanentemente

---

*Parte do ecossistema [Siaa](../../README.md) — desenvolvido por Rod Barenco.*