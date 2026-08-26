"""
Prompts do pipeline de Análise de Contas Condominiais v7.0.
Cada prompt é associado a um módulo (00-07) que gera um relatório Markdown.

Módulos:
- Módulo 00: estrutura do documento, conformidade formal, organização
- Módulo 01: receitas — taxa condominial, fundos, multas, aluguéis
- Módulo 02: conformidade legal e assembleia — Lei 4.591/64, atas, aprovações
- Módulo 03: despesas — legitimidade, proporcionalidade, razoabilidade
- Módulo 04: consistência lógica e financeira — cruzamento números ↔ texto
- Módulo 05: qualidade documental — clareza, terminologia, erros
- Módulo 06: síntese e parecer final — veredito, nota 0-10, recomendações
- Módulo 07: auditoria quantitativa profunda — planilhas, totais, validates
"""

SYSTEM_PERSONA = (
    "Você é um Consultor Financeiro e Contábil Sênior com mais de 15 anos de experiência em "
    "análise de contas condominiais, auditoria financeira de condomínios e gestão patrimonial. "
    "Possui domínio da Lei 4.591/64, normas contábeis brasileiras (CFC), legislação tributária "
    "aplicável e boas práticas de administração predial.\n\n"
    "DIRETRIZES DE CONDUTA:\n"
    "1. Tom: Técnico e objetivo. Identifique irregularidades com justificativa e sugira correções.\n"
    "2. Ancoragem factual: Baseie-se EXCLUSIVAMENTE no documento fornecido. Se uma informação "
    "   não existir no documento, declare 'NÃO ENCONTRADO NO DOCUMENTO'.\n"
    "3. Calibração de certeza: Diferencie afirmações definitivas de observações prováveis. "
    "   Use 'O documento não apresenta...' ao invés de 'Não há...'.\n"
    "4. Evidência documental: Para cada constatação, cite o trecho, linha ou seção específica do documento.\n"
    "5. Priorização: Classifique problemas por impacto financeiro e legal para o condomínio.\n"
    "6. Idioma: Detecte o idioma predominante do documento e produza a análise nesse idioma.\n"
    "7. Consistência Modular: Cada módulo alimenta o seguinte. Seja consistente entre módulos."
)

