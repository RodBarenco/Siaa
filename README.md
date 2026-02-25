# 🤖 Siaa — Scaffoldable IA Assistant

[![Siaa-Bot](https://img.shields.io/badge/Siaa--Bot-stable-brightgreen?style=flat-square&logo=python)](src/siaa/)
[![Siaa-Proxy](https://img.shields.io/badge/Siaa--Proxy-active-blue?style=flat-square&logo=fastapi)](src/siaa_proxy/)
[![Siaa-Vault](https://img.shields.io/badge/Siaa--Vault-active-blueviolet?style=flat-square&logo=fastapi)](src/siaa_vault/)
[![Nginx](https://img.shields.io/badge/Nginx-WIP-orange?style=flat-square&logo=nginx)](/)

> **Projeto pessoal** desenvolvido para facilitar a organização diária e a gestão de tarefas através de uma interface inteligente, modular e escalável.

---

## 🧠 A Filosofia do Projeto

### 1. Eficiência Reativa — Economia de Tokens

O propósito central é evitar a **queima desenfreada de tokens** em ações simplórias.

- **Classificação Local:** SVM identifica a intenção do usuário sem chamar a nuvem.
- **Inteligência Just-in-Time:** O LLM (Granite 3.3) só entra para linguagem natural complexa ou consolidação de memórias.

### 2. Scaffolding — A Meta de "Alguns Minutos"

A arquitetura modular permite isolar problemas e escalar funcionalidades de forma independente. A meta é que adicionar um novo módulo leve apenas **alguns minutos**: criar, acoplar e rodar.

---

## 🏗️ Arquitetura "Shield"

```text
🌎 INTERNET (Telegram Webhooks)
     │
     ▼ [ Portas 80 / 443 ]
┌──────────────┐
│    NGINX     │──► 🚧 WIP — Gateway & Proxy Reverso (Ocultação de IP)
└──────┬───────┘
       │  (Rede Interna Docker)
       ├────────────────────┬────────────────────┐
       ▼                    ▼                    ▼
  [ Siaa-Bot ]       [ Siaa-Vault ]       [ Siaa-Proxy ]──► 🌐 PROXIES EXTERNOS
  (Core / SVM)    (Cofre de Secrets)   (Navegação Anônima)
```

| Serviço | Papel | Estado | Segurança |
|---|---|---|---|
| **Siaa-Bot** | Cérebro / Agente | ✅ Estável | Rede interna isolada |
| **Siaa-Proxy** | Saída Anônima | ✅ Ativo | Token Rotativo (1h) |
| **Siaa-Vault** | Gestão de Secrets | ✅ Ativo | Fernet / JWT / Audit Log |
| **Nginx** | Proteção de Borda | 🚧 WIP | Proxy Pass & Stealth Mode |

---

## 🎯 Intenções Ativas (SVM)

| Intenção | Descrição | Status |
|---|---|---|
| `AGENDA_*` | Gestão de compromissos — Adicionar, Listar, Remover | ✅ Ativo |
| `FINANCE_*` | Controle financeiro — Registrar, Resumir, Remover | ✅ Ativo |
| `WEATHER` | Previsão do tempo em tempo real (via Proxy) | ✅ Ativo |
| `MEMORY_SEARCH` | Busca contextual no histórico de conversas | ✅ Ativo |
| `CHAT` | Conversação genérica e interações sociais | ✅ Ativo |

**Exemplos de classificação:**
```
'agenda médico amanhã 10h'     → AGENDA_ADD
'quanto gastei hoje?'          → FINANCE_LIST  (filtra por data)
'gastos do dia 15'             → FINANCE_LIST  (filtra por data específica)
'o que tenho amanhã?'          → AGENDA_LIST   (filtra por data)
'vai chover hoje?'             → WEATHER
'o que falamos ontem?'         → MEMORY_SEARCH
```

---

## 📦 Sistema de Módulos

Cada módulo vive em `src/siaa/modules/<nome>/` e é carregado automaticamente pelo `module_loader`. Zero edição de arquivos do core.

```text
modules/<nome>/
├── config.py        ← intenções, flags HAS_CRON / HAS_WEB
├── entity.py        ← lógica de conversa  (herda BaseEntity)
├── actions.py       ← CRUD SQLite         (herda BaseActions)
├── cron.py          ← job agendado        (herda BaseCron)    [opcional]
├── web.py           ← API externa         (herda BaseWeb)     [opcional]
└── training.json    ← exemplos de frases por intenção
```

### Bases disponíveis no framework

| Base | Arquivo | Responsabilidade |
|---|---|---|
| `BaseEntity` | `framework/base_entity.py` | Conversa, confirmações, seleção |
| `BaseActions` | `framework/base_actions.py` | CRUD SQLite com busca por keywords |
| `BaseCron` | `framework/base_cron.py` | Jobs agendados com config por JSON |
| `BaseWeb` | `framework/base_web.py` | Requests externos, fallback proxy→direto |
| `BaseVault` | `framework/base_vault.py` | Persistência de segredos no Siaa-Vault |

### Config de Cron Jobs

Módulos com cron **não usam `.env`**. Cada um lê suas configs de:

```
volumes/siaa-data/contexts/cron-jobs/<nome>.json
```

Estrutura padrão (gerada automaticamente pelo scaffolder):

```json
{
  "enabled": true,
  "trigger": "cron",
  "cron":     { "hour": 8, "minute": 0 },
  "interval": null,
  "settings": {
    "locale": "pt-BR"
  }
}
```

Para múltiplos horários no mesmo módulo, `cron` aceita lista:
```json
"cron": [{ "hour": 8, "minute": 0 }, { "hour": 18, "minute": 0 }]
```

### Criar um novo módulo

```bash
python add_module.py
```

O scaffolder pergunta interativamente: nome, intenções, se tem cron/web, horário, settings. Gera toda a estrutura incluindo o JSON de config do cron. Após criar:

```bash
# 1. Preencha training.json com exemplos de frases por intenção
# 2. Retreine o SVM
make train
# 3. Reinicie o bot — o módulo já será detectado automaticamente
make restart
```

> Módulos puramente cron (sem intenções de conversa) não geram `entity.py` nem `actions.py`.

---

## 🚀 Quick Start

### Passo 1 — Preparar o ambiente

```bash
git clone https://github.com/RodBarenco/Siaa.git
cd Siaa
make setup-dirs
cp .env.example .env
```

### Passo 2 — Gerar chaves de segurança

```bash
# MASTER_KEY (Vault — Fernet, gere UMA VEZ e nunca mude)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# JWT_SECRET e INTERNAL_SECRET_KEY (Vault)
openssl rand -hex 32
openssl rand -hex 32

# ADMIN_PASSWORD (Vault admin)
openssl rand -hex 16

# PROXY_SECRET_KEY / SECRET_KEY (devem ter o mesmo valor)
openssl rand -hex 32
```

⚠️ `PROXY_SECRET_KEY` (lida pelo Bot) e `SECRET_KEY` (lida pelo Proxy) **devem ter exatamente o mesmo valor**.

Exemplo no `.env`:
```env
PROXY_SECRET_KEY=sua_chave_aqui
SECRET_KEY=sua_chave_aqui
```

### Passo 3 — Subir a stack

```bash
make up
```

O entrypoint baixa o modelo Granite 3.3 e treina o SVM automaticamente na primeira execução (~30s).

### Passo 4 — Registrar o Bot no Vault

```bash
make vault-register ID=siaa-bot NS='*' DESC='Bot principal'
```

Copie o `client_secret` retornado para o `.env`:

```env
VAULT_CLIENT_SECRET=valor-retornado-aqui
```

Reinicie para o bot autenticar:

```bash
make restart
```

---

## 🛠️ Makefile — Referência Rápida

```bash
# Stack
make up               # Sobe toda a stack
make down             # Para tudo
make restart          # Reinicia só o bot (sem derrubar vault/proxy/ollama)
make restart-all      # Reinicia tudo
make status           # RAM, CPU e status dos containers

# Build (necessário apenas ao mudar Dockerfile ou requirements.txt)
make build            # Rebuilda todos os serviços
make build-bot        # Rebuilda apenas o siaa

# Logs
make logs             # Todos os serviços em tempo real
make logs-bot         # Apenas o bot
make logs-proxy       # Apenas o proxy

# SVM
make train            # Força retreinamento do SVM

# Vault
make vault-register ID=... NS=... DESC='...'   # Registra módulo
make vault-clients                              # Lista módulos registrados
make vault-audit                                # Log de auditoria (últimas 50)

# Proxy
make proxy-fetch      # Força busca de novos proxies públicos
make proxy-validate   # Força validação dos proxies existentes
make proxy-stats      # Estatísticas: ativos / validados / inativos

# Shells de debug
make shell            # Shell no container do bot
make shell-proxy      # Shell no container do proxy
make shell-vault      # Shell no container do vault
```

> **Quando rebuildar?** Apenas ao mudar `Dockerfile`, `requirements.txt` ou `entrypoint.sh`. Mudanças em `.py` e `.json` não precisam de rebuild — `make restart` basta.

---

## 🗺️ Roadmap

### 🛡️ Infraestrutura & Segurança
- [x] Handshake com rotação automática de tokens (Siaa ↔ Proxy)
- [x] UX progressiva no Telegram (Lendo → Pensando → Escrevendo)
- [x] Siaa-Vault — KV store cifrado por módulo (Fernet + JWT + Audit Log)
- [x] Siaa-Proxy — denuncia de falhas, 3 tentativas, SSL habilitado
- [ ] **Nginx Gateway** — ocultar portas internas e centralizar tráfego

### 📦 Módulos & Inteligência
- [x] Agenda com filtro por data (hoje, amanhã, dia X, DD/MM)
- [x] Finance com totais por período e filtro por data
- [x] **Módulo News** — digest matinal via Google News RSS (sem API key)
- [x] **Sistema de Cron Config** — configs por JSON, sem poluir o `.env`
- [ ] Conversação com Vault — interface para gerir segredos via chat
- [ ] Scaffolder Pro — templates com testes e `web_actions`

### 🧪 DX & Estabilidade
- [ ] Suite de testes automatizada por módulo
- [ ] Melhorias no módulo de memória (consolidação e busca)
- [ ] Desacoplamento do Telegram — arquitetura multiplataforma
- [ ] Desacoplamento da IA — suporte a providers além do Ollama

---

## 🤝 Colaboração

Projeto vivo e aberto. Sinta-se à vontade para sugerir módulos, reportar bugs ou contribuir com testes. Se você curte arquitetura modular e assistentes eficientes, junte-se.

---

*Desenvolvido por Rod Barenco.*