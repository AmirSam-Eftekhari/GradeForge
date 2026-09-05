"""
QThread workers around the existing pipeline.

Nothing in this file re-implements grading, parsing, or OCR -- every
worker's run() body is a thin loop that calls straight into
src.parser / src.ai / src.grading, exactly like main.py does. The only
job here is: do that work off the GUI thread, and emit Qt signals so
widgets can show progress instead of freezing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.ai.embedding_backend import EmbeddingBackend, get_backend
from src.config.strictness import StrictnessPolicy
from src.grading.engine import GradingEngine
from src.models.domain import AnswerKey, GradingResult, StudentPaper
from src.ocr.tesseract_engine import TesseractOCREngine
from src.parser.answer_key_parser import parse_answer_key
from src.parser.document_reader import ExtractedDocument, read_document
from src.parser.student_paper_parser import parse_student_paper

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".docx", ".txt"}


def human_error(exc: Exception, file_path: Path | None = None) -> str:
    """Turn a raw exception into something a teacher can act on. Never
    surfaces a bare traceback in the UI (spec: error handling)."""
    name = file_path.name if file_path else None
    if isinstance(exc, ValueError) and "Unsupported file type" in str(exc):
        suffix = file_path.suffix if file_path else "?"
        return (
            f"'{name}' isn't a supported file type ({suffix}). "
            "Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG, TIFF, BMP."
        )
    if isinstance(exc, FileNotFoundError):
        return f"'{name or exc}' could not be found. It may have been moved or deleted."
    if "tesseract" in str(exc).lower():
        return (
            "OCR failed because Tesseract isn't installed or isn't on PATH. "
            "Install it (see Settings > OCR) and try again."
        )
    if "poppler" in str(exc).lower() or "pdf2image" in str(exc).lower():
        return "This scanned PDF couldn't be rasterized -- poppler-utils may be missing. See Settings > OCR."
    return f"Something went wrong while processing '{name or ''}': {exc}"


@dataclass
class ImportedFile:
    path: Path
    status: str = "ready"  # ready | processing | completed | needs_review | error
    paper: StudentPaper | None = None
    doc: ExtractedDocument | None = None
    error: str | None = None

    @property
    def detected_name(self) -> str:
        if self.paper and self.paper.identity.name:
            return self.paper.identity.name
        return "(pending)"


class AnswerKeyImportWorker(QThread):
    """Reads + parses the answer key file off the GUI thread."""

    succeeded = Signal(object, object)  # AnswerKey, ExtractedDocument
    failed = Signal(str)

    def __init__(self, path: Path, languages: list[str], exam_title: str, parent=None):
        super().__init__(parent)
        self._path = path
        self._languages = languages
        self._exam_title = exam_title

    def run(self) -> None:
        try:
            ocr = TesseractOCREngine()
            doc = read_document(self._path, ocr, self._languages)
            answer_key = parse_answer_key(doc.text, exam_title=self._exam_title)
            self.succeeded.emit(answer_key, doc)
        except Exception as exc:  # noqa: BLE001 -- surfaced via signal, not raised
            logger.exception("Answer key import failed")
            self.failed.emit(human_error(exc, self._path))


class StudentImportWorker(QThread):
    """Reads + parses a batch of student papers off the GUI thread, one
    at a time, so the import queue can update file-by-file."""

    file_started = Signal(int)
    file_done = Signal(int, object)   # index, ImportedFile
    all_done = Signal()

    def __init__(self, files: list[ImportedFile], languages: list[str], parent=None):
        super().__init__(parent)
        self._files = files
        self._languages = languages
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        ocr = TesseractOCREngine()
        for i, item in enumerate(self._files):
            if self._cancelled:
                break
            self.file_started.emit(i)
            try:
                doc = read_document(item.path, ocr, self._languages)
                paper = parse_student_paper(doc.text, source_path=str(item.path), ocr_confidence=doc.confidence)
                item.doc = doc
                item.paper = paper
                low_conf = paper.identity.identity_confidence < 0.6 or doc.confidence < 0.55
                item.status = "needs_review" if low_conf else "completed"
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to import %s", item.path)
                item.status = "error"
                item.error = human_error(exc, item.path)
            self.file_done.emit(i, item)
        self.all_done.emit()


@dataclass
class GradingProgress:
    current_index: int
    total: int
    student_name: str
    questions_in_paper: int


class GradingWorker(QThread):
    """Runs GradingEngine.grade_paper over an already-imported batch.
    Deliberately takes pre-parsed StudentPaper objects (built by
    StudentImportWorker) rather than re-reading files, so OCR never runs
    twice for the same paper."""

    backend_ready = Signal(str, str)     # backend name, warning (may be empty)
    progress = Signal(object)            # GradingProgress
    student_graded = Signal(str, object)  # source_path, GradingResult
    finished_all = Signal(list)          # list[GradingResult]
    failed = Signal(str)

    def __init__(
        self, answer_key: AnswerKey, files: list[ImportedFile],
        policy: StrictnessPolicy, embedding_preference: str, model_name: str,
        enable_contradiction_detection: bool, parent=None,
    ):
        super().__init__(parent)
        self._answer_key = answer_key
        self._files = [f for f in files if f.paper is not None and f.status != "error"]
        self._policy = policy
        self._embedding_preference = embedding_preference
        self._model_name = model_name
        self._enable_contradiction_detection = enable_contradiction_detection
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            backend: EmbeddingBackend = get_backend(
                preference=self._embedding_preference, model_name=self._model_name,
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(human_error(exc))
            return

        warning = ""
        if backend.name == "tfidf_fallback":
            warning = (
                "Using the offline TF-IDF fallback -- semantic accuracy is reduced. "
                "Install sentence-transformers + torch for production-grade grading."
            )
        self.backend_ready.emit(backend.name, warning)

        engine = GradingEngine(
            backend=backend, policy=self._policy,
            enable_contradiction_detection=self._enable_contradiction_detection,
        )

        results: list[GradingResult] = []
        total = len(self._files)
        for i, item in enumerate(self._files):
            if self._cancelled:
                break
            name = item.detected_name if item.detected_name != "(pending)" else item.path.name
            self.progress.emit(GradingProgress(
                current_index=i, total=total, student_name=name,
                questions_in_paper=len(item.paper.answers) if item.paper else 0,
            ))
            try:
                result = engine.grade_paper(self._answer_key, item.paper)
            except Exception:
                logger.exception("Grading failed for %s", item.path)
                continue
            results.append(result)
            self.student_graded.emit(str(item.path), result)

        self.finished_all.emit(results)
