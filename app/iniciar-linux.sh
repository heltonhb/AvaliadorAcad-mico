#!/usr/bin/env bash
# =====================================================================
# Avaliador Acadêmico - Inicializador para Linux
# =====================================================================

set -e

# Mudar para o diretório de onde o script está sendo chamado
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================="
echo "🎓 Iniciando o Avaliador Acadêmico..."
echo "========================================================="

# 1. Checar se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Erro: Python 3 não foi encontrado no sistema."
    echo "Por favor, instale o Python 3 para rodar este aplicativo."
    read -p "Pressione ENTER para sair..."
    exit 1
fi

# 2. Criar ambiente virtual isolado (apenas na primeira vez)
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente isolado (primeira execução)..."
    python3 -m venv venv
fi

# 3. Ativar o ambiente virtual
source venv/bin/activate

# 4. Instalar dependências (apenas na primeira vez ou se houver mudança)
if [ ! -f "venv/.instalado" ]; then
    echo "📥 Instalando dependências (isso pode demorar alguns minutos na primeira vez)..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Instalar a CLI do NotebookLM e o motor de navegador (Playwright)
    echo "🌐 Configurando motor do navegador invisível..."
    pip install notebooklm-py playwright
    playwright install chromium
    
    # Marca como instalado
    touch venv/.instalado
    echo "✅ Instalação concluída com sucesso!"
fi

# 5. Configurar o modo de execução local (Stand-alone, sem Redis/Celery)
export CELERY_TASK_ALWAYS_EAGER=true
export API_PORT=8000

# 6. Checar se o frontend já foi construído
if [ ! -d "frontend/dist" ]; then
    echo "⚠️ Aviso: O frontend não foi compilado."
    echo "Se você está apenas rodando, você deve primeiro compilar o frontend."
    echo "Rode: cd frontend && npm install && npm run build"
fi

# 7. Iniciar o servidor e abrir o navegador
echo "🚀 Servidor iniciando..."
echo "O aplicativo será aberto automaticamente no seu navegador padrão."
echo "(Para desligar, basta fechar esta janela do terminal ou apertar Ctrl+C)"
echo "---------------------------------------------------------"

# Tentar abrir o navegador de forma assíncrona com um leve atraso
(sleep 2 && xdg-open "http://localhost:8000" &> /dev/null) &

# Roda o backend
python3 api.py
