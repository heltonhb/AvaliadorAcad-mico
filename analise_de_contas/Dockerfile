FROM python:3.11-slim

# Evitar que o Python grave arquivos .pyc e forçar stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar Node.js para build do frontend + poppler-utils (OCR) + ghostscript (compressão de PDFs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    poppler-utils \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependências Python
COPY requirements.txt .

# Instalar pacotes pip do requirements e pacotes extras para API
RUN pip install --no-cache-dir -r requirements.txt \
    fastapi uvicorn python-multipart pydantic

# O pacote notebooklm-py é instalado via uv
RUN pip install --no-cache-dir uv && \
    uv tool install notebooklm-py

# Garantir que ferramentas instaladas pelo uv fiquem no path
ENV PATH="/root/.local/bin:$PATH"

# Copiar código da aplicação (excluindo .env via .dockerignore)
COPY . .

# Build do frontend React
RUN cd frontend && npm ci --no-audit --no-fund && npm run build

# Permissão de execução para o script de inicialização
RUN chmod +x start.sh

# Porta: 8000 (FastAPI)
EXPOSE 8000

# Comando padrão: inicia a API com uvicorn
# ENV vars sensíveis (ANALISE_PASSWORD) devem ser injetadas
# em runtime (docker run -e K=V ou docker-compose), NUNCA via .env dentro da imagem.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
