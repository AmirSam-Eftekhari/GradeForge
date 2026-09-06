from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.ui.app_context import AppContext
from src.ui.theme import palette_for
from src.ui.widgets.charts import bar_chart
from src.ui.widgets.common import Card, EmptyState, StatCard, badge, h1, h2, icon_button, muted, subtitle


class DashboardPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(28, 24, 28, 24)
        self._outer.setSpacing(16)
        self._content: QWidget | None = None

    def on_show(self, **_params) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.hide()
            self._content.deleteLater()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(h1("Dashboard"))
        title_col.addWidget(subtitle("An overview of your grading activity."))
        header.addLayout(title_col)
        header.addStretch()
        layout.addLayout(header)

        stats = self.ctx.repo.dashboard_stats()

        if stats.total_exams == 0:
            empty_btn = icon_button("New Grading", "plus-circle", cls="primary")
            empty_btn.clicked.connect(lambda: self.ctx.navigate("new_grading"))
            empty_card = Card()
            empty_card.setMinimumHeight(320)
            empty_card.body.addWidget(EmptyState(
                "No exams yet",
                "Create your first grading session to get started.",
                action=empty_btn, icon_name="sparkles",
            ))
            layout.addWidget(empty_card)
        else:
            layout.addLayout(self._stats_row(stats))
            mid = QHBoxLayout()
            mid.setSpacing(16)
            mid.addWidget(self._distribution_card(stats), 1)
            mid.addWidget(self._quick_actions_card(), 0)
            layout.addLayout(mid)
            layout.addWidget(self._recent_exams_card())
            hardest = self.ctx.repo.hardest_questions(limit=5)
            if hardest:
                layout.addWidget(self._hardest_questions_card(hardest))

        layout.addStretch()
        scroll.setWidget(inner)
        self._outer.addWidget(scroll)
        self._content = scroll

    def _stats_row(self, stats) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(StatCard("Total Exams", str(stats.total_exams), icon_name="book-open"))
        row.addWidget(StatCard("Students Graded", str(stats.total_students), icon_name="users"))
        row.addWidget(StatCard("Average Score", f"{stats.average_pct:.1f}%", icon_name="bar-chart"))
        row.addWidget(StatCard("Pass Rate", f"{stats.pass_rate_pct:.1f}%", icon_name="award"))
        pending_card = StatCard(
            "Pending Reviews", str(stats.pending_review_count), icon_name="alert-triangle",
            trend="Needs attention" if stats.pending_review_count else "All clear",
            variant="warning" if stats.pending_review_count else "success",
        )
        row.addWidget(pending_card)
        return row

    def _distribution_card(self, stats) -> QWidget:
        card = Card()
        card.body.addWidget(h2("Performance Distribution"))
        if stats.histogram:
            palette = palette_for(self.ctx.theme)
            cats = list(stats.histogram.keys())
            vals = [float(v) for v in stats.histogram.values()]
            card.body.addWidget(bar_chart(cats, vals, palette, y_title="Students"))
        else:
            card.body.addWidget(muted("No scores yet."))
        return card

    def _quick_actions_card(self) -> QWidget:
        card = Card()
        card.setFixedWidth(240)
        card.body.addWidget(h2("Quick Actions"))
        actions = [
            ("New Grading", "plus-circle", lambda: self.ctx.navigate("new_grading")),
            ("Review Results", "check-circle", lambda: self.ctx.navigate("review")),
            ("Open Reports", "download", lambda: self.ctx.navigate("reports")),
            ("View Exams", "book-open", lambda: self.ctx.navigate("exams")),
        ]
        for label, icon_name, handler in actions:
            btn = icon_button(label, icon_name, cls="primary" if label == "New Grading" else "ghost")
            btn.clicked.connect(handler)
            card.body.addWidget(btn)
        card.body.addStretch()
        return card

    def _recent_exams_card(self) -> QWidget:
        card = Card()
        card.body.addWidget(h2("Recent Grading Sessions"))
        exams = self.ctx.repo.list_exams()[:6]
        table = QTableWidget(len(exams), 6)
        table.setHorizontalHeaderLabels(["Exam", "Students", "Average", "Pass Rate", "Pending Review", "Created"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        for row, e in enumerate(exams):
            table.setItem(row, 0, QTableWidgetItem(e.title))
            table.setItem(row, 1, QTableWidgetItem(str(e.student_count)))
            table.setItem(row, 2, QTableWidgetItem(f"{e.average_pct:.1f}%"))
            table.setItem(row, 3, QTableWidgetItem(f"{e.pass_rate_pct:.1f}%"))
            table.setItem(row, 4, QTableWidgetItem(str(e.pending_review_count) if e.pending_review_count else "—"))
            table.setItem(row, 5, QTableWidgetItem(str(e.created_at)[:16]))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        table.cellDoubleClicked.connect(lambda r, _c: self.ctx.navigate("exam_detail", exam_id=exams[r].id))
        table.setMinimumHeight(min(280, 44 + 34 * max(1, len(exams))))
        card.body.addWidget(table)
        hint = muted("Double-click a row to open its results.")
        card.body.addWidget(hint)
        return card

    def _hardest_questions_card(self, hardest: list[tuple[str, str, float]]) -> QWidget:
        card = Card()
        card.body.addWidget(h2("Hardest Questions (recent exams)"))
        for exam_title, qnum, avg_pct in hardest:
            row = QHBoxLayout()
            row.addWidget(muted(f"{exam_title} — Q{qnum}"))
            row.addStretch()
            lbl = badge(f"{avg_pct:.0f}% avg", "danger" if avg_pct < 50 else "warning")
            row.addWidget(lbl)
            wrapper = QWidget()
            wrapper.setLayout(row)
            card.body.addWidget(wrapper)
        return card
