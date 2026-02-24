#!/bin/bash
# =============================================================
# SIAA — Setup Oracle Cloud Free Tier (Ubuntu ARM64)
# Execute UMA VEZ após criar a VM:
#   chmod +x setup-oracle.sh && sudo ./setup-oracle.sh
# =============================================================
set -e

echo "============================================="
echo "🚀 SIAA — Setup Oracle Cloud Free Tier"
echo "============================================="

# -------------------------------------------------------
# 1. Atualiza o sistema
# -------------------------------------------------------
echo "📦 Atualizando sistema..."
apt-get update -y && apt-get upgrade -y

# -------------------------------------------------------
# 2. Instala Docker
# -------------------------------------------------------
echo "🐳 Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ubuntu || true
    echo "✅ Docker instalado."
else
    echo "✅ Docker já instalado."
fi

# -------------------------------------------------------
# 3. Instala Docker Compose plugin
# -------------------------------------------------------
echo "🐳 Instalando Docker Compose..."
if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose instalado."
else
    echo "✅ Docker Compose já instalado."
fi

# -------------------------------------------------------
# 4. Configura swap (4GB — evita OOM em picos pontuais)
# -------------------------------------------------------
echo "💾 Configurando SWAP (4GB)..."
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    echo "✅ Swap de 4GB ativado."
else
    echo "✅ Swap já configurado."
fi

sysctl vm.swappiness=5
echo "vm.swappiness=5" >> /etc/sysctl.conf

# -------------------------------------------------------
# 5. Cria estrutura de diretórios para volumes
# -------------------------------------------------------
echo "📁 Criando estrutura de diretórios..."
PROJECT_DIR="/opt/siaa"

mkdir -p "$PROJECT_DIR/volumes/siaa-data/contexts"
mkdir -p "$PROJECT_DIR/volumes/siaa-model"
mkdir -p "$PROJECT_DIR/volumes/ollama-data"
mkdir -p "$PROJECT_DIR/volumes/vault-data"
mkdir -p "$PROJECT_DIR/volumes/proxy-data"
mkdir -p "$PROJECT_DIR/src/siaa"
mkdir -p "$PROJECT_DIR/src/siaa_vault"
mkdir -p "$PROJECT_DIR/src/siaa_proxy"

chown -R ubuntu:ubuntu "$PROJECT_DIR" 2>/dev/null || true
echo "✅ Diretórios criados em $PROJECT_DIR"

# -------------------------------------------------------
# 6. Firewall (Oracle Cloud usa iptables)
#    Vault e proxy ficam APENAS na rede interna Docker.
#    Nenhuma porta interna é exposta externamente.
# -------------------------------------------------------
echo "🔥 Configurando firewall..."
iptables -I INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
echo "✅ Firewall configurado."

# -------------------------------------------------------
# 7. Instruções finais
# -------------------------------------------------------
echo ""
echo "============================================="
echo "✅ Setup concluído!"
echo "============================================="
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1. Clone o repositório:"
echo "   git clone <URL_DO_REPO> $PROJECT_DIR"
echo "   cd $PROJECT_DIR"
echo ""
echo "2. Configure o .env:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "   Chaves obrigatórias a gerar:"
echo "   MASTER_KEY  →  python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
echo "   JWT_SECRET  →  openssl rand -hex 32"
echo "   INTERNAL_SECRET_KEY  →  openssl rand -hex 32"
echo "   ADMIN_PASSWORD  →  openssl rand -hex 16"
echo ""
echo "3. Suba a stack completa:"
echo "   make up"
echo ""
echo "4. Baixe o modelo LLM:"
echo "   make pull-model"
echo ""
echo "5. Registre o siaa-bot no vault:"
echo "   make vault-register ID=siaa-bot NS='*' DESC='Bot principal'"
echo "   # Salve o client_secret retornado no .env (VAULT_CLIENT_SECRET)"
echo ""
echo "6. Acompanhe os logs:"
echo "   make logs"
echo ""
echo "📁 Estrutura de serviços:"
echo "   siaa        → bot principal   (src/siaa/)"
echo "   siaa-vault  → cofre KV        (src/siaa_vault/)  porta 8002 (interna)"
echo "   siaa-proxy  → proxy externo   (src/siaa_proxy/)  porta 8001 (interna)"
echo "   ollama      → LLM local"
echo ""
echo "📁 Volumes em: $PROJECT_DIR/volumes/"
echo "   siaa-data/   ollama-data/   vault-data/   proxy-data/"
echo ""
echo "⚠️  Faça logout e login novamente para usar Docker sem sudo."
echo "============================================="
