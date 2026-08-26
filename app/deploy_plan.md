# Plano de Deploy do AnaliseTextos em Serviço de Nuvem Gratuito

## Objetivo
Colocar a aplicação AnaliseTextos (backend API, worker Celery e frontend) em execução em um provedor de nuvem que ofereça camada gratuita, utilizando Docker (ou Docker Compose) e serviços gerenciados (Redis) quando possível, mantendo o mínimo de custos e garantindo funcionalidade completa.

## Estratégia Geral
1. **Escolher um provedor** com camada gratuita que suporte:
   - Execução de containers Docker (ou Docker Compose).
   - Serviço Redis gerenciado (ou a possibilidade de rodar Redis dentro de um container dentro do limite de memória).
   - Variáveis de ambiente configuráveis via UI ou secrets.
   - Opção de múltiplos serviços (web + worker) ou um único compose.
2. **Adaptar a aplicação** para:
   - Instalar o binário `notebooklm` dentro das imagens backend e worker (necessário para o pipeline).
   - Utilizar o Redis externo via variável de ambiente `REDIS_URL` (desativando a inicialização local do Redis no `start.sh` quando estiver em produção).
   - Expor as portas necessárias (backend 8000, frontend 5173, Redis 6379 – embora o Redis possa ficar interno).
   - Permitir que o frontend seja servido como um serviço separado (modo dev) ou como build estático.
3. **Definir arquivos de configuração**:
   - `Dockerfile.backend` e `Dockerfile.worker` (baseados na imagem `python:3.12-slim` ou similar).
   - `Dockerfile.frontend` (baseado em `node:20-alpine`).
   - `docker-compose.yml` para testes locais e como base para os provedores que aceitam compose (Render via Render.yaml, Railway aceita compose direto).
   - Arquivo `.env` de exemplo com as variáveis necessárias.
4. **Passos de deploy** para cada provedor escolhido (Render e Railway como exemplos principais).
5. **Checklist de validação** antes e após o deploy.
6. **Considerações de limites** (memória, CPU, horas/mês, storage efêmero) e como mitigá‑los.

---

## 1. Provedores Candidatos (Camada Gratuita)

| Provedor | Oferta Gratuita Relevante | Comentário |
|----------|--------------------------|------------|
| **Render** | Web Service (Docker) + Worker Service + Redis (managed) – plano Free (750 h/mês, 512 MiB RAM) | Fácil de ligar múltiplos serviços via `render.yaml` ou UI. |
| **Railway** | Web Service, Worker, Redis (managed) – plano Free (~500 h/mês, 512 MiB RAM) | UI intuitiva, variáveis de ambiente e secrets fáceis. |
| **Fly.io** | 3 VMs compartilhadas (CPU < 1 core, 256 MiB RAM cada) – 160 GB‑hora/mês (~3 VMs 24/7) | Precisa de um pouco mais de configuração (flyctl) mas permite controle total. |
| **Google Cloud Run** | 2 mil requisições/mês, 360 000 GB‑s, 2 GiB‑s de memória | Não ideal para worker Celery de longa duração (melhor para APIs event‑driven). |
| **AWS Free Tier** | t2.micro (750 h/mês) + ElastiCache free (750 h) | Mais trabalhoso (EC2/EBS manual). |

**Recomendação inicial**: **Render** (por ter suporte nativo a workers e Redis gerenciado) ou **Railway** (simplicidade). O plano a seguir descreve ambas as opções.

---

## 2. Arquivos Necessários

### 2.1 Dockerfiles

#### `Dockerfile.backend` (e `Dockerfile.worker` – podem ser idênticos, diferenciando apenas o comando de entrada)
```dockerfile
# ---- Base Imagem ----
FROM python:3.12-slim

# ---- Dependências do sistema ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        gnupg \
        && rm -rf /var/lib/apt/lists/*

# ---- Instalação do NotebookLM CLI (ajuste URL/versão conforme oficial) ----
# Exemplo genérico – substituir pelo link real de download do pacote .deb ou script.
RUN wget -qO /tmp/notebooklm.deb https://example.com/notebooklm_latest_amd64.deb && \
    dpkg -i /tmp/notebooklm.deb && \
    rm -f /tmp/notebooklm.deb && \
    # Caso o pacote falhe por dependências, tentar instalar as faltantes:
    apt-get install -f -y || true

# ---- Criação do diretório de trabalho ----
WORKDIR /app

# ---- Copiar apenas os arquivos de dependência primeiro (para melhor cache) ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copiar o restante do código ----
COPY . .

# ---- Variáveis de ambiente padrão (podem ser sobrescritas no runtime) ----
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=text

# ---- Entrypoint padrão (será sobrescrito nos serviços) ----
CMD ["python", "-m", "pipeline.runner", "--help"]  # apenas um placeholder
```

