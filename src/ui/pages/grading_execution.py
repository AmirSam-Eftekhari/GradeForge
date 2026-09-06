from __future__ import annotations

import time

from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QVBoxLayout, QWidget,
)

from src.services.grading_service import GradingProgress, GradingWorker
from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, badge, h1, h2, icon_button, muted, subtitle


class GradingExecutionPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._worker: GradingWorker | None = None
        self._answer_key = None
        self._strictness_level = "balanced"
        self._start_time = 0.0
        self._results: list = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        outer.addWidget(h1("Grading in Progress"))
        self.subtitle_label = subtitle("")
        outer.addWidget(self.subtitle_label)

        card = Card()
        self.status_label = h2("Preparing…")
        card.body.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        card.body.addWidget(self.progress_bar)

        info_row = QHBoxLayout()
        self.count_label = muted("")
        self.speed_label = muted("")
        self.eta_label = muted("")
        info_row.addWidget(self.count_label)
        info_row.addStretch()
        info_row.addWidget(self.speed_label)
        info_row.addWidget(self.eta_label)
        card.body.addLayout(info_row)

        self.backend_badge = badge("—", "neutral")
        card.body.addWidget(self.backend_badge)
        self.warning_label = muted("")
        self.warning_label.setVisible(False)
        card.body.addWidget(self.warning_label)

        outer.addWidget(card)

        log_card = Card()
        log_card.body.addWidget(h2("Log"))
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(240)
        log_card.body.addWidget(self.log_list)
        outer.addWidget(log_card, 1)

        actions = QHBoxLayout()
        self.cancel_btn = icon_button("Cancel", "x", cls="danger")
        self.cancel_btn.clicked.connect(self._cancel)
        actions.addWidget(self.cancel_btn)
        actions.addStretch()
        self.view_results_btn = icon_button("View Results", "chevron-right", cls="primary")
        self.view_results_btn.setEnabled(False)
        self.view_results_btn.clicked.connect(self._view_results)
        actions.addWidget(self.view_results_btn)
        outer.addLayout(actions)

    def on_show(self, **params) -> None:
        answer_key = params.get("answer_key")
        files = params.get("files")
        policy = params.get("policy")
        if answer_key is None or files is None or policy is None:
            self.status_label.setText("Nothing to grade.")
            return

        self._answer_key = answer_key
        self._strictness_level = params.get("strictness_level", "balanced")
        self._results = []
        self.log_list.clear()
        self.view_results_btn.setEnabled(False)
        self.warning_label.setVisible(False)
        self.subtitle_label.setText(f"Grading “{answer_key.exam_title}” against {len(files)} student paper(s).")
        self.status_label.setText("Loading semantic engine…")
        self.progress_bar.setValue(0)
        self.count_label.setText("")
        self.speed_label.setText("")
        self.eta_label.setText("")
        self.backend_badge.setText("Loading…")
        self.backend_badge.setProperty("cls", "badge-neutral")
        self.cancel_btn.setEnabled(True)

        self._start_time = time.monotonic()
        self._worker = GradingWorker(
            answer_key=answer_key, files=files, policy=policy,
            embedding_preference=params.get("embedding_preference", "auto"),
            model_name=params.get("model_name", "intfloat/multilingual-e5-large"),
            enable_contradiction_detection=params.get("enable_contradiction_detection", True),
        )
        self._worker.backend_ready.connect(self._on_backend_ready)
        self._worker.progress.connect(self._on_progress)
        self._worker.student_graded.connect(self._on_student_graded)
        self._worker.finished_all.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_backend_ready(self, name: str, warning: str) -> None:
        variant = "warning" if warning else "success"
        self.backend_badge.setText(name)
        self.backend_badge.setProperty("cls", f"badge-{variant}")
        self.backend_badge.style().unpolish(self.backend_badge)
        self.backend_badge.style().polish(self.backend_badge)
        if warning:
            self.warning_label.setText(warning)
            self.warning_label.setVisible(True)
        self._log(f"Semantic engine ready: {name}")

    def _on_progress(self, progress: GradingProgress) -> None:
        self.status_label.setText(f"Grading {progress.current_index + 1} of {progress.total} students")
        pct = int(round(100 * (progress.current_index) / max(1, progress.total)))
        self.progress_bar.setValue(pct)
        self.count_label.setText(f"Current: {progress.student_name} ({progress.questions_in_paper} answer(s) found)")

        elapsed = max(0.001, time.monotonic() - self._start_time)
        done = progress.current_index
        if done > 0:
            rate = done / elapsed
            remaining = progress.total - done
            eta_seconds = remaining / rate if rate > 0 else 0
            self.speed_label.setText(f"{rate:.2f} students/sec")
            self.eta_label.setText(f"~{int(eta_seconds)}s remaining")

    def _on_student_graded(self, _source_path: str, result) -> None:
        self._results.append(result)
        flag = "  [NEEDS REVIEW]" if result.student.identity_confidence < 0.6 else ""
        self._log(f"{result.student.name or 'Unknown'}: {result.total_score:g}/{result.max_total_score:g} ({result.percentage:.1f}%){flag}")

    def _on_finished(self, results: list) -> None:
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(False)
        if not results:
            self.status_label.setText("Grading finished with no results.")
            self._log("No students were graded.")
            return

        exam_id = self.ctx.repo.save_exam(self._answer_key, self._strictness_level, results)
        self.ctx.notify_data_changed()
        review_count = sum(1 for r in results if r.student.identity_confidence < 0.6 or any(
            fb.confidence < 0.6 or fb.contradictions_detected for fb in r.per_question
        ))
        self.status_label.setText(f"Done — {len(results)} student(s) graded.")
        self.count_label.setText(f"{review_count} answer set(s) flagged for review." if review_count else "Nothing flagged for review.")
        self._log(f"Saved to database as exam #{exam_id}.")
        self._exam_id = exam_id
        self.view_results_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self.status_label.setText("Grading failed.")
        self.cancel_btn.setEnabled(False)
        QMessageBox.critical(self, "Grading failed", message)
        self._log(f"Error: {message}")

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Cancelling…")

    def _view_results(self) -> None:
        exam_id = getattr(self, "_exam_id", None)
        if exam_id is not None:
            self.ctx.navigate("exam_detail", exam_id=exam_id)

    def _log(self, text: str) -> None:
        self.log_list.addItem(QListWidgetItem(text))
        self.log_list.scrollToBottom()
