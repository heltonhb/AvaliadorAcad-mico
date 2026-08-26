"""
Gerador de Parecer Técnico Oficial em PDF para Banca Examinadora.
Utiliza ReportLab para compor um documento acadêmico formal e visualmente polido.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from utils import extract_structured_score, extract_nota_from_synthesis

_logger = logging.getLogger("pipeline")


def log(msg: str):
    _logger.info(msg)


class NumberedCanvas(canvas.Canvas):
    """Canvas customizado para rodapé com paginação 'Página X de Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6B7280"))
        
        # Linha divisória suave
        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.5)
        self.line(40, 35, A4[0] - 40, 35)

        # Texto do rodapé
        self.drawString(40, 22, "AnaliseTextos v6.0 — Sistema Automatizado de Peer-Review Acadêmico")
        self.drawRightString(A4[0] - 40, 22, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()


def generate_official_pdf_report(output_dir: Path, pdf_name: str, domain: str = "cs") -> bool:
    """Gera o arquivo parecer_banca_oficial.pdf no diretório de saída."""
    if not REPORTLAB_AVAILABLE:
        log("  ✗ reportlab não instalado — parecer oficial em PDF não gerado")
        return False

    pdf_target = output_dir / "parecer_banca_oficial.pdf"

    # Ler dados dos módulos
    md06_file = output_dir / "06_sintese_parecer.md"
    parecer_text = md06_file.read_text(encoding="utf-8", errors="ignore") if md06_file.exists() else ""
    structured = extract_structured_score(parecer_text)

    # Nota e decisão
    nota = structured.get("nota")
    if nota is None:
        nota = extract_nota_from_synthesis(parecer_text)
    nota_str = f"{nota:.1f}" if isinstance(nota, (int, float)) else "N/A"

    decisao = structured.get("decisao") or "Aguardando Avaliação"
    coerencia = structured.get("coerencia_narrativa")
    coerencia_str = f"{coerencia:.1f}/10" if isinstance(coerencia, (int, float)) else "N/A"

    # Cor da decisão
    dec_upper = decisao.upper()
    if "ACCEPT" in dec_upper or "ACEITO" in dec_upper:
        verdict_color = colors.HexColor("#15803D")  # Green
        verdict_bg = colors.HexColor("#DCFCE7")
    elif "MINOR" in dec_upper:
        verdict_color = colors.HexColor("#0284C7")  # Sky blue
        verdict_bg = colors.HexColor("#E0F2FE")
    elif "MAJOR" in dec_upper:
        verdict_color = colors.HexColor("#D97706")  # Amber
        verdict_bg = colors.HexColor("#FEF3C7")
    else:
        verdict_color = colors.HexColor("#DC2626")  # Red
        verdict_bg = colors.HexColor("#FEE2E2")

    # Auditoria bibliográfica
    bib_json = output_dir / "auditoria_bibliografica.json"
    bib_data = {}
    if bib_json.exists():
        try:
            bib_data = json.loads(bib_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Configuração do documento
    doc = SimpleDocTemplate(
        str(pdf_target),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,  # Center
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
        alignment=1,
    )

    section_heading = ParagraphStyle(
        "SecHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1F2937"),
    )

    bold_body = ParagraphStyle(
        "DocBoldBody",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    story = []

    # Cabeçalho Oficial
    story.append(Paragraph("PARECER TÉCNICO DE AVALIAÇÃO ACADÊMICA", title_style))
    story.append(Paragraph("COMISSÃO EXAMINADORA · AVALIAÇÃO CRÍTICA PEER-REVIEW", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=12))

    # Tabela de Metadados do Documento
    domain_map = {
        "cs": "Ciência da Computação / Informática (IEEE/ACM)",
        "med": "Medicina / Ciências da Saúde (CONSORT/PRISMA)",
        "human": "Humanidades e Ciências Sociais (APA)",
    }
    domain_label = domain_map.get(domain, domain.upper())
    now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")

    meta_table_data = [
        [
            Paragraph("<b>Documento Avaliado:</b>", body_style),
            Paragraph(pdf_name, bold_body),
            Paragraph("<b>Data da Análise:</b>", body_style),
            Paragraph(now_str, body_style),
        ],
        [
            Paragraph("<b>Domínio Acadêmico:</b>", body_style),
            Paragraph(domain_label, body_style),
            Paragraph("<b>Sistema / Versão:</b>", body_style),
            Paragraph("AnaliseTextos v6.0", body_style),
        ],
    ]

    meta_table = Table(meta_table_data, colWidths=[110, 190, 95, 120])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F3F4F6")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Box do Veredito / Nota
    verdict_box_data = [
        [
            Paragraph("<font size=9 color='#6B7280'>NOTA GLOBAL</font><br/><font size=22 color='#1E3A8A'><b>" + nota_str + "</b></font><font size=11 color='#6B7280'> / 10</font>", body_style),
            Paragraph("<font size=9 color='#6B7280'>DECISÃO RECOMENDADA</font><br/><font size=14 color='" + verdict_color.hexval() + "'><b>" + decisao + "</b></font>", body_style),
            Paragraph("<font size=9 color='#6B7280'>COERÊNCIA NARRATIVA</font><br/><font size=14 color='#1E3A8A'><b>" + coerencia_str + "</b></font>", body_style),
        ]
    ]
    verdict_table = Table(verdict_box_data, colWidths=[140, 235, 140])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 10))

    # Resumo da Auditoria Modular
    story.append(Paragraph("1. Síntese dos Módulos Avaliados", section_heading))
    
    modules_summary = [
        ["#", "Módulo Analítico", "Foco da Avaliação", "Status"],
        ["00", "Estrutura do Documento", "Conformidade IMRAD, proporções e narrativa", "Auditado"],
        ["01", "Metodologia & Desenho", "Validade interna/externa, amostragem e vieses", "Auditado"],
        ["02", "Conformidade Editorial & Ética", "Comitê de ética, conflitos de interesse, FAIR", "Auditado"],
        ["03", "SOTA & Referencial Teórico", "Atualidade das fontes, marcos conceituais e gaps", "Auditado"],
        ["04", "Consistência Lógica", "Cadeia de evidência e detecção de falácias", "Auditado"],
        ["05", "Qualidade da Escrita", "Gramática, registro acadêmico e detecção de IA", "Auditado"],
        ["07", "Auditoria Quantitativa", "Consistência de tabelas, figuras e estatística", "Auditado"],
    ]
    if bib_data:
        rec_pct = bib_data.get('recent_articles_pct', 0)
        modules_summary.append(["08", "Auditoria Bibliográfica", f"{bib_data.get('valid_dois_count', 0)} DOIs verificados ({rec_pct}% recentes)", "Validado"])

    mod_table = Table(modules_summary, colWidths=[25, 175, 245, 70])
    mod_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
    ]))
    story.append(mod_table)
    story.append(Spacer(1, 10))

    # Pontos Fortes e Fragilidades
    fortes = structured.get("pontos_fortes", [])
    fragilidades = structured.get("fragilidades", [])
    rec_obrigatorias = structured.get("recomendacoes_obrigatorias", [])

    if fortes or fragilidades:
        story.append(Paragraph("2. Principais Achados da Avaliação", section_heading))
        
        fortes_text = "<br/>".join([f"• {f}" for f in fortes]) if fortes else "• Nenhum ponto forte listado."
        frag_text = "<br/>".join([f"• {f}" for f in fragilidades]) if fragilidades else "• Nenhuma fragilidade crítica listada."

        findings_data = [
            [
                Paragraph("<b>Pontos Fortes Identificados:</b><br/><br/>" + fortes_text, body_style),
                Paragraph("<b>Fragilidades e Limitações:</b><br/><br/>" + frag_text, body_style),
            ]
        ]
        findings_table = Table(findings_data, colWidths=[252, 253])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#F0FDF4")),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#FEF2F2")),
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor("#86EFAC")),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor("#FCA5A5")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(findings_table)
        story.append(Spacer(1, 10))

    # Recomendações Priorizadas
    if rec_obrigatorias:
        story.append(Paragraph("3. Recomendações Essenciais para Adequação", section_heading))
        for idx, rec in enumerate(rec_obrigatorias, 1):
            story.append(Paragraph(f"<b>{idx}. [OBRIGATÓRIO]</b> {rec}", body_style))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 8))

    # Campo de Assinatura da Banca
    story.append(KeepTogether([
        Paragraph("4. Declaração da Comissão Examinadora", section_heading),
        Paragraph(
            "Os membros da banca examinadora abaixo assinados atestam a realização do processo de avaliação "
            "e revisão crítica, manifestando sua concordância com o parecer técnico aqui emitido.",
            body_style,
        ),
        Spacer(1, 30),
        Table([
            [
                Paragraph("__________________________________________<br/><b>Presidente da Banca</b><br/><font size=7 color='#6B7280'>Avaliador 1</font>", ParagraphStyle('Sig1', parent=body_style, alignment=1)),
                Paragraph("__________________________________________<br/><b>Membro Avaliador</b><br/><font size=7 color='#6B7280'>Avaliador 2</font>", ParagraphStyle('Sig2', parent=body_style, alignment=1)),
            ]
        ], colWidths=[250, 250]),
    ]))

    try:
        doc.build(story, canvasmaker=NumberedCanvas)
        log(f"  ✅ Parecer Oficial em PDF gerado: {pdf_target.name}")
        return True
    except Exception as e:
        log(f"  ❌ Erro ao gerar parecer em PDF: {e}")
        return False
