
---

# 🤖 Siaa — Scaffoldable IA Assistant

> **Nota:** Este é um **projeto pessoal** desenvolvido para facilitar a organização diária e a gestão de tarefas através de uma interface inteligente, modular e escalável.

Nesse projeto, você também pode encontrar já de forma funcional os microsserviços de infraestrutura:
[](https://www.google.com/search?q=src/siaa-proxy/) [](https://www.google.com/search?q=src/siaa-vault/)

---

## 🧠 A Filosofia do Projeto

O **Siaa** nasceu da necessidade de um assistente que fosse, ao mesmo tempo, potente e consciente de recursos. O desenvolvimento modular não é apenas uma escolha técnica, é o que torna a vida do desenvolvedor mais simples e ágil.

### 1. Eficiência Reativa (Economia de Tokens)

O propósito central é evitar a **queima desenfreada de tokens** e seus impactos financeiros e ambientais em ações absolutamente simplórias.

* **Classificação Local:** Usamos SVM para identificar o que o usuário quer sem precisar "perguntar" para a nuvem.
* **Inteligência Just-in-Time:** O LLM (Granite 3.3) só entra em cena para processar linguagem natural complexa ou consolidar memórias.

### 2. Scaffolding: A Meta de "Alguns Minutos"

O foco está na experiência do desenvolvedor (DX). A arquitetura modular permite isolar problemas e escalar funcionalidades de forma independente.

* **A Meta:** Finalizar o sistema de **Scaffolding** para que a implementação de um novo módulo leve apenas **alguns minutos**. Criar, acoplar e rodar — essa é a agilidade que buscamos.

---

## 🎯 Intenções Ativas (SVM Core)

| Intenção | Descrição | Status |
| --- | --- | --- |
| `AGENDA_*` | Gestão de compromissos (Adicionar, Listar, Remover) | ✅ Ativo |
| `FINANCE_*` | Controle financeiro pessoal e gastos | ✅ Ativo |
| `WEATHER` | Consulta de meteorologia em tempo real (via Proxy) | ✅ Ativo |
| `MEMORY_SEARCH` | Busca contextual no histórico de conversas | ✅ Ativo |
| `CHAT` | Conversação genérica e interações sociais | ✅ Ativo |

**✅ Resultados de Validação (Teste Rápido):**

* *'agenda medico amanha 10h'* → `AGENDA_ADD`
* *'quanto gastei esse mês?'* → `FINANCE_LIST`
* *'vai chover hoje?'* → `WEATHER`
* *'o que falamos ontem?'* → `MEMORY_SEARCH`

---

## 🏗️ Arquitetura "Shield" (Em Desenvolvimento)

O sistema foi pensado para utilizar um gateway **Nginx** como escudo frontal para mascarar o IP da VPS e centralizar a comunicação. A segurança interna é blindada por um sistema de **Handshake Dinâmico** com tokens rotativos e cofres criptografados.

```text
🌎 INTERNET (Telegram Webhooks)
     │
     ▼ [ Portas 80 / 443 ]
┌──────────────┐
│    NGINX     │──► 🚧 (WIP) Gateway & Proxy Reverso (Ocultação de IP)
└──────┬───────┘
       │
       │ (Rede Interna Docker - Bridge)
       ├────────────────────────┬────────────────────────┐
       ▼                        ▼                        ▼
  [ Siaa-Bot ]           [ Siaa-Vault ]           [ Siaa-Proxy ] ──► 🌐 PROXIES EXTERNOS
  (Core / SVM)           (Cofre de Secrets)       (Navegação / Scraper)    (Saída Anônima)

```

---

## 📦 Ecossistema de Módulos

O sistema é dividido em entidades funcionais, como o módulo de Chat, que gerencia interações genéricas e saudações.

| Módulo | Papel | Estado | Segurança |
| --- | --- | --- | --- |
| **Siaa-Bot** | Cérebro / Agente | ✅ Estável | Isolado na rede interna |
| **Siaa-Proxy** | Saída Anônima | ✅ Ativo | Token Rotativo (Hora em Hora) |
| **Siaa-Vault** | Gestão de Secrets | ✅ Ativo | Criptografia Fernet / JWT / Audit Log |
| **Nginx** | Proteção de Borda | 🚧 WIP | Proxy Pass & Stealth Mode |

---

## 🗺️ Roadmap de Desenvolvimento

### 🛡️ Infraestrutura & Segurança (Foco Atual)

* [x] Handshake com Rotação automática de Tokens (Siaa ↔ Proxy).
* [x] UX Progressiva no Telegram (Lendo/Pensando/Escrevendo).
* [ ] **Nginx Gateway:** Finalizar a configuração para ocultar todas as portas internas e gerenciar o tráfego.
* [ ] **Interface de Comunicação Externa:** Criar uma interface funcional para que o Siaa receba e envie dados para serviços externos.

### 📰 Expansão de Inteligência

* [ ] **Módulo Cron News:** Automação matinal de notícias via Proxy.
* [ ] **Conversação com Vault:** Interface para gerir chaves e informações que queria manter secretas com segurança máxima.
* [ ] **Scaffolder Pro:** Gerador automático de módulos com templates de testes e `web_actions`.

### 🧪 DX & Estabilidade

* [ ] **Suite de Testes Automatizada:** Cada novo módulo gerado pelo scaffold virá com testes unitários pré-implementados.
* [ ] **Memória Persistente:** O sistema já conta com salvamento de interações em banco de dados SQL (`long_term`) e consolidação de contexto em camadas (`actual_context`, `broader_context`), mas vamos melhorar o framework no que se refere a isso.

---

## 🚀 Quick Start (Ecossistema Docker)

A infraestrutura foi desenhada para rodar em containers geridos por `docker compose` e facilitados pelo nosso `Makefile`.

### Passo 1: Preparar o Ambiente

Clone o repositório e crie a estrutura de diretórios necessária para os volumes:

```bash
git clone https://github.com/RodBarenco/Siaa.git
cd Siaa
make setup-dirs
cp .env.example .env

```

### Passo 2: Gerar Chaves de Segurança

Edite o arquivo `.env` e gere chaves fortes para os serviços. Utilize os comandos abaixo no seu terminal para gerar os valores com segurança:

```bash
# MASTER_KEY (Vault - Criptografia Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# JWT_SECRET (Vault Auth)
openssl rand -hex 32

# ADMIN_PASSWORD (Vault Admin - Pode ser uma senha forte da sua escolha)
openssl rand -hex 16

# Chaves de Autenticação do Proxy (Handshake)
openssl rand -hex 32

```

⚠️ **Atenção ao Proxy:** Para que o Bot e o Proxy consigam se comunicar, as variáveis `PROXY_SECRET_KEY` (lida pelo Bot) e `SECRET_KEY` (lida pelo Proxy) no seu `.env` **devem ter exatamente o mesmo valor** gerado pelo comando `openssl` acima.

Exemplo no `.env`:

```env
PROXY_SECRET_KEY=sua_chave_gerada_aqui
SECRET_KEY=sua_chave_gerada_aqui

```

### Passo 3: Subir a Infraestrutura

Construa e inicie todos os containers (Ollama, Vault, Proxy e Bot):

```bash
make up

```

*(Nota: O script de inicialização cuidará de baixar o modelo Granite 3.3 automaticamente).*

### Passo 4: Registrar o Bot no Vault (Obrigatório)

Na primeira execução, o **Siaa-Bot** subirá, mas não terá autorização para acessar o cofre. Para gerar as credenciais do bot com permissão total (asterisco), execute:

```bash
make vault-register ID=siaa-bot NS='*' DESC='Bot principal'

```

O comando vai retornar um JSON com o `client_secret` gerado. Copie esse valor e cole no seu arquivo `.env`:

```env
VAULT_CLIENT_SECRET=valor-retornado-aqui

```

Após salvar o `.env`, reinicie o ecossistema para que o bot carregue a nova chave e se autentique com sucesso:

```bash
make restart

```

---

## 🤝 Colaboração

O Siaa é um projeto vivo e aberto a colaborações. Sinta-se à vontade para sugerir novos módulos, reportar bugs ou trabalhar na Suite de Testes. Se você gosta de arquitetura modular e quer ajudar a construir um assistente eficiente, junte-se ao projeto!

---
