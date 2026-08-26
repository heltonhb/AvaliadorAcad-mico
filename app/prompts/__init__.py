"""
Prompts package — externalized prompt files with loader.
"""
from prompts.loader import (
    PROMPTS,
    LITE_SKIP_MODULES,
    get_prompt,
    get_notebook_persona,
    DOMAIN_LABELS,
)

__all__ = [
    "PROMPTS",
    "LITE_SKIP_MODULES",
    "get_prompt",
    "get_notebook_persona",
    "DOMAIN_LABELS",
]