PROMPTS = {
    "00": """\
Mapeie e avalie a estrutura completa do documento de prestação de contas condominiais.
Identifique o idioma e o tipo de documento.
Use EXATAMENTE a seguinte estrutura de saída em Markdown:

# Estrutura do Documento
## Identificação
- **Idioma Predominante:** [Português / Inglês / Espanhol / etc.]
- **Tipo de Documento Detectado:** [Prestação de Contas Anual / Relatório Mensal / Balancete / Mapa de Custos / Orçamento / Outro]
- **Condomínio:** [Nome, se identificado]
- **Período de Referência:** [Ex: Janeiro a Dezembro de 2025]
- **Síndico / Administradora:** [Nome, se identificado]
- **Qualidade do PDF/Documento:** [Texto legível / Escaneado com OCR ruim / Problemas de formatação?]

## Conformidade Formal
- **Seções Presentes:** [Liste todas as seções/capítulos encontrados]
- **Seções Ausentes (obrigatórias para o tipo):** [Verifique se há:]
  - [ ] Balanço patrimonial ou demonstrativo de receitas e despesas
  - [ ] Demonstrativo do fundo de reserva
  - [ ] Demonstrativo do fundo de manutenção
  - [ ] Relação de despesas detalhada (folha de pagamento, fornecedores, impostos)
  - [ ] Mapa de Rateio / Quadro de cotas
  - [ ] Extratos bancários ou conciliação
  - [ ] Ata de assembleia (se aplicável)
  - [ ] Relatório do conselho fiscal (se houver)
- **Coerência Geral:** [O período declarado é consistente com os dados apresentados?]

## Mapeamento Detalhado
### [Nome da Seção/Demonstrativo 1]
- **Objetivo:** [Descreva em até 2 linhas]
- **Dados Apresentados:** [Resumo do que contém]
- **Proporção do Documento:** [Adequada / Subdimensionada / Superdimensionada]

### [Nome da Seção/Demonstrativo 2]
... (continue para todas as seções principais)

## Fluxo do Documento
- **Sequência Lógica:** [Receitas → Despesas → Saldo? A ordem dos dados faz sentido contábil?]
- **Cruzamentos Possíveis:** [Os dados de uma seção permitem verificação cruzada com outra?]""",

    "01": """\
Realize uma auditoria completa das RECEITAS do condomínio.
Identifique todas as fontes de receita, sua composição e eventuais irregularidades.
Use EXATAMENTE a seguinte estrutura de saída em Markdown:

# Auditoria de Receitas

## Receitas Condominiais (Taxa Mensal)
- **Valor Total Arrecadado com Taxas:** [R$ X,XX ou N/A]
- **Valor Total de Cotas (Base de Cálculo):** [R$ X,XX ou N/A]
- **Taxa de Inadimplência Estimada:** [X% — se disponível]
- **Variação vs. Período Anterior:** [Aumento/estável/diminuição de X%]
- **Composição:** [Taxa fixa + (%) / Taxa variável + (%) / IPTU antecipado + (%)]

## Fundos Especiais
- **Fundo de Reserva:**
  - Saldo anterior: [R$ X,XX]
  - Recolhimentos no período: [R$ X,XX]
  - Aplicações/saques: [R$ X,XX]
  - Saldo final: [R$ X,XX]
  - [ ] O fundo segue a proporção mínima legal/estatutária?
- **Fundo de Manutenção / Obra:**
  - Saldo anterior: [R$ X,XX]
  - Recolhimentos no período: [R$ X,XX]
  - Aplicações/saques: [R$ X,XX]
  - Saldo final: [R$ X,XX]
  - [ ] Finalidade dos saques é compatível com a destinação do fundo?
- **Outros Fundos:** [Liste se houver]

## Multas e Juros
- **Total Arrecadado com Multas:** [R$ X,XX]
- **Base Legal/Estatutária das Multas:** [Percentual previsto no regimento? Conforme qual artigo?]
- **Multas Cobradas vs. Regulamento:** [Consistente? Há divergência?]

## Outras Receitas
- **Aluguéis de Áreas Comuns:** [R$ X,XX — salões, churrasqueiras, vagas extras]
- **Ganhos Financeiros (Rendimento Poupança/CDB):** [R$ X,XX]
- **Repasses de Terceiros (IPTU antecipado, seguro, etc.):** [R$ X,XX]
- **Outras:** [Detalhe]

## Análise de Regularidade
- **Repasses de IPTU ao Município:** [Estão em dia? Há débitos?]
- **Contribuição Patronal (INSS/FGTS da administração):** [Regular?]
- **Notas Fiscais / Recibos:** [Todos documentados?]
- **Riscos Identificados:** [Liste eventuais irregularidades ou pontos de atenção]

## Consistência e Alertas
- [ ] A soma das receitas parciais confere com o total declarado?
- [ ] A taxa por unidade é consistente com o quadro de rateio?
- [ ] Há receitas não previstas no orçamento aprovado em assembleia?
- [ ] Há valores arrecadados e não aplicados conforme finalidade declarada?""",

    "02": """\
Realize a AUDITORIA DE CONFORMIDADE LEGAL E ASSEMBLEIA do condomínio.
Verifique se o documento atende à legislação vigente e às deliberações assembleares.
Use EXATAMENTE a seguinte estrutura de saída em Markdown:

# Conformidade Legal e Assembleia

## Base Legal Aplicável
- **Lei 4.591/64 (Condomínios):** [O documento atende aos artigos aplicáveis?]
  - Art. 12 — Contas do síndico: apresentação anual? Aprovação em assembleia?
  - Art. 22 — Prestação de contas: completa e detalhada?
  - Art. 23 — Rateio das despesas: baseado na fração ideal?
- **Código Civil ( arts. 1.330 a 1.353):** [Disposições sobre administração?]
- **Normas do CFC (Conselho Federal de Contabilidade):** [NBC TGA aplicável?]

## Ata de Assembleia
- **Ata Presente no Documento:** [Sim / Não]
- **Data da Última Assembleia:** [DD/MM/AAAA]
- **Deliberações Relevantes:**
  - Aprovação das contas: [Sim / Não / Parcial]
  - Aprovação do orçamento: [Sim / Não]
  - Definição de taxa condominial: [Sim / Não]
  - Autorização de despesas específicas: [Quais?]
- **Quórum de Aprovação:** [Apresentado? Adequado ao estatuto?]

## Conselho Fiscal
- **Relatório do Conselho Fiscal Presente:** [Sim / Não / Não aplicável]
- **Parecer do Conselho:** [Favorável / Com ressalvas / Desfavorável / Ausente]
- **Observações do Conselho:** [Resumo, se houver]

## Conformidade Tributária
- **retenção na Fonte (IR/ISS/PIS/COFINS):** [Regular? Alíquotas corretas?]
- **DIRPF/DIRPJ do Síndico/Administradora:** [Informado?]
- **DARF's pagos:** [Em dia? Atrasados?]
- **Nota Fiscal de Serviços:** [Todos os fornecedores emitiram?]

## Conformidade com Regulamento Interno
- **Regimento Interno / Convenção Condominial:** [O documento segue as normas internas?]
- **Limites de Gastos Sem Aprovação:** [Ultrapassados?]
- **Competências do Síndico vs. Assembleia:** [Respeitadas?]

## Alertas e Irregularidades Legais
- [ ] Há despesas sem aprovação assemblear quando obrigatória?
- [ ] Há indício de desvio de finalidade de fundos?
- [ ] As contas estão de acordo com a Lei 4.591/64?
- [ ] Há pendências fiscais ou tributárias?""",

    "03": """\
Auditoria de DESPESAS do condomínio. Seja conciso: liste apenas itens encontrados no documento.

# Auditoria de Despesas

## Despesas Fixas
- **Folha de pagamento:** [Total — detalhe apenas se houver irregularidade]
- **Energia/Água/Seguro/IPTU:** [Valores e variação vs período anterior]

## Despesas Variáveis
- **Manutenção/Reformas:** [Itens, valores, se há orçamento e NF]
- **Jurídicas/Administrativas:** [Valores e justificativa]

## Análise
- **Custo por unidade:** [R$ X,XX/mês]
- **Top 3 categorias:** [Representam X% do total]

## Irregularidades
[Lista apenas problemas encontrados com evidência documental]""",

    "04": """\
Identifique inconsistências lógicas e financeiras. Para cada problema, cite o trecho do documento.

# Consistência Lógica e Financeira

## Cadeia Financeira
- **Receitas → Despesas → Saldo:** [Saldo final explicável?]
- **Orçamento vs. Realizado:** [Divergências?]
- **Saldos de Fundos:** [Iniciais + recolhimentos - saídas = final?]

## Problemas por Gravidade
- 🔴 **Crítica:** [Lista com citação do trecho]
- 🟡 **Moderada:** [Lista com citação do trecho]
- 🟢 **Leve:** [Lista com citação do trecho]

## Consistência Numérica
[Verifique: soma de despesas = total? soma de receitas = total? saldos bancários batem?]""",

    "05": """\
Faça uma revisão da qualidade documental cobrindo clareza, terminologia contábil
e adequação da apresentação das contas.
Detecte o idioma do documento e produza a análise nesse mesmo idioma.
Use a seguinte estrutura:

# Qualidade Documental

## Erros e Inconsistências de Apresentação
| Seção / Demonstrativo | Tipo de Problema | Descrição | Sugestão de Correção |
|---|---|---|---|
| (Ex: Balanço de Receitas) | (Valor incoerente / Rótulo incorreto / Dado faltante) | "descrição" | "sugestão" |

## Clareza e Organização
- **Rótulos e Títulos:** [Os demonstrativos têm títulos claros e padronizados?]
- **Unidades Monetárias:** [R$ é usado de forma consistente? Há confusão entre R$ e outros?]
- **Período:** [O período de referência está claramente indicado em cada seção?]
- **Separação de Competências:** [Despesas de meses diferentes estão separadas?]

## Terminologia Contábil
- **Termos Técnicos:** [Termos como "rateio", "competência", "caixa", "compromisso" são usados corretamente?]
- **Classificação de Despesas:** [Fixas vs. variáveis está clara? Capital vs. operacional?]
- **Fundos:** [Fundo de reserva e de manutenção estão claramente diferenciados?]

## Ausência de Informação
- **Dados Obrigatórios Ausentes:** [Quais informações esperadas em uma prestação de contas não estão presentes?]
- **Justificativas Faltantes:** [Há valores significativos sem explicação?]

## Resumo Estatístico
- Total de problemas encontrados por gravidade
- Seções com maior concentração de problemas
- Avaliação geral da qualidade documental (1-5: 1=muito confuso, 5=impecável)""",

    "06": """\
Realize a avaliação final (Parecer do Auditor). Leia o documento COMO UM TODO,
considerando as análises dos módulos anteriores (que foram adicionados ao notebook),
e sintetize seu veredito. INTEGRE e REFERENCIE os achados dos módulos anteriores
em seu parecer. Para cada ponto forte e fragilidade, cite qual módulo identificou.
Não repita análises — sintetize.
Use EXATAMENTE a seguinte estrutura:

# Parecer Final da Auditoria Condominial

## Resumo Executivo
[1-2 parágrafos: período analisado, tipo de condomínio, situação geral das contas,
valores totais movimentados e conclusão de alto nível]

## Situação Financeira
- **Receitas Totais do Período:** [R$ X,XX]
- **Despesas Totais do Período:** [R$ X,XX]
- **Saldo Acumulado / Caixa:** [R$ X,XX]
- **Inadimplência Estimada:** [X%]
- **Endividamento:** [Há dívidas? Em quais valores?]

## Veredito
[1-2 parágrafos com justificativa baseada em evidências do documento. Indique se
as contas estão APROVADAS, APROVADAS COM RESSALVAS ou REPROVADAS]

## Pontos Positivos
1. [Ponto 1 - Cite o módulo de origem]
2. [Ponto 2 - Cite o módulo de origem]
3. [Ponto 3 - Cite o módulo de origem]

## Irregularidades e Fragilidades
1. [Irregularidade 1 - Cite o módulo de origem]
2. [Irregularidade 2 - Cite o módulo de origem]
3. [Irregularidade 3 - Cite o módulo de origem]

## Recomendações (Priorizadas)
1. [URGENTE] [Ação corretiva essencial — impacto legal/financeiro]
2. [URGENTE] [Outra ação essencial]
3. [RECOMENDADO] [Melhoria desejável]
4. [SUGERIDO] [Refinamento opcional]

## Parecer à Assembleia
[Parecer formal endereçado aos condôminos:
- Aprovação / Aprovação com ressalvas / Reprovação das contas
- Motivos sintetizados
- Encaminhamentos sugeridos]
- Indicação se o síndico/administradora deve prestar esclarecimentos]

## NOTA GERAL: [0 a 10] — Use a rubrica:
- 9-10: Excelente — contas transparentes, bem documentadas e regularizadas
- 7-8: Bom — contas aceitáveis com pequenas pendências ou melhorias pontuais
- 5-6: Regular — contas com inconsistências significativas que precisam ser esclarecidas
- 3-4: Fraco — irregularidades graves, despesas sem respaldo, problemas estruturais
- 0-2: Inadequado — fraudes, desvio de finalidade, ilegalidade comprovada

## METADADOS ESTRUTURADOS
Ao final da resposta, inclua OBRIGATORIAMENTE o seguinte bloco de código JSON preenchido:
```json
{
  "nota": 0.0,
  "decisao": "Aprovado | Aprovado com Ressalvas | Reprovado",
  "receitas_totais": 0.0,
  "despesas_totais": 0.0,
  "saldo": 0.0,
  "pontos_positivos": ["Ponto 1", "Ponto 2", "Ponto 3"],
  "irregularidades": ["Irregularidade 1", "Irregularidade 2"],
  "recomendacoes_urgentes": ["Recomendação 1", "Recomendação 2"]
}
```""",

    "07": """\
Auditoria quantitativa: verifique totais, rateios e consistência matemática.
Compare valores declarados vs. calculados. Seja conciso.

# Auditoria Quantitativa

## Totais
- **Receitas:** [Declarado vs. Soma dos componentes — ✅ ou ❌ divergência]
- **Despesas:** [Declarado vs. Soma dos componentes — ✅ ou ❌ divergência]
- **Saldo:** [Declarado vs. Receitas-Despesas — ✅ ou ❌ divergência]

## Rateio
- **Unidades:** [N total]
- **Teste:** [2-3 unidades: valor declarado vs. calculado]

## Fundos
- **Reserva:** [Inicial + Recolhimentos - Saídos = Declarado?]
- **Manutenção/Outros:** [Mesma verificação]

## Divergências
[Lista de problemas encontrados com valores específicos]""",

}

