"""
Prompt loader — reads prompts from external markdown files.
Allows versioning, hot-reload, and A/B testing of prompts.
"""
import os
import re
from pathlib import Path
from functools import lru_cache

PROMPTS_DIR = Path(__file__).parent / "v6"
DOMAINS_DIR = PROMPTS_DIR / "domains"

# Cache for loaded prompts
_prompt_cache: dict[str, str] = {}
_domain_cache: dict[str, str] = {}

def _read_prompt_file(module: str) -> str:
    """Read prompt from markdown file."""
    # Try exact match first
    for ext in [".md", ".txt"]:
        prompt_file = PROMPTS_DIR / f"{module}{ext}"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")

    # Try with module prefix (e.g., 00_estrutura_documento.md)
    for prompt_file in PROMPTS_DIR.glob(f"{module}_*.md"):
        return prompt_file.read_text(encoding="utf-8")

    # Fallback to hardcoded prompts
    return _get_fallback_prompt(module)


def _read_domain_file(domain: str) -> str:
    """Read domain guidelines from markdown file."""
    domain_file = DOMAINS_DIR / f"{domain}.md"
    if domain_file.exists():
        return domain_file.read_text(encoding="utf-8")
    return ""


def _get_fallback_prompt(module: str) -> str:
    """Fallback prompts if files don't exist."""
    fallbacks = {
        "00": "Analise a estrutura do documento.",
        "01": "Realize auditoria metodologica.",
        "02": "Realize checklist editorial.",
        "03": "Analise referencial teorico.",
        "04": "Identifique gaps logicos.",
        "05": "Analise qualidade da escrita.",
        "06": "Produza parecer final.",
        "07": "Realize auditoria quantitativa.",
    }
    return fallbacks.get(module, "")


@lru_cache(maxsize=1)
def get_system_persona() -> str:
    """Load system persona from file or use default."""
    persona_file = PROMPTS_DIR / "system_persona.md"
    if persona_file.exists():
        return persona_file.read_text(encoding="utf-8")
    return """Você é um Revisor Acadêmico Sênior — Parecerista com mais de 15 anos de experiência em
avaliação para periódicos Qualis A1 / Q1 (JCR/Scopus). Possui expertise em metodologia de
pesquisa, análise estatística e ética em publicação científica.

DIRETRIZES DE CONDUTA:
1. Tom: Rigoroso, mas construtivo. Aponte falhas com justificativa e sugira correções.
2. Ancoragem factual: Baseie-se EXCLUSIVAMENTE no documento fornecido. Se uma informação
   não existir no texto, declare 'NÃO ENCONTRADO NO DOCUMENTO'.
3. Calibração de certeza: Diferencie afirmações definitivas de observações prováveis.
   Use 'O documento não apresenta...' ao invés de 'Não há...'.
4. Evidência textual: Para cada crítica, cite o trecho ou seção específica do documento.
5. Priorização: Classifique problemas por impacto na validade científica do trabalho.
6. Idioma: Detecte o idioma predominante do documento e produza a análise nesse idioma.
7. Consistência Modular: Cada módulo alimenta o seguinte. Seja consistente em suas avaliações entre módulos."""


def get_prompt(module: str, domain: str = "cs") -> str:
    """Get prompt for a module with domain-specific guidelines injected."""
    # Load base prompt
    base_prompt = _read_prompt_file(module)

    # Load domain guidelines
    domain_guidelines = _read_domain_file(domain)
    domain_label = _get_domain_label(domain)

    # Inject domain-specific content
    prompt = base_prompt.replace("{{DOMAIN_PROMPT}}", domain_guidelines)
    prompt = prompt.replace("{{DOMAIN_LABEL}}", domain_label)
    prompt = prompt.replace("{{DOMAIN_GUIDELINES}}", domain_guidelines)

    return prompt


def get_notebook_persona(domain: str = "cs") -> str:
    """Get complete persona for notebook configuration."""
    persona = get_system_persona()
    domain_label = _get_domain_label(domain)
    domain_guidelines = _read_domain_file(domain)
    return f"{persona}\n\n[DOMÍNIO: {domain_label}]\n[DIRETRIZES: {domain_guidelines}]"


def _get_domain_label(domain: str) -> str:
    """Get human-readable domain label."""
    labels = {
        "cs": "Computação",
        "med": "Medicina e Ciências da Saúde",
        "human": "Humanidades e Ciências Sociais",
    }
    return labels.get(domain, domain)


# Módulos que são pulados no modo "lite"
# NOTA v6.0: Ética (02) NUNCA é pulada — apenas SOTA (03) e Quantitativa (07)
LITE_SKIP_MODULES = {"03", "07"}

# Domínios suportados
DOMAIN_LABELS = {
    "cs": "Computação",
    "med": "Medicina e Ciências da Saúde",
    "human": "Humanidades e Ciências Sociais",
}

# Pre-load all prompts for backwards compatibility
PROMPTS = {f"{i:02d}": get_prompt(f"{i:02d}") for i in range(8)}