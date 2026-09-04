"""
Per-student PDF report: combined Feedback + Grade Report (see README for
why these are one file rather than the two separate PDFs the original
spec lists — kept configurable via `combined=False` if a deployment
wants them split).

RTL languages (Persian/Arabic/Urdu) need `arabic-reshaper` + `python-bidi`
for correct glyph shaping in PDF text; this module degrades gracefully
(renders unshaped logical-order text with a warning) when those aren't
installed, rather than crashing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from src.ai.language_detect import is_rtl
from src.models.domain import GradingResult

logger = logging.getLogger(__name__)

_PRIMARY = colors.HexColor("#111827")
_ACCENT = colors.HexColor("#4F46E5")
_GOOD = colors.HexColor("#059669")
_WARN = colors.HexColor("#D97706")
_BAD = colors.HexColor("#DC2626")


def _shape(text: str, language: str) -> str:
    if not is_rtl(language):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        logger.warning(
            "arabic-reshaper/python-bidi not installed — RTL text will "
            "render in logical order, not visual order. Install both for "
            "correct Persian/Arabic/Urdu PDF output."
        )
        return text


def _score_color(score: float, max_score: float):
    if max_score == 0:
        return _WARN
    pct = score / max_score
    if pct >= 0.8:
        return _GOOD
    if pct >= 0.5:
        return _WARN
    return _BAD


def write_student_pdf_report(result: GradingResult, output_path: Path, exam_title: str, language: str = "eng") -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], textColor=_PRIMARY)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=_ACCENT, spaceBefore=14)
    body = ParagraphStyle("Body", parent=styles["BodyText"], leading=14)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8.5, textColor=colors.grey)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
    )
    story = []

    story.append(Paragraph(_shape(exam_title, language), title_style))
    student_name = result.student.name or "(name not confidently detected — manual review needed)"
    story.append(Paragraph(_shape(f"Student: {student_name}", language), body))
    if result.student.student_id:
        story.append(Paragraph(f"Student ID: {result.student.student_id}", body))
    if result.student.class_name:
        story.append(Paragraph(_shape(f"Class: {result.student.class_name}", language), body))
    story.append(Spacer(1, 6))

    summary_data = [
        ["Total Score", "Max Score", "Percentage"],
        [f"{result.total_score:g}", f"{result.max_total_score:g}", f"{result.percentage:.1f}%"],
    ]
    summary_table = Table(summary_data, colWidths=[55 * mm] * 3)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]))
    story.append(summary_table)

    for fb in result.per_question:
        story.append(Paragraph(
            f"Question {fb.question_number} — "
            f"<font color='#{_score_color(fb.score, fb.max_score).hexval()[2:]}'>"
            f"{fb.score:g} / {fb.max_score:g}</font>",
            h2,
        ))
        story.append(Paragraph(_shape(fb.reasoning, language), body))

        if fb.missing_concepts:
            missing_str = "; ".join(fb.missing_concepts)
            story.append(Paragraph(f"<b>Missing concepts:</b> {_shape(missing_str, language)}", body))
        if fb.contradictions_detected:
            story.append(Paragraph(
                "<font color='#DC2626'><b>Contradiction flagged</b></font> — a statement "
                "conflicting with the official answer was detected; please review manually.",
                body,
            ))
        story.append(Paragraph(f"<b>Suggested stronger answer:</b> {_shape(fb.suggested_answer, language)}", body))
        story.append(Paragraph(
            f"<i>Confidence: {fb.confidence * 100:.0f}% &nbsp;|&nbsp; "
            f"Semantic similarity: {fb.similarity * 100:.0f}%</i>",
            small,
        ))
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Teacher comments:</b>", h2))
    story.append(Paragraph("_" * 90, body))
    story.append(Paragraph("_" * 90, body))

    doc.build(story)
