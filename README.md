# 🤖 Siaa — Scaffoldable IA Assistant

Assistente de IA pessoal, modular e escalável. Combina **SVM** para classificação de intenções com **Granite LLM** (via Ollama local) e integração com **Telegram**.

Projetado para rodar em VPS Oracle Free Tier (ARM) com Docker.

---

## 📦 Módulos

| Módulo | Descrição | Porta interna |
|--------|-----------|---------------|
| [🤖 Siaa](./src/siaa/readme.md) | Core do assistente — SVM, LLM, memória, entidades | 8000 |
| [🌐 Siaa-Proxy](./src/siaa-proxy/README.md) | Gerenciador de proxies com cron jobs e navegador serverless | 8001 |
| [🔐 Siaa-Vault](./src/siaa-vault/README.md) | Cofre de credenciais com criptografia Fernet e JWT | 8002 |

---

## 🏗️ Estrutura do Projeto

```
/
├── docker-compose.yml
├── .env                    ← variáveis globais (não commitar)
├── .env.example
│
├── src/
│   ├── siaa/               ← core do assistente
│   ├── siaa-proxy/         ← gerenciador de proxies
│   └── siaa-vault/         ← cofre de credenciais
│
├── nginx/
│   └── nginx.conf
│
└── volumes/
    ├── siaa-data/          ← contextos, banco e datasets do Siaa
    ├── proxy-data/         ← banco do siaa-proxy
    ├── vault-data/         ← banco do siaa-vault (sensível)
    └── config/             ← config.json compartilhado
```

---

## 🧠 Como funciona

```
Telegram
   │
   ▼
Siaa (app.py)
   ├── SVM classifica a intenção (rápido, local)
   ├── Granite LLM processa linguagem (Ollama)
   ├── Entity executa a ação
   │     ├── web_actions/ → chama Siaa-Proxy para navegar
   │     └── web_actions/ → chama Siaa-Vault para credenciais
   └── Memória em 4 camadas atualiza contexto
```

---

## 🚀 Quick Start

```bash
# 1. Clone o repositório
git clone https://github.com/RodBarenco/Siaa.git
cd Siaa

# 2. Configure as variáveis de ambiente
cp .env.example .env
# edite o .env com suas chaves

# 3. Suba os containers
docker compose up -d

# 4. Instale o modelo Granite no Ollama
docker exec -it ollama ollama pull granite3.1-dense:2b
```

---

## 📋 Pré-requisitos

- Docker + Docker Compose
- Conta Oracle Cloud (Free Tier ARM — 4 OCPU / 24GB RAM)
- Bot do Telegram ([@BotFather](https://t.me/botfather))

---

🗺️ Roadmap de Desenvolvimento

    [x] Core SVM + Granite LLM

    [x] Integração Telegram (Texto/Áudio)

    [x] Memória em 4 camadas (Flash, Short, Medium, Long term)

    [x] Scaffolding de módulos (add_module.py)

    [x] Siaa-Proxy (Gerenciador de proxies)

    [x] Siaa-Vault (Cofre de credenciais)

    [ ] Reconfiguração da ordenação MVC para Arquitetura Modular

    [ ] Criação de novos módulos básicos (Finanças, Saúde, Clima)

    [ ] Docker Compose completo com Nginx Router

    [ ] Melhoria na usabilidade: Evitar chamadas desnecessárias à LLM

    [ ] Serviço de lembretes e tarefas agendadas (Cron Jobs)

    [ ] Suite de testes automatizados

    [ ] Extensibilidade externa via interface de integração

    [ ] Nginx como Gateway para evitar exposição de portas

    [ ] Redis para cache rápido de contexto

    [ ] Procura vetorial com Embeddings (RAG de longo prazo)