> **Observação**: O `Dockerfile.worker` pode ser exatamente o mesmo; a diferença está no `command` definido no compose ou na configuração do serviço worker (celery worker).

#### `Dockerfile.frontend`
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build   # gera a pasta /app/dist (ou .output se for Vite)

# ---- Estágio de produção (servir com um servidor leve) ----
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Copie um nginx.conf customizado se precisar de rewrite para SPA (opcional)
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Se o provedor não suportar builds multi‑estágios, pode simplesmente usar a imagem `node:20-alpine` e rodar `npm run dev` em modo desenvolvimento (o consumo de CPU é baixo o suficiente para a camada gratuita).

### 2.2 docker-compose.yml (para testes locais e como base)
```yaml
version: "3.8"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - redis
    command: >
      sh -c "
        uvicorn api:app --host 0.0.0.0 --port 8000 --reload
      "

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    env_file: .env
    depends_on:
      - redis
    command: >
      sh -c "
        celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo
      "

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    ports:
      - "5173:5173"
    env_file: .env
    # Caso queira passar a URL do backend como variável de build:
    # environment:
    #   VITE_API_URL: http://backend:8000

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: ["redis-server", "--save", "60", "1", "--loglevel", "warning"]
```

### 2.3 Arquivo `.env` de exemplo
```dotenv
# Segredo JWT – gere com: openssl rand -hex 32
JWT_SECRET=__REPLACE_WITH_32_HEX_CHARS__

# URL do Redis (se estiver usando o serviço gerenciado do provedor, substitua)
# Exemplo para Redis local (docker compose):
REDIS_URL=redis://localhost:6379/0
# Exemplo para Redis gerenciado (Render/Railway):
# REDIS_URL=rediss://:<password>@<host>:6379/0

LOG_LEVEL=INFO
LOG_FORMAT=text

# Opcional: caso queira forçar o modo eager (sem worker) – NÃO recomendado em prod
# CELERY_TASK_ALWAYS_EAGER=false

# Frontend (se precisar informar a URL do backend em tempo de build ou runtime)
# VITE_API_URL=http://localhost:8000
```

### 2.4 Alterações no `start.sh` (para uso local apenas)
- O `start.sh` já contém a lógica para iniciar o worker com `PYTHONPATH` exportado.
- Em produção (quando usando Docker), o `start.sh` **não será executado**; o comando de inicialização vem do Dockerfile/compose.
- Não é necessário modificar o `start.sh` para o deploy em nuvem, mas garante que a variável `PYTHONPATH` esteja correta caso alguém ainda queira usar o script localmente.

---

## 3. Passos de Deploy

### 3.1 Render (usando Render.yaml)

1. **Criar o arquivo `render.yaml` na raiz do repositório**:
   ```yaml
   services:
     - type: web
       name: analisetextos-backend
       env: docker
       plan: free
       dockerfilePath: Dockerfile.backend
       envVars:
         - key: JWT_SECRET
           fromSecret: jwt_secret
         - key: REDIS_URL
           fromSecret: redis_url
         - key: LOG_LEVEL
           value: INFO
         - key: LOG_FORMAT
           value: text
       autoDeploy: true

     - type: worker
       name: analisetextos-worker
       env: docker
       plan: free
       dockerfilePath: Dockerfile.worker
       envVars:
         - key: JWT_SECRET
           fromSecret: jwt_secret
         - key: REDIS_URL
           fromSecret: redis_url
         - key: LOG_LEVEL
           value: INFO
         - key: LOG_FORMAT
           value: text
       autoDeploy: true

     - type: web
       name: analisetextos-frontend
       env: docker
       plan: free
       dockerfilePath: ./frontend/Dockerfile.frontend   # ajuste se usar outro nome
       envVars:
         - key: VITE_API_URL
           value: https://analisetextos-backend.onrender.com
       autoDeploy: true

   databases:
     - name: analisetextos-redis
       plan: free
       ipAllowList: []   # permite acesso de serviços dentro da mesma conta
   ```

2. **Criar secrets no painel do Render**:
   - `jwt_secret`: saída de `openssl rand -hex 32`.
   - `redis_url`: será preenchido automaticamente ao criar o banco Redis acima ( formato `rediss://:<password>@<host>:6379/0` ).

3. **No Render Dashboard**:
   - Clique em **New → Blueprint**, conecte seu repositório GitHub/GitLab/Bitbucket.
   - Selecione o `render.yaml` criado.
   - O Render irá ler o arquivo, criar os três serviços (backend, worker, frontend) e o banco Redis.
   - Aguarde o build (alguns minutos). Quando todos estiverem **Live**, teste:
     - Backend API: `https://analisetextos-backend.onrender.com/docs`
     - Frontend: `https://analisetextos-frontend.onrender.com`

