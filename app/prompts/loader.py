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
    """Fallback mínimo usado APENAS se o arquivo .md do módulo estiver ausente.
    Emite um aviso — o fallback não contém instruções de estrutura, domínio nem
    anti-alucinação. O arquivo deve ser restaurado o quanto antes.
    """
    import warnings
    warnings.warn(
        f"Arquivo de prompt para módulo '{module}' não encontrado em {PROMPTS_DIR}. "
        "Usando fallback mínimo — a qualidade da análise será degradada. "
        "Restaure os arquivos do diretório prompts/v6/.",
        RuntimeWarning,
        stacklevel=3,
    )
    fallbacks = {
        "00": "Analise a estrutura do documento e produza um relatório Markdown detalhado.",
        "01": "Realize auditoria metodológica rigorosa e produza um relatório Markdown detalhado.",
        "02": "Realize checklist editorial completo e produza um relatório Markdown detalhado.",
        "03": "Analise o referencial teórico e produza um relatório Markdown detalhado.",
        "04": "Identifique gaps lógicos e produza um relatório Markdown detalhado.",
        "05": "Analise a qualidade da escrita e produza um relatório Markdown detalhado.",
        "06": "Produza o parecer final com nota de 0-10, decisão editorial e bloco JSON de metadados.",
        "07": "Realize auditoria quantitativa e produza um relatório Markdown detalhado.",
    }
    return fallbacks.get(module, f"Analise o documento para o módulo {module} e produza relatório Markdown.")


@lru_cache(maxsize=1)
def get_system_persona() -> str:
    """Carrega a persona do arquivo system_persona.md.

    O arquivo é OBRIGATÓRIO. Se estiver ausente, a aplicação falha no startup
    em vez de usar silenciosamente uma persona inferior (que não contém as
    diretrizes de idioma, citação exata e anti-alucinação).
    """
    persona_file = PROMPTS_DIR / "system_persona.md"
    if not persona_file.exists():
        raise FileNotFoundError(
            f"Arquivo de persona obrigatório não encontrado: {persona_file}\n"
            "Verifique se o diretório prompts/v6/ está completo."
        )
    return persona_file.read_text(encoding="utf-8")


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