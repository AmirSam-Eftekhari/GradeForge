"""
Wraps src.reports.* for the UI's Reports screen. No report-formatting
logic lives here -- this only resolves *where* files go and loops over
the requested students, reusing the exact writers main.py uses.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from src.database.dto import ExamDetail, StudentRecord
from src.models.domain import GradingResult
from src.reports.excel_report import write_class_excel_report
from src.reports.json_report import write_grading_json
from src.reports.pdf_report import write_student_pdf_report


def _safe_folder_name(name: str | None, fallback: str) -> str:
    name = (name or fallback).strip() or fallback
    cleaned = re.sub(r"[^\w\s\-\u0600-\u06FF]", "", name, flags=re.UNICODE).strip()
    return cleaned or fallback


def student_to_grading_result(record: StudentRecord) -> GradingResult:
    """Reconstruct a GradingResult using each question's *effective*
    score (human-adjusted where present) so exports reflect what the
    teacher actually finalized, not just the raw AI output."""
    from dataclasses import replace

    per_question = [
        replace(fr.feedback, score=fr.effective_score) for fr in record.feedback
    ]
    return GradingResult(
        student=record.identity, source_path=record.source_path, per_question=per_question,
    )


def export_student_pdf(record: StudentRecord, exam: ExamDetail, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    folder = output_dir / _safe_folder_name(record.identity.name, f"student_{record.db_id}")
    folder.mkdir(parents=True, exist_ok=True)
    result = student_to_grading_result(record)
    pdf_path = folder / "Grade Report.pdf"
    write_student_pdf_report(result, pdf_path, exam_title=exam.title, language=exam.language)
    return pdf_path


def export_student_json(record: StudentRecord, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    folder = output_dir / _safe_folder_name(record.identity.name, f"student_{record.db_id}")
    folder.mkdir(parents=True, exist_ok=True)
    result = student_to_grading_result(record)
    json_path = folder / "grading.json"
    write_grading_json(result, json_path)
    return json_path


def export_class_excel(exam: ExamDetail, output_dir: Path, students: list[StudentRecord] | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = students if students is not None else exam.students
    results = [student_to_grading_result(r) for r in records]
    safe_title = _safe_folder_name(exam.title, f"exam_{exam.id}")
    xlsx_path = output_dir / f"{safe_title} - Class Report.xlsx"
    write_class_excel_report(results, xlsx_path)
    return xlsx_path


def export_original_paper_copy(record: StudentRecord, output_dir: Path) -> Path | None:
    src_path = Path(record.source_path)
    if not src_path.exists():
        return None
    folder = output_dir / _safe_folder_name(record.identity.name, f"student_{record.db_id}")
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"Original Exam{src_path.suffix}"
    shutil.copy2(src_path, dest)
    return dest
