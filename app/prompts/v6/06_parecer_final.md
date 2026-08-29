---
module: "06"
title: "Parecer Final"
description: "Realize a avaliação final (Parecer do Revisor)"
---

> ⚠️ ANTI-ALUCINAÇÃO: Baseie cada afirmação em evidências dos módulos anteriores ou do
> documento principal. Não invente pontos fortes para "equilibrar" — se o trabalho tem
> três fragilidades críticas e dois pontos fortes, reporte exatamente isso.

Realize a avaliação final (Parecer do Revisor). Leia o documento principal COMO UM TODO e,
OBRIGATORIAMENTE, leia os relatórios dos módulos anteriores salvos neste workspace
(Módulos 00 a 05 e 07).

**INSTRUÇÃO DE COERÊNCIA OBRIGATÓRIA — leia antes de escrever:**
Antes de atribuir a nota final, faça mentalmente esta checagem:
1. Liste internamente os problemas de GRAVIDADE CRÍTICA identificados nos módulos anteriores.
2. Se houver 1+ problema crítico não resolvido → nota máxima é 6.9 (Major Revisions).
3. Se houver 2+ problemas críticos → nota máxima é 4.9 (Reject & Resubmit).
4. Se houver violação ética (sem CEP, sem TCLE em estudo com humanos) → nota máxima é 2.9 (Reject).
5. Se a nota que você calculou contradiz os achados dos módulos, EXPLIQUE EXPLICITAMENTE
   a divergência na seção "Justificativa da Nota". Nunca ignore uma contradição silenciosamente.

**RUBRICA DE NOTA CALIBRADA POR DOMÍNIO ({{DOMAIN_LABEL}}):**
{{DOMAIN_PROMPT}}

Use esta rubrica genérica como base e ajuste conforme os pesos específicos do domínio acima:
- **9.0 – 10.0 (Excelente / Accept):** Metodologia impecável para o domínio, contribuição
  significativa ao estado da arte, escrita madura, todos os critérios obrigatórios do domínio
  atendidos, zero problemas críticos.
- **7.0 – 8.9 (Bom / Minor Revisions):** Mérito científico evidente, pequenas lacunas
  não estruturais, zero problemas críticos, no máximo 2 problemas moderados não resolvidos.
- **5.0 – 6.9 (Regular / Major Revisions):** Potencial existente mas com 1+ problema crítico
  ou fragilidades metodológicas que exigem retrabalho substancial.
- **3.0 – 4.9 (Fraco / Reject & Resubmit):** 2+ problemas críticos, falhas estruturais severas,
  reformulação profunda necessária.
- **0.0 – 2.9 (Inadequado / Reject):** Falhas fatais de metodologia, violações éticas graves,
  ausência de originalidade ou dados, ou integridade científica comprometida.

Sintetize seu veredito GARANTINDO que não contradiga os achados dos módulos anteriores.
INTEGRE e REFERENCIE cada ponto forte e fragilidade citando o módulo de origem.
Use EXATAMENTE a seguinte estrutura (cabeçalhos em português):

# Parecer Final
## Resumo Executivo
[2-3 parágrafos: objetivo do estudo, método empregado, principais achados e contribuição
declarada à área — baseado no documento, não nos módulos]

## Originalidade e Contribuição
- **Novidade:** [O que este trabalho acrescenta ao estado da arte? Cite evidência do documento]
- **Relevância teórica:** [Avança o conhecimento na área? Como?]
- **Relevância prática:** [Tem aplicabilidade? Para quem? Em que contexto?]
- **Nível de contribuição:** [Incremental / Significativa / Transformadora — justifique]

## Síntese dos Módulos Anteriores
Antes do veredito, sintetize os principais achados de cada módulo com sua classificação:
- **Módulo 00 (Estrutura):** [Achado principal + classificação: OK / Atenção / Crítico]
- **Módulo 01 (Metodologia):** [Achado principal + classificação]
- **Módulo 02 (Editorial):** [Achado principal + classificação]
- **Módulo 03 (Referencial):** [Achado principal + classificação — se executado]
- **Módulo 04 (Gaps):** [Número de problemas críticos/moderados/leves encontrados]
- **Módulo 05 (Escrita):** [Nota de maturidade textual + total de erros]
- **Módulo 07 (Quantitativo):** [Achado principal + classificação — se executado]

## Veredito
[2-3 parágrafos com justificativa baseada em evidências dos módulos e do documento.
Se houver contradições entre módulos (ex: módulo 01 encontrou falha grave mas o documento
tem metodologia aparentemente sólida), explique a contradição aqui.]

## Pontos Fortes (com módulo de origem)
1. [Força 1 — Módulo XX: cite a evidência textual que sustenta este ponto]
2. [Força 2 — Módulo XX: cite a evidência]
3. [Força 3 — Módulo XX: cite a evidência]
(adicione mais se necessário; omita se não houver evidência)

## Fragilidades Principais (com módulo de origem)
1. [Fraqueza 1 — Módulo XX: gravidade + cite a evidência textual ou ausência]
2. [Fraqueza 2 — Módulo XX: gravidade + cite a evidência]
3. [Fraqueza 3 — Módulo XX: gravidade + cite a evidência]
(adicione mais se necessário)

## Recomendações ao Autor (priorizadas)
1. [OBRIGATÓRIO] [Correção essencial para publicação — sem ela, rejeição]
2. [OBRIGATÓRIO] [Outra correção essencial]
3. [RECOMENDADO] [Melhoria metodológica ou textual desejável]
4. [SUGERIDO] [Refinamento opcional que fortaleceria o trabalho]

## Carta ao Editor (Confidencial)
Prezado(a) Editor(a),

[Carta formal contendo:
- Avaliação resumida da qualidade científica (2-3 frases)
- Principais problemas que impedem ou condicionam a publicação
- Recomendação clara e justificada com base na rubrica do domínio {{DOMAIN_LABEL}}
- Indicação se o trabalho é adequado ao escopo do periódico alvo (se declarado)]

Atenciosamente,
Revisor Acadêmico Sênior

## DECISÃO FINAL: [Accept / Minor Revisions / Major Revisions / Reject]

## ÍNDICE DE COERÊNCIA NARRATIVA: [0 a 10]
Justificativa: [1 frase explicando a nota — Introdução, Método, Resultados e Discussão
formam uma narrativa coerente e sem contradições internas?]

## NOTA FINAL: [0.0 a 10.0]
Justificativa da nota: [Explique OBRIGATORIAMENTE como chegou a esta nota considerando
a rubrica do domínio e os achados dos módulos. Se a nota contradiz algum achado crítico,
justifique explicitamente por quê.]

## METADADOS ESTRUTURADOS
Ao final da resposta, inclua OBRIGATORIAMENTE o seguinte bloco JSON exatamente neste formato.
Preencha todos os campos — não deixe nenhum como null sem justificativa no campo "observacoes":

```json
{
  "nota": 0.0,
  "decisao": "Accept | Minor Revisions | Major Revisions | Reject",
  "coerencia_narrativa": 0.0,
  "nivel_contribuicao": "Incremental | Significativa | Transformadora",
  "dominio": "{{DOMAIN_LABEL}}",
  "problemas_criticos": 0,
  "problemas_moderados": 0,
  "pontos_fortes": ["Ponto forte 1", "Ponto forte 2"],
  "fragilidades": ["Fragilidade 1", "Fragilidade 2"],
  "recomendacoes_obrigatorias": ["Recomendação obrigatória 1", "Recomendação obrigatória 2"],
  "observacoes": ""
}
```
