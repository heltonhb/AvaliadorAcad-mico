#!/usr/bin/env bash
# kill_all.sh - Mata todos os processos relacionados ao AnaliseTextos
# Uso: ./kill_all.sh

set -euo pipefail

echo "🛑 Encerrando processos do AnaliseTextos..."

# Lista de padrões de processos a serem finalizados
PATTERNS=(
    "uvicorn"
    "celery"
    "vite"
    "node"   # caso o frontend esteja rodando via node diretamente
    "python.*pipeline.runner"
)

for pattern in "${PATTERNS[@]}"; do
    echo "🔍 Procurando por: $pattern"
    pkill -f "$pattern" || true
done

# Também garante que qualquer worker celery em modo solo seja finalizado
pkill -f "celery worker" || true

echo "✅ Todos os processos relacionados foram encerrados."