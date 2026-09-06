from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, EmptyState, StatCard, h1, subtitle


class StudentHistoryPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._key: str | None = None
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(28, 24, 28, 24)
        self._outer.setSpacing(16)
        self._content: QWidget | None = None

    def on_show(self, key: str | None = None, **_params) -> None:
        self._key = key
        self._rebuild()

    def _rebuild(self) -> None:
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.hide()
            self._content.deleteLater()
            self._content = None

        if self._key is None:
            return
        records = self.ctx.repo.get_student_history(self._key)
        if not records:
            self._content = EmptyState("No history found", "This student has no graded exams.", icon_name="clock")
            self._outer.addWidget(self._content)
            return

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(14)

        back_btn = QPushButton("← Back to students")
        back_btn.setProperty("cls", "ghost")
        back_btn.setFixedWidth(150)
        back_btn.clicked.connect(lambda: self.ctx.navigate("students"))
        layout.addWidget(back_btn)

        name = records[0].identity.name or "(unnamed)"
        layout.addWidget(h1(name))
        student_id = records[0].identity.student_id
        layout.addWidget(subtitle(f"Student ID: {student_id}" if student_id else "No student ID on file"))

        percentages = [r.percentage for r in records]
        stats_row = QHBoxLayout()
        stats_row.addWidget(StatCard("Exams Taken", str(len(records))))
        stats_row.addWidget(StatCard("Average", f"{sum(percentages) / len(percentages):.1f}%"))
        stats_row.addWidget(StatCard("Best", f"{max(percentages):.1f}%"))
        stats_row.addWidget(StatCard("Lowest", f"{min(percentages):.1f}%"))
        if len(percentages) >= 2:
            trend = percentages[-1] - percentages[0]
            trend_text = f"{'+' if trend >= 0 else ''}{trend:.1f} pts since first exam"
            stats_row.addWidget(StatCard("Trend", trend_text, variant="success" if trend >= 0 else "danger"))
        layout.addLayout(stats_row)

        table_card = Card()
        table = QTableWidget(len(records), 4)
        table.setHorizontalHeaderLabels(["Exam", "Score", "Percentage", "Needs Review"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        for row, r in enumerate(records):
            table.setItem(row, 0, QTableWidgetItem(str(r.graded_at)[:16]))
            table.setItem(row, 1, QTableWidgetItem(f"{r.total_score:g} / {r.max_total_score:g}"))
            table.setItem(row, 2, QTableWidgetItem(f"{r.percentage:.1f}%"))
            table.setItem(row, 3, QTableWidgetItem("Yes" if r.needs_review else "No"))
        table.cellDoubleClicked.connect(lambda row, _c: self.ctx.navigate(
            "student_result", exam_id=records[row].exam_id, student_db_id=records[row].db_id,
        ))
        table_card.body.addWidget(table)
        layout.addWidget(table_card)

        layout.addStretch()
        self._outer.addWidget(container)
        self._content = container
