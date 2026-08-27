#!/usr/bin/env bash
# =====================================================================
# Avaliador Acadêmico - Inicializador para Mac
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
    echo "Baixe o Python em: https://www.python.org/downloads/macos/"
    read -p "Pressione ENTER para sair..."
    exit 1
fi

# 2. Criar ambiente virtual isolado
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente isolado (primeira execução)..."
    python3 -m venv venv
fi

# 3. Ativar o ambiente virtual
source venv/bin/activate

# 4. Instalar dependências
if [ ! -f "venv/.instalado" ]; then
    echo "📥 Instalando dependências (isso pode demorar alguns minutos na primeira vez)..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "🌐 Configurando motor do navegador invisível..."
    pip install notebooklm-py playwright
    playwright install chromium
    
    touch venv/.instalado
    echo "✅ Instalação concluída com sucesso!"
fi

# 5. Configurar o modo de execução local
export CELERY_TASK_ALWAYS_EAGER=true
export API_PORT=8000

# 6. Checar frontend
if [ ! -d "frontend/dist" ]; then
    echo "⚠️ Aviso: O frontend não foi compilado."
fi

# 7. Iniciar o servidor e abrir o navegador (Mac usa 'open')
echo "🚀 Servidor iniciando..."
echo "O aplicativo será aberto automaticamente no seu navegador padrão."
echo "(Para desligar, basta fechar esta janela do terminal ou apertar Ctrl+C)"
echo "---------------------------------------------------------"

(sleep 2 && open "http://localhost:8000" &> /dev/null) &

python3 api.py
