---
module: "00"
title: "Estrutura do Documento"
description: "Mapeie e avalie a estrutura do documento"
---

> ⚠️ ANTI-ALUCINAÇÃO: Antes de listar qualquer achado, verifique se ele está
> documentado no texto. Em caso de dúvida, declare 'NÃO ENCONTRADO NO DOCUMENTO'.
> Seção obrigatória totalmente ausente = achado de GRAVIDADE CRÍTICA, não lacuna analítica.

Mapeie e avalie a estrutura do documento. Identifique primeiro o idioma e o tipo de documento.

**Diretrizes de domínio aplicáveis a este módulo:**
{{DOMAIN_PROMPT}}

Use EXATAMENTE a seguinte estrutura de saída em Markdown (cabeçalhos em português):

# Estrutura do Documento
## Pre-flight e Qualificação
- **Idioma Predominante:** [Português / Inglês / Espanhol / outro — identifique]
- **Tipo de Documento Detectado:** [Artigo completo / Short paper / Tese / Dissertação / TCC / Preprint / Relatório técnico / Proposta de qualificação / Outro]
- **Qualidade do PDF:** [Texto vetorial legível / Escaneado com OCR / Problemas de formatação detectados]

## Conformidade Estrutural
- **Padrão Estrutural Esperado:** [IMRAD para artigos empíricos / Específico para o tipo detectado — ex: CONSORT flow para RCT, PRISMA para revisão sistemática]
- **Seções Presentes:** [Liste todas as seções encontradas]
- **Seções Obrigatórias Ausentes:** [Liste o que falta para o tipo detectado — se nenhuma, escreva "Nenhuma seção obrigatória ausente"]
- **🔴 Ausências Críticas:** [Seções cuja ausência inviabiliza a avaliação — ex: Metodologia ausente num artigo empírico]
- **Coerência Introdução→Conclusão:** ["O objetivo declarado em [citar trecho da Introdução] é [respondido / parcialmente respondido / não respondido] na Conclusão [citar trecho]"]

## Mapeamento Detalhado
Para CADA seção principal encontrada, preencha:

### [Nome exato da seção]
- **Objetivo cumprido:** [O que a seção se propõe a fazer e se cumpre]
- **Proporção estimada:** [Adequada / Subdimensionada / Superdimensionada — justifique: ex: "Introdução ocupa ~35% do texto, desproporcional para IMRAD"]
- **Achados notáveis:** [Qualquer elemento que precise de análise mais profunda nos módulos seguintes]

## Fluxo Narrativo
- **Coesão entre seções:** [O texto flui logicamente? Cite trechos de transições abruptas ou redundâncias encontradas]
- **Alinhamento Objetivo–Método–Resultado–Conclusão:** [Avalie cada par com citação textual de suporte]
- **Inconsistências detectadas neste módulo:** [Liste inconsistências estruturais que os módulos posteriores devem investigar]
