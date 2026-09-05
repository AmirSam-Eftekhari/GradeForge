from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox, QHBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from src.database.dto import REASON_LABELS, FeedbackRecord
from src.ui.app_context import AppContext
from src.ui.theme import palette_for, score_color
from src.ui.widgets.common import Card, badge, h1, h2, h3, hline, muted, subtitle


class QuestionCard(Card):
    def __init__(self, ctx: AppContext, record: FeedbackRecord, on_reviewed, parent=None):
        super().__init__(parent=parent)
        self.ctx = ctx
        self.record = record
        self._on_reviewed = on_reviewed
        fb = record.feedback
        palette = palette_for(ctx.theme)

        header = QHBoxLayout()
        header.addWidget(h3(f"Question {fb.question_number}"))
        pct = (record.effective_score / fb.max_score * 100) if fb.max_score else 0.0
        score_lbl = muted(f"{record.effective_score:g} / {fb.max_score:g}  ({pct:.0f}%)")
        score_lbl.setStyleSheet(f"color: {score_color(pct, palette)}; font-weight: 700; font-size: 14px;")
        header.addWidget(score_lbl)
        if record.is_adjusted:
            header.addWidget(badge("Adjusted", "warning"))
        header.addStretch()
        if fb.contradictions_detected:
            header.addWidget(badge("Contradiction", "danger"))
        if record.review.needs_review and record.review.review_status == "pending":
            header.addWidget(badge("Needs review", "warning"))
        self.body.addLayout(header)

        self.toggle_btn = QPushButton("Show details ▾")
        self.toggle_btn.setProperty("cls", "ghost")
        self.toggle_btn.clicked.connect(self._toggle)
        self.body.addWidget(self.toggle_btn)

        self.details = QWidget()
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(6)

        stats_row = QHBoxLayout()
        stats_row.addWidget(muted(f"Semantic similarity: {fb.similarity * 100:.0f}%"))
        stats_row.addWidget(muted(f"Concept coverage: {fb.coverage * 100:.0f}%"))
        stats_row.addWidget(muted(f"Confidence: {fb.confidence * 100:.0f}%"))
        stats_row.addStretch()
        details_layout.addLayout(stats_row)

        details_layout.addWidget(_field_label("Reasoning"))
        details_layout.addWidget(muted(fb.reasoning or "—"))

        if fb.missing_concepts:
            details_layout.addWidget(_field_label("Missing Concepts"))
            for c in fb.missing_concepts:
                details_layout.addWidget(muted(f"• {c}"))
        else:
            details_layout.addWidget(_field_label("Missing Concepts"))
            details_layout.addWidget(muted("None"))

        details_layout.addWidget(_field_label("Contradiction"))
        details_layout.addWidget(muted("Detected — review manually" if fb.contradictions_detected else "None detected"))

        details_layout.addWidget(_field_label("Suggested / Model Answer"))
        details_layout.addWidget(muted(fb.suggested_answer or "—"))

        if record.review.reasons:
            details_layout.addWidget(_field_label("Flagged For Review Because"))
            details_layout.addWidget(muted(", ".join(REASON_LABELS.get(r, r) for r in record.review.reasons)))

        if record.review.review_status != "pending":
            note = f"Marked {record.review.review_status}"
            if record.review.review_note:
                note += f" — “{record.review.review_note}”"
            details_layout.addWidget(_field_label("Teacher Review"))
            details_layout.addWidget(muted(note))
        elif record.review.needs_review:
            details_layout.addWidget(hline())
            details_layout.addLayout(self._review_actions())

        self.details.setVisible(False)
        self.body.addWidget(self.details)

    def _toggle(self) -> None:
        visible = not self.details.isVisible()
        self.details.setVisible(visible)
        self.toggle_btn.setText("Hide details ▴" if visible else "Show details ▾")

    def _review_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        accept_btn = QPushButton("Accept AI Grade")
        accept_btn.clicked.connect(self._accept)
        row.addWidget(accept_btn)

        self.score_input = QDoubleSpinBox()
        self.score_input.setRange(0, self.record.feedback.max_score)
        self.score_input.setValue(self.record.feedback.score)
        self.score_input.setSingleStep(0.5)
        row.addWidget(self.score_input)

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Optional note")
        row.addWidget(self.note_input, 1)

        adjust_btn = QPushButton("Save Adjusted Score")
        adjust_btn.setProperty("cls", "primary")
        adjust_btn.clicked.connect(self._adjust)
        row.addWidget(adjust_btn)
        return row

    def _accept(self) -> None:
        self.ctx.repo.update_review(self.record.db_id, status="accepted", human_score=None, note=self.note_input.text().strip() or None)
        self.ctx.notify_data_changed()
        self._on_reviewed()

    def _adjust(self) -> None:
        self.ctx.repo.update_review(
            self.record.db_id, status="adjusted",
            human_score=self.score_input.value(), note=self.note_input.text().strip() or None,
        )
        self.ctx.notify_data_changed()
        self._on_reviewed()


