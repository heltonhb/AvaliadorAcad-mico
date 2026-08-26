#!/usr/bin/env bash
# =====================================================================
# AnaliseTextos — Script de inicialização unificado
# =====================================================================
# Uso:
#   ./start.sh dev          # Desenvolvimento (sem Redis, pipeline inline)
#   ./start.sh prod         # Produção local (com Redis + Celery worker)
#   ./start.sh docker       # Via Docker Compose (recomendado para produção)
#   ./start.sh test         # Rodar testes
#   ./start.sh help         # Mostra esta ajuda
# =====================================================================

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------
# Verificações iniciais
# ---------------------------------------------------------------
check_env() {
    if [[ ! -f .env ]]; then
        log_warn "Arquivo .env não encontrado. Copiando de .env.example..."
        cp .env.example .env
        log_warn "Edite .env e defina JWT_SECRET antes de continuar em produção!"
    fi
}

check_venv() {
    if [[ ! -d venv ]]; then
        log_info "Criando virtual environment..."
        python3 -m venv venv
    fi
    # shellcheck disable=SC1091
    source venv/bin/activate
    if ! pip show fastapi &>/dev/null; then
        log_info "Instalando dependências Python..."
        pip install -q -r requirements.txt
    fi
}

check_redis() {
    if ! command -v redis-server &> /dev/null; then
        log_error "redis-server não instalado. Instale com: sudo apt-get install redis-server"
        exit 1
    fi
    if ! redis-cli ping &> /dev/null; then
        log_info "Iniciando Redis..."
        redis-server --daemonize yes
        sleep 1
    fi
    log_ok "Redis rodando"
}

# ---------------------------------------------------------------
# Modos de execução
# ---------------------------------------------------------------
run_dev() {
    log_info "Modo DESENVOLVIMENTO (pipeline inline, sem Redis)"
    check_env
    check_venv
    export CELERY_TASK_ALWAYS_EAGER=true
    log_ok "Iniciando API em http://localhost:8000"
    log_ok "Swagger UI em http://localhost:8000/docs"
    uvicorn api:app --reload --host 0.0.0.0 --port 8000
}

run_prod() {
    log_info "Modo PRODUÇÃO LOCAL (com Redis + Celery worker)"
    check_env
    check_venv
    check_redis

    # Iniciar frontend (se existir)
    FRONTEND_PID=""
    if [[ -d frontend ]]; then
        log_info "Iniciando frontend..."
        (cd frontend && npm run dev) &
        FRONTEND_PID=$!
        log_ok "Frontend iniciado (PID: $FRONTEND_PID)"
    fi

    log_info "Iniciando Celery worker..."
    export PYTHONPATH="/home/helton/AnaliseTextos/app${PYTHONPATH:+:$PYTHONPATH}"
    celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo &
    WORKER_PID=$!
    log_ok "Worker iniciado (PID: $WORKER_PID)"

    # Trap para matar worker e frontend ao sair
    trap "kill $WORKER_PID 2>/dev/null; log_info 'Worker finalizado'; if [[ -n "$FRONTEND_PID" ]]; then kill $FRONTEND_PID 2>/dev/null; log_info 'Frontend finalizado'; fi" INT TERM EXIT

    log_ok "Iniciando API em http://localhost:8000"
    log_ok "Swagger UI em http://localhost:8000/docs"
    uvicorn api:app --reload --host 0.0.0.0 --port 8000
}

run_docker() {
    log_info "Modo DOCKER (stack completa: nginx + backend + worker + redis)"
    if ! command -v docker &> /dev/null; then
        log_error "Docker não instalado"
        exit 1
    fi
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose não disponível"
        exit 1
    fi
    check_env
    log_ok "Subindo containers..."
    docker compose up -d
    log_ok "Aplicação rodando em http://localhost:8000"
    log_ok "Para ver logs: docker compose logs -f"
    log_ok "Para parar: docker compose down"
}

run_test() {
    log_info "Rodando testes..."
    check_venv
    python -m pytest tests/ -v --tb=short
}

run_lint() {
    log_info "Rodando linters..."
    check_venv
    pip install -q ruff mypy
    ruff check .
    mypy api.py auth.py security.py utils.py pipeline/
}

# ---------------------------------------------------------------
# Help
# ---------------------------------------------------------------
show_help() {
    cat <<EOF
${BLUE}AnaliseTextos — Script de inicialização${NC}

${GREEN}Uso:${NC} ./start.sh <comando>

${GREEN}Comandos:${NC}
  ${YELLOW}dev${NC}      Desenvolvimento rápido (sem Redis, pipeline inline)
  ${YELLOW}prod${NC}     Produção local (Redis + Celery worker + API)
  ${YELLOW}docker${NC}   Stack completa via Docker Compose (nginx + backend + worker + redis)
  ${YELLOW}test${NC}     Rodar suite de testes (91 testes)
  ${YELLOW}lint${NC}     Rodar ruff + mypy
  ${YELLOW}help${NC}     Mostra esta ajuda

${GREEN}Exemplos:${NC}
  ./start.sh dev        # Desenvolvimento rápido
  ./start.sh docker     # Produção via Docker
  ./start.sh test       # Validar alterações

${GREEN}Endpoints principais:${NC}
  http://localhost:8000/api/health/live   - Liveness probe
  http://localhost:8000/api/health/ready  - Readiness probe
  http://localhost:8000/docs              - Swagger UI
  http://localhost:8000/redoc             - ReDoc

${GREEN}Variáveis de ambiente (.env):${NC}
  JWT_SECRET                - Obrigatório em produção (openssl rand -hex 32)
  CELERY_TASK_ALWAYS_EAGER  - 'true' para rodar pipeline inline (dev)
  REDIS_URL                 - URL do Redis (padrão: redis://localhost:6379/0)
  LOG_LEVEL                 - DEBUG, INFO, WARNING, ERROR
  LOG_FORMAT                - json ou text

EOF
}

# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
main() {
    case "${1:-help}" in
        dev)      run_dev ;;
        prod)     run_prod ;;
        docker)   run_docker ;;
        test)     run_test ;;
        lint)     run_lint ;;
        help|*)   show_help ;;
    esac
}

main "$@"