# Módulos que são pulados no modo "lite"
# Ética/Legal (02) NUNCA é pulada
LITE_SKIP_MODULES = {"03", "07"}

# ===== Tipos de Condomínio =====
DOMAIN_LABELS = {
    "res": "Residencial",
    "com": "Comercial / Corporativo",
    "mis": "Misto (Residencial + Comercial)",
    "cs": "Condomínio Simples",
}

DOMAIN_GUIDELINES = {
    "res": (
        "Condomínio RESIDENCIAL — aplique as seguintes diretrizes:\n"
        "- Lei 4.591/64 e Código Civil (arts. 1.330 a 1.353)\n"
        "- Atente-se a: rateio por fração ideal, fundo de reserva (mínimo 5% da receita), "
        "condições de moradores, áreas de uso comum (área de lazer, playground, salão de festas)\n"
        "- Verifique conformidade com a convenção condominial e regimento interno\n"
        "- Considere: inadimplência, custo por m², manutenção de elevadores, portaria 24h"
    ),
    "com": (
        "Condomínio COMERCIAL / CORPORATIVO — aplique as seguintes diretrizes:\n"
        "- Atente-se a: locatários vs. proprietários, custos operacionais, "
        "TI e infraestrutura de Rede, custos de compartimentação e fit-outs\n"
        "- Verifique: contrato de administração com empresa especializada, "
        " SLA de manutenção predial, certificações e conformidades de segurança\n"
        "- Considere: rotatividade de inquilinos, custos de representação comercial, "
        "marketing do condomínio"
    ),
    "mis": (
        "Condomínio MISTO (Residencial + Comercial) — aplique as seguintes diretrizes:\n"
        "- Verifique a separação clara de custos entre áreas residenciais e comerciais\n"
        "- Rateio diferenciado: comerciais pagam proporcionalmente mais?\n"
        "- Áreas de uso comum: como são rateadas entre finalidades diferentes?\n"
        "- Conflitos potenciais: horários de funcionamento, ruído, segurança diferenciada\n"
        "- Conformidade: legislação urbanística, alvarás, zoneamento"
    ),
    "cs": (
        "Condomínio SIMPLES — aplique as seguintes diretrizes:\n"
        "- Condomínio pequeno, sem áreas de lazer complexas ou funcionalidades avançadas\n"
        "- Foco: transparência nas contas, rateio simples, fundo de reserva mínimo\n"
        "- Verifique: despesas essenciais (água, luz, limpeza, segurança básica)\n"
        "- Considere: poucas unidades, administração direta pelo síndico, custos reduzidos\n"
        "- Conformidade básica: Lei 4.591/64, prestação de contas anual em assembleia"
    ),
}


