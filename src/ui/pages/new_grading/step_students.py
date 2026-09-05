from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.services.grading_service import ImportedFile, StudentImportWorker
from src.ui.widgets.common import Card, badge, h3, muted
from src.ui.widgets.dropzone import DropZone

_COLUMNS = ["Filename", "Detected Name", "Student ID", "Extraction", "Confidence", "Status", ""]
_STATUS_VARIANT = {
    "ready": "neutral", "processing": "neutral", "completed": "success",
    "needs_review": "warning", "error": "danger",
}
_STATUS_LABEL = {
    "ready": "Ready", "processing": "Processing…", "completed": "Completed",
    "needs_review": "Needs Review", "error": "Error",
}


class StudentPapersStep(QWidget):
    ready_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files: list[ImportedFile] = []
        self._worker: StudentImportWorker | None = None
        self._languages: list[str] = ["eng", "fas"]
        self._current_batch: list[ImportedFile] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        card = Card()
        card.body.addWidget(h3("Student Papers"))
        card.body.addWidget(muted("Drop individual files or an entire folder. Mixed formats are fine."))
        self.dropzone = DropZone(
            title="Drag & drop student papers (or a folder) here",
            subtitle_text="TXT · DOCX · PDF · PNG · JPG · TIFF · BMP",
            allow_folders=True, multiple=True,
        )
        self.dropzone.files_accepted.connect(self._on_files_dropped)
        self.dropzone.files_rejected.connect(self._on_files_rejected)
        card.body.addWidget(self.dropzone)
        layout.addWidget(card)

        table_card = Card()
        header_row = QHBoxLayout()
        header_row.addWidget(h3("Import Queue"))
        header_row.addStretch()
        self.summary_badge = badge("0 files", "neutral")
        header_row.addWidget(self.summary_badge)
        table_card.body.addLayout(header_row)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(_COLUMNS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(len(_COLUMNS) - 1, 36)
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.setMinimumHeight(280)
        table_card.body.addWidget(self.table)
        layout.addWidget(table_card, 1)

    def set_languages(self, languages: list[str]) -> None:
        self._languages = languages

    def _on_files_rejected(self, reasons: list[str]) -> None:
        QMessageBox.warning(self, "Some files were skipped", "\n".join(reasons))

    def _on_files_dropped(self, paths: list[Path]) -> None:
        existing = {f.path for f in self.files}
        new_items = [ImportedFile(path=p) for p in paths if p not in existing]
        if not new_items:
            return
        self.files.extend(new_items)
        for item in new_items:
            self._add_row(item)
        self._update_summary()

        self._current_batch = new_items
        self._worker = StudentImportWorker(new_items, self._languages)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.all_done.connect(self._update_summary)
        self._worker.start()

    def _add_row(self, item: ImportedFile) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(item.path.name))
        self.table.setItem(row, 1, QTableWidgetItem("—"))
        self.table.setItem(row, 2, QTableWidgetItem("—"))
        self.table.setItem(row, 3, QTableWidgetItem("—"))
        self.table.setItem(row, 4, QTableWidgetItem("—"))
        status_badge = badge(_STATUS_LABEL["ready"], _STATUS_VARIANT["ready"])
        self.table.setCellWidget(row, 5, status_badge)
        remove_btn = QPushButton("✕")
        remove_btn.setProperty("cls", "ghost")
        remove_btn.setFixedWidth(28)
        remove_btn.clicked.connect(lambda: self._remove_file(item))
        self.table.setCellWidget(row, 6, remove_btn)

    def _row_for(self, item: ImportedFile) -> int | None:
        for row in range(self.table.rowCount()):
            cell = self.table.item(row, 0)
            if cell and cell.text() == item.path.name and self.files[row].path == item.path:
                return row
        return None

    def _on_file_started(self, index: int) -> None:
        item = self._find_item_by_index(index)
        if item is None:
            return
        # Visual-only: never mutate item.status here. The worker thread is
        # the sole writer of the authoritative status (it may already have
        # finished and written a terminal status by the time this queued
        # signal is delivered) -- overwriting it here would be a race.
        row = self._row_index_of(item)
        if row is not None:
            self.table.setCellWidget(row, 5, badge(_STATUS_LABEL["processing"], _STATUS_VARIANT["processing"]))

    def _find_item_by_index(self, index: int) -> ImportedFile | None:
        # index is relative to the batch most recently handed to StudentImportWorker.
        batch = getattr(self, "_current_batch", [])
        if 0 <= index < len(batch):
            return batch[index]
        return None

    def _on_file_done(self, _index: int, item: ImportedFile) -> None:
        self._refresh_row(item)
        self._update_summary()

    def _refresh_row(self, item: ImportedFile) -> None:
        row = self._row_index_of(item)
        if row is None:
            return
        name = item.paper.identity.name if item.paper and item.paper.identity.name else "—"
        student_id = item.paper.identity.student_id if item.paper and item.paper.identity.student_id else "—"
        method = "OCR" if item.doc and item.doc.used_ocr else ("Direct text" if item.doc else "—")
        confidence = f"{item.doc.confidence * 100:.0f}%" if item.doc else "—"

        self.table.item(row, 1).setText(name)
        self.table.item(row, 2).setText(student_id)
        self.table.item(row, 3).setText(method)
        self.table.item(row, 4).setText(confidence)

        status_badge = badge(_STATUS_LABEL.get(item.status, item.status), _STATUS_VARIANT.get(item.status, "neutral"))
        self.table.setCellWidget(row, 5, status_badge)
        if item.status == "error" and item.error:
            self.table.item(row, 1).setToolTip(item.error)

    def _row_index_of(self, item: ImportedFile) -> int | None:
        try:
            idx = self.files.index(item)
        except ValueError:
            return None
        return idx if idx < self.table.rowCount() else None

    def _remove_file(self, item: ImportedFile) -> None:
        row = self._row_index_of(item)
        if row is None:
            return
        self.table.removeRow(row)
        self.files.remove(item)
        self._update_summary()

    def _update_summary(self) -> None:
        total = len(self.files)
        errors = sum(1 for f in self.files if f.status == "error")
        review = sum(1 for f in self.files if f.status == "needs_review")
        processing = sum(1 for f in self.files if f.status in ("ready", "processing"))
        parts = [f"{total} file{'s' if total != 1 else ''}"]
        if review:
            parts.append(f"{review} need review")
        if errors:
            parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        self.summary_badge.setText(" · ".join(parts))
        variant = "danger" if errors else ("warning" if review else "success" if total else "neutral")
        self.summary_badge.setProperty("cls", f"badge-{variant}")
        self.summary_badge.style().unpolish(self.summary_badge)
        self.summary_badge.style().polish(self.summary_badge)
        self.ready_changed.emit(total > 0 and processing == 0)

    def is_valid(self) -> bool:
        if not self.files:
            return False
        return all(f.status not in ("ready", "processing") for f in self.files)
