from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, EmptyState, h1, subtitle

_COLUMNS = ["Name", "Student ID", "Exams Taken", "Average", "Last Exam", "Last Graded"]


class StudentsPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        outer.addWidget(h1("Students"))
        outer.addWidget(subtitle("Every student who has been graded, across all exams."))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or student ID…")
        self.search_input.textChanged.connect(self._refresh)
        outer.addWidget(self.search_input)

        self._card = Card()
        outer.addWidget(self._card, 1)
        self._students = []

    def on_show(self, **_params) -> None:
        self._refresh()

    def _refresh(self) -> None:
        while self._card.body.count():
            item = self._card.body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search = self.search_input.text().strip().lower()
        all_students = self.ctx.repo.list_all_students()
        self._students = [
            s for s in all_students
            if not search or search in s.name.lower() or search in (s.student_id or "").lower()
        ]

        if not self._students:
            msg = "No students match your search." if search else "No students yet."
            desc = "Try a different search." if search else "Grade an exam to see students here."
            self._card.body.addWidget(EmptyState(msg, desc))
            return

        table = QTableWidget(len(self._students), len(_COLUMNS))
        table.setHorizontalHeaderLabels(_COLUMNS)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        for row, s in enumerate(self._students):
            table.setItem(row, 0, QTableWidgetItem(s.name))
            table.setItem(row, 1, QTableWidgetItem(s.student_id or "—"))
            table.setItem(row, 2, QTableWidgetItem(str(s.exams_taken)))
            table.setItem(row, 3, QTableWidgetItem(f"{s.average_pct:.1f}%"))
            table.setItem(row, 4, QTableWidgetItem(s.last_exam_title))
            table.setItem(row, 5, QTableWidgetItem(str(s.last_graded_at)[:16]))
        table.cellDoubleClicked.connect(lambda r, _c: self.ctx.navigate("student_history", key=self._students[r].key))
        self._card.body.addWidget(table)