4. **Health Checks** (opcional, mas recomendado):
   - Em cada serviço web, defina a *Health Check Path* como `/api/health/live` (backend) ou `/` (frontend) para que o Render considere o serviço saudável antes de tráfego.

### 3.2 Railway

1. **Criar um novo projeto** → **Deploy from Repo** → conecte seu repositório.
2. **Adicionar o plugin Redis**:
   - No painel do projeto, vá em **Plugins → Add Redis**, escolha o plano **Free**.
   - O plugin criará uma variável de ambiente chamada `DATABASE_URL` (ou similar) que contém a conexão Redis. Renomeie ou copie para `REDIS_URL` se necessário (ex.: `REDIS_URL=${DATABASE_URL}`).
3. **Definir variáveis de ambiente** (no painel **Variables**):
   - `JWT_SECRET` → `<32 hex chars>`
   - `REDIS_URL` → (valor do plugin Redis, ou `redis://:<password>@<host>:6379/0`)
   - `LOG_LEVEL=INFO`
   - `LOG_FORMAT=text`
   - (Opcional) `VITE_API_URL=https://<seu-frontend>.railway.app`
4. **Configurar os serviços**:
   - **Backend Service**:
     - Source: seu repositório.
     - Dockerfile path: `Dockerfile.backend`.
     - Start Command: `uvicorn api:app --host 0.0.0.0 --port 8000`.
   - **Worker Service**:
     - Source: mesmo repositório.
     - Dockerfile path: `Dockerfile.worker`.
     - Start Command: `celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo`.
   - **Frontend Service**:
     - Source: mesmo repositório (ou subpasta `frontend` se o repositório for monorepo).
     - Dockerfile path: `./frontend/Dockerfile.frontend`.
     - Start Command: (nginx já está no CMD do Dockerfile, então pode deixar em branco ou usar `nginx -g "daemon off;"`).
   - Em cada serviço, ative **Auto Deploy** para que atualizações no repo disparem um novo build.
5. **Aguardar o deploy** (Railway mostra logs de build). Quando estiver em estado **Healthy**, acesse:
   - Backend API: `https://<seu-backend>.railway.app/docs`
   - Frontend: `https://<seu-frontend>.railway.app`

### 3.3 Fly.io (alternativa)

1. **Instalar o flyctl** e fazer login.
2. **Inicializar a aplicação**:
   ```bash
   flyctl launch --name analisetextos --copy-config
   ```
   - Isso criará um `fly.toml` baseado no Dockerfile detectado (precisaremos ter um `Dockerfile` que rode tudo ou usar múltiplos processos com `[services]`).
   - Como o flyctl atualmente suporta apenas um único processo por serviço, podemos usar um **supervisor** (ex.: `supervisord`) ou rodar múltiplas apps (backend, worker, frontend) como aplicações separadas.
   - Simplificar: criar três aplicações Fly (`analisetextos-backend`, `analisetextos-worker`, `analisetextos-frontend`) cada uma apontando para o mesmo repo mas com diferentes `Dockerfile` e comandos.
3. **Criar um Redis gerenciado** (ex.: usar Upstash ou o add‑on Redis da Fly):
   ```bash
   # Exemplo Upstash (gratuito até certo limite)
   flyctl secrets add REDIS_URL=rediss://:<password>@<host>:6379/0
   ```
4. **Definir secrets**:
   ```bash
   flyctl secrets add JWT_SECRET=<32 hex chars>
   flyctl secrets add LOG_LEVEL=INFO
   flyctl secrets add LOG_FORMAT=text
   ```
5. **Definir o `fly.toml` para cada app** (exemplo para backend):
   ```toml
   app = "analisetextos-backend"
   kill_signal = "SIGINT"
   kill_timeout = 5

   [experimental]
     allowed_public_ports = []
     auto_rollback = true

   [[services]]
     internal_port = 8000
     protocol = "tcp"
     [[services.ports]]
       port = 80
       handlers = ["http"]
     [[services.tcp_checks]]
       interval = "10s"
       timeout = "2s"
       restart_limit = 0
   ```
   - Repetir para worker (porta não exposta, apenas interna) e frontend (porta 80 → 5173 se usar nginx ou ajustar).
6. **Deploy**:
   ```bash
   flyctl deploy --remote-only --app analisetextos-backend
   flyctl deploy --remote-only --app analisetextos-worker
   flyctl deploy --remote-only --app analisetextos-frontend
   ```
7. **Verificar**:
   - Backend: `https://analisetextos-backend.fly.dev/docs`
   - Frontend: `https://analisetextos-frontend.fly.dev`

> O Fly.io demanda um pouco mais de trabalho devido à limitação de um único processo por app, mas ainda está dentro da camada gratuita (3 VMs compartilhadas).

---

## 4. Checklist Pré‑Deploy

