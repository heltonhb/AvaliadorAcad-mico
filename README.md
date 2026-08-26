# 🔬 AnaliseTextos — Peer-Review Científico via NotebookLM

Pipeline automatizado de análise peer-review de artigos acadêmicos (TCCs, dissertações, papers) usando Google NotebookLM como motor de raciocínio.

## Arquitetura

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Streamlit   │────▶│  pipeline.py  │────▶│  NotebookLM CLI  │
│   (app.py)   │     │              │     │                  │
└──────────────┘     └──────┬───────┘     └──────────────────┘
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
          📄 7 relatórios  📊 PPTX     🖼️ Infográfico
          (Markdown)       (python-pptx) (NotebookLM)
```

## Pré-requisitos

- Python 3.11+
- `notebooklm` CLI instalado e autenticado (`~/.notebooklm/`)
- Node.js (apenas se precisar de artefatos extras do NotebookLM)

## Instalação

```bash
cd AnaliseTextos/app
pip install -r requirements.txt
```

## Uso

### Interface Web (Streamlit)

```bash
bash start.sh
# → http://localhost:8501
```

### CLI direto

```bash
# Análise completa (7 módulos)
python pipeline.py paper.pdf

# Com opções
python pipeline.py paper.pdf --domain med --mode lite

# Retomar de checkpoint (se interrompido)
python pipeline.py paper.pdf --resume
```

### Flags

| Flag | Descrição |
|------|-----------|
| `--domain cs\|med\|human` | Domínio acadêmico (default: cs) |
| `--mode full\|lite` | full = 7 módulos, lite = 5 (sem 02/03) |
| `--force` | Força re-execução completa (default) |
| `--resume` | Retoma de checkpoint existente |

## Módulos de Análise

| # | Arquivo | Descrição |
|---|---------|-----------|
| 00 | `00_estrutura_documento.md` | Mapa hierárquico do documento |
| 01 | `01_metodologia.md` | Auditoria metodológica |
| 02 | `02_auditoria_editorial.md` | Revisão editorial (pulado no lite) |
| 03 | `03_sota_referencias.md` | Estado da arte e referências (pulado no lite) |
| 04 | `04_gaps_logicos.md` | Gaps lógicos e fragilidades |
| 05 | `05_analise_escrita.md` | Análise de escrita + tabela de erros |
| 06 | `06_sintese_parecer.md` | Síntese e parecer final |

### Artefatos gerados

- 📊 **Apresentações PPTX** (completa + auditoria) — via python-pptx
- 🖼️ **Infográfico** — via NotebookLM
- 🧠 **Mapa Mental** — via NotebookLM
- 📄 **Relatório consolidado** — Markdown concatenado
- 📊 **CSV de erros** — tabela com page/line numbers

## Autenticação (opcional)

Para proteger a interface web:

```bash
# Opção 1: variável de ambiente
export ANALISE_PASSWORD="sua_senha"

# Opção 2: Streamlit secrets
echo '[password]' >> ~/.streamlit/secrets.toml
echo 'password = "sua_senha"' >> ~/.streamlit/secrets.toml
```

## Estrutura

```
AnaliseTextos/
├── app/
│   ├── app.py              # Interface Streamlit
│   ├── pipeline.py         # Pipeline principal
│   ├── start.sh            # Script de inicialização
│   ├── requirements.txt    # Dependências Python
│   └── tests/
│       └── test_pipeline.py
├── analises/               # Saídas (gerado pelo pipeline)
│   └── <nome_do_paper>/
│       ├── 00_*.md ... 06_*.md
│       ├── tabela_erros.csv
│       ├── relatorio_completo.md
│       ├── apresentacao_completa.pptx
│       ├── apresentacao_auditoria.pptx
│       └── .checkpoint.json
└── README.md
```

## Testes

```bash
python -m pytest tests/test_pipeline.py -v
```

## Segurança

- **Sem `shell=True`** — todos os comandos usam listas de argumentos
- **Validação de upload** — magic bytes PDF + tamanho máximo 50MB
- **Sanitização de HTML** — remove `<script>`, `on*` handlers, `javascript:` URIs
- **Autenticação** — opcional via env var ou Streamlit secrets

## Licença

Uso acadêmico / interno.
