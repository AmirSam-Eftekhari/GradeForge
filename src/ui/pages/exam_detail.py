from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.analytics.class_analytics import compute_class_analytics
from src.services.report_service import student_to_grading_result
from src.ui.app_context import AppContext
from src.ui.theme import palette_for
from src.ui.widgets.charts import bar_chart
from src.ui.widgets.common import Card, EmptyState, StatCard, badge, h1, h2, muted, subtitle


class ExamDetailPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._exam_id: int | None = None
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(28, 24, 28, 24)
        self._outer.setSpacing(16)
        self._content: QWidget | None = None

    def on_show(self, exam_id: int | None = None, **_params) -> None:
        self._exam_id = exam_id
        self._rebuild()

    def _rebuild(self) -> None:
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.deleteLater()
            self._content = None

        if self._exam_id is None:
            return
        detail = self.ctx.repo.get_exam_detail(self._exam_id)
        if detail is None:
            self._content = EmptyState("Exam not found", "It may have been deleted.")
            self._outer.addWidget(self._content)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(h1(detail.title))
        subtitle_text = f"{detail.language} · {detail.strictness.replace('_', ' ').title()} · {len(detail.questions)} question(s)"
        if detail.description:
            subtitle_text += f" · {detail.description}"
        title_col.addWidget(subtitle(subtitle_text))
        header.addLayout(title_col)
        header.addStretch()

        report_btn = QPushButton("Export Reports")
        report_btn.clicked.connect(lambda: self.ctx.navigate("reports", exam_id=detail.id))
        header.addWidget(report_btn)

        analytics_btn = QPushButton("Full Analytics")
        analytics_btn.clicked.connect(lambda: self.ctx.navigate("analytics", exam_id=detail.id))
        header.addWidget(analytics_btn)

        delete_btn = QPushButton("Delete Exam")
        delete_btn.setProperty("cls", "danger")
        delete_btn.clicked.connect(self._delete_exam)
        header.addWidget(delete_btn)
        layout.addLayout(header)

        if not detail.students:
            empty_card = Card()
            empty_card.setMinimumHeight(240)
            empty_card.body.addWidget(EmptyState("No students graded yet", "This exam has no graded papers."))
            layout.addWidget(empty_card)
            scroll.setWidget(inner)
            self._outer.addWidget(scroll)
            self._content = scroll
            return

        results = [student_to_grading_result(s) for s in detail.students]
        analytics = compute_class_analytics(results)

        stats_row = QHBoxLayout()
        stats_row.addWidget(StatCard("Students", str(analytics.count)))
        stats_row.addWidget(StatCard("Average", f"{analytics.average_pct:.1f}%"))
        stats_row.addWidget(StatCard("Median", f"{analytics.median_pct:.1f}%"))
        stats_row.addWidget(StatCard("Highest", f"{analytics.highest_pct:.1f}%"))
        stats_row.addWidget(StatCard("Lowest", f"{analytics.lowest_pct:.1f}%"))
        stats_row.addWidget(StatCard("Pass Rate", f"{analytics.pass_rate_pct:.1f}%"))
        review_card = StatCard(
            "Pending Review", str(detail.pending_review_count),
            trend="Review needed" if detail.pending_review_count else "All clear",
            variant="warning" if detail.pending_review_count else "success",
        )
        stats_row.addWidget(review_card)
        layout.addLayout(stats_row)

        if analytics.histogram:
            chart_card = Card()
            chart_card.body.addWidget(h2("Score Distribution"))
            palette = palette_for(self.ctx.theme)
            chart_card.body.addWidget(bar_chart(
                list(analytics.histogram.keys()), [float(v) for v in analytics.histogram.values()],
                palette, y_title="Students",
            ))
            layout.addWidget(chart_card)

        table_card = Card()
        table_card.body.addWidget(h2("Students"))
        table = QTableWidget(len(detail.students), 6)
        table.setHorizontalHeaderLabels(["Name", "Student ID", "Score", "Percentage", "Identity", "Review"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        for row, s in enumerate(detail.students):
            table.setItem(row, 0, QTableWidgetItem(s.identity.name or "(unidentified)"))
            table.setItem(row, 1, QTableWidgetItem(s.identity.student_id or "—"))
            table.setItem(row, 2, QTableWidgetItem(f"{s.total_score:g} / {s.max_total_score:g}"))
            table.setItem(row, 3, QTableWidgetItem(f"{s.percentage:.1f}%"))

            identity_variant = "success" if s.identity.identity_confidence >= 0.6 else "warning"
            identity_text = "Confirmed" if s.identity.identity_confidence >= 0.6 else "Uncertain"
            table.setCellWidget(row, 4, badge(identity_text, identity_variant))

            table.setCellWidget(row, 5, badge("Needs review", "warning") if s.needs_review else badge("OK", "success"))
        table.cellDoubleClicked.connect(lambda r, _c: self.ctx.navigate(
            "student_result", exam_id=detail.id, student_db_id=detail.students[r].db_id,
        ))
        table.setMinimumHeight(min(420, 44 + 34 * len(detail.students)))
        table_card.body.addWidget(table)
        table_card.body.addWidget(muted("Double-click a student to see the full question-by-question breakdown."))
        layout.addWidget(table_card)

        layout.addStretch()
        scroll.setWidget(inner)
        self._outer.addWidget(scroll)
        self._content = scroll

    def _delete_exam(self) -> None:
        if self._exam_id is None:
            return
        confirm = QMessageBox.question(
            self, "Delete exam",
            "This permanently deletes this exam and all of its student results. This cannot be undone. Continue?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.ctx.repo.delete_exam(self._exam_id)
            self.ctx.notify_data_changed()
            self.ctx.navigate("exams")
