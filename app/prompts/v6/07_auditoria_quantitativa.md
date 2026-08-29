---
module: "07"
title: "Auditoria Quantitativa"
description: "Realize uma auditoria das evidências quantitativas apresentadas no documento"
---

> ⚠️ ANTI-ALUCINAÇÃO: Liste APENAS inconsistências que você pode verificar diretamente
> pelo texto do documento. Para cada inconsistência, cite os dois valores conflitantes
> com suas fontes exatas (ex: "Tabela 3 reporta N=120" vs. "texto da Seção 3.1 cita N=115").

Realize uma auditoria das evidências quantitativas apresentadas no documento:
tabelas, figuras, gráficos e análises estatísticas.

**INSTRUÇÃO SOBRE ARITMÉTICA:**
Você NÃO deve "calcular manualmente" e confiar no resultado — modelos de linguagem
cometem erros aritméticos silenciosos. Em vez disso:
1. Identifique e cite os números COMO REPORTADOS pelo autor em cada local do documento.
2. Sinalize quando o autor reporta valores conflitantes entre si (ex: dois lugares com N diferente).
3. Sinalize quando o autor afirma um resultado que contraria a lógica dos dados apresentados
   (ex: "a Tabela 2 apresenta 4 grupos com médias X, Y, Z, W, mas o texto afirma que 'apenas
   3 grupos foram comparados'").
4. Sinalize quando percentuais declarados pelo autor são inconsistentes entre si
   (ex: autor reporta 45% + 60% = 100% — a soma declarada não fecha).
NÃO invente erros aritméticos — se os números parecem plausíveis, declare "Aparentemente consistente".

Use EXATAMENTE a seguinte estrutura (cabeçalhos em português):

# Auditoria Quantitativa
## Tabelas
- **Quantidade encontrada:** [N tabelas — liste os títulos]
- **Formatação:** [Numeradas sequencialmente? Títulos descritivos? Unidades nas colunas?]
- **Inconsistências declaradas vs. texto:** [Para cada discrepância: "Tabela X reporta [valor]" vs. "Seção Y cita [outro valor]"]
- **Valores suspeitos reportados pelo autor:** [Percentuais que o próprio autor declara e que não fecham, N declarados inconsistentes entre passagens, etc. — cite ambos os trechos]

## Figuras e Gráficos
- **Quantidade encontrada:** [N figuras — liste os títulos]
- **Legibilidade:** [Eixos rotulados? Legendas adequadas?]
- **Adequação do tipo de gráfico:** [O tipo escolhido é apropriado para os dados? Ex: boxplot para distribuição vs. barplot para proporção]
- **Redundância com tabelas:** [Alguma figura repete exatamente dados já tabelados sem acréscimo informacional?]
- **Não citadas no texto:** [Liste figuras ou tabelas presentes no documento mas não discutidas no texto]

## Análise Estatística
- **Testes identificados:** [Liste todos os testes estatísticos mencionados]
- **Adequação declarada:** [O autor justifica a escolha dos testes? São adequados ao tipo de dado e ao desenho do estudo?]
- **Pressupostos:** [O autor menciona verificação de normalidade, homocedasticidade, independência? Se não, sinalize]
- **Tamanho de efeito:** [Reportado? Qual medida? (Cohen's d, η², OR, RR, r de Pearson, etc.) IC95%?]
- **Correção para múltiplas comparações:** [Bonferroni, FDR/Benjamini-Hochberg, Holm? Se houver múltiplas comparações sem correção, sinalize como problema]
- **Poder estatístico:** [Calculado a priori? Se calculado post-hoc, sinalize — poder post-hoc é amplamente considerado não informativo]
- **Dados faltantes:** [O autor reporta como foram tratados? Imputação? Exclusão listwise? Análise de sensibilidade?]

## Consistência Numérica (cross-check declarativo)
Para cada inconsistência encontrada, use o formato:
- **[Tipo]:** "[Valor em local A]" (Seção/Tabela X) ≠ "[Valor em local B]" (Seção/Tabela Y) — [impacto na validade]

Tipos a verificar:
- N amostral entre metodologia, resultados e tabelas
- Valores de p entre texto e tabelas
- Percentuais cujas bases de cálculo o autor torna impossível reconciliar
- Afirmações de resultado que contradizem visualmente os dados apresentados

Se nenhuma inconsistência for encontrada, declare explicitamente:
"Nenhuma inconsistência numérica declarativa identificada entre as passagens verificadas."
