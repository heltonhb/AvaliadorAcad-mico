# teste

## Objetivo do Projeto

================================================================================
1. DESCRIÇÃO DETALHADA DO APLICATIVO
================================================================================

1.1. O QUE É O ANALISETEXTOS?
O AnaliseTextos é uma plataforma avançada e automatizada de Auditoria Científica
e Peer-Review Acadêmico desenvolvida para analisar trabalhos acadêmicos (artigos
científicos, dissertações de mestrado, teses de doutorado, TCCs e propostas de
qualificação de bancas examinadoras).

O sistema utiliza o Google NotebookLM como motor de inteligência e raciocínio 
profundo (reasoning engine), complementado por validação bibliográfica em tempo 
real via Crossref, orquestração de pipeline com tolerância a falhas, geração de 
múltiplos artefatos de saída (PDFs formais, slides PPTX, dashboards interativos, 
CSV de erros e apresentações HTML animadas) e uma interface moderna em React.

1.2. OBJETIVOS PRINCIPAIS
- Prover uma banca examinadora virtual rigorosa, consistente e padronizada.
- Auditar minuciosamente a metodologia, a consistência estatística, os gaps lógicos
  e a conformidade ética e editorial dos documentos submetidos.
- Detectar falhas argumentativas, non sequitur, inconsistências numéricas entre
  tabelas e texto, além de potenciais problemas de integridade científica.
- Gerar pareceres oficiais formais prontos para emissão por comissões de bancas
  examinadoras e editores científicos.
- Permitir a comparação evolutiva entre versões de um mesmo paper ou entre múltiplos
  candidatos em processos seletivos e bancas de defesa.

## Regras de Negócio

- Cada  cliente  deve se logar com sua  conta do notebooklm

## Entidades

- [ Entidade 1: Id, Campo1, Campo2,... ]

## Requisitos Funcionais

- FRONTEND (Interface do Usuário):    - Single Page Application (SPA) construída em React 19, Vite e Tailwind CSS v4.    - Biblioteca de ícones Lucide React e visualizações de dados com Recharts.    - Renderização Markdown em tempo real com suporte a tabelas GFM (remark-gfm).    - Comunicação assíncrona com a API via Server-Sent Events (SSE) para atualização      de logs e barra de progresso em tempo real.    - Módulos de Dashboard de Estatísticas, Upload & Início de Análise, Visualizador      de Resultados com filtros, Histórico Geral e Módulo Comparativo de Versões.  B) BACKEND REST API (Servidor de Aplicação):    - Desenvolvido em Python com FastAPI e Uvicorn.    - Endpoints REST para upload seguro de PDFs, controle do pipeline, leitura de      status via SSE, download de artefatos e navegação segura de diretórios.    - Camada de segurança com autenticação opcional via API Key (header X-API-Key),      prevenção contra Path Traversal, validação estrita de magic bytes de arquivos      e sanitização XSS de conteúdos HTML via Bleach.  C) MOTOR DE RACIOCÍNIO CIENTÍFICO (Google NotebookLM CLI):    - O orquestrador interage com a CLI `notebooklm-py` autenticada.    - Cria notebooks dedicados para cada trabalho submetido.    - Configura a Persona do Revisor Sênior com diretrizes específicas por domínio.    - Raciocínio contextual cumulativo: os relatórios de cada módulo concluído são      reinseridos no notebook como novas fontes de conhecimento, permitindo que os      módulos seguintes façam validações cruzadas.  D) GERADORES DE ARTEFATOS E GROUNDING EXTERNO:    - ReportLab: Geração do Parecer Técnico Oficial da Banca em PDF diagramado.    - Crossref API (HTTPX): Auditoria bibliográfica factual de DOIs e artigos retratados.    - Mira Animator (Jinja2 + D3.js + Tailwind): Apresentação animada interativa.    - Python-PPTX: Apresentações de slides em formato PowerPoint para bancas.    - Parser CSV: Extração tabular de todos os erros gramaticais e estilísticos.

## Requisitos Visuais
- Opcoes do menu lateral: [ digitar as opcoes separadas por virgula ]
- Tema visual: [ especificar cores, modos, tipografia, espacamento etc ]

---
> **Instrucoes para a Inteligencia Artificial**
>
> Este documento contem os requisitos de negocio e visuais do projeto.
> As especificacoes tecnicas detalhadas estao nos arquivos de contexto do pacote. Comece pelo arquivo **`Prompt.txt`**.
