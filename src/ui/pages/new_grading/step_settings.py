from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QHBoxLayout, QProgressBar, QRadioButton, QVBoxLayout, QWidget,
)

from src.ai.embedding_backend import is_sentence_transformer_available
from src.config.strictness import POLICIES, StrictnessLevel, StrictnessPolicy
from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, badge, h3, muted, subtitle

_DESCRIPTIONS = {
    StrictnessLevel.VERY_LENIENT: "Rewards any recognizable attempt at the concept; missing details barely cost points.",
    StrictnessLevel.LENIENT: "Generous partial credit for partially correct or incomplete answers.",
    StrictnessLevel.BALANCED: "A reasonable balance between rewarding partial conceptual understanding and penalizing missing or contradictory information.",
    StrictnessLevel.STRICT: "Requires strong concept coverage for full credit; omissions and contradictions cost more.",
    StrictnessLevel.VERY_STRICT: "Near-complete, non-contradictory coverage is required for credit at all.",
}

_PARAM_LABELS = [
    ("full_credit_coverage", "Coverage needed for full credit"),
    ("partial_credit_floor", "Coverage floor for any credit"),
    ("contradiction_penalty", "Contradiction penalty (multiplier)"),
    ("omission_penalty_weight", "Omission penalty weight"),
    ("min_similarity_for_any_credit", "Minimum similarity to count as an attempt"),
]


class ParamBar(QWidget):
    def __init__(self, label: str, value: float, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = muted(label)
        lbl.setFixedWidth(230)
        layout.addWidget(lbl)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(round(value * 100)))
        bar.setFormat(f"{value:.2f}")
        bar.setFixedHeight(14)
        layout.addWidget(bar, 1)


class GradingSettingsStep(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        left = QVBoxLayout()
        card = Card()
        card.body.addWidget(h3("Grading Strictness"))
        card.body.addWidget(muted("Every level plugs the same four numbers into the same transparent formula — nothing is a hidden threshold."))

        self.group = QButtonGroup(self)
        self._radios: dict[StrictnessLevel, QRadioButton] = {}
        for level in StrictnessLevel:
            radio = QRadioButton(level.value.replace("_", " ").title())
            self.group.addButton(radio)
            self._radios[level] = radio
            card.body.addWidget(radio)
        self._radios[StrictnessLevel(self.ctx.config.grading.strictness)].setChecked(True)
        self.group.buttonClicked.connect(self._update_explanation)

        card.body.addSpacing(8)
        self.explanation_label = subtitle("")
        self.explanation_label.setWordWrap(True)
        card.body.addWidget(self.explanation_label)

        self.params_box = QVBoxLayout()
        card.body.addLayout(self.params_box)
        left.addWidget(card)

        toggle_card = Card()
        toggle_card.body.addWidget(h3("Detection Options"))
        self.contradiction_checkbox = QCheckBox("Enable contradiction detection")
        self.contradiction_checkbox.setChecked(self.ctx.config.grading.enable_contradiction_detection)
        toggle_card.body.addWidget(self.contradiction_checkbox)
        toggle_card.body.addWidget(muted(
            "Flags answers that negate a concept the official answer states positively (or vice versa)."
        ))
        left.addWidget(toggle_card)
        left.addStretch()
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        ai_card = Card()
        ai_card.body.addWidget(h3("Semantic Engine"))
        available = is_sentence_transformer_available()
        self._preference = self.ctx.config.embedding.backend
        self._model_name = self.ctx.config.embedding.model_name

        if self._preference == "tfidf":
            self._will_use_transformer = False
        elif self._preference == "sentence_transformer":
            self._will_use_transformer = True  # will raise at grading time if actually unavailable
        else:  # "auto"
            self._will_use_transformer = available

        if self._will_use_transformer:
            ai_card.body.addWidget(badge("Ready", "success"))
            ai_card.body.addWidget(muted(self._model_name))
        else:
            ai_card.body.addWidget(badge("Offline fallback: TF-IDF", "warning"))
            ai_card.body.addWidget(muted(
                "sentence-transformers / torch isn't installed, or the backend is set to TF-IDF in "
                "Settings. This works, but has reduced semantic accuracy — install the real "
                "dependencies for production-grade multilingual grading."
            ))
        ai_card.body.addWidget(muted("Change the backend or model in Settings → AI."))
        ai_card.body.addWidget(muted("Fully offline: point Settings → AI → Model at a folder from download_model.py."))

        self.prewarm_status_label = muted("")
        ai_card.body.addWidget(self.prewarm_status_label)
        right.addWidget(ai_card)
        right.addStretch()
        layout.addLayout(right, 1)

        self._prewarm_worker = None
        self._prewarm_started = False
        self._update_explanation()

    def start_prewarm(self) -> None:
        """Called by the wizard when this step becomes visible. Loads the
        model into src.services.backend_cache in the background, so by
        the time "Start Grading" is clicked it's often already warm --
        this is what actually fixes the "grading is slow every time it
        starts" complaint (the model used to reload from scratch on
        every run)."""
        if self._prewarm_started or not self._will_use_transformer:
            return
        self._prewarm_started = True
        from src.services.grading_service import BackendPrewarmWorker

        self.prewarm_status_label.setText("Warming up the semantic model in the background…")
        self._prewarm_worker = BackendPrewarmWorker(self._preference, self._model_name)
        self._prewarm_worker.ready.connect(lambda name: self.prewarm_status_label.setText(f"{name} is warmed up and ready."))
        self._prewarm_worker.failed.connect(lambda msg: self.prewarm_status_label.setText(f"Background warm-up failed (will retry when grading starts): {msg}"))
        self._prewarm_worker.start()

    def _update_explanation(self) -> None:
        level = self.selected_level()
        self.explanation_label.setText(_DESCRIPTIONS[level])
        policy = POLICIES[level]
        while self.params_box.count():
            child = self.params_box.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for attr, label in _PARAM_LABELS:
            value = getattr(policy, attr)
            self.params_box.addWidget(ParamBar(label, value))

    def selected_level(self) -> StrictnessLevel:
        for level, radio in self._radios.items():
            if radio.isChecked():
                return level
        return StrictnessLevel.BALANCED

    def selected_policy(self) -> StrictnessPolicy:
        return POLICIES[self.selected_level()]

    def contradiction_detection_enabled(self) -> bool:
        return self.contradiction_checkbox.isChecked()
