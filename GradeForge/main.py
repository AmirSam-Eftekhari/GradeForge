#!/usr/bin/env python3
"""
Exam Grader — CLI entrypoint.

This is the same pipeline the PySide6 desktop UI will call into (see
src/ui/README.md for why the GUI itself is a phase-2 deliverable). Every
line of business logic here lives in src/ — main.py only wires it
together, so the UI's "Run Grading" button will call these same
functions, not duplicate them.

Usage:
    python main.py --answer-key sample_data/answer_key.txt \\
                    --students-dir sample_data/students \\
                    --strictness balanced
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
from pathlib import Path

from src.ai.embedding_backend import get_backend
from src.analytics.class_analytics import compute_class_analytics
from src.config.strictness import get_policy
from src.database.repository import ExamRepository
from src.grading.engine import GradingEngine
from src.ocr.tesseract_engine import TesseractOCREngine
from src.parser.answer_key_parser import parse_answer_key
from src.parser.document_reader import read_document
from src.parser.student_paper_parser import parse_student_paper
from src.reports.excel_report import write_class_excel_report
from src.reports.json_report import write_grading_json
from src.reports.pdf_report import write_student_pdf_report
from src.utils.logging_config import configure_logging

logger = logging.getLogger("exam_grader")

_SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".docx", ".txt"}


def _safe_folder_name(name: str | None, fallback: str) -> str:
    name = (name or fallback).strip() or fallback
    cleaned = re.sub(r"[^\w\s\-\u0600-\u06FF]", "", name, flags=re.UNICODE).strip()
    return cleaned or fallback


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI-powered exam grading pipeline")
    parser.add_argument("--answer-key", required=True, type=Path)
    parser.add_argument("--students-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("Results"), type=Path)
    parser.add_argument("--db", default=Path("exam_grader.db"), type=Path)
    parser.add_argument(
        "--strictness", default="balanced",
        choices=["very_lenient", "lenient", "balanced", "strict", "very_strict"],
    )
    parser.add_argument("--languages", nargs="*", default=["eng", "fas"])
    parser.add_argument("--embedding-backend", default="auto", choices=["auto", "sentence_transformer", "tfidf"])
    parser.add_argument("--no-contradiction-detection", action="store_true")
    parser.add_argument("--exam-title", default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def run(args: argparse.Namespace) -> None:
    configure_logging(args.verbose)
    ocr_engine = TesseractOCREngine()

    logger.info("Reading official answer key: %s", args.answer_key)
    answer_key_doc = read_document(args.answer_key, ocr_engine, args.languages)
    if answer_key_doc.confidence < 0.55:
        logger.warning(
            "Low-confidence OCR (%.0f%%) on the answer key — verify question "
            "detection below before trusting grades.", answer_key_doc.confidence * 100,
        )
    exam_title = args.exam_title or args.answer_key.stem.replace("_", " ").title()
    answer_key = parse_answer_key(answer_key_doc.text, exam_title=exam_title)
    logger.info(
        "Detected %d question(s) in answer key (language=%s): %s",
        len(answer_key.questions), answer_key.language,
        ", ".join(f"Q{q.number}={q.max_score:g}pts" for q in answer_key.questions),
    )
    if not answer_key.questions:
        raise SystemExit(
            "No questions were detected in the answer key. Expected a format like "
            "'Question 1 (3 points)' followed by 'Answer: ...'. See README for examples."
        )

    student_files = sorted(
        p for p in args.students_dir.iterdir() if p.suffix.lower() in _SUPPORTED_SUFFIXES
    )
    if not student_files:
        raise SystemExit(f"No supported student files found in {args.students_dir}")

    backend = get_backend(preference=args.embedding_backend)
    logger.info("Embedding backend in use: %s", backend.name)
    policy = get_policy(args.strictness)
    engine = GradingEngine(
        backend=backend, policy=policy,
        enable_contradiction_detection=not args.no_contradiction_detection,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    used_folder_names: set[str] = set()

    for student_file in student_files:
        logger.info("Grading %s", student_file.name)
        doc = read_document(student_file, ocr_engine, args.languages)
        paper = parse_student_paper(doc.text, source_path=str(student_file), ocr_confidence=doc.confidence)

        if paper.identity.name is None:
            logger.warning("Could not detect a student name in %s — flagged for manual review.", student_file.name)

        result = engine.grade_paper(answer_key, paper)
        results.append(result)

        folder_name = _safe_folder_name(result.student.name, student_file.stem)
        unique_name = folder_name
        suffix = 1
        while unique_name in used_folder_names:
            suffix += 1
            unique_name = f"{folder_name} ({suffix})"
        used_folder_names.add(unique_name)

        student_dir = args.output_dir / unique_name
        student_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(student_file, student_dir / f"Original Exam{student_file.suffix}")
        write_grading_json(result, student_dir / "grading.json")
        write_student_pdf_report(
            result, student_dir / "Grade Report.pdf",
            exam_title=answer_key.exam_title, language=answer_key.language,
        )
        logger.info(
            "  -> %s: %.1f / %.1f (%.1f%%)%s",
            result.student.name or "UNKNOWN", result.total_score, result.max_total_score,
            result.percentage, "  [NEEDS REVIEW]" if result.student.identity_confidence < 0.6 else "",
        )

    write_class_excel_report(results, args.output_dir / "class_report.xlsx")

    repo = ExamRepository(args.db)
    repo.save_exam(answer_key, args.strictness, results)
    repo.close()

    analytics = compute_class_analytics(results)
    logger.info(
        "Class summary — n=%d avg=%.1f%% median=%.1f%% high=%.1f%% low=%.1f%% pass_rate=%.1f%%",
        analytics.count, analytics.average_pct, analytics.median_pct,
        analytics.highest_pct, analytics.lowest_pct, analytics.pass_rate_pct,
    )
    if analytics.question_difficulty:
        hardest = analytics.question_difficulty[0]
        logger.info("Most-missed question: Q%s (avg %.1f%%)", hardest.question_number, hardest.average_score_pct)

    logger.info("Done. Results written to %s", args.output_dir.resolve())


if __name__ == "__main__":
    run(build_arg_parser().parse_args())
