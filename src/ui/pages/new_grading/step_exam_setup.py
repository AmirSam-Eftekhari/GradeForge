from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.ai.language_detect import detect_language
from src.database.dto import ExamDetail
from src.models.domain import AnswerKey, Question
from src.services.grading_service import AnswerKeyImportWorker
from src.ui.widgets.common import Card, badge, h3, muted
from src.ui.widgets.dropzone import DropZone

_LANGUAGES = [
    ("auto", "Auto-detect"), ("eng", "English"), ("fas", "Persian"), ("ara", "Arabic"),
    ("fra", "French"), ("deu", "German"), ("spa", "Spanish"), ("rus", "Russian"),
    ("zho", "Chinese"), ("jpn", "Japanese"), ("kor", "Korean"), ("tur", "Turkish"),
    ("hin", "Hindi"), ("urd", "Urdu"),
]

_NUM_COL, _QUESTION_COL, _ANSWER_COL, _SCORE_COL, _REMOVE_COL = range(5)


class ExamSetupStep(QWidget):
    ready_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.answer_key: AnswerKey | None = None
        self._import_confidence: float = 1.0
        self._worker: AnswerKeyImportWorker | None = None

        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(12)
        form_card = Card()
        form_card.body.addWidget(h3("Exam Details"))
        form = QFormLayout()
        form.setSpacing(8)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Biology Midterm")
        self.title_input.textChanged.connect(self._emit_ready)
        form.addRow("Exam title", self.title_input)

        self.language_combo = QComboBox()
        for code, label in _LANGUAGES:
            self.language_combo.addItem(label, userData=code)
        form.addRow("Language", self.language_combo)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Optional note for your own reference")
        form.addRow("Description", self.description_input)

        self.default_score_input = QDoubleSpinBox()
        self.default_score_input.setRange(0.5, 100.0)
        self.default_score_input.setValue(1.0)
        self.default_score_input.setSingleStep(0.5)
        form.addRow("Default max score\n(if not detected)", self.default_score_input)
        form_card.body.addLayout(form)
        left.addWidget(form_card)

        key_card = Card()
        key_card.body.addWidget(h3("Answer Key"))
        key_card.body.addWidget(muted("TXT, DOCX, PDF, or a scanned image."))
        self.dropzone = DropZone(
            title="Drag & drop the answer key here",
            subtitle_text="TXT · DOCX · PDF · PNG · JPG · TIFF · BMP",
            multiple=False,
        )
        self.dropzone.files_accepted.connect(self._on_file_dropped)
        self.dropzone.files_rejected.connect(self._on_files_rejected)
        key_card.body.addWidget(self.dropzone)

        self.file_status_label = muted("No file imported yet.")
        key_card.body.addWidget(self.file_status_label)
        left.addWidget(key_card)
        left.addStretch()

        left_wrap = QWidget()
        left_wrap.setLayout(left)
        left_wrap.setFixedWidth(340)
        layout.addWidget(left_wrap)

        right = QVBoxLayout()
        header_row = QHBoxLayout()
        header_row.addWidget(h3("Detected Questions"))
        header_row.addStretch()
        self.confidence_badge = badge("—", "neutral")
        header_row.addWidget(self.confidence_badge)
        right.addLayout(header_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Question", "Official Answer", "Max Score", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(_NUM_COL, 50)
        self.table.setColumnWidth(_SCORE_COL, 90)
        self.table.setColumnWidth(_REMOVE_COL, 36)
        self.table.horizontalHeader().setSectionResizeMode(_QUESTION_COL, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(_ANSWER_COL, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.verticalHeader().setMinimumSectionSize(52)
        self.table.itemChanged.connect(self._on_table_edited)
        right.addWidget(self.table, 1)

        add_row_btn = QPushButton("+ Add Question")
        add_row_btn.clicked.connect(self._add_blank_row)
        right.addWidget(add_row_btn)

        right_wrap = QWidget()
        right_wrap.setLayout(right)
        layout.addWidget(right_wrap, 1)

    # ------------------------------------------------------------------
    def load_from_exam(self, exam: ExamDetail) -> None:
        """Pre-fill from a re-grade / template exam, if ever invoked that way."""
        self.title_input.setText(exam.title)
        self.description_input.setText(exam.description)
        idx = self.language_combo.findData(exam.language)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self._populate_table(exam.questions)
        self.answer_key = AnswerKey(exam_title=exam.title, questions=exam.questions, language=exam.language)
        self._emit_ready()

    def _on_file_dropped(self, paths: list[Path]) -> None:
        path = paths[0]
        self.file_status_label.setText(f"Importing {path.name}…")
        self.confidence_badge.setText("Importing…")
        self.confidence_badge.setProperty("cls", "badge-neutral")
        lang = self.language_combo.currentData()
        languages = ["eng", "fas"] if lang == "auto" else [lang]
        title = self.title_input.text().strip() or path.stem.replace("_", " ").title()

        self._worker = AnswerKeyImportWorker(path, languages, title)
        self._worker.succeeded.connect(self._on_import_succeeded)
        self._worker.failed.connect(self._on_import_failed)
        self._worker.start()

    def _on_files_rejected(self, reasons: list[str]) -> None:
        QMessageBox.warning(self, "File not supported", "\n".join(reasons))

    def _on_import_succeeded(self, answer_key: AnswerKey, doc) -> None:
        self.answer_key = answer_key
        self._import_confidence = doc.confidence
        if not self.title_input.text().strip():
            self.title_input.setText(answer_key.exam_title)

        detected_lang = answer_key.language
        idx = self.language_combo.findData(detected_lang)
        if self.language_combo.currentData() == "auto" and idx >= 0:
            self.language_combo.setCurrentIndex(idx)

        self._populate_table(answer_key.questions)

        conf_pct = doc.confidence * 100
        variant = "success" if conf_pct >= 80 else ("warning" if conf_pct >= 55 else "danger")
        method = "OCR" if doc.used_ocr else "direct text extraction"
        self.confidence_badge.setText(f"{conf_pct:.0f}% confidence")
        self.confidence_badge.setProperty("cls", f"badge-{variant}")
        self.confidence_badge.style().unpolish(self.confidence_badge)
        self.confidence_badge.style().polish(self.confidence_badge)

        n = len(answer_key.questions)
        self.file_status_label.setText(
            f"Imported via {method}. Detected {n} question(s) — review them below before continuing."
            if n else "No questions were detected automatically. Add them manually below, or check the file format."
        )
        self._emit_ready()

    def _on_import_failed(self, message: str) -> None:
        self.file_status_label.setText(message)
        self.confidence_badge.setText("Failed")
        self.confidence_badge.setProperty("cls", "badge-danger")
        QMessageBox.critical(self, "Couldn't import answer key", message)

    def _populate_table(self, questions: list[Question]) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for q in questions:
            self._append_row(q.number, q.text, q.official_answer, q.max_score)
        self.table.blockSignals(False)
        self.table.resizeRowsToContents()

    def _append_row(self, number: str, text: str, answer: str, max_score: float) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, _NUM_COL, QTableWidgetItem(str(number)))
        self.table.setItem(row, _QUESTION_COL, QTableWidgetItem(text))
        self.table.setItem(row, _ANSWER_COL, QTableWidgetItem(answer))

        spin = QDoubleSpinBox()
        spin.setRange(0.5, 100.0)
        spin.setSingleStep(0.5)
        spin.setValue(max_score)
        spin.valueChanged.connect(self._emit_ready)
        self.table.setCellWidget(row, _SCORE_COL, spin)

        remove_btn = QPushButton("✕")
        remove_btn.setProperty("cls", "ghost")
        remove_btn.setFixedWidth(28)
        remove_btn.clicked.connect(lambda: self._remove_row(remove_btn))
        self.table.setCellWidget(row, _REMOVE_COL, remove_btn)
        self.table.resizeRowToContents(row)

    def _remove_row(self, button: QPushButton) -> None:
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, _REMOVE_COL) is button:
                self.table.removeRow(row)
                self._emit_ready()
                return

    def _add_blank_row(self) -> None:
        next_num = str(self.table.rowCount() + 1)
        self._append_row(next_num, "", "", self.default_score_input.value())
        self._emit_ready()

    def _on_table_edited(self, item) -> None:
        if item is not None:
            self.table.resizeRowToContents(item.row())
        self._emit_ready()

    def _emit_ready(self) -> None:
        self.ready_changed.emit(self.is_valid())

    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        return bool(self.title_input.text().strip()) and self.table.rowCount() > 0

    def build_answer_key(self) -> AnswerKey:
        questions: list[Question] = []
        for row in range(self.table.rowCount()):
            number = (self.table.item(row, _NUM_COL).text() or "").strip() or str(row + 1)
            text = (self.table.item(row, _QUESTION_COL).text() or "").strip()
            answer = (self.table.item(row, _ANSWER_COL).text() or "").strip()
            spin: QDoubleSpinBox = self.table.cellWidget(row, _SCORE_COL)
            questions.append(Question(number=number, text=text or f"Question {number}", official_answer=answer, max_score=spin.value()))

        title = self.title_input.text().strip()
        lang_code = self.language_combo.currentData()
        if lang_code == "auto":
            sample_text = " ".join(q.official_answer for q in questions)
            lang_code = detect_language(sample_text)

        return AnswerKey(
            exam_title=title, questions=questions, language=lang_code,
            description=self.description_input.text().strip(),
        )

    def selected_language_code(self) -> str:
        code = self.language_combo.currentData()
        return code if code != "auto" else (self.answer_key.language if self.answer_key else "eng")
