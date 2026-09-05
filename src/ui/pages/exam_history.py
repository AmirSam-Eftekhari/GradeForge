from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, EmptyState, h1, subtitle

_COLUMNS = ["Exam", "Language", "Strictness", "Students", "Average", "Pass Rate", "Pending Review", "Created"]


class ExamHistoryPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(h1("Exams"))
        title_col.addWidget(subtitle("Every grading session, searchable."))
        header.addLayout(title_col)
        header.addStretch()
        new_btn = QPushButton("New Grading")
        new_btn.setProperty("cls", "primary")
        new_btn.clicked.connect(lambda: self.ctx.navigate("new_grading"))
        header.addWidget(new_btn)
        outer.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search exams by title…")
        self.search_input.textChanged.connect(self._refresh)
        outer.addWidget(self.search_input)

        self._card = Card()
        outer.addWidget(self._card, 1)
        self._table: QTableWidget | None = None
        self._exams = []

    def on_show(self, **_params) -> None:
        self._refresh()

    def _refresh(self) -> None:
        while self._card.body.count():
            item = self._card.body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search = self.search_input.text().strip() or None
        self._exams = self.ctx.repo.list_exams(search=search)

        if not self._exams:
            msg = "No exams match your search." if search else "No exams yet."
            desc = "Try a different search." if search else "Create your first grading session to get started."
            self._card.body.addWidget(EmptyState(msg, desc))
            return

        table = QTableWidget(len(self._exams), len(_COLUMNS))
        table.setHorizontalHeaderLabels(_COLUMNS)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        for row, e in enumerate(self._exams):
            table.setItem(row, 0, QTableWidgetItem(e.title))
            table.setItem(row, 1, QTableWidgetItem(e.language))
            table.setItem(row, 2, QTableWidgetItem(e.strictness.replace("_", " ").title()))
            table.setItem(row, 3, QTableWidgetItem(str(e.student_count)))
            table.setItem(row, 4, QTableWidgetItem(f"{e.average_pct:.1f}%"))
            table.setItem(row, 5, QTableWidgetItem(f"{e.pass_rate_pct:.1f}%"))
            table.setItem(row, 6, QTableWidgetItem(str(e.pending_review_count) if e.pending_review_count else "—"))
            table.setItem(row, 7, QTableWidgetItem(str(e.created_at)[:16]))
        table.cellDoubleClicked.connect(self._open_exam)
        self._table = table
        self._card.body.addWidget(table)

    def _open_exam(self, row: int, _col: int) -> None:
        exam = self._exams[row]
        self.ctx.navigate("exam_detail", exam_id=exam.id)
