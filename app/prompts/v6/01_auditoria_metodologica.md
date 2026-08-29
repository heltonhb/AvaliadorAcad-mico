---
module: "01"
title: "Auditoria Metodológica"
description: "Realize uma auditoria metodológica rigorosa"
---

> ⚠️ ANTI-ALUCINAÇÃO: Antes de listar qualquer achado, verifique se ele está documentado
> no texto. Para problemas presentes: cite a frase exata entre aspas. Para ausências
> (ex: cálculo amostral não reportado): descreva o que falta sem inventar evidências.
> Declare 'NÃO ENCONTRADO NO DOCUMENTO' quando uma informação esperada estiver ausente.

Realize uma auditoria metodológica rigorosa. Identifique primeiro o TIPO DE ESTUDO
(experimental, observacional, revisão sistemática, qualitativo, misto, etc.)
e adapte a avaliação conforme. {{DOMAIN_PROMPT}}

Para cada problema ou observação, VOCÊ DEVE EXTRAIR A FRASE EXATA do documento e
colocá-la ENTRE ASPAS, ou declarar explicitamente a ausência. Não invente ou parafraseie.

Use EXATAMENTE a seguinte estrutura de saída em Markdown (mantenha os cabeçalhos em português):

# Auditoria Metodológica
## Classificação do Estudo
- **Tipo de estudo:** [Ex: Ensaio clínico randomizado, estudo de coorte, survey, etc.]
- **Paradigma:** [Quantitativo / Qualitativo / Misto]

## Desenho de Pesquisa
- **Adequação do desenho ao objetivo:** [O desenho permite responder à pergunta de pesquisa?]
- **Validade interna:** [Ameaças identificadas]
- **Validade externa:** [Generalização possível? Limitações de contexto?]

## Amostra / Participantes
- **Cálculo amostral:** [Foi justificado? É adequado para o efeito esperado?]
- **Critérios de inclusão/exclusão:** [Explícitos? Adequados?]
- **Representatividade:** [A amostra representa a população-alvo?]

## Controle de Vieses
- **Vieses identificados:** [Seleção, informação, confusão, publicação, etc.]
- **Variáveis de confusão:** [Controladas? Como?]

## Instrumentos e Coleta de Dados
- **Validade dos instrumentos:** [Validados previamente? Referências?]
- **Confiabilidade:** [Teste-reteste, Cronbach α, kappa?]

## Análise de Dados
- **Testes estatísticos:** [Adequados ao tipo de dado e distribuição?]
- **Tamanho de efeito:** [Reportado? Intervalo de confiança?]
- **Poder estatístico:** [Mencionado? A priori (antes do estudo) ou post-hoc (após)? Adequado?]

## Reprodutibilidade ({{DOMAIN_LABEL}})
- **Ambiente/Protocolo:** [CS: ambiente computacional, SO, hardware, seeds, splits, ablation? / MED: protocolo de intervenção, cegamento, adherence? / Humanas: detalhamento do corpus/campo?]
- **Dados abertos:** [Disponíveis? Repositório?]
- **Código/scripts/materiais:** [Compartilhados?]
- **Protocolo detalhado:** [Suficiente para replicação completa?]

## Aderência às Diretrizes
- **Checklist aplicável:** [CONSORT/STROBE/PRISMA/COREQ/etc.]
- **Conformidade:** [Itens atendidos e não atendidos]