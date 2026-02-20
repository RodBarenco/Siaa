# =============================================================
# SIAA — Makefile
# Target: Oracle Cloud Free Tier ARM64 (4 OCPU / 24GB RAM)
# =============================================================
.PHONY: help build up down logs restart train shell clean pull-model status

GREEN  = \033[0;32m
YELLOW = \033[1;33m
CYAN   = \033[0;36m
NC     = \033[0m

help: ## Mostra esta ajuda
	@echo "$(GREEN)SIAA — Comandos disponíveis:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(NC) %s\n", $$1, $$2}'

# --- Setup ---
setup-dirs: ## Cria todos os diretórios de volume
	mkdir -p volumes/siaa-data/contexts volumes/siaa-model volumes/ollama-data
	@echo "$(GREEN)✅ Diretórios criados.$(NC)"

# --- Build e ciclo de vida ---
build: ## Builda a imagem do Siaa
	docker compose build siaa

up: setup-dirs ## Sobe todos os serviços (Ollama + Bot)
	docker compose up -d
	@echo "$(GREEN)✅ Stack rodando.$(NC)"
	@echo "$(CYAN)   Aguarde o Ollama iniciar antes do bot conectar (~30s)$(NC)"
	@echo "   Use 'make logs' para acompanhar."

down: ## Para todos os serviços
	docker compose down

restart: ## Reinicia apenas o bot (sem derrubar Ollama)
	docker compose restart siaa

# --- Logs ---
logs: ## Logs de todos os serviços em tempo real
	docker compose logs -f

logs-bot: ## Logs apenas do bot
	docker compose logs -f siaa

logs-ollama: ## Logs apenas do Ollama
	docker compose logs -f ollama

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

# --- Debug ---
shell: ## Abre shell dentro do container do bot
	docker compose exec siaa bash

shell-ollama: ## Abre shell dentro do container Ollama
	docker compose exec ollama bash

status: ## Status resumido de todos os containers
	@docker compose ps
	@echo ""
	@echo "$(CYAN)RAM em uso:$(NC)"
	@docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# --- Manutenção ---
clean: ## Remove containers e imagens não utilizadas
	docker compose down --remove-orphans
	docker image prune -f
	@echo "$(GREEN)✅ Limpeza concluída.$(NC)"

update: ## Atualiza imagem do Ollama e rebuilda o bot
	docker compose pull ollama
	docker compose build siaa
	docker compose up -d
	@echo "$(GREEN)✅ Stack atualizada.$(NC)"
