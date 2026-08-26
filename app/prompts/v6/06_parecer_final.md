---
module: "06"
title: "Parecer Final"
description: "Realize a avaliação final (Parecer do Revisor)"
---

Realize a avaliação final (Parecer do Revisor). Leia o documento COMO UM TODO, \
considerando as análises dos módulos anteriores (que foram adicionados ao notebook), \
e sintetize seu veredito. INTEGRE e REFERENCIE os achados dos módulos anteriores \
em seu parecer. Para cada ponto forte e fragilidade, cite qual módulo identificou o problema (ex: Módulo 01 — Validade Interna). Não repita análises — sintetize.
Use EXATAMENTE a seguinte estrutura:

# Parecer Final
## Resumo Executivo
[1-2 parágrafos: objetivo do estudo, método, principais achados e contribuição à área]

## Originalidade e Contribuição
- **Novidade:** [O que este trabalho acrescenta ao estado da arte?]
- **Relevância teórica:** [Avança o conhecimento na área?]
- **Relevância prática:** [Tem aplicabilidade? Para quem?]
- **Nível de contribuição:** [Incremental / Significativa / Transformadora]

## Veredito
[1-2 parágrafos com justificativa baseada em evidências do documento]

## Pontos Fortes
1. [Força 1 - Cite o módulo de origem]
2. [Força 2 - Cite o módulo de origem]
3. [Força 3 - Cite o módulo de origem]

## Fragilidades Principais
1. [Fraqueza 1 - Cite o módulo de origem]
2. [Fraqueza 2 - Cite o módulo de origem]
3. [Fraqueza 3 - Cite o módulo de origem]

## Recomendações ao Autor (priorizadas)
1. [OBRIGATÓRIO] [Correção essencial para publicação]
2. [OBRIGATÓRIO] [Outra correção essencial]
3. [RECOMENDADO] [Melhoria desejável]
4. [SUGERIDO] [Refinamento opcional]

## Carta ao Editor (Confidencial)
[Carta formal ao editor contendo:
- Avaliação resumida da qualidade científica
- Problemas que impedem ou não a publicação
- Recomendação clara e justificada
- Indicação se o trabalho é adequado ao escopo do periódico]

## DECISÃO FINAL: [Accept / Minor Revisions / Major Revisions / Reject]

## ÍNDICE DE COERÊNCIA NARRATIVA: [0 a 10] — Introdução, Método, Resultados e Discussão formam uma narrativa coerente?

## NOTA: [0 a 10] — Use a rubrica:
- 9-10: Excelente — pronto para publicação ou com ajustes mínimos
- 7-8: Bom — necessita revisões menores
- 5-6: Regular — necessita revisões maiores, potencial de publicação após correções
- 3-4: Fraco — problemas estruturais graves, requer reescrita substancial
- 0-2: Inadequado — falhas fatais de método, ética ou originalidade

## METADADOS ESTRUTURADOS
Ao final da resposta, inclua OBRIGATORIAMENTE o seguinte bloco de código JSON preenchido:
```json
{
  "nota": 0.0,
  "decisao": "Accept | Minor Revisions | Major Revisions | Reject",
  "coerencia_narrativa": 0.0,
  "pontos_fortes": ["Ponto 1", "Ponto 2", "Ponto 3"],
  "fragilidades": ["Fragilidade 1", "Fragilidade 2", "Fragilidade 3"],
  "recomendacoes_obrigatorias": ["Recomendação 1", "Recomendação 2"]
}
```