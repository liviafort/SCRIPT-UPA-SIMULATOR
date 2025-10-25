#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/upa-simulator"
LOG_DIR="/var/log/upa-simulator"
SERVICE_NAME="upa-simulator"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

if [ "$EUID" -ne 0 ]; then
    print_error "Este script deve ser executado como root ou com sudo"
    exit 1
fi

print_header "UPA Simulator - Instalação no Servidor"

print_info "Verificando Python 3..."
if ! command -v python3 &> /dev/null; then
    print_info "Instalando Python 3..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
    print_success "Python 3 instalado"
else
    PYTHON_VERSION=$(python3 --version)
    print_success "Python 3 encontrado: $PYTHON_VERSION"
fi

print_info "Criando diretórios..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
print_success "Diretórios criados"

print_info "Copiando arquivos..."
CURRENT_DIR=$(pwd)

if [ -f "$CURRENT_DIR/upa_simulator.py" ]; then
    cp "$CURRENT_DIR/upa_simulator.py" "$INSTALL_DIR/"
    cp "$CURRENT_DIR/config.json" "$INSTALL_DIR/"
    cp "$CURRENT_DIR/requirements.txt" "$INSTALL_DIR/"
    cp "$CURRENT_DIR/run_simulator.sh" "$INSTALL_DIR/"
    cp "$CURRENT_DIR/SIMULATOR_README.md" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/run_simulator.sh"
    print_success "Arquivos copiados para $INSTALL_DIR"
else
    print_error "Arquivos não encontrados no diretório atual"
    print_info "Execute este script no diretório onde estão os arquivos do simulador"
    exit 1
fi

print_info "Criando ambiente virtual Python..."
cd "$INSTALL_DIR"
python3 -m venv venv
print_success "Ambiente virtual criado"

print_info "Instalando dependências Python..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r requirements.txt
print_success "Dependências instaladas"

print_info "Configurando URLs dos serviços..."
read -p "URL do serviço Monitoring [http://localhost:8086]: " MONITORING_URL
MONITORING_URL=${MONITORING_URL:-http://localhost:8086}

read -p "URL do serviço Gateway [http://localhost:8084]: " GATEWAY_URL
GATEWAY_URL=${GATEWAY_URL:-http://localhost:8084}

python3 << EOF
import json

with open('$INSTALL_DIR/config.json', 'r') as f:
    config = json.load(f)

config['monitoring_service']['base_url'] = '$MONITORING_URL'
config['gateway_service']['base_url'] = '$GATEWAY_URL'

with open('$INSTALL_DIR/config.json', 'w') as f:
    json.dump(config, f, indent=2)
EOF

print_success "URLs configuradas"

print_info "Instalando serviço systemd..."
if [ -f "$CURRENT_DIR/upa-simulator.service" ]; then
    cp "$CURRENT_DIR/upa-simulator.service" "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
    print_success "Serviço systemd instalado"
else
    print_info "Arquivo upa-simulator.service não encontrado, pulando instalação do serviço"
fi

print_info "Configurando permissões..."
chown -R root:root "$INSTALL_DIR"
chown -R root:root "$LOG_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 755 "$LOG_DIR"
print_success "Permissões configuradas"

print_header "Teste de Conectividade"

print_info "Testando conexão com Monitoring Service ($MONITORING_URL)..."
if curl -s -f -m 5 "$MONITORING_URL/actuator/health" > /dev/null 2>&1; then
    print_success "Monitoring Service acessível"
else
    print_error "Monitoring Service não acessível"
    print_info "Verifique se o serviço está rodando e a URL está correta"
fi

print_info "Testando conexão com Gateway Service ($GATEWAY_URL)..."
if curl -s -f -m 5 "$GATEWAY_URL/actuator/health" > /dev/null 2>&1; then
    print_success "Gateway Service acessível"
else
    print_error "Gateway Service não acessível"
    print_info "Verifique se o serviço está rodando e a URL está correta"
fi

print_header "Instalação Concluída!"

echo ""
echo "Diretório de instalação: $INSTALL_DIR"
echo "Diretório de logs: $LOG_DIR"
echo ""
echo "Próximos passos:"
echo ""
echo "1. Editar configuração (se necessário):"
echo "   nano $INSTALL_DIR/config.json"
echo ""
echo "2. Opção A - Executar manualmente:"
echo "   cd $INSTALL_DIR"
echo "   ./run_simulator.sh start"
echo "   ./run_simulator.sh status"
echo "   ./run_simulator.sh logs"
echo ""
echo "3. Opção B - Executar como serviço systemd (recomendado):"
echo "   systemctl enable $SERVICE_NAME"
echo "   systemctl start $SERVICE_NAME"
echo "   systemctl status $SERVICE_NAME"
echo "   journalctl -u $SERVICE_NAME -f"
echo ""
echo "4. Verificar logs:"
echo "   tail -f $INSTALL_DIR/upa_simulator.log"
echo "   # ou"
echo "   tail -f $LOG_DIR/upa-simulator.log"
echo ""
print_success "Instalação finalizada com sucesso!"