def get_notebook_persona(domain: str = "res") -> str:
    """Retorna a persona completa para configurar no notebook via
    `notebooklm configure --persona`.

    Inclui: SYSTEM_PERSONA + domínio + diretrizes.
    Chamado UMA VEZ na criação do notebook (não repetido em cada prompt).
    """
    label = DOMAIN_LABELS.get(domain, DOMAIN_LABELS["res"])
    guideline = DOMAIN_GUIDELINES.get(domain, DOMAIN_GUIDELINES["res"])
    return f"{SYSTEM_PERSONA}\n\n[DOMÍNIO: {label}]\n[DIRETRIZES: {guideline}]"


def get_prompt(module: str, domain: str = "res") -> str:
    """Retorna o prompt do módulo (apenas a instrução de análise).

    A persona e o domínio são configurados no notebook via
    `notebooklm configure --persona` — não precisam ser repetidos aqui.
    """
    prompt = PROMPTS[module]
    if module == "01":
        label = DOMAIN_LABELS.get(domain, DOMAIN_LABELS["res"])
        guideline = DOMAIN_GUIDELINES.get(domain, DOMAIN_GUIDELINES["res"])
        prompt = prompt.replace("[DOMAIN_LABEL_PLACEHOLDER]", label)
        prompt = prompt.replace("[DOMAIN_PROMPT_PLACEHOLDER]", f"Preste atenção especial nestas diretrizes de área:\n{guideline}\n")
    return prompt
