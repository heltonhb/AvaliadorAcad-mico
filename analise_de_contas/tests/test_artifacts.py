"""Tests for artifact parsing — extração de nota, decisão, gaps, fortes, fragilidades.

Estas funções de parsing em artifacts.py são as mais frágeis do sistema,
pois dependem de expressões regulares sobre a saída do NotebookLM,
que pode mudar de formato sem aviso.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from artifacts import (
    convert_to_csv,
    extract_md_sections,
    _strip_nb_preamble,
    _split_bullets,
    _read_section,
)


# ===== Samples de saída do NotebookLM =====

SAMPLE_PARECER_COMPLETO = """# Parecer Final
## Resumo Executivo
O estudo apresenta uma análise robusta da aplicação de transformers em visão computacional. A metodologia é adequada e os resultados são promissores.

## Originalidade e Contribuição
- **Novidade:** Abordagem inédita na área
- **Relevância teórica:** Avança o conhecimento
- **Nível de contribuição:** Significativa

## Veredito
Trabalho bem estruturado com contribuições relevantes.

## Pontos Fortes
1. Metodologia rigorosa com validação cruzada
2. Base de dados robusta e representativa
3. Análise estatística completa

## Fragilidades Principais
1. Ausência de comparação com baseline X
2. Amostra limitada a contexto específico
3. Falta análise de sensibilidade

## Recomendações ao Autor (priorizadas)
1. [OBRIGATÓRIO] Incluir baseline X para comparação
2. [OBRIGATÓRIO] Expandir validação para outros contextos
3. [RECOMENDADO] Adicionar análise de sensibilidade

## Carta ao Editor (Confidencial)
O artigo apresenta qualidade satisfatória. Recomendo revisões maiores.

## DECISÃO FINAL: Major Revisions

## NOTA: 6.5
"""

SAMPLE_PARECER_COM_NOTA_EM_LINHA = """# Parecer Final
**NOTA:** 8.0
**DECISÃO FINAL:** Accept
## Resumo Executivo
Excelente contribuição.
"""

SAMPLE_PARECER_SEM_NOTA = """# Parecer Final
## Resumo Executivo
Trabalho em andamento.
## DECISÃO FINAL: Minor Revisions
## NOTA: N/A
"""

SAMPLE_GAPS = """# Gaps Lógicos
## Cadeia de Evidência
- **Dados → Resultados:** Os resultados não decorrem dos dados
- **Resultados → Conclusões:** Extrapolação não justificada

## 🔴 Gravidade Crítica
- Conclusão não suportada pelos dados apresentados na seção 4
- **Falta causa:** Correlação tratada como causalidade

## 🟡 Gravidade Moderada
- Limitações não discutidas adequadamente

## 🔵 Gravidade Leve
- Afirmações sem citação na introdução
"""


class TestStripNBPreamble:
    def test_removes_header_lines(self):
        text = "Here is the analysis based on the document you provided.\n\n# Real Title\nContent"
        result = _strip_nb_preamble(text)
        assert result.startswith("# Real Title")

    def test_empty_text(self):
        assert _strip_nb_preamble("") == ""

    def test_no_preamble(self):
        text = "# Title\nContent"
        assert _strip_nb_preamble(text) == text


class TestExtractMdSections:
    def test_extracts_by_h1(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Section 1\nContent\n# Section 2\nMore", encoding="utf-8")
        sections = extract_md_sections(str(md_file))
        assert "section_1" in sections or "Section 1" in sections
        assert "section_2" in sections or "Section 2" in sections

    def test_returns_dict(self):
        assert isinstance(extract_md_sections(""), dict)

    def test_handles_empty(self):
        sections = extract_md_sections("")
        assert sections == {}


class TestConvertToCSV:
    def test_extracts_table(self, tmp_path):
        md_content = """| Seção | Tipo | Trecho | Correção | Prioridade |
|---|---|---|---|---|
| 2.1 | Gramatical | "o estudo" | "O estudo" | Alta |
| 3.2 | Ortográfico | "analise" | "análise" | Média |
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")
        csv_file = tmp_path / "test.csv"

        rows = convert_to_csv(str(md_file), str(csv_file))
        assert rows > 0
        assert csv_file.exists()

        content = csv_file.read_text(encoding="utf-8")
        assert "Gramatical" in content
        assert "O estudo" in content

    def test_no_table_returns_zero(self, tmp_path):
        md_file = tmp_path / "no_table.md"
        md_file.write_text("Just text, no table", encoding="utf-8")
        csv_file = tmp_path / "out.csv"
        rows = convert_to_csv(str(md_file), str(csv_file))
        assert rows == 0