def _field_label(text: str):
    lbl = h3(text)
    return lbl


class StudentResultPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._exam_id: int | None = None
        self._student_db_id: int | None = None
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(28, 24, 28, 24)
        self._outer.setSpacing(16)
        self._content: QWidget | None = None

    def on_show(self, exam_id: int | None = None, student_db_id: int | None = None, **_params) -> None:
        self._exam_id = exam_id
        self._student_db_id = student_db_id
        self._rebuild()

    def _rebuild(self) -> None:
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.deleteLater()
            self._content = None

        if self._exam_id is None or self._student_db_id is None:
            return
        detail = self.ctx.repo.get_exam_detail(self._exam_id)
        if detail is None:
            return
        record = next((s for s in detail.students if s.db_id == self._student_db_id), None)
        if record is None:
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(14)

        back_btn = QPushButton("← Back to results")
        back_btn.setProperty("cls", "ghost")
        back_btn.clicked.connect(lambda: self.ctx.navigate("exam_detail", exam_id=self._exam_id))
        back_btn.setFixedWidth(150)
        layout.addWidget(back_btn)

        header_card = Card()
        top = QHBoxLayout()
        name_col = QVBoxLayout()
        name_col.addWidget(h1(record.identity.name or "(name not confidently detected)"))
        meta_bits = [detail.title]
        if record.identity.student_id:
            meta_bits.append(f"ID {record.identity.student_id}")
        if record.identity.class_name:
            meta_bits.append(record.identity.class_name)
        name_col.addWidget(subtitle(" · ".join(meta_bits)))
        top.addLayout(name_col)
        top.addStretch()

        palette = palette_for(self.ctx.theme)
        score_lbl = h1(f"{record.total_score:g} / {record.max_total_score:g}")
        score_lbl.setStyleSheet(f"color: {score_color(record.percentage, palette)};")
        score_col = QVBoxLayout()
        score_col.addWidget(score_lbl)
        pct_lbl = muted(f"{record.percentage:.1f}%")
        score_col.addWidget(pct_lbl)
        top.addLayout(score_col)
        header_card.body.addLayout(top)

        badges_row = QHBoxLayout()
        identity_ok = record.identity.identity_confidence >= 0.6
        badges_row.addWidget(badge("Identity confirmed" if identity_ok else "Identity uncertain", "success" if identity_ok else "warning"))
        badges_row.addWidget(badge("Needs review" if record.needs_review else "Reviewed / OK", "warning" if record.needs_review else "success"))
        badges_row.addStretch()
        header_card.body.addLayout(badges_row)
        layout.addWidget(header_card)

        layout.addWidget(h2("Question-by-Question Results"))
        for fr in record.feedback:
            layout.addWidget(QuestionCard(self.ctx, fr, on_reviewed=self._rebuild))

        layout.addStretch()
        scroll.setWidget(inner)
        self._outer.addWidget(scroll)
        self._content = scroll
