@echo off
setlocal
chcp 65001 > nul
TITLE Avaliador Acadêmico

cd /d "%~dp0"

echo =========================================================
echo 🎓 Iniciando o Avaliador Acadêmico...
echo =========================================================

:: 1. Checar se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Erro: Python nao foi encontrado no sistema.
    echo Por favor, instale o Python 3 ^(marque a opcao "Add Python to PATH" durante a instalacao^).
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. Criar ambiente virtual se nao existir
if not exist "venv" (
    echo 📦 Criando ambiente isolado ^(primeira execucao^)...
    python -m venv venv
)

:: 3. Ativar o ambiente virtual
call venv\Scripts\activate.bat

:: 4. Instalar dependencias
if not exist "venv\.instalado" (
    echo 📥 Instalando dependencias ^(isso pode demorar alguns minutos na primeira vez^)...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    
    echo 🌐 Configurando motor do navegador invisivel...
    pip install notebooklm-py playwright
    playwright install chromium
    
    type nul > venv\.instalado
    echo ✅ Instalacao concluida com sucesso!
)

:: 5. Configurar modo local
set CELERY_TASK_ALWAYS_EAGER=true
set API_PORT=8000

if not exist "frontend\dist" (
    echo ⚠️ Aviso: O frontend nao foi compilado.
)

:: 6. Iniciar servidor e abrir navegador
echo 🚀 Servidor iniciando...
echo O aplicativo sera aberto automaticamente no seu navegador padrao.
echo ^(Para desligar, basta fechar esta janela ou apertar Ctrl+C^)
echo ---------------------------------------------------------

:: Inicia o navegador em paralelo usando um delay simulado com ping
start /b cmd /c "ping 127.0.0.1 -n 3 > nul && start http://localhost:8000"

:: Roda o backend
python api.py
