from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from src.services.report_service import export_class_excel, export_student_json, export_student_pdf
from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, EmptyState, h1, h2, muted, subtitle


class ReportsPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._exam_id: int | None = None
        self._detail = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(h1("Reports"))
        title_col.addWidget(subtitle("Export PDF, Excel, or JSON reports for any past exam."))
        header.addLayout(title_col)
        header.addStretch()
        self.exam_combo = QComboBox()
        self.exam_combo.setMinimumWidth(280)
        self.exam_combo.currentIndexChanged.connect(self._on_exam_selected)
        header.addWidget(self.exam_combo)
        outer.addLayout(header)

        self._body = QVBoxLayout()
        outer.addLayout(self._body, 1)

    def on_show(self, exam_id: int | None = None, **_params) -> None:
        exams = self.ctx.repo.list_exams()
        self.exam_combo.blockSignals(True)
        self.exam_combo.clear()
        for e in exams:
            self.exam_combo.addItem(e.title, userData=e.id)
        self.exam_combo.blockSignals(False)

        if exam_id is not None and self.exam_combo.findData(exam_id) >= 0:
            self.exam_combo.setCurrentIndex(self.exam_combo.findData(exam_id))
            self._exam_id = exam_id
        elif exams:
            self.exam_combo.setCurrentIndex(0)
            self._exam_id = exams[0].id
        else:
            self._exam_id = None
        self._rebuild()

    def _on_exam_selected(self, _index: int) -> None:
        self._exam_id = self.exam_combo.currentData()
        self._rebuild()

    def _clear_body(self) -> None:
        while self._body.count():
            item = self._body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _rebuild(self) -> None:
        self._clear_body()
        if self._exam_id is None:
            card = Card()
            card.body.addWidget(EmptyState("No exams to export", "Grade an exam first."))
            self._body.addWidget(card)
            return

        self._detail = self.ctx.repo.get_exam_detail(self._exam_id)
        if self._detail is None or not self._detail.students:
            card = Card()
            card.body.addWidget(EmptyState("No results yet", "This exam has no graded students."))
            self._body.addWidget(card)
            return

        scope_card = Card()
        scope_card.body.addWidget(h2("Student Scope"))
        self.scope_all_radio = QRadioButton("Entire class")
        self.scope_all_radio.setChecked(True)
        self.scope_selected_radio = QRadioButton("Selected students only")
        self.scope_all_radio.toggled.connect(self._update_list_enabled)
        scope_card.body.addWidget(self.scope_all_radio)
        scope_card.body.addWidget(self.scope_selected_radio)

        self.student_list = QListWidget()
        self.student_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for s in self._detail.students:
            item = QListWidgetItem(f"{s.identity.name or '(unnamed)'} — {s.percentage:.1f}%")
            item.setData(1, s.db_id)
            self.student_list.addItem(item)
        self.student_list.setEnabled(False)
        self.student_list.setMaximumHeight(160)
        scope_card.body.addWidget(self.student_list)
        self._body.addWidget(scope_card)

        export_card = Card()
        export_card.body.addWidget(h2("Export"))
        export_card.body.addWidget(muted(f"Files are written under: {self.ctx.config.paths.output_dir}"))

        change_dir_btn = QPushButton("Change output folder…")
        change_dir_btn.clicked.connect(self._change_output_dir)
        export_card.body.addWidget(change_dir_btn)

        buttons_row = QHBoxLayout()
        pdf_btn = QPushButton("Export PDF (per student)")
        pdf_btn.setProperty("cls", "primary")
        pdf_btn.clicked.connect(self._export_pdf)
        buttons_row.addWidget(pdf_btn)

        json_btn = QPushButton("Export JSON (per student)")
        json_btn.clicked.connect(self._export_json)
        buttons_row.addWidget(json_btn)

        excel_btn = QPushButton("Export Class Excel")
        excel_btn.clicked.connect(self._export_excel)
        buttons_row.addWidget(excel_btn)
        export_card.body.addLayout(buttons_row)

        self.status_label = muted("")
        export_card.body.addWidget(self.status_label)
        self._body.addWidget(export_card)
        self._body.addStretch()

    def _update_list_enabled(self, _checked: bool) -> None:
        self.student_list.setEnabled(self.scope_selected_radio.isChecked())

    def _change_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self.ctx.config.paths.output_dir))
        if chosen:
            self.ctx.config.paths.output_dir = Path(chosen)
            self.ctx.save_config()
            self._rebuild()

    def _selected_students(self) -> list:
        if self.scope_all_radio.isChecked():
            return self._detail.students
        ids = {item.data(1) for item in self.student_list.selectedItems()}
        return [s for s in self._detail.students if s.db_id in ids]

    def _export_pdf(self) -> None:
        students = self._selected_students()
        if not students:
            QMessageBox.warning(self, "Nothing selected", "Select at least one student.")
            return
        out_dir = self.ctx.config.paths.output_dir / self._safe_exam_folder()
        paths = [export_student_pdf(s, self._detail, out_dir) for s in students]
        self._report_success(out_dir, len(paths))

    def _export_json(self) -> None:
        students = self._selected_students()
        if not students:
            QMessageBox.warning(self, "Nothing selected", "Select at least one student.")
            return
        out_dir = self.ctx.config.paths.output_dir / self._safe_exam_folder()
        paths = [export_student_json(s, out_dir) for s in students]
        self._report_success(out_dir, len(paths))

    def _export_excel(self) -> None:
        students = self._selected_students()
        if not students:
            QMessageBox.warning(self, "Nothing selected", "Select at least one student.")
            return
        out_dir = self.ctx.config.paths.output_dir / self._safe_exam_folder()
        path = export_class_excel(self._detail, out_dir, students=students)
        self.status_label.setText(f"Saved: {path}")
        self._offer_open(path.parent)

    def _safe_exam_folder(self) -> str:
        cleaned = re.sub(r"[^\w\s\-\u0600-\u06FF]", "", self._detail.title, flags=re.UNICODE).strip()
        return cleaned or f"exam_{self._detail.id}"

    def _report_success(self, out_dir: Path, count: int) -> None:
        self.status_label.setText(f"Exported {count} file(s) to: {out_dir}")
        self._offer_open(out_dir)

    def _offer_open(self, folder: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
