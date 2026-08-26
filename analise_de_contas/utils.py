"""
Módulo de utilitários — funções compartilhadas entre app.py e pipeline.py.
"""

import os
import re
import time
from pathlib import Path
from functools import lru_cache


import json


def extract_structured_score(md_text: str) -> dict:
    """Extrai metadados estruturados (nota, decisão, pontos fortes, fragilidades) do módulo 06.

    Prioriza blocos JSON embutidos (```json ... ```) e faz fallback para expressões regulares.
    Retorna dicionário com:
        - nota: float | None
        - decisao: str | None
        - coerencia_narrativa: float | None
        - pontos_fortes: list[str]
        - fragilidades: list[str]
        - recomendacoes_obrigatorias: list[str]
    """
    if not md_text:
        return {
            "nota": None,
            "decisao": None,
            "coerencia_narrativa": None,
            "pontos_fortes": [],
            "fragilidades": [],
            "recomendacoes_obrigatorias": [],
        }

    # 1. Tenta extrair de bloco JSON estruturado
    json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", md_text, flags=re.IGNORECASE)
    for block in reversed(json_blocks):
        try:
            data = json.loads(block)
            if isinstance(data, dict) and ("nota" in data or "decisao" in data):
                nota_val = data.get("nota")
                if nota_val is not None:
                    try:
                        nota_val = float(str(nota_val).replace(",", "."))
                    except (ValueError, TypeError):
                        nota_val = None

                coerencia_val = data.get("coerencia_narrativa")
                if coerencia_val is not None:
                    try:
                        coerencia_val = float(str(coerencia_val).replace(",", "."))
                    except (ValueError, TypeError):
                        coerencia_val = None

                return {
                    "nota": nota_val,
                    "decisao": str(data.get("decisao", "")).strip() or None,
                    "coerencia_narrativa": coerencia_val,
                    "pontos_fortes": list(data.get("pontos_fortes", [])),
                    "fragilidades": list(data.get("fragilidades", [])),
                    "recomendacoes_obrigatorias": list(data.get("recomendacoes_obrigatorias", [])),
                }
        except (json.JSONDecodeError, ValueError):
            continue

    # 2. Fallback via regex
    nota = None
    decisao = None
    coerencia = None

    num_after_label = re.compile(
        r"(?im)^\s*[^a-zA-Z]*"
        r"\*?\s*"
        r"(?:nota\s+final|nota\s+geral|nota)"
        r"[^a-zA-Z\d]*"
        r"(?P<v>\d+(?:[.,]\d+)?)"
    )

    for line in md_text.splitlines():
        if nota is None:
            m = num_after_label.search(line)
            if m:
                try:
                    nota = float(m.group("v").replace(",", "."))
                except ValueError:
                    pass

        if decisao is None:
            m_dec = re.search(r'(?i)\bDECIS[ÃA]O\s*(?:EDITORIAL|FINAL|RECOMENDADA)?\s*[:=\-—]?\s*(?:\*\*\s*)?([A-Za-z\s]+?)(?:\s*\*\*)?$', line)
            if m_dec and m_dec.group(1).strip():
                clean_dec = re.sub(r'\*\*', '', m_dec.group(1)).strip()
                if any(s in clean_dec.lower() for s in ("aprovado", "reprovado", "ressalva", "accept", "reject")):
                    decisao = clean_dec

        if coerencia is None:
            m_coer = re.search(r'(?i)coer[êe]ncia\s*narrativa[^0-9]*(\d+(?:[.,]\d+)?)', line)
            if m_coer:
                try:
                    coerencia = float(m_coer.group(1).replace(",", "."))
                except ValueError:
                    pass

    if nota is None:
        inline = re.search(
            r"(?im)\*\*(?:nota\s*final|nota)\*\*\s*"
            r"[:\-–=]?\s*"
            r"(\d+(?:[.,]\d+)?)",
            md_text,
        )
        if inline:
            try:
                nota = float(inline.group(1).replace(",", "."))
            except ValueError:
                pass

    return {
        "nota": nota,
        "decisao": decisao,
        "coerencia_narrativa": coerencia,
        "pontos_fortes": [],
        "fragilidades": [],
        "recomendacoes_obrigatorias": [],
    }


def extract_nota_from_synthesis(md_text: str) -> float | None:
    """Extrai a nota do texto markdown do módulo 06.

    Suporta formato JSON embutido e variações textuais com fallback regex.
    """
    structured = extract_structured_score(md_text)
    return structured.get("nota")


def sanitize_filename(name: str) -> str:
    """Remove path components e caracteres perigosos do nome do arquivo.

    Exemplos:
        >>> sanitize_filename("../../etc/passwd.pdf")
        'passwd'
        >>> sanitize_filename("paper$(evil).pdf")
        'paper_evil'
        >>> sanitize_filename("paper_v2.pdf")
        'paper_v2'
        >>> sanitize_filename(".pdf")
        'documento'
    """
    name = os.path.basename(name)
    stem = name.rsplit(".", 1)[0] if name.lower().endswith(".pdf") else name
    safe = re.sub(r"[^\w\-]", "_", stem)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "documento"


_rglob_cache: dict[str, tuple[float, list]] = {}


def find_all_peer_review_dirs(base_dir: Path, ttl: int = 60) -> list[Path]:
    """Encontra todos os diretórios peer_review_* no diretório base. Ordenados por modificação.
    
    Cacheia resultado por `ttl` segundos (default 60) para evitar rglob em cada rerun do Streamlit.
    """
    key = str(base_dir.resolve())
    now = time.time()
    cached = _rglob_cache.get(key)
    if cached and (now - cached[0]) < ttl:
        return cached[1]

    dirs = []
    
    # Faz uma busca recursiva, ignorando pastas do app, uploads ou ambientes virtuais
    for p in base_dir.rglob("peer_review_*"):
        if p.is_dir():
            # Ignora se estiver dentro do app, uploads ou pastas ocultas (como .venv, .git)
            if any(part == "app" or part == "uploads" or part.startswith(".") for part in p.parts):
                continue
            dirs.append(p)

    result = sorted(dirs, key=lambda x: x.stat().st_mtime, reverse=True)
    _rglob_cache[key] = (now, result)
    return result


def format_file_size(size_bytes: int) -> str:
    """Formata tamanho de arquivo para exibição legível."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"


def file_icon(extension: str) -> str:
    """Retorna ícone Unicode para um tipo de arquivo."""
    return {
        "md": "📄",
        "csv": "📋",
        "pdf": "📑",
        "pptx": "📊",
        "png": "🖼️",
        "html": "🌐",
        "json": "📎",
    }.get(extension.lower(), "📎")
