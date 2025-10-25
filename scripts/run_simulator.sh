#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_SCRIPT="$SCRIPT_DIR/src/upa_simulator.py"
CONFIG_FILE="$SCRIPT_DIR/config/config.json"
LOG_FILE="$SCRIPT_DIR/upa_simulator.log"
PID_FILE="$SCRIPT_DIR/upa_simulator.pid"
REQUIREMENTS_FILE="$SCRIPT_DIR/src/requirements.txt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

check_requirements() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 não encontrado. Instale com: sudo apt-get install python3"
        exit 1
    fi

    if [ ! -d "$VENV_DIR" ]; then
        print_info "Criando ambiente virtual..."
        python3 -m venv "$VENV_DIR"
        print_success "Ambiente virtual criado"

        print_info "Instalando dependências..."
        "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
        print_success "Dependências instaladas"
    fi

    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Arquivo config.json não encontrado em $CONFIG_FILE"
        exit 1
    fi
}

start_simulator() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_error "Simulador já está rodando (PID: $PID)"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi

    print_info "Iniciando UPA Simulator..."
    check_requirements

    nohup "$VENV_DIR/bin/python" "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"

    sleep 2
    if ps -p "$PID" > /dev/null 2>&1; then
        print_success "Simulador iniciado (PID: $PID)"
        print_info "Logs: tail -f $LOG_FILE"
    else
        print_error "Falha ao iniciar simulador. Verifique os logs."
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_simulator() {
    if [ ! -f "$PID_FILE" ]; then
        print_error "Simulador não está rodando"
        exit 1
    fi

    PID=$(cat "$PID_FILE")

    if ps -p "$PID" > /dev/null 2>&1; then
        print_info "Parando simulador (PID: $PID)..."
        kill "$PID"

        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        if ps -p "$PID" > /dev/null 2>&1; then
            print_info "Forçando parada..."
            kill -9 "$PID"
        fi

        rm -f "$PID_FILE"
        print_success "Simulador parado"
    else
        print_error "Processo não encontrado (PID: $PID)"
        rm -f "$PID_FILE"
    fi
}

status_simulator() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_success "Simulador está rodando (PID: $PID)"

            echo ""
            echo "Informações do processo:"
            ps -p "$PID" -o pid,ppid,cmd,%mem,%cpu,etime

            if [ -f "$LOG_FILE" ]; then
                echo ""
                echo "Últimas 10 linhas do log:"
                tail -n 10 "$LOG_FILE"
            fi

            exit 0
        else
            print_error "Simulador não está rodando (PID obsoleto: $PID)"
            rm -f "$PID_FILE"
            exit 1
        fi
    else
        print_error "Simulador não está rodando"
        exit 1
    fi
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "Exibindo logs (Ctrl+C para sair)..."
        tail -f "$LOG_FILE"
    else
        print_error "Arquivo de log não encontrado: $LOG_FILE"
        exit 1
    fi
}

restart_simulator() {
    print_info "Reiniciando simulador..."
    stop_simulator 2>/dev/null || true
    sleep 2
    start_simulator
}

case "${1:-}" in
    start)
        start_simulator
        ;;
    stop)
        stop_simulator
        ;;
    restart)
        restart_simulator
        ;;
    status)
        status_simulator
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "UPA Simulator - Script de Gerenciamento"
        echo ""
        echo "Uso: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Comandos:"
        echo "  start    - Inicia o simulador"
        echo "  stop     - Para o simulador"
        echo "  restart  - Reinicia o simulador"
        echo "  status   - Verifica status do simulador"
        echo "  logs     - Exibe logs em tempo real"
        echo ""
        exit 1
        ;;
esac

exit 0