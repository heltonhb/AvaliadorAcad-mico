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

# Permite execução direta: python3 pipeline/runner.py
# Adiciona o diretório pai ao sys.path para que imports como
# 'from pipeline.constants' funcionem.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from prompts import PROMPTS, LITE_SKIP_MODULES, get_prompt, get_notebook_persona
from artifacts import convert_to_csv, generate_pptx_fallback, generate_mira_artifact
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

    md_path = Path(output_dir) / "06_parecer_final.md"
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
        description="Pipeline de auditoria de contas condominiais via NotebookLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python pipeline.py prestacao_contas.pdf
  python pipeline.py prestacao_contas.pdf --domain com --mode lite
  python pipeline.py prestacao_contas.pdf --resume
""",
    )
    parser.add_argument("pdf", help="Caminho para o PDF da prestação de contas a analisar")
    parser.add_argument("--domain", choices=["res", "com", "mis", "cs"], default="res",
                        help="Tipo de condomínio (default: res - residencial, cs - condomínio simples)")
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
        output_dir = Path(args.output_dir) / f"peer_review_{safe_name}"
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
    log("INICIANDO PIPELINE DE AUDITORIA CONDOMINIAL v7.0" + (" [RESUME]" if cp else ""))
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
        title = f"Auditoria Condominial: {pdf_name}"
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
        save_step(output_dir, "configure_persona", "🎭 Configurando persona do auditor")
        log("\n🎭 Configurando persona do auditor contábil...")
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
        save_step(output_dir, "initial_slides", "📊 Gerando resumo inicial")
        log("\n📊 Gerando apresentação inicial do documento...")
        desc_init = "Apresentação executiva resumida do conteúdo do documento original. A apresentação deve conter: Capa (nome do condomínio e período), Resumo Financeiro (Receitas, Despesas, Saldo), Principais Itens de Despesa, Situação dos Fundos, e Observações Gerais."
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
        ("01", "01_receitas.md"),
        ("02", "02_conformidade_legal.md"),
        ("03", "03_despesas.md"),
        ("04", "04_consistencia_financeira.md"),
        ("05", "05_qualidade_documental.md"),
        ("06", "06_parecer_final.md"),
        ("07", "07_auditoria_quantitativa.md"),
    ]
    module_labels = {
        "00": "📋 00: Estrutura do Documento",
        "01": "💰 01: Auditoria de Receitas",
        "02": "⚖️  02: Conformidade Legal e Assembleia",
        "03": "📉 03: Auditoria de Despesas",
        "04": "🔍 04: Consistência Lógica e Financeira",
        "05": "✏️  05: Qualidade Documental",
        "06": "📝 06: Parecer Final",
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

    # 4.8 Auditoria Bibliográfica (desabilitada para contas condominiais)
    # save_step(output_dir, "bibliography", "📚 Auditoria Bibliográfica")
    # log("\n📚 Auditoria bibliográfica não aplicável para contas condominiais.")

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
            "OBJETIVO PRINCIPAL: Apresentação executiva formal e estruturada do PARECER TÉCNICO DE AUDITORIA "
            "DE CONTAS CONDOMINAIS realizada pela análise automatizada sobre a prestação de contas. "
            "ATENÇÃO: Esta apresentação NÃO deve resumir o documento como se fosse o síndico, mas sim DETALHAR "
            "A ANÁLISE CRÍTICA REALIZADA (achados da auditoria de receitas e despesas, conformidade legal, "
            "consistência financeira, qualidade documental, veredito final e recomendações prioritárias).\n\n"
            "A apresentação deve seguir RIGOROSAMENTE a seguinte estrutura de 15 slides:\n\n"

            "SLIDE 1 — CAPA:\n"
            "- Título: Parecer Técnico de Auditoria de Contas Condominiais\n"
            "- Subtítulo: Análise Crítica da Prestação de Contas: [Nome do Condomínio]\n"
            "- Período Analisado\n"
            "- Data da Análise\n\n"

            "SLIDE 2 — RESUMO EXECUTIVO:\n"
            "- Condomínio analisado, período e tipo (residencial/comercial/misto)\n"
            "- Valores totais movimentados (receitas e despesas)\n"
            "- Saldo acumulado e situação do caixa\n"
            "- Veredito geral: Aprovado / Aprovado com Ressalvas / Reprovado\n\n"

            "SLIDE 3 — ESTRUTURA DO DOCUMENTO (Módulo 00):\n"
            "- Tipo de documento e período de referência\n"
            "- Seções presentes vs. ausentes\n"
            "- Conformidade formal verificada\n\n"

            "SLIDE 4 — RECEITAS (Módulo 01):\n"
            "- Composição das receitas: taxa condominial, fundos, multas, outras\n"
            "- Taxa de inadimplência estimada\n"
            "- Variação vs. período anterior\n\n"

            "SLIDE 5 — CONFORMIDADE LEGAL (Módulo 02):\n"
            "- Status de conformidade com Lei 4.591/64\n"
            "- Ata de assembleia e deliberações\n"
            "- Parecer do conselho fiscal\n"
            "- Conformidade tributária\n\n"

            "SLIDE 6 — DESPESAS FIXAS (Módulo 03):\n"
            "- Folha de pagamento\n"
            "- Custos operacionais fixos (energia, água, seguro, IPTU)\n"
            "- Custo por unidade imobiliária\n\n"

            "SLIDE 7 — DESPESAS VARIÁVEIS E EVENTUAIS (Módulo 03):\n"
            "- Manutenção predial e obras\n"
            "- Despesas jurídicas e administrativas\n"
            "- Obras e reformas realizadas\n\n"

            "SLIDE 8 — CONSISTÊNCIA FINANCEIRA (Módulo 04):\n"
            "- Cruzamento Receitas → Despesas → Saldo\n"
            "- Orçamento vs. Executado\n"
            "- Inconsistências numericas encontradas\n\n"

            "SLIDE 9 — QUALIDADE DOCUMENTAL (Módulo 05):\n"
            "- Clareza e organização dos demonstrativos\n"
            "- Terminologia contábil empregada\n"
            "- Informações ausentes ou insuficientes\n\n"

            "SLIDE 10 — AUDITORIA QUANTITATIVA (Módulo 07):\n"
            "- Totais conferidos vs. calculados\n"
            "- Rateio por unidade verificado\n"
            "- Saldos de fundos validados\n\n"

            "SLIDE 11 — PONTOS POSITIVOS:\n"
            "- Lista de 3 a 5 pontos positivos identificados\n"
            "- Módulo de origem de cada ponto\n\n"

            "SLIDE 12 — IRREGULARIDADES E FRAGILIDADES:\n"
            "- Lista de irregularidades encontradas, ordenadas por gravidade\n"
            "- Citação do trecho problemático\n\n"

            "SLIDE 13 — RECOMENDAÇÕES PRIORIZADAS:\n"
            "- [URGENTE] Ações corretivas essenciais\n"
            "- [RECOMENDADO] Melhorias desejáveis\n"
            "- [SUGERIDO] Refinamentos opcionais\n\n"

            "SLIDE 14 — SITUAÇÃO FINANCEIRA CONSOLIDADA:\n"
            "- Receitas totais, despesas totais, saldo final\n"
            "- Custo por unidade e por m²\n"
            "- Inadimplência e endividamento\n\n"

            "SLIDE 15 — VEREDITO E PARECER FINAL:\n"
            "- Decisão: Aprovado / Aprovado com Ressalvas / Reprovado\n"
            "- Justificativa detalhada\n"
            "- Nota Geral (0-10) com rubrica:\n"
            "  • 9-10: Excelente — contas transparentes e regularizadas\n"
            "  • 7-8: Bom — pendências pontuais\n"
            "  • 5-6: Regular — inconsistências significativas\n"
            "  • 3-4: Fraco — irregularidades graves\n"
            "  • 0-2: Inadequado — fraudes ou ilegalidade\n\n"

            "DIRETRIZES GERAIS:\n"
            "- Tom: Consultor contábil técnico e objetivo\n"
            "- Apresente os resultados da ANÁLISE e não o conteúdo bruto do documento\n"
            "- Inclua valores específicos e citações documentais\n"
            "- Use elementos visuais: ícones de severidade (🔴🟡🟢), status (✅❌⚠️)\n"
            "- Cada slide deve ter título claro e conteúdo em bullet points concisos\n"
            "- Evite texto excessivo — priorize clareza e impacto visual"
        )
        aid1, rl1 = generate_artifact(nb_id, "slide-deck", desc1)
        if aid1:
            download_artifact(nb_id, "slide-deck", aid1, str(output_dir / "apresentacao_completa.pdf"))
            log("✅ Apresentação completa baixada")
        elif rl1:
            log("⚠️ Rate limit na apresentação completa — acionando fallback PPTX...")
            generate_pptx_fallback(output_dir, pdf_name, "completa")

        log("🖼️ Gerando infográfico...")
        desc3 = (
            "Infográfico visual: Mostre nota geral com gauge visual, veredito em destaque, "
            "top 3 irregularidades, distribuição de problemas por gravidade (gráfico de pizza ou barras), "
            "composição de receitas vs. despesas, custo por unidade, e recomendações."
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

        log("📑 Gerando Parecer Técnico Oficial em PDF...")
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
    log("AUDITORIA CONDOMINIAL CONCLUÍDA!")
    log("=" * 60)
    log(f"📁 Diretório: {output_dir}")
    log(f"🔗 Notebook: {nb_id}")
    log(f"🔗 Web: https://notebooklm.google.com/notebook/{nb_id}")

    try:
        subprocess.run(
            ["notify-send", "🏢 Auditoria Condominial Concluída",
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
    log("\n" + "=" * 60)


if __name__ == "__main__":
    main()
