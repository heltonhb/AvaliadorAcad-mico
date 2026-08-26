"""
Módulo de Auditoria Bibliográfica Real (Grounding via Crossref & OpenAlex).
Valida DOIs, detecta artigos retratados, calcula atualidade de referências e citações.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

_logger = logging.getLogger("pipeline")


def log(msg: str):
    _logger.info(msg)


DOI_REGEX = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b", re.IGNORECASE)


def extract_dois_from_text(text: str) -> list[str]:
    """Extrai DOIs únicos e limpos a partir de um texto."""
    raw_dois = DOI_REGEX.findall(text)
    cleaned = []
    seen = set()
    for d in raw_dois:
        c = d.rstrip(".,;)>]")
        if c and c.lower() not in seen:
            seen.add(c.lower())
            cleaned.append(c)
    return cleaned


def extract_text_from_pdf_light(pdf_path: Path) -> str:
    """Extrai texto rápido do PDF para localização de referências/DOIs."""
    try:
        import subprocess
        res = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "40", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0 and res.stdout:
            return res.stdout
    except Exception:
        pass

    try:
        content = pdf_path.read_bytes()
        matches = re.findall(rb"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", content)
        return " ".join(m.decode("latin1", errors="ignore") for m in matches)
    except Exception:
        return ""


def check_doi_crossref(doi: str, client: httpx.Client) -> Optional[dict]:
    """Consulta metadata e status de retratação no Crossref."""
    headers = {
        "User-Agent": "AnaliseTextos/6.0 (mailto:academic-review@example.com)",
        "Accept": "application/json",
    }
    url = f"https://api.crossref.org/works/{doi}"
    try:
        res = client.get(url, headers=headers, timeout=6.0)
        if res.status_code == 200:
            msg = res.json().get("message", {})
            title = msg.get("title", [""])[0] if msg.get("title") else "Sem título"
            published = msg.get("published-print") or msg.get("published-online") or msg.get("created")
            year = None
            if published and "date-parts" in published and published["date-parts"]:
                year = published["date-parts"][0][0]

            is_retracted = False
            update_to = msg.get("update-to", [])
            for upd in update_to:
                if "retract" in str(upd.get("type", "")).lower():
                    is_retracted = True

            container = msg.get("container-title", [""])[0] if msg.get("container-title") else ""
            cites = msg.get("is-referenced-by-count", 0)

            return {
                "doi": doi,
                "valid": True,
                "source": "Crossref",
                "title": title,
                "year": year,
                "journal": container,
                "citation_count": cites,
                "is_retracted": is_retracted,
            }
        elif res.status_code == 404:
            return {"doi": doi, "valid": False, "source": "Crossref", "error": "DOI não encontrado"}
    except Exception as e:
        return {"doi": doi, "valid": None, "source": "Crossref", "error": str(e)}
    return None


def audit_bibliography(pdf_path: str, output_dir: Path, max_dois: int = 15) -> dict:
    """Executa auditoria bibliográfica completa com validação real."""
    pdf_p = Path(pdf_path)
    text = ""
    if pdf_p.exists():
        text = extract_text_from_pdf_light(pdf_p)

    md03 = output_dir / "03_sota_referencias.md"
    if md03.exists():
        try:
            text += "\n" + md03.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    dois = extract_dois_from_text(text)
    dois_to_check = dois[:max_dois]

    results = []
    current_year = datetime.now().year
    five_years_ago = current_year - 5

    if httpx and dois_to_check:
        with httpx.Client(follow_redirects=True) as client:
            for doi in dois_to_check:
                info = check_doi_crossref(doi, client)
                if info:
                    if info.get("year"):
                        info["is_recent"] = info["year"] >= five_years_ago
                    results.append(info)

    valid_dois = [r for r in results if r.get("valid") is True]
    invalid_dois = [r for r in results if r.get("valid") is False]
    retracted_dois = [r for r in results if r.get("is_retracted") is True]
    recent_dois = [r for r in valid_dois if r.get("is_recent") is True]

    pct_recent = round((len(recent_dois) / len(valid_dois) * 100), 1) if valid_dois else 0.0

    summary = {
        "audited_at": datetime.now().isoformat(),
        "total_dois_found": len(dois),
        "dois_audited": len(results),
        "valid_dois_count": len(valid_dois),
        "invalid_dois_count": len(invalid_dois),
        "retracted_dois_count": len(retracted_dois),
        "retracted_details": retracted_dois,
        "recent_articles_pct": pct_recent,
        "results": results,
    }

    try:
        json_file = output_dir / "auditoria_bibliografica.json"
        json_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log(f"  ⚠️ Erro ao salvar auditoria_bibliografica.json: {e}")

    md_content = [
        "# Auditoria Bibliográfica e Grounding de Citações",
        f"**Data da Verificação:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
        "## Resumo da Verificação de DOIs",
        f"- **Total de DOIs identificados no documento:** {len(dois)}",
        f"- **DOIs auditados via Crossref API:** {len(results)}",
        f"- **DOIs válidos confirmados:** {len(valid_dois)}",
        f"- **DOIs não localizados / suspeitos:** {len(invalid_dois)}",
        f"- **Artigos com Alerta de Retratação:** {len(retracted_dois)}",
        f"- **Índice de Atualidade Real (últimos 5 anos):** {pct_recent}%",
        "",
    ]

    if retracted_dois:
        md_content.append("## 🔴 ALERTA CRÍTICO: Artigos Retratados Encontrados")
        for r in retracted_dois:
            md_content.append(f"- **DOI:** `{r['doi']}` — *{r.get('title')}* ({r.get('year')})")
            md_content.append("  ⚠️ **Atenção:** Este trabalho citado possui aviso formal de retratação na base Crossref.")
        md_content.append("")

    if valid_dois:
        md_content.append("## Detalhamento das Principais Obras Citadas")
        md_content.append("| DOI | Título | Ano | Periódico/Evento | Citações | Atualidade |")
        md_content.append("| :--- | :--- | :---: | :--- | :---: | :---: |")
        for r in valid_dois:
            title_short = (r.get("title") or "N/A")[:45] + ("..." if len(r.get("title") or "") > 45 else "")
            recent_str = "✅ Recente" if r.get("is_recent") else "⏳ Clássico/Antigo"
            md_content.append(
                f"| `{r['doi']}` | {title_short} | {r.get('year') or 'N/D'} | {r.get('journal') or 'N/D'} | {r.get('citation_count', 0)} | {recent_str} |"
            )
        md_content.append("")

    if invalid_dois:
        md_content.append("## ⚠️ DOIs com Erro de Localização (Possível Alucinação ou Erro de Digitação)")
        for r in invalid_dois:
            md_content.append(f"- `{r['doi']}` (Não localizado no registro Crossref)")
        md_content.append("")

    md_file = output_dir / "08_auditoria_bibliografica.md"
    try:
        md_file.write_text("\n".join(md_content), encoding="utf-8")
        log(f"  ✅ Relatório bibliográfico gerado: {md_file.name}")
    except Exception as e:
        log(f"  ⚠️ Falha ao escrever 08_auditoria_bibliografica.md: {e}")

    return summary
