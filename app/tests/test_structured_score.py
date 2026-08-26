"""Testes para extração estruturada de score e endpoint de comparação."""
import pytest
from utils import extract_structured_score, extract_nota_from_synthesis


def test_extract_structured_score_json_block():
    md = """
    # Parecer Final
    O artigo apresenta contribuição válida.

    ```json
    {
      "nota": 9.2,
      "decisao": "Accept",
      "coerencia_narrativa": 9.0,
      "pontos_fortes": ["Algoritmo inovador", "Avaliação experimental sólida"],
      "fragilidades": ["Falta discussão de trabalhos futuros"],
      "recomendacoes_obrigatorias": ["Adicionar seção de limitações"]
    }
    ```
    """
    res = extract_structured_score(md)
    assert res["nota"] == 9.2
    assert res["decisao"] == "Accept"
    assert res["coerencia_narrativa"] == 9.0
    assert len(res["pontos_fortes"]) == 2
    assert len(res["fragilidades"]) == 1
    assert extract_nota_from_synthesis(md) == 9.2


def test_extract_structured_score_regex_fallback():
    md = """
    # Parecer Final
    ## NOTA FINAL: 7,5/10
    ## DECISÃO FINAL: Minor Revisions
    ## ÍNDICE DE COERÊNCIA NARRATIVA: 8.0
    """
    res = extract_structured_score(md)
    assert res["nota"] == 7.5
    assert res["decisao"] == "Minor Revisions"
    assert res["coerencia_narrativa"] == 8.0
