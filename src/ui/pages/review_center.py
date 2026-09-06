from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QSplitter, QVBoxLayout, QWidget,
)

from src.database.dto import REASON_LABELS, ReviewItem
from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, EmptyState, add_leading_icon, badge, clear_layout, h1, h2, h3, hline, icon_button, muted, subtitle

_REASON_OPTIONS = [("", "All reasons")] + list(REASON_LABELS.items())


class ReviewCenterPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._items: list[ReviewItem] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(h1("Review Center"))
        title_col.addWidget(subtitle("Everything that needs a human look before it's final."))
        header.addLayout(title_col)
        header.addStretch()
        outer.addLayout(header)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by student or exam…")
        add_leading_icon(self.search_input, "search")
        self.search_input.textChanged.connect(self._refresh)
        filters.addWidget(self.search_input, 1)

        self.reason_combo = QComboBox()
        for value, label in _REASON_OPTIONS:
            self.reason_combo.addItem(label, userData=value)
        self.reason_combo.currentIndexChanged.connect(self._refresh)
        filters.addWidget(self.reason_combo)

        self.status_combo = QComboBox()
        for value, label in [("pending", "Pending"), ("accepted", "Accepted"), ("adjusted", "Adjusted"), ("all", "All")]:
            self.status_combo.addItem(label, userData=value)
        self.status_combo.currentIndexChanged.connect(self._refresh)
        filters.addWidget(self.status_combo)
        outer.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(360)
        self.list_widget.currentRowChanged.connect(self._show_detail)
        splitter.addWidget(self.list_widget)

        self.detail_card = Card()
        self.detail_card.body.addWidget(EmptyState("Select an item", "Pick something from the list to review it.", icon_name="eye"))
        splitter.addWidget(self.detail_card)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)

    def on_show(self, exam_id: int | None = None, **_params) -> None:
        self._exam_filter = exam_id
        self._refresh()

    def _refresh(self) -> None:
        search = self.search_input.text().strip() or None
        reason = self.reason_combo.currentData() or None
        status = self.status_combo.currentData() or "pending"
        self._items = self.ctx.repo.list_review_items(
            exam_id=getattr(self, "_exam_filter", None), reason=reason, status=status, search=search,
        )
        self.list_widget.clear()
        for item in self._items:
            label = f"{item.student_name} — {item.exam_title} — Q{item.question_number}"
            list_item = QListWidgetItem(label)
            self.list_widget.addItem(list_item)

        if not self._items:
            self._clear_detail()
            self.detail_card.body.addWidget(EmptyState(
                "Everything is reviewed" if status == "pending" else "Nothing here",
                "No answers currently require attention." if status == "pending" else "No items match these filters.",
                icon_name="check-circle" if status == "pending" else "search",
            ))
        else:
            self.list_widget.setCurrentRow(0)

    def _clear_detail(self) -> None:
        clear_layout(self.detail_card.body)

    def _show_detail(self, row: int) -> None:
        self._clear_detail()
        if row < 0 or row >= len(self._items):
            return
        item = self._items[row]

        header = QHBoxLayout()
        header.addWidget(h2(f"{item.student_name} — Question {item.question_number}"))
        header.addStretch()
        self.detail_card.body.addLayout(header)
        self.detail_card.body.addWidget(muted(item.exam_title))

        reasons_row = QHBoxLayout()
        for r in item.reasons:
            reasons_row.addWidget(badge(REASON_LABELS.get(r, r), "warning"))
        reasons_row.addStretch()
        self.detail_card.body.addLayout(reasons_row)
        self.detail_card.body.addWidget(hline())

        stats = QHBoxLayout()
        stats.addWidget(muted(f"AI score: {item.score:g} / {item.max_score:g}"))
        stats.addWidget(muted(f"Similarity: {item.similarity * 100:.0f}%"))
        stats.addWidget(muted(f"Coverage: {item.coverage * 100:.0f}%"))
        stats.addWidget(muted(f"Confidence: {item.confidence * 100:.0f}%"))
        stats.addStretch()
        self.detail_card.body.addLayout(stats)

        self.detail_card.body.addWidget(h3("Reasoning"))
        self.detail_card.body.addWidget(muted(item.reasoning or "—"))

        if item.missing_concepts:
            self.detail_card.body.addWidget(h3("Missing Concepts"))
            for c in item.missing_concepts:
                self.detail_card.body.addWidget(muted(f"• {c}"))

        if item.contradictions_detected:
            self.detail_card.body.addWidget(badge("Contradiction detected", "danger"))

        self.detail_card.body.addWidget(hline())

        if item.review_status != "pending":
            note = f"Already marked {item.review_status}."
            if item.review_note:
                note += f" Note: “{item.review_note}”"
            self.detail_card.body.addWidget(muted(note))
            open_btn = icon_button("Open Full Student Result", "chevron-right")
            open_btn.clicked.connect(lambda: self.ctx.navigate("student_result", exam_id=item.exam_id, student_db_id=item.student_db_id))
            self.detail_card.body.addWidget(open_btn)
            return

        actions = QHBoxLayout()
        accept_btn = icon_button("Accept AI Grade", "check")
        accept_btn.clicked.connect(lambda: self._accept(item))
        actions.addWidget(accept_btn)

        score_input = QDoubleSpinBox()
        score_input.setRange(0, item.max_score)
        score_input.setValue(item.score)
        actions.addWidget(score_input)

        note_input = QLineEdit()
        note_input.setPlaceholderText("Optional note")
        actions.addWidget(note_input, 1)

        adjust_btn = icon_button("Save Adjusted Score", "save", cls="primary")
        adjust_btn.clicked.connect(lambda: self._adjust(item, score_input.value(), note_input.text().strip()))
        actions.addWidget(adjust_btn)
        self.detail_card.body.addLayout(actions)

        open_btn = icon_button("Open Full Student Result", "chevron-right", cls="ghost")
        open_btn.clicked.connect(lambda: self.ctx.navigate("student_result", exam_id=item.exam_id, student_db_id=item.student_db_id))
        self.detail_card.body.addWidget(open_btn)
        self.detail_card.body.addStretch()

    def _accept(self, item: ReviewItem) -> None:
        self.ctx.repo.update_review(item.feedback_db_id, status="accepted", human_score=None, note=None)
        self.ctx.notify_data_changed()
        self._refresh()

    def _adjust(self, item: ReviewItem, score: float, note: str) -> None:
        self.ctx.repo.update_review(item.feedback_db_id, status="adjusted", human_score=score, note=note or None)
        self.ctx.notify_data_changed()
        self._refresh()
