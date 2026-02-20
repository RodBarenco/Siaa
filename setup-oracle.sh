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
    # Permite usar Docker sem sudo (requer novo login)
    usermod -aG docker ubuntu || true
    echo "✅ Docker instalado."
else
    echo "✅ Docker já instalado."
fi

# -------------------------------------------------------
# 3. Instala Docker Compose (plugin moderno)
# -------------------------------------------------------
echo "🐳 Instalando Docker Compose..."
if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose instalado."
else
    echo "✅ Docker Compose já instalado."
fi

# -------------------------------------------------------
# 4. Configura swap (pequeno — 24GB RAM é mais que suficiente,
#    mas swap evita OOM killer em picos pontuais)
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

# Swappiness baixa — RAM é abundante, só usa swap em emergência
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

# Permissões para o usuário ubuntu
chown -R ubuntu:ubuntu "$PROJECT_DIR" 2>/dev/null || true

echo "✅ Diretórios criados em $PROJECT_DIR"

# -------------------------------------------------------
# 6. Regras de firewall (Oracle Cloud usa iptables)
# -------------------------------------------------------
echo "🔥 Configurando firewall..."
# Oracle Cloud bloqueia portas por padrão — o Siaa usa só Telegram (saída)
# Nenhuma porta de entrada é necessária para o bot funcionar
iptables -I INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
echo "✅ Firewall configurado."

# -------------------------------------------------------
# 7. Instrucções finais
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
echo "   nano .env  # preencha TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OLLAMA_URL"
echo ""
echo "3. Copie o dataset para o volume:"
echo "   cp volumes/siaa-data/intent_dataset.json $PROJECT_DIR/volumes/siaa-data/"
echo ""
echo "4. Inicie o bot:"
echo "   docker compose up -d --build"
echo ""
echo "5. Veja os logs:"
echo "   docker compose logs -f"
echo ""
echo "⚠️  IMPORTANTE: Faça logout e login novamente para usar Docker sem sudo."
echo "============================================="