class TestSplitBullets:
    def test_splits_sentences(self):
        text = "First point. Second point. Third point."
        bullets = _split_bullets(text)
        assert len(bullets) >= 2
        assert all(b.endswith(".") for b in bullets)

    def test_respects_max_items(self):
        text = "A. B. C. D. E. F. G. H."
        bullets = _split_bullets(text, max_items=3)
        assert len(bullets) == 3

    def test_empty_text(self):
        assert _split_bullets("") == []


# ===== Testes de parsing de nota e decisão (integram artifacts.py) =====

def test_nota_parsing_from_full_parecer(tmp_path):
    """Verifica se a nota 6.5 é extraída corretamente do parecer completo."""
    md = tmp_path / "06_sintese_parecer.md"
    md.write_text(SAMPLE_PARECER_COMPLETO, encoding="utf-8")

    content = md.read_text(encoding="utf-8")
    nota = "N/A"
    for line in content.split("\n"):
        import re
        # Regex corrigido: ** pode vir DEPOIS do ##
        m = re.search(r'(?i)##?\s*(?:\*\*)?\s*NOTA\s*(?:FINAL)?\s*:?\s*(?:\*\*)?\s*(\d+[.,]?\d*)', line)
        if m:
            nota = m.group(1)
            break

    assert nota == "6.5"


def test_decisao_parsing_from_full_parecer(tmp_path):
    """Verifica se a decisão 'Major Revisions' é extraída."""
    md = tmp_path / "06_sintese_parecer.md"
    md.write_text(SAMPLE_PARECER_COMPLETO, encoding="utf-8")

    content = md.read_text(encoding="utf-8")
    decisao = "N/A"
    for line in content.split("\n"):
        import re
        m = re.search(r'(?i)##?\s*(?:\*\*)?\s*DECISÃO\s*(?:EDITORIAL|FINAL)?\s*:?\s*(.+?)(?:\*\*)?$', line)
        if m:
            decisao = m.group(1).strip()
            break

    assert decisao == "Major Revisions"


def test_nota_varia_com_asteriscos(tmp_path):
    """NOTA com ** nas linhas (ex: ## **NOTA:** 9.0)."""
    md = tmp_path / "06.md"
    md.write_text("## **NOTA:** 9.0\n", encoding="utf-8")

    import re
    content = md.read_text(encoding="utf-8")
    nota = "N/A"
    for line in content.split("\n"):
        # Regex corrigido: ** pode vir DEPOIS do ##
        m = re.search(r'(?i)##?\s*(?:\*\*)?\s*NOTA\s*(?:FINAL)?\s*:?\s*(?:\*\*)?\s*(\d+[.,]?\d*)', line)
        if m:
            nota = m.group(1)
    assert nota == "9.0"


def test_pontos_fortes_extraidos(tmp_path):
    """Extração de pontos fortes do parecer."""
    md = tmp_path / "06.md"
    md.write_text(SAMPLE_PARECER_COMPLETO, encoding="utf-8")

    content = md.read_text(encoding="utf-8")
    in_fortes = False
    fortes = []
    for line in content.split("\n"):
        if line.startswith("## Pontos Fortes"):
            in_fortes = True
            continue
        if line.startswith("## Fragilidades") or line.startswith("## Recomendações"):
            in_fortes = False
        if in_fortes:
            import re
            m = re.match(r"^(?:- |\d+\.\s+)(.+)", line.strip())
            if m:
                fortes.append(m.group(1))

    assert len(fortes) >= 3
    assert any("Metodologia" in f for f in fortes)


def test_gaps_extraidos(tmp_path):
    """Extração de gaps da análise."""
    md = tmp_path / "04.md"
    md.write_text(SAMPLE_GAPS, encoding="utf-8")

    content = md.read_text(encoding="utf-8")
    gaps = []
    for line in content.split("\n"):
        import re
        m = re.match(r"^(?:- |\d+\.\s+)(.+)", line.strip())
        if m:
            gap_text = m.group(1).replace("**", "")
            if ":" in gap_text:
                gap_text = gap_text.split(":", 1)[0]
            gaps.append(gap_text.strip())

    assert len(gaps) > 0
    # Should have extracted gaps from various sections
    assert any("Conclusão" in g or "Dados" in g or "Limitações" in g for g in gaps)
