# =============================================================
# SIAA — Makefile
# Target: Oracle Cloud Free Tier ARM64 (4 OCPU / 24GB RAM)
# Serviços: siaa, siaa-vault, siaa-proxy, ollama
# =============================================================
.PHONY: help build up down logs restart train shell clean status \
        pull-model pull list-models \
        logs-bot logs-ollama logs-vault logs-proxy \
        shell-ollama shell-vault shell-proxy \
        up-bot up-vault up-proxy \
        vault-register vault-audit vault-clients \
        proxy-fetch proxy-validate proxy-stats

GREEN  = \033[0;32m
YELLOW = \033[1;33m
CYAN   = \033[0;36m
RED    = \033[0;31m
NC     = \033[0m

help: ## Mostra esta ajuda
	@echo "$(GREEN)SIAA — Comandos disponíveis:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-22s$(NC) %s\n", $$1, $$2}'

# --- Setup ---
setup-dirs: ## Cria todos os diretórios de volume
	mkdir -p volumes/siaa-data/contexts \
	         volumes/siaa-data/contexts/cron-jobs \
	         volumes/siaa-model \
	         volumes/ollama-data \
	         volumes/vault-data \
	         volumes/proxy-data
	@echo "$(GREEN)✅ Diretórios criados.$(NC)"

# --- Build ---
build: ## Builda todos os serviços
	docker compose build siaa siaa-vault siaa-proxy

build-bot: ## Builda apenas o siaa
	docker compose build siaa

build-vault: ## Builda apenas o siaa-vault
	docker compose build siaa-vault

build-proxy: ## Builda apenas o siaa-proxy
	docker compose build siaa-proxy

# --- Ciclo de vida completo ---
up: setup-dirs ## Sobe toda a stack (vault e proxy sobem antes do bot)
	docker compose up -d
	@echo "$(GREEN)✅ Stack rodando.$(NC)"
	@echo "$(CYAN)   Ordem: vault → proxy → bot$(NC)"
	@echo "$(CYAN)   Aguarde o Ollama iniciar antes do bot conectar (~30s)$(NC)"
	@echo "   Use 'make logs' para acompanhar."

down: ## Para todos os serviços
	docker compose down

restart: ## Reinicia apenas o bot (sem derrubar vault/proxy/ollama)
	docker compose restart siaa

restart-all: ## Reinicia toda a stack
	docker compose restart

# --- Subir serviços individuais ---
up-bot: ## Sobe apenas o siaa (vault, proxy e ollama já devem estar rodando)
	docker compose up -d siaa

up-vault: ## Sobe apenas o siaa-vault
	docker compose up -d siaa-vault

up-proxy: ## Sobe apenas o siaa-proxy
	docker compose up -d siaa-proxy

# --- Logs ---
logs: ## Logs de todos os serviços em tempo real
	docker compose logs -f

logs-bot: ## Logs apenas do siaa
	docker compose logs -f siaa

logs-ollama: ## Logs apenas do Ollama
	docker compose logs -f ollama

logs-vault: ## Logs apenas do siaa-vault
	docker compose logs -f siaa-vault

logs-proxy: ## Logs apenas do siaa-proxy
	docker compose logs -f siaa-proxy

# --- Ollama / Modelos ---
pull-model: ## Baixa o modelo configurado no .env (OLLAMA_MODEL_CHAT)
	docker compose run --rm ollama-init
	@echo "$(GREEN)✅ Modelo baixado.$(NC)"

pull: ## Baixa um modelo manualmente. Ex: make pull MODEL=llama3.2:3b
	docker compose exec ollama ollama pull $(MODEL)

list-models: ## Lista modelos baixados no Ollama
	docker compose exec ollama ollama list

# --- SVM ---
train: ## Força retreinamento do SVM de intenções
	docker compose run --rm -e FORCE_TRAIN=true siaa python train_svm.py
	@echo "$(GREEN)✅ SVM retreinado.$(NC)"

# --- Vault ---
vault-register: ## Registra um módulo no vault. Ex: make vault-register ID=modulo-multas NS=modulo-multas DESC='descricao'
	@echo "$(CYAN)Registrando módulo '$(ID)' no vault...$(NC)"
	@curl -s -X POST http://localhost:8002/admin/clients \
		-H "X-Admin-Password: $$(grep ADMIN_PASSWORD .env | cut -d= -f2)" \
		-H "Content-Type: application/json" \
		-d "{\"client_id\": \"$(ID)\", \"allowed_namespaces\": \"$(NS)\", \"description\": \"$(DESC)\"}" \
		| python3 -m json.tool
	@echo "$(YELLOW)⚠️  Salve o client_secret acima — não será exibido novamente.$(NC)"

vault-audit: ## Mostra o log de auditoria do vault (últimas 50 entradas)
	@curl -s http://localhost:8002/admin/audit?limit=50 \
		-H "X-Admin-Password: $$(grep ADMIN_PASSWORD .env | cut -d= -f2)" \
		| python3 -m json.tool

vault-clients: ## Lista os módulos registrados no vault
	@curl -s http://localhost:8002/admin/clients \
		-H "X-Admin-Password: $$(grep ADMIN_PASSWORD .env | cut -d= -f2)" \
		| python3 -m json.tool

# --- Proxy ---
_proxy-token: ## (interno) Obtém o token atual do proxy
	$(eval PROXY_TOKEN := $(shell curl -s http://localhost:8001/internal/current-token \
		-H "X-Secret-Key: $$(grep PROXY_SECRET_KEY .env | cut -d= -f2)" \
		| python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"))

proxy-fetch: _proxy-token ## Força busca de novos proxies públicos
	@curl -s -X POST http://localhost:8001/jobs/fetch-proxies \
		-H "X-API-Token: $(PROXY_TOKEN)" \
		| python3 -m json.tool
	@echo "$(GREEN)✅ Job de fetch iniciado.$(NC)"

proxy-validate: _proxy-token ## Força validação dos proxies existentes
	@curl -s -X POST http://localhost:8001/jobs/validate-proxies \
		-H "X-API-Token: $(PROXY_TOKEN)" \
		| python3 -m json.tool
	@echo "$(GREEN)✅ Job de validação iniciado.$(NC)"

proxy-stats: _proxy-token ## Exibe estatísticas dos proxies (ativos, validados, inativos)
	@curl -s http://localhost:8001/proxies/stats \
		-H "X-API-Token: $(PROXY_TOKEN)" \
		| python3 -m json.tool

# --- Shell de debug ---
shell: ## Shell dentro do container do siaa
	docker compose exec siaa bash

shell-ollama: ## Shell dentro do container Ollama
	docker compose exec ollama bash

shell-vault: ## Shell dentro do container siaa-vault
	docker compose exec siaa-vault bash

shell-proxy: ## Shell dentro do container siaa-proxy
	docker compose exec siaa-proxy bash

# --- Status e monitoramento ---
status: ## Status resumido de todos os containers
	@docker compose ps
	@echo ""
	@echo "$(CYAN)RAM e CPU em uso:$(NC)"
	@docker stats --no-stream --format \
		"table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# --- Manutenção ---
clean: ## Remove containers e imagens não utilizadas
	docker compose down --remove-orphans
	docker image prune -f
	@echo "$(GREEN)✅ Limpeza concluída.$(NC)"

update: ## Atualiza imagens e rebuilda todos os serviços
	docker compose pull ollama
	docker compose build siaa siaa-vault siaa-proxy
	docker compose up -d
	@echo "$(GREEN)✅ Stack atualizada.$(NC)"