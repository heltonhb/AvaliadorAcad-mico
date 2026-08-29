"""
hf_integration.py — Integração Hugging Face para AnaliseTextos v6.0

Usa HF_TOKEN do .env (validado: heltonhb1912) para:
- whoami / list_models via huggingface_hub
- Inference API (serverless) via httpx + Bearer HF_TOKEN
- Download/caching de modelos via hf download

Gateway token (HF_GATEWAY_TOKEN) é armazenado mas NÃO é um token HF válido
(Invalid user token) — mantido para uso com gateway alternativo se necessário.

Uso:
    from hf_integration import get_hf_token, hf_whoami, hf_inference, list_recommended_models
    token = get_hf_token()
    info = hf_whoami()
    emb = hf_inference("sentence-transformers/all-MiniLM-L6-v2", "texto científico")

Requisitos mínimos: huggingface_hub, httpx, python-dotenv
Opcionais: transformers, sentence-transformers (para inferência local)
"""
import os
from pathlib import Path
from functools import lru_cache

import dotenv

# Carrega .env do app
dotenv.load_dotenv(Path(__file__).parent / ".env")
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")

HF_API = "https://api-inference.huggingface.co/models"
HF_WHOAMI_URL = "https://huggingface.co/api/whoami-v2"

RECOMMENDED_MODELS = {
    "embeddings": [
        "sentence-transformers/all-MiniLM-L6-v2",  # 384 dim, rápido, 80MB
        "sentence-transformers/all-mpnet-base-v2",  # 768 dim, melhor qualidade
        "BAAI/bge-m3",  # multilíngue, inclui PT-BR
    ],
    "summarization": [
        "facebook/bart-large-cnn",
        "google/pegasus-xsum",
    ],
    "scientific": [
        "allenai/scibert_scivocab_uncased",  # BERT científico
        "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract",
        "allenai/specter",  # embeddings de papers
    ],
    "portuguese": [
        "neuralmind/bert-base-portuguese-cased",
        "pierreguillou/bert-base-cased-squad-v1.1-portuguese",
    ],
}


def get_hf_token() -> str | None:
    """Retorna HF_TOKEN do env (ou None se ausente)."""
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")


def get_gateway_token() -> str | None:
    """Token de gateway alternativo (não HF)."""
    return os.environ.get("HF_GATEWAY_TOKEN")


@lru_cache(maxsize=1)
def hf_whoami() -> dict | None:
    """Valida token e retorna info do usuário (cacheado)."""
    token = get_hf_token()
    if not token:
        return None
    try:
        from huggingface_hub import whoami
        return whoami(token=token)
    except Exception:
        # Fallback via API direta
        try:
            import httpx
            r = httpx.get(HF_WHOAMI_URL, headers={"Authorization": f"Bearer {token}"}, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None


def hf_inference(model_id: str, inputs, params: dict | None = None, timeout: int = 30) -> dict | list:
    """
    Chama Inference API serverless: POST https://api-inference.huggingface.co/models/{model_id}
    Retorna JSON (embeddings, summary, etc. dependendo do modelo).
    """
    token = get_hf_token()
    if not token:
        raise RuntimeError("HF_TOKEN não configurado — defina no .env")
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"inputs": inputs}
    if params:
        payload["parameters"] = params
    r = httpx.post(f"{HF_API}/{model_id}", headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def hf_download_model(model_id: str, cache_dir: str | None = None) -> Path:
    """Baixa modelo via huggingface_hub snapshot_download."""
    from huggingface_hub import snapshot_download
    token = get_hf_token()
    return Path(snapshot_download(model_id, token=token, cache_dir=cache_dir))


def list_recommended_models(category: str | None = None) -> dict | list:
    """Lista modelos recomendados para análise científica."""
    if category:
        return RECOMMENDED_MODELS.get(category, [])
    return RECOMMENDED_MODELS


# --- Helpers para pipeline ---

def get_embeddings_via_api(texts: list[str] | str, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> list[list[float]]:
    """
    Gera embeddings via Inference API (sem precisar baixar modelo local).
    Usa mean pooling se o modelo retornar token embeddings.
    """
    result = hf_inference(model, texts)
    # Inference API para embeddings retorna lista de vetores ou lista de lista
    if isinstance(result, list) and result and isinstance(result[0], list):
        # Já é lista de embeddings
        if isinstance(result[0][0], float):
            return [result] if isinstance(texts, str) else result
        # Token-level embeddings — faz mean pooling simples
        import statistics
        # result shape: [tokens, dim] para single input
        if isinstance(texts, str):
            # Mean pool
            dim = len(result[0])
            pooled = [sum(t[d] for t in result) / len(result) for d in range(dim)]
            return [pooled]
        # Batch: lista de lista de tokens
        pooled_batch = []
        for emb in result:
            dim = len(emb[0])
            pooled = [sum(t[d] for t in emb) / len(emb) for d in range(dim)]
            pooled_batch.append(pooled)
        return pooled_batch
    return result


def check_hf_setup() -> dict:
    """Health check para /api/health/ready — verifica HF."""
    token = get_hf_token()
    if not token:
        return {"status": "missing", "detail": "HF_TOKEN não configurado"}
    info = hf_whoami()
    if info and info.get("name"):
        return {"status": "ok", "user": info.get("name"), "type": info.get("type")}
    return {"status": "error", "detail": "Falha ao validar HF_TOKEN (whoami)"}
