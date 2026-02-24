# 🌐 Siaa-Proxy — Gerenciador de Proxies & Shield

> **Nota:** Este é um **projeto pessoal** integrante do ecossistema Siaa, desenvolvido para fornecer uma camada de anonimato e resiliência para buscas web, garantindo que o IP real da infraestrutura permaneça oculto.

---

## 🧠 Propósito e Filosofia

O **Siaa-Proxy** atua como o "escudo de rede" do assistente Siaa. Sua função principal é gerenciar o ciclo de vida de proxies públicos e privados, permitindo que ações de *web scraping* e consultas externas sejam feitas sem expor a VPS.

* **Eficiência de Recursos:** Evita que o bot principal precise gerenciar conexões complexas, centralizando a lógica de busca e validação de IPs em um serviço especializado.
* **Desenvolvimento Modular:** Seguindo a meta de scaffolding do projeto, o proxy-server é independente, comunicando-se via API REST protegida.

---

## 🛡️ Segurança & Auth (Handshake Rotativo)

O serviço implementa um sistema de segurança robusto baseado em **X-API-Token**:

* **Token Rotativo:** Um job agendado rotaciona as chaves de API periodicamente para garantir que o acesso interno seja sempre renovado.
* **Provisionamento Inicial:** No startup, o sistema verifica a existência de tokens ativos; caso não existam, gera automaticamente a primeira chave de acesso.
* **Validação Estrita:** Cada requisição passa por um middleware que verifica a atividade e a expiração do token no banco de dados.

---

## ⚙️ Automatização (Cron Jobs)

O serviço utiliza o `APScheduler` para manter a saúde da malha de proxies de forma autônoma:

* **Fetch Job:** Busca novos proxies públicos em intervalos configurados.
* **Validation Job:** Testa a latência e a integridade de todos os proxies ativos no banco.
* **Rotate Job:** Executa a rotação de tokens de segurança de hora em hora.

---

## 🏗️ Estrutura do Projeto

```text
/
├── app/
│   ├── jobs/           # Agendadores (Scheduler)
│   ├── models/         # Definições SQLAlchemy (Proxy, Token)
│   ├── controllers/    # Lógica de negócio e CRUD
│   ├── routes/         # Endpoints da API
│   ├── services/       # Integrações externas (Fetcher, Validator)
│   └── database.py     # Conexão assíncrona com o banco
├── main.py             # Entrada da aplicação FastAPI
└── auth.py             # Middleware de autenticação

```

---

## 📋 Endpoints Principais

| Rota | Método | Descrição |
| --- | --- | --- |
| `/proxies/best` | `GET` | Retorna o melhor proxy disponível (menor latência). |
| `/proxies/stats` | `GET` | Estatísticas de proxies ativos, validados e inativos. |
| `/internal/current-token` | `GET` | Endpoint interno para o Siaa-Bot buscar o token atual. |
| `/health` | `GET` | Verificação de status do serviço. |

---

## 🚀 Como Rodar

```bash
# Instale as dependências
pip install -r requirements.txt

# Configure o .env (URL do Banco, Secret Keys)

# Inicie o servidor
python app/main.py

```

---

## 🛠️ Roadmap

* [x] Rotação automática de tokens (Handshake).
* [x] Sistema de validação de latência automática.
* [ ] **Nginx Stealth:** Implementar configuração de Nginx para mascarar completamente a porta 8001.
* [ ] **Vault Integration:** Migrar o `PROXY_SECRET_KEY` para o serviço Siaa-Vault.
* [ ] **Suite de Testes:** Implementar testes de carga para o dispatcher de proxies.

---

*Desenvolvido como parte do ecossistema Siaa por Rod Barenco.*

---
