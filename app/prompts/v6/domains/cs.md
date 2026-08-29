Avalie conforme normas IEEE / ACM / SBC / CORE. Preste atenção especial a:

**Reprodutibilidade computacional:**
- Código-fonte disponível em repositório público (GitHub, Zenodo, etc.)
- Dataset aberto com DOI ou link permanente
- Especificação de sementes aleatórias (random seeds) para experimentos estocásticos
- Hardware utilizado (GPU, CPU, RAM) e versões exatas de bibliotecas e frameworks

**Conformidade FAIR:**
- Findable: artefatos possuem identificadores persistentes (DOI)?
- Accessible: dados acessíveis sem barreiras injustificadas?
- Interoperable: formatos padrão de dados (CSV, JSON, HDF5)?
- Reusable: licença explícita (MIT, Apache, CC)?

**Rigor experimental:**
- Baselines atualizadas (estado da arte no período de submissão)?
- Estudos de ablação (ablation studies) reportados?
- Análise de sensibilidade a hiperparâmetros?
- Testes de significância estatística (Wilcoxon, bootstrap, etc.) com correção para múltiplas comparações?
- Intervalo de confiança ou desvio padrão reportado para todas as métricas?

**Validação:**
- Separação estrita treino / validação / teste (sem data leakage)?
- Cross-validation adequada ao tamanho do dataset?
- Conjunto de teste mantido intocado até avaliação final?
- Métricas adequadas ao problema (ex: F1 para classes desbalanceadas, não apenas acurácia)?

**Rubrica de peso por critério (CS):**
- Reprodutibilidade: 25%
- Rigor experimental e baselines: 25%
- Validação e métricas: 20%
- Contribuição técnica ao estado da arte: 20%
- Qualidade da escrita e estrutura: 10%