| Item | Verificação |
|------|--------------|
| **Dockerfiles** | Testam localmente: `docker build -t backend -f Dockerfile.backend .` e `docker run --rm backend which notebooklm` (deve retornar caminho). |
| **requirements.txt** | Contém todas as dependências Python (FastAPI, Celery, Redis, etc.). |
| **frontend build** | `cd frontend && npm run build` produz arquivos em `dist/` (ou `.output` dependendo do Vite). |
| **.env** | Contém `JWT_SECRET`, `REDIS_URL`, `LOG_LEVEL`, `LOG_FORMAT`. |
| **start.sh** (local) | Ainda funciona para testes locais; não interfere no deploy Docker. |
| **Portas expostas** | Backend 8000, Frontend 5173, Redis 6379 (se estiver rodando localmente). |
| **Health check endpoint** | `GET /api/health/live` retorna `{status:"alive"}`. |
| **Limites de memória** | Rode `docker compose up` localmente e veja `docker stats`; garanta que cada container fique < 400 MiB para ficar confortável nos planos gratuitos. |
| **Armazenamento efêmero** | Caso queira manter os relatórios entre deploys, planeje montar um volume (Render Disk, Railway Volume, ou bucket S3 compatível) e aponte as pastas `arquivos_bancas/` e `data/` para esse volume. |

---

## 5. Considerações de Limites e Mitigações

| Limite | Impacto | Mitigação |
|--------|---------|-----------|
| **RAM (≈512 MiB)** | Múltiplos containers podem estourar a memória se não forem otimizados. | - Use imagens `*-slim`. <br> - Limite o concurrency do worker a `1` (já está). <br> - Monitore com `docker stats` ou painel do provedor. |
| **CPU compartilhada** | Picos de uso podem causar lentidão. | - Evite tarefas pesadas no worker além do pipeline (o pipeline já é o trabalho pesado). <br> - Se necessário, reduza a frequência de uploads ou processe em lotes. |
| **Horas/mês (ex.: 750 h)** | Se deixar os serviços rodando 24/7, pode consumir a cota rapidamente. | - Desative o worker quando não houver jobs (pode escalar para 0 replicas em alguns provedores). <br> - Use o modo `CELERY_TASK_ALWAYS_EAGER=true` somente em desenvolvimento ou para testes pontuais. |
| **Storage efêmero** | Reiniciar o container perde os arquivos de upload/relatórios. | - Use volumes persistentes oferecidos pelo provedor (Render Disk, Railway Volume, ou bucket S3). <br> - Ou configure o aplicativo para enviar os resultados a um storage externo (ex.: Google Drive, AWS S3 via boto3) – fora do escopo inicial. |
| **Limite de requisições (Cloud Run)** | Não recomendado para worker de longa execução. | - Não usar Cloud Run para o worker; usar serviços que permitem processos de longa duração (Render, Railway, Fly). |

---

## 6. Próximos Passos Sugeridos

1. **Teste local com Docker Compose** (validar que tudo builda e funciona):
   ```bash
   cd /home/helton/AnaliseTextos/app
   docker compose up --build
   ```
   Acesse `http://localhost:8000/docs` e `http://localhost:5173/`.

2. **Criar os arquivos de configuração** (Dockerfiles, `.env` exemplo, `docker-compose.yml`) – já temos um rascunho acima; copie para o repositório.

3. **Escolher o provedor** (Render ou Railway) e seguir o respectivo passo‑a‑passo da seção 3.

4. **Após o deploy**, executar um teste de ponta a ponta:
   - Registrar um usuário via `/api/auth/register`.
   - Fazer login e obter JWT.
   - Fazer upload de um PDF de exemplo.
   - Iniciar o pipeline via `/api/pipeline/start`.
   - Polling de status até `SUCCESS`.
   - Baixar o relatório gerado (`/api/analyses/<id>/download?artifact=relatorio_completo.md`).

5. **Documentar o processo** neste mesmo `deploy_plan.md` ou em um `README_deploy.md` para futura referência da equipe.

---

## Conclusão
Com as adaptações acima (instalação do `notebooklm` nos containers, uso de Redis gerenciado via `REDIS_URL`, e separação de serviços backend/worker/frontend), o AnaliseTextos pode ser colocado em execução em um provedor de nuvem gratuito sem custos, desde que se respeite os limites de memória, CPU e horas/mês. O plano apresentado oferece um caminho claro e testável para colocar a aplicação em produção usando Render ou Railway como exemplos principais, com alternativa Fly.io para quem deseja mais controle.

--- 
*Este documento deve ser versionado juntamente com o código do projeto (ex.: `docs/deploy_plan.md`) e atualizado sempre que houver mudanças nas dependências, nos Dockerfiles ou nas variáveis de ambiente essenciais.*