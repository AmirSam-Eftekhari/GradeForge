from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.analytics.class_analytics import compute_class_analytics
from src.services.report_service import student_to_grading_result
from src.ui.app_context import AppContext
from src.ui.theme import palette_for, score_color
from src.ui.widgets.charts import bar_chart
from src.ui.widgets.common import Card, EmptyState, StatCard, h1, h2, subtitle


class AnalyticsPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._exam_id: int | None = None

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(28, 24, 28, 24)
        self._outer.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(h1("Analytics"))
        title_col.addWidget(subtitle("Class performance and question difficulty for one exam at a time."))
        header.addLayout(title_col)
        header.addStretch()
        self.exam_combo = QComboBox()
        self.exam_combo.setMinimumWidth(280)
        self.exam_combo.currentIndexChanged.connect(self._on_exam_selected)
        header.addWidget(self.exam_combo)
        self._outer.addLayout(header)

        self._content: QWidget | None = None

    def on_show(self, exam_id: int | None = None, **_params) -> None:
        exams = self.ctx.repo.list_exams()
        self.exam_combo.blockSignals(True)
        self.exam_combo.clear()
        for e in exams:
            self.exam_combo.addItem(e.title, userData=e.id)
        self.exam_combo.blockSignals(False)

        if exam_id is not None:
            idx = self.exam_combo.findData(exam_id)
            if idx >= 0:
                self.exam_combo.setCurrentIndex(idx)
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

    def _rebuild(self) -> None:
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.deleteLater()
            self._content = None

        if self._exam_id is None:
            self._content = Card()
            self._content.body.addWidget(EmptyState("No grading history available yet", "Grade an exam to see analytics."))
            self._outer.addWidget(self._content)
            return

        detail = self.ctx.repo.get_exam_detail(self._exam_id)
        if detail is None or not detail.students:
            self._content = Card()
            self._content.body.addWidget(EmptyState("No students graded yet", "This exam has no results to analyze."))
            self._outer.addWidget(self._content)
            return

        results = [student_to_grading_result(s) for s in detail.students]
        analytics = compute_class_analytics(results)
        palette = palette_for(self.ctx.theme)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(16)

        stats_row = QHBoxLayout()
        stats_row.addWidget(StatCard("Average", f"{analytics.average_pct:.1f}%"))
        stats_row.addWidget(StatCard("Median", f"{analytics.median_pct:.1f}%"))
        stats_row.addWidget(StatCard("Highest", f"{analytics.highest_pct:.1f}%"))
        stats_row.addWidget(StatCard("Lowest", f"{analytics.lowest_pct:.1f}%"))
        stats_row.addWidget(StatCard("Pass Rate", f"{analytics.pass_rate_pct:.1f}%"))
        layout.addLayout(stats_row)

        charts_row = QHBoxLayout()
        dist_card = Card()
        dist_card.body.addWidget(h2("Score Distribution"))
        dist_card.body.addWidget(bar_chart(
            list(analytics.histogram.keys()), [float(v) for v in analytics.histogram.values()],
            palette, y_title="Students",
        ))
        charts_row.addWidget(dist_card)

        diff_card = Card()
        diff_card.body.addWidget(h2("Question Difficulty (hardest first)"))
        diff_labels = [f"Q{d.question_number}" for d in analytics.question_difficulty]
        diff_values = [d.average_score_pct for d in analytics.question_difficulty]
        diff_card.body.addWidget(bar_chart(diff_labels, diff_values, palette, bar_color=palette.warning, y_title="Avg %", max_y=100))
        charts_row.addWidget(diff_card)
        layout.addLayout(charts_row)

        table_card = Card()
        table_card.body.addWidget(h2("Question Analysis"))
        table = QTableWidget(len(analytics.question_difficulty), 4)
        table.setHorizontalHeaderLabels(["Question", "Average %", "Times Missed (<40%)", "Difficulty Rank"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        for row, d in enumerate(analytics.question_difficulty):
            table.setItem(row, 0, QTableWidgetItem(f"Q{d.question_number}"))
            pct_item = QTableWidgetItem(f"{d.average_score_pct:.1f}%")
            pct_item.setForeground(QColor(score_color(d.average_score_pct, palette)))
            table.setItem(row, 1, pct_item)
            table.setItem(row, 2, QTableWidgetItem(str(d.times_missed)))
            table.setItem(row, 3, QTableWidgetItem(f"#{row + 1} hardest"))
        table_card.body.addWidget(table)
        layout.addWidget(table_card)

        layout.addStretch()
        scroll.setWidget(inner)
        self._outer.addWidget(scroll)
        self._content = scroll
