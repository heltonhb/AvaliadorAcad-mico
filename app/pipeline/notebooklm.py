"""Operações com NotebookLM: create, configure, ask, artifacts com suporte a multi-profile."""
import json
import os
import re
import subprocess
import tempfile
import time

from pipeline.utils import run_cmd


def _nlm_cmd(*args):
    """Monta comando base notebooklm incluindo --profile se especificado."""
    cmd = ["notebooklm"]
    profile = os.environ.get("NOTEBOOKLM_PROFILE")
    if profile and profile != "default":
        cmd.extend(["--profile", profile])
    cmd.extend(args)
    return cmd


def create_notebook(title):
    """Cria notebook no NotebookLM e retorna o ID."""
    cmd = _nlm_cmd("create", title)
    stdout, _, code = run_cmd(cmd)
    if code == 0:
        match = re.search(r"Created notebook: ([a-f0-9-]+)", stdout)
        if match:
            return match.group(1)
    return None


def configure_notebook(nb_id, persona_text):
    """Configura a persona do revisor no notebook."""
    cmd = _nlm_cmd(
        "configure",
        "--notebook", nb_id,
        "--persona", persona_text,
        "--response-length", "longer",
    )
    _, stderr, code = run_cmd(cmd)
    return code == 0, stderr


def add_source(nb_id, path):
    """Adiciona PDF como fonte ao notebook."""
    cmd = _nlm_cmd("source", "add", "--notebook", nb_id, str(path))
    _, _, code = run_cmd(cmd)
    return code == 0


def wait_source(nb_id, timeout=None):
    """Aguarda o notebook indexar o PDF com polling exponencial."""
    timeout = timeout or int(os.environ.get("WAIT_SOURCE_TIMEOUT", "240"))
    delay = 1
    max_delay = 15
    elapsed = 0
    while elapsed < timeout:
        cmd = _nlm_cmd("source", "list", "--notebook", nb_id, "--json")
        stdout, _, code = run_cmd(cmd)
        if code == 0:
            try:
                data = json.loads(stdout)
                sources = data.get("sources", [])
                if sources and sources[0].get("status") == "ready":
                    return True
            except (json.JSONDecodeError, IndexError, KeyError):
                pass
        time.sleep(delay)
        elapsed += delay
        delay = min(delay * 2, max_delay)
    return False


def run_ask(nb_id, prompt, output_file):
    """Executa pergunta ao notebook e salva resposta em arquivo."""
    prompt_fd, prompt_file = tempfile.mkstemp(suffix=".txt", prefix="prompt_")
    try:
        with os.fdopen(prompt_fd, "w", encoding="utf-8") as f:
            f.write(prompt)

        cmd = _nlm_cmd("ask", "--notebook", nb_id, "--prompt-file", prompt_file)
        with open(output_file, "w", encoding="utf-8") as out_f:
            r = subprocess.run(
                cmd, shell=False, stdout=out_f, stderr=subprocess.STDOUT,
                text=True, timeout=300,
            )

        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            if size > 100:
                add_source(nb_id, output_file)
                return True
            return False
        return False
    finally:
        if os.path.exists(prompt_file):
            os.remove(prompt_file)


def generate_artifact(nb_id, artifact_type, description, extra_args=None):
    """Gera artefato via notebooklm generate. Retorna (artifact_id, rate_limited)."""
    desc_fd, desc_file = tempfile.mkstemp(suffix=".txt", prefix="art_desc_")
    try:
        with os.fdopen(desc_fd, "w", encoding="utf-8") as f:
            f.write(description)
        rate_limited = False
        base_cmd = _nlm_cmd(
            "generate", artifact_type,
            "--notebook", nb_id, "--prompt-file", desc_file,
            "--wait", "--timeout", os.environ.get("GENERATE_TIMEOUT", "600"),
            "--retry", "3",
        )
        if extra_args:
            base_cmd.extend(extra_args)
        base_delay = 15
        for attempt in range(3):
            stdout, stderr, code = run_cmd(base_cmd, timeout=650)
            match = re.search(r"(?:Task|Artifact|ID):\s*([a-f0-9-]+)", stdout, re.IGNORECASE)
            if match:
                return match.group(1), False
            if "RateLimit" in (stderr or "") or "rate limit" in (stderr or "").lower():
                delay = base_delay * (2 ** attempt)
                rate_limited = True
                time.sleep(delay)
            else:
                break
        return None, rate_limited
    finally:
        if os.path.exists(desc_file):
            os.remove(desc_file)


def download_artifact(nb_id, artifact_type, artifact_id, output_path):
    """Baixa artefato gerado pelo NotebookLM garantindo o ID correto e sobrescrita."""
    cmd = _nlm_cmd("download", artifact_type, "--notebook", nb_id)
    if artifact_id:
        cmd.extend(["-a", str(artifact_id)])
    cmd.extend(["--force", str(output_path)])
    _, _, code = run_cmd(cmd, timeout=120)
    return code == 0
