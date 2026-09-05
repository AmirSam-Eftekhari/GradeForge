from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.ui.app_context import AppContext
from src.ui.pages.new_grading.step_exam_setup import ExamSetupStep
from src.ui.pages.new_grading.step_settings import GradingSettingsStep
from src.ui.pages.new_grading.step_students import StudentPapersStep
from src.ui.widgets.common import h1, muted, subtitle

_STEP_TITLES = ["Exam Setup", "Student Papers", "Grading Settings"]


class NewGradingWizard(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 20)
        outer.setSpacing(14)

        outer.addWidget(h1("New Grading"))
        outer.addWidget(subtitle("Import an answer key, add student papers, choose how strictly to grade, then run."))

        self._step_indicator = QHBoxLayout()
        outer.addLayout(self._step_indicator)
        self._step_labels: list[muted] = []
        for i, title in enumerate(_STEP_TITLES):
            lbl = muted(f"{i + 1}. {title}")
            self._step_labels.append(lbl)
            self._step_indicator.addWidget(lbl)
            if i < len(_STEP_TITLES) - 1:
                sep = muted("—")
                self._step_indicator.addWidget(sep)
        self._step_indicator.addStretch()

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        self.exam_setup_step = ExamSetupStep()
        self.students_step = StudentPapersStep()
        self.settings_step = GradingSettingsStep(ctx)
        for step in (self.exam_setup_step, self.students_step, self.settings_step):
            self.stack.addWidget(step)

        nav_row = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._go_back)
        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("cls", "primary")
        self.next_btn.clicked.connect(self._go_next)
        nav_row.addWidget(self.back_btn)
        nav_row.addStretch()
        nav_row.addWidget(self.next_btn)
        outer.addLayout(nav_row)

        self.exam_setup_step.ready_changed.connect(self._refresh_next_button)
        self.students_step.ready_changed.connect(self._refresh_next_button)

        self._current = 0
        self._refresh_step_indicator()
        self._refresh_next_button()

    def on_show(self, **_params) -> None:
        self._current = 0
        self.stack.setCurrentIndex(0)
        self._refresh_step_indicator()
        self._refresh_next_button()

    def _refresh_step_indicator(self) -> None:
        for i, lbl in enumerate(self._step_labels):
            lbl.setProperty("cls", "h3" if i == self._current else "muted")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        self.back_btn.setEnabled(self._current > 0)
        is_last = self._current == self.stack.count() - 1
        self.next_btn.setText("Start Grading" if is_last else "Next")

    def _refresh_next_button(self) -> None:
        if self._current == 0:
            self.next_btn.setEnabled(self.exam_setup_step.is_valid())
        elif self._current == 1:
            self.next_btn.setEnabled(self.students_step.is_valid())
        else:
            self.next_btn.setEnabled(True)

    def _go_back(self) -> None:
        if self._current == 0:
            return
        self._current -= 1
        self.stack.setCurrentIndex(self._current)
        self._refresh_step_indicator()
        self._refresh_next_button()

    def _go_next(self) -> None:
        if self._current == 0:
            if not self.exam_setup_step.is_valid():
                QMessageBox.warning(self, "Missing information", "Give the exam a title and at least one question.")
                return
            lang = self.exam_setup_step.selected_language_code()
            languages = [lang] if lang in ("eng", "fas", "ara") else [lang, "eng"]
            self.students_step.set_languages(languages)
            self._current += 1
        elif self._current == 1:
            if not self.students_step.is_valid():
                QMessageBox.warning(self, "No student papers", "Add at least one student paper to continue.")
                return
            self._current += 1
        else:
            self._start_grading()
            return
        self.stack.setCurrentIndex(self._current)
        self._refresh_step_indicator()
        self._refresh_next_button()

    def _start_grading(self) -> None:
        answer_key = self.exam_setup_step.build_answer_key()
        files = self.students_step.files
        usable = [f for f in files if f.paper is not None and f.status != "error"]
        if not usable:
            QMessageBox.warning(self, "Nothing to grade", "None of the imported student papers could be parsed.")
            return

        policy = self.settings_step.selected_policy()
        strictness_level = self.settings_step.selected_level()
        enable_contradiction = self.settings_step.contradiction_detection_enabled()

        self.ctx.navigate(
            "grading_execution",
            answer_key=answer_key, files=files, policy=policy,
            strictness_level=strictness_level.value,
            embedding_preference=self.ctx.config.embedding.backend,
            model_name=self.ctx.config.embedding.model_name,
            enable_contradiction_detection=enable_contradiction,
        )
        self._reset_for_next_time()

    def _reset_for_next_time(self) -> None:
        # Fresh steps next time "New Grading" is opened, so a completed
        # run never bleeds into the next one.
        idx = self.stack.indexOf(self.exam_setup_step)
        self.stack.removeWidget(self.exam_setup_step)
        self.exam_setup_step.deleteLater()
        self.exam_setup_step = ExamSetupStep()
        self.exam_setup_step.ready_changed.connect(self._refresh_next_button)
        self.stack.insertWidget(idx, self.exam_setup_step)

        idx2 = self.stack.indexOf(self.students_step)
        self.stack.removeWidget(self.students_step)
        self.students_step.deleteLater()
        self.students_step = StudentPapersStep()
        self.students_step.ready_changed.connect(self._refresh_next_button)
        self.stack.insertWidget(idx2, self.students_step)
