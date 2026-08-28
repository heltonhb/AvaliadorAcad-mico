"""Orquestrador do pipeline (main + _run_pipeline)."""
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import dotenv

from pipeline.constants import APP_DIR, CHECKPOINT_FILE
from pipeline.lock import acquire_pipeline_lock, release_pipeline_lock
from pipeline.checkpoint import load_checkpoint, save_checkpoint, save_step
from pipeline.utils import run_cmd, check_ocr_needed, compress_pdf_if_large
from pipeline.notebooklm import (
    create_notebook,
    configure_notebook,
    add_source,
    wait_source,
    run_ask,
    generate_artifact,
    download_artifact,
)
from prompts.loader import PROMPTS, LITE_SKIP_MODULES, get_prompt, get_notebook_persona
from artifacts import convert_to_csv, generate_mira_artifact
from pipeline.bibliography import audit_bibliography
from pipeline.pdf_report import generate_official_pdf_report

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
_logger = logging.getLogger("pipeline")


def log(msg):
    _logger.info(msg)


def _persist_score_json(output_dir):
    """Extrai a NOTA do MD 06_sintese_parecer.md e escreve output_dir/score.json.

    O score.json é a fonte de verdade para o dashboard (não precisamos re-parsear
    o MD a cada request). Se a nota não for encontrada, não escreve — mantém MD
    como fonte e o front pode dar fallback.
    """
    from utils import extract_nota_from_synthesis

    md_path = Path(output_dir) / "06_sintese_parecer.md"
    if not md_path.exists():
        log("  ⚠️ score.json não gerado: 06_sintese_parecer.md ausente")
        return None
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log(f"  ⚠️ Não foi possível ler 06: {exc}")
        return None

    nota = extract_nota_from_synthesis(text)
    if nota is None:
        log("  ⚠️ NOTA FINAL não encontrada em 06 (score.json não escrito)")
        return None

    score = {
        "nota": nota,
        "extracted_at": datetime.now().isoformat(),
        "source": "06_sintese_parecer.md",
    }
    try:
        score_path = Path(output_dir) / "score.json"
        score_path.write_text(
            json.dumps(score, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log(f"  ✅ score.json escrito (nota {nota})")
    except OSError as exc:
        log(f"  ⚠️ Falha ao escrever score.json: {exc}")
    return nota


# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de análise peer-review via NotebookLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python pipeline.py paper.pdf
  python pipeline.py paper.pdf --domain med --mode lite
  python pipeline.py paper.pdf --resume
""",
    )
    parser.add_argument("pdf", help="Caminho para o PDF a analisar")
    parser.add_argument("--domain", choices=["cs", "med", "human"], default="cs",
                        help="Domínio acadêmico (default: cs)")
    parser.add_argument("--mode", choices=["full", "lite"], default="full",
                        help="Modo full (7 módulos) ou lite (5 módulos)")
    parser.add_argument("--output-dir", dest="output_dir", default=None,
                        help="Diretório de saída (default: ao lado do PDF)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--force", action="store_true", dest="force",
                       help="Forçar re-execução completa")
    group.add_argument("--resume", dest="force", action="store_false",
                       help="Retomar de checkpoint existente (default)")
    parser.set_defaults(force=False)
    args = parser.parse_args()

    pdf_path = args.pdf
    domain = args.domain
    mode = args.mode
    force = args.force

    if not os.path.exists(pdf_path):
        log(f"❌ PDF não encontrado: {pdf_path}")
        sys.exit(1)

    pdf_name = Path(pdf_path).stem
    safe_name = re.sub(r"[^\w\-_]", "_", pdf_name)
    if args.output_dir:
        out_p = Path(args.output_dir)
        if out_p.name.startswith("peer_review_"):
            output_dir = out_p
        else:
            output_dir = out_p / f"peer_review_{safe_name}"
        log(f"📁 Diretório de saída: {output_dir}")
    else:
        output_dir = Path(pdf_path).parent / f"peer_review_{safe_name}"
        log(f"📁 Diretório de saída (padrão): {output_dir}")

    if force and output_dir.exists():
        shutil.rmtree(output_dir)
        log("🔄 Diretório limpo")

    output_dir.mkdir(parents=True, exist_ok=True)

    cp = load_checkpoint(output_dir) if not force else None
    state = cp if cp else {
        "notebook_id": None,
        "persona_configured": False,
        "source_added": False,
        "source_ready": False,
        "initial_slides_done": False,
        "completed_modules": [],
        "artifacts_done": False,
    }

    if cp:
        log("♻️ Checkpoint encontrado — retomando de onde parou")

    lock_fd = acquire_pipeline_lock(output_dir)
    if not lock_fd:
        log("❌ Outro pipeline está em execução neste diretório. Aguarde.")
        sys.exit(1)

    try:
        _run_pipeline(pdf_path, domain, mode, force, output_dir, pdf_name, safe_name, cp, state)
    finally:
        release_pipeline_lock(lock_fd)


# =============================================================================


def _run_pipeline(pdf_path, domain, mode, force, output_dir, pdf_name, safe_name, cp, state):
    log("=" * 60)
    log("INICIANDO PIPELINE v6.0" + (" [RESUME]" if cp else ""))
    log("=" * 60)
    log(f"PDF: {pdf_path}")
    log(f"Domínio: {domain}")
    log(f"Modo: {mode}")
    log(f"Saída: {output_dir}")

    nb_id = state.get("notebook_id")

    # 0. Pre-flight & Otimização de PDF grande (>100MB)
    save_step(output_dir, "preflight", "🔍 Verificação OCR e Otimização")
    pdf_to_process, was_compressed = compress_pdf_if_large(pdf_path, output_dir, threshold_mb=100.0)
    if was_compressed:
        log(f"  📄 Usando PDF otimizado para o pipeline: {pdf_to_process}")

    log("\n🔍 Verificando se PDF precisa de OCR...")
    needs_ocr = check_ocr_needed(pdf_to_process)
    if needs_ocr:
        log("  ⚠️ O PDF parece ser escaneado (imagem). A análise pode ser limitada.")
        log("  💡 Considere executar OCR primeiro: ocrmypdf --force-ocr input.pdf output.pdf")

    # 1. Criar notebook
    if not nb_id:
        save_step(output_dir, "create_notebook", "📝 Criando notebook no NotebookLM")
        log("\n📝 Criando notebook...")
        title = f"Peer-Review v6: {pdf_name}"
        nb_id = create_notebook(title)
        if not nb_id:
            log("❌ Falha ao criar notebook")
            sys.exit(1)
        state["notebook_id"] = nb_id
        save_checkpoint(output_dir, state)
        log(f"✅ Notebook: {nb_id}")
    else:
        log(f"✅ Notebook recuperado do checkpoint: {nb_id}")

    # 1.5 Configurar persona
    if not state.get("persona_configured"):
        save_step(output_dir, "configure_persona", "🎭 Configurando persona do revisor")
        log("\n🎭 Configurando persona do revisor...")
        persona_text = get_notebook_persona(domain)
        config_ok, stderr = configure_notebook(nb_id, persona_text)
        if config_ok:
            state["persona_configured"] = True
            save_checkpoint(output_dir, state)
            log(f"✅ Persona configurada ({len(persona_text)} chars)")
        else:
            log(f"⚠️ Falha ao configurar persona: {stderr} (continuando com fallback nos prompts)")
    else:
        log("✅ Persona já configurada (checkpoint)")

    # 2. Adicionar PDF
    if not state.get("source_added"):
        save_step(output_dir, "add_source", "📄 Adicionando PDF ao notebook")
        log("\n📄 Adicionando PDF...")
        if not add_source(nb_id, pdf_to_process):
            log("❌ Falha ao adicionar PDF")
            sys.exit(1)
        state["source_added"] = True
        save_checkpoint(output_dir, state)
        log("✅ PDF adicionado")
    else:
        log("✅ PDF já adicionado (checkpoint)")

    # 3. Aguardar indexação
    if not state.get("source_ready"):
        save_step(output_dir, "wait_index", "⏳ Aguardando indexação do PDF")
        log("\n⏳ Aguardando indexação...")
        if wait_source(nb_id):
            state["source_ready"] = True
            save_checkpoint(output_dir, state)
            log("✅ PDF indexado")
        else:
            log("⚠️ Timeout na indexação")
    else:
        log("✅ PDF já indexado (checkpoint)")

    # 3.5 Slides iniciais
    if not state.get("initial_slides_done"):
        save_step(output_dir, "initial_slides", "📊 Gerando slides iniciais")
        log("\n📊 Gerando apresentação inicial (apenas PDF)...")
        desc_init = "Apresentação acadêmica resumida com o conteúdo do arquivo original. A apresentação deve conter: Capa, Objetivo, Método, Resultados Principais, Conclusão."
        aid_init, rl_init = generate_artifact(nb_id, "slide-deck", desc_init)
        if aid_init:
            download_artifact(nb_id, "slide-deck", aid_init, str(output_dir / "apresentacao_inicial.pdf"))
            log("✅ Apresentação inicial baixada")
            state["initial_slides_done"] = True
            save_checkpoint(output_dir, state)
        elif rl_init:
            log("⚠️ Rate limit na apresentação inicial (sem fallback disponível) — não marcaremos como concluído para tentar no resume")
    else:
        log("✅ Apresentação inicial já gerada (checkpoint)")

    # 4. Módulos
    completed_before = set(state.get("completed_modules", []))
    completed = set(state.get("completed_modules", []))
    modules = [
        ("00", "00_estrutura_documento.md"),
        ("01", "01_metodologia.md"),
        ("02", "02_auditoria_editorial.md"),
        ("03", "03_sota_referencias.md"),
        ("04", "04_gaps_logicos.md"),
        ("05", "05_analise_escrita.md"),
        ("06", "06_sintese_parecer.md"),
        ("07", "07_auditoria_quantitativa.md"),
    ]
    module_labels = {
        "00": "📋 00: Estrutura do Documento",
        "01": "🔬 01: Auditoria Metodológica",
        "02": "📋 02: Auditoria Editorial",
        "03": "📚 03: SOTA & Referências",
        "04": "🔍 04: Gaps Lógicos",
        "05": "✏️  05: Análise de Escrita",
        "06": "📝 06: Síntese & Parecer",
        "07": "📊 07: Auditoria Quantitativa",
    }

    for step_num, filename in modules:
        if mode == "lite" and step_num in LITE_SKIP_MODULES:
            save_step(output_dir, f"module_{step_num}", f"⏭️ Módulo {step_num} (pulado)", "skipped")
            log(f"\n⏭️ Módulo {step_num} (pulado no modo lite)")
            continue
        if step_num in completed:
            save_step(output_dir, f"module_{step_num}", f"✅ Módulo {step_num} já concluído", "done")
            log(f"✅ Módulo {step_num} já concluído (checkpoint)")
            continue

        save_step(output_dir, f"module_{step_num}", module_labels.get(step_num, f"Módulo {step_num}"))
        log(f"\n📋 Módulo {step_num}: {filename}...")
        output_file = str(output_dir / filename)
        prompt = get_prompt(step_num, domain)
        if run_ask(nb_id, prompt, output_file):
            completed.add(step_num)
            state["completed_modules"] = sorted(completed)
            save_checkpoint(output_dir, state)
            log(f"✅ Módulo {step_num} concluído")
        else:
            log(f"❌ Módulo {step_num} FALHOU")

    # Garante geração do score.json mesmo no resume, caso o módulo 06 esteja concluído
    if "06" in completed:
        _persist_score_json(output_dir)

    # 4.5 Verificar se novos módulos foram completados → forçar re-geração
    if completed - completed_before and state.get("artifacts_done"):
        log("\n🔄 Novos módulos completados — forçando re-geração de artefatos")
        state["artifacts_done"] = False
        save_checkpoint(output_dir, state)

    # 4.8 Auditoria Bibliográfica Real (Crossref / DOIs)
    save_step(output_dir, "bibliography", "📚 Auditoria Bibliográfica Real (Crossref)")
    log("\n📚 Realizando auditoria bibliográfica e checagem de DOIs/retratações via Crossref...")
    try:
        audit_bibliography(pdf_to_process, output_dir)
    except Exception as e:
        log(f"  ⚠️ Auditoria bibliográfica ignorada por erro: {e}")

    # 5. CSV
    save_step(output_dir, "csv", "📊 Gerando CSV de erros")
    log("\n📊 Gerando CSV de erros...")
    md_file = str(output_dir / "05_analise_escrita.md")
    csv_file = str(output_dir / "tabela_erros.csv")
    if os.path.exists(md_file):
        n = convert_to_csv(md_file, csv_file)
        log(f"✅ CSV: {n} erros")

    # 6. Relatório consolidado
    save_step(output_dir, "report", "📄 Gerando relatório consolidado")
    log("\n📄 Gerando relatório consolidado...")
    relatorio_path = output_dir / "relatorio_completo.md"
    total_size = 0
    with open(relatorio_path, "w", encoding="utf-8") as f:
        f.write(f"# RELATÓRIO PEER-REVIEW v6.0\n")
        f.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"**Arquivo:** {pdf_name}\n")
        f.write(f"**Domínio:** {domain}\n")
        f.write(f"**Modo:** {mode}\n\n")
        f.write(f"> ⚠️ **Atenção:** Esta é uma análise gerada por IA e pode estar sujeita a erros.\n\n---\n\n")
        for md in sorted(output_dir.glob("*.md")):
            if md.name != "relatorio_completo.md":
                content = md.read_text(encoding="utf-8")
                total_size += len(content.encode("utf-8"))
                if total_size > 5 * 1024 * 1024:  # 5MB limit
                    log("  ⚠️ Relatório consolidado muito grande (>5MB) — truncando")
                    f.write(content[:50000])
                    f.write("\n\n[... TRUNCADO por tamanho ...]\n\n")
                    break
                f.write(content)
                f.write("\n\n---\n\n")
    size_kb = total_size / 1024
    log(f"✅ Relatório consolidado criado: {size_kb:.0f} KB")
    if relatorio_path.exists() and total_size > 100:
        add_source(nb_id, relatorio_path)

    # 7. Artefatos
    if not state.get("artifacts_done"):
        save_step(output_dir, "artifacts", "🎨 Gerando artefatos (slides, infográfico, HTML)")
        log("\n🎨 Gerando artefatos...")

        log("📊 Gerando apresentação completa...")
        desc1 = (
            "OBJETIVO PRINCIPAL: Apresentação acadêmica formal e estruturada do PARECER TÉCNICO E AUDITORIA PEER-REVIEW "
            "completa realizada pela banca examinadora sobre o artigo. "
            "ATENÇÃO: Esta apresentação NÃO deve resumir o artigo original como se fosse o autor, mas sim DETALHAR "
            "A ANÁLISE CRÍTICA REALIZADA (achados da auditoria metodológica, consistência estatística, checklist editorial, "
            "gaps lógicos, qualidade da escrita, veredito da banca, nota final e recomendações prioritárias).\n\n"
            "A apresentação deve seguir RIGOROSAMENTE a seguinte estrutura de 15 slides:\n\n"

            "SLIDE 1 — CAPA:\n"
            "- Título: Parecer Técnico e Auditoria Peer-Review\n"
            "- Subtítulo: Avaliação Crítica do Paper: [Título do paper analisado]\n"
            "- Autores do paper avaliado\n"
            "- Linha: Banca Avaliadora Peer-Review\n"
            "- Data da análise\n\n"

            "SLIDE 2 — SÍNTESE DA AVALIAÇÃO DA BANCA (RESUMO EXECUTIVO DO PARECER):\n"
            "- Veredito Geral da Banca e Decisão Editorial (Accept / Minor Revisions / Major Revisions / Reject)\n"
            "- Nota Final Atribuída (0-10) e Índice de Coerência Narrativa\n"
            "- Síntese dos Principais Méritos Científicos Identificados na Auditoria\n"
            "- Síntese das Principais Fragilidades Críticas Detectadas pela Banca\n\n"

            "SLIDE 3 — ESTRUTURA DO DOCUMENTO (Módulo 00):\n"
            "- Tipo de documento detectado e conformidade estrutural (IMRAD ou específico)\n"
            "- Seções presentes vs. ausentes identificadas pela auditoria\n"
            "- Avaliação do fluxo narrativo e coesão entre seções\n"
            "- Alinhamento Objetivo–Método–Resultado–Conclusão\n\n"

            "SLIDE 4 — AUDITORIA METODOLÓGICA (Módulo 01):\n"
            "- Classificação do estudo e desenho de pesquisa pela banca\n"
            "- Avaliação de validade interna e externa (ameaças detectadas)\n"
            "- Auditoria do cálculo amostral e representatividade\n"
            "- Controle de vieses identificado pelos revisores\n\n"

            "SLIDE 5 — ANÁLISE ESTATÍSTICA E DADOS (Módulos 01 + 07):\n"
            "- Avaliação dos testes estatísticos e sua adequação\n"
            "- Tamanho de efeito, intervalos de confiança e poder estatístico\n"
            "- Auditoria de consistência numérica entre tabelas, figuras e texto\n"
            "- Discrepâncias numéricas ou valores suspeitos encontrados na auditoria\n\n"

            "SLIDE 6 — CHECKLIST EDITORIAL E ÉTICA (Módulo 02):\n"
            "- Status de aprovação ética (CEP/IRB), consentimento e conformidade\n"
            "- Auditoria de conflito de interesses, financiamento e integridade\n"
            "- Disponibilidade de dados (Data Availability) e CRediT\n"
            "- Declaração sobre uso de IA generativa e formatação de referências\n"
            "- Apresentar como checklist visual da banca (✅ / ❌ / ⚠️)\n\n"

            "SLIDE 7 — REFERENCIAL TEÓRICO E SOTA (Módulo 03):\n"
            "- Avaliação do marco teórico e coerência paradigmática\n"
            "- Qualidade da revisão de literatura (síntese crítica vs. mera listagem)\n"
            "- Avaliação da lacuna de pesquisa (gap) e atualidade das fontes (% últimos 5 anos)\n"
            "- Presença de SOTA e análise de viés de citação pela banca\n\n"

            "SLIDE 8 — GAPS LÓGICOS E ARGUMENTATIVOS (Módulo 04):\n"
            "- Avaliação da cadeia de evidência (Dados → Resultados → Conclusões)\n"
            "- Problemas críticos (🔴) com citação textual do trecho problemático\n"
            "- Problemas moderados (🟡) com citação textual\n"
            "- Falácias identificadas (non sequitur, falsa causa, etc.) e contradições internas\n\n"

            "SLIDE 9 — QUALIDADE DA ESCRITA (Módulo 05):\n"
            "- Resumo estatístico da auditoria textual: total de erros por tipo\n"
            "- Seções com maior concentração de problemas gramaticais e estilísticos\n"
            "- Avaliação do registro acadêmico, clareza e detecção de padrões de LLM\n"
            "- Nota de maturidade textual (1-5) e exemplos de correções sugeridas\n\n"

            "SLIDE 10 — PANORAMA DE ERROS (VISÃO CONSOLIDADA):\n"
            "- Distribuição dos problemas encontrados por gravidade (Crítico / Moderado / Leve)\n"
            "- Distribuição por módulo de auditoria\n"
            "- Top 5 problemas mais impactantes para a validade científica\n"
            "- Cada problema com descrição, módulo de origem e citação do trecho\n\n"

            "SLIDE 11 — PONTOS FORTES IDENTIFICADOS:\n"
            "- Lista de 3 a 5 pontos fortes constatados pela banca\n"
            "- Módulo de origem de cada ponto forte\n"
            "- Contribuições originais e aspectos metodologicamente sólidos reconhecidos\n\n"

            "SLIDE 12 — FRAGILIDADES PRINCIPAIS DETECTADAS:\n"
            "- Lista de 3 a 5 fragilidades principais apontadas pelos revisores\n"
            "- Módulo de origem e trecho problemático de cada fragilidade\n"
            "- Ordenadas pelo impacto na validade científica\n\n"

            "SLIDE 13 — RECOMENDAÇÕES PRIORIZADAS AO AUTOR:\n"
            "- [OBRIGATÓRIO] Correções essenciais e mandatórias para publicação (2-3 itens)\n"
            "- [RECOMENDADO] Melhorias metodológicas e textuais desejáveis (2-3 itens)\n"
            "- [SUGERIDO] Refinamentos e expansões opcionais (1-2 itens)\n"
            "- Recomendações acionáveis, precisas e objetivas\n\n"

            "SLIDE 14 — ORIGINALIDADE E CONTRIBUIÇÃO CIENTÍFICA:\n"
            "- Avaliação da banca sobre o acréscimo real ao estado da arte\n"
            "- Relevância teórica e aplicabilidade prática\n"
            "- Nível de contribuição atribuído: Incremental / Significativa / Transformadora\n"
            "- Potencial de impacto e público-alvo\n\n"

            "SLIDE 15 — VEREDITO E PARECER FINAL DA BANCA:\n"
            "- Decisão Editorial Final: Accept / Minor Revisions / Major Revisions / Reject\n"
            "- Justificativa detalhada do veredito baseada nas evidências da análise\n"
            "- Índice de Coerência Narrativa (0-10)\n"
            "- NOTA FINAL (0-10) fundamentada na rubrica de avaliação:\n"
            "  • 9-10: Excelente — pronto para publicação\n"
            "  • 7-8: Bom — revisões menores necessárias\n"
            "  • 5-6: Regular — revisões maiores necessárias\n"
            "  • 3-4: Fraco — reescrita substancial\n"
            "  • 0-2: Inadequado — falhas fatais\n\n"

            "DIRETRIZES GERAIS DA APRESENTAÇÃO:\n"
            "- Tom: Revisor acadêmico formal, rigoroso e construtivo\n"
            "- Apresente os resultados da ANÁLISE / AUDITORIA e não o conteúdo bruto do paper\n"
            "- Inclua citações textuais (entre aspas) dos trechos problemáticos avaliados\n"
            "- O parecer e a conclusão DEVEM ser estritamente coerentes com as notas e fragilidades apontadas\n"
            "- Use elementos visuais: ícones de severidade (🔴🟡🟢), status (✅❌⚠️)\n"
            "- Cada slide deve ter título claro e conteúdo em bullet points concisos\n"
            "- Evite texto excessivo — priorize clareza e impacto visual"
        )
        aid1, rl1 = generate_artifact(nb_id, "slide-deck", desc1)
        pdf_slide_deck = output_dir / "apresentacao_completa.pdf"
        downloaded = False
        if aid1:
            if download_artifact(nb_id, "slide-deck", aid1, str(pdf_slide_deck)) and pdf_slide_deck.exists() and pdf_slide_deck.stat().st_size > 1000:
                log("✅ Apresentação completa baixada (PDF)")
                downloaded = True
            else:
                log("⚠️ Falha ao baixar apresentação do NotebookLM")


        log("🖼️ Gerando infográfico...")
        desc3 = (
            "Infográfico visual: Mostre nota geral com gauge visual, decisão editorial em destaque, "
            "top 3 fragilidades, distribuição de erros por gravidade (gráfico de pizza ou barras), "
            "timeline de veredito, Status FAIR e Recomendações."
        )
        aid3, rl3 = generate_artifact(
            nb_id, "infographic", desc3,
            ["--style", "scientific", "--detail", "detailed"],
        )
        if aid3:
            download_artifact(nb_id, "infographic", aid3, str(output_dir / "infografico.png"))
            log("✅ Infográfico baixado")
        elif rl3:
            log("⚠️ Rate limit no infográfico (sem fallback disponível)")

        log("🎬 Gerando apresentação animada HTML...")
        html_ok = generate_mira_artifact(output_dir, pdf_name)
        if html_ok:
            log("✅ Apresentação animada HTML gerada")
        else:
            log("❌ Falha ao gerar apresentação animada")

        log("📑 Gerando Parecer Técnico Oficial da Banca em PDF...")
        pdf_ok = generate_official_pdf_report(output_dir, pdf_name, domain)
        if pdf_ok:
            log("✅ Parecer Oficial em PDF gerado")

        # Só marca como concluído se a geração principal (HTML) funcionou, 
        # permitindo retentativa via --resume caso tenha falhado.
        if html_ok:
            state["artifacts_done"] = True
            save_checkpoint(output_dir, state)
    else:
        log("✅ Artefatos já gerados (checkpoint)")

    
    # Final
    log("\n" + "=" * 60)
    log("PIPELINE CONCLUÍDO!")
    log("=" * 60)
    log(f"📁 Diretório: {output_dir}")
    log(f"🔗 Notebook: {nb_id}")
    log(f"🔗 Web: https://notebooklm.google.com/notebook/{nb_id}")

    try:
        subprocess.run(
            ["notify-send", "🔬 Análise Peer-Review Concluída",
             f"{pdf_name}\n📁 {output_dir}"],
            timeout=5, capture_output=True,
        )
    except Exception:
        pass

    log("\n📄 Arquivos gerados:")
    for f in sorted(output_dir.glob("*")):
        if f.name != CHECKPOINT_FILE:
            log(f"  {f.name}: {f.stat().st_size} bytes")

    save_step(output_dir, "done", "✅ Análise Concluída", status="done")
# =============================================================================
# Celery-compatible entry point
# =============================================================================

def run_pipeline(cmd: list[str], env: dict, job_id: str, user_id: int) -> Path | None:
    """
    Executa pipeline a partir de argumentos de linha de comando (para Celery).

    Args:
        cmd: Lista de argumentos estilo sys.argv (ex: ['pipeline.py', 'paper.pdf', '--domain', 'cs', ...])
        env: Dicionário de variáveis de ambiente
        job_id: ID do job para tracking
        user_id: ID do usuário

    Returns:
        Path do diretório de saída ou None se falhou
    """
    import argparse
    import shutil

    # Parse arguments from cmd list
    parser = argparse.ArgumentParser(
        description="Pipeline de análise peer-review via NotebookLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pdf", help="Caminho para o PDF a analisar")
    parser.add_argument("--domain", choices=["cs", "med", "human"], default="cs")
    parser.add_argument("--mode", choices=["full", "lite"], default="full")
    parser.add_argument("--output-dir", dest="output_dir", default=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--force", action="store_true", dest="force")
    group.add_argument("--resume", dest="force", action="store_false")
    parser.set_defaults(force=False)

    # Remove script name if present
    if cmd and cmd[0].endswith(".py"):
        cmd = cmd[1:]

    args = parser.parse_args(cmd)

    pdf_path = args.pdf
    domain = args.domain
    mode = args.mode
    force = args.force

    if not os.path.exists(pdf_path):
        log(f"❌ PDF não encontrado: {pdf_path}")
        return None

    pdf_name = Path(pdf_path).stem
    safe_name = re.sub(r"[^\w\-_]", "_", pdf_name)

    if args.output_dir:
        out_p = Path(args.output_dir)
        if out_p.name.startswith("peer_review_"):
            output_dir = out_p
        else:
            output_dir = out_p / f"peer_review_{safe_name}"
        log(f"📁 Diretório de saída: {output_dir}")
    else:
        output_dir = Path(pdf_path).parent / f"peer_review_{safe_name}"
        log(f"📁 Diretório de saída (padrão): {output_dir}")

    if force and output_dir.exists():
        shutil.rmtree(output_dir)
        log("🔄 Diretório limpo")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Update job status in DB
    from auth import get_db
    from datetime import datetime, timezone
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE pipeline_jobs SET output_dir = ?, updated_at = ? WHERE id = ?",
                (str(output_dir), datetime.now(timezone.utc).isoformat(), job_id),
            )
    except Exception as e:
        log(f"⚠️ Failed to update job output_dir: {e}")

    cp = load_checkpoint(output_dir) if not force else None
    state = cp if cp else {
        "notebook_id": None,
        "persona_configured": False,
        "source_added": False,
        "source_ready": False,
        "initial_slides_done": False,
        "completed_modules": [],
        "artifacts_done": False,
    }

    if cp:
        log("♻️ Checkpoint encontrado — retomando de onde parou")

    lock_fd = acquire_pipeline_lock(output_dir)
    if not lock_fd:
        log("❌ Outro pipeline está em execução neste diretório. Aguarde.")
        return None

    try:
        _run_pipeline(pdf_path, domain, mode, force, output_dir, pdf_name, safe_name, cp, state)
        return output_dir
    finally:
        release_pipeline_lock(lock_fd)


if __name__ == "__main__":
    main()
