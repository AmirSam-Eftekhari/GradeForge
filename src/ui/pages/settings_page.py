from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from src.config.strictness import StrictnessLevel
from src.ui.app_context import AppContext
from src.ui.widgets.common import Card, h1, muted, subtitle

_MODEL_PRESETS = [
    "intfloat/multilingual-e5-large",
    "BAAI/bge-m3",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
]


class SettingsPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)
        outer.addWidget(h1("Settings"))
        outer.addWidget(subtitle("Changes are saved immediately and apply to future grading runs."))

        tabs = QTabWidget()
        tabs.addTab(self._general_tab(), "General")
        tabs.addTab(self._grading_tab(), "Grading")
        tabs.addTab(self._ai_tab(), "AI")
        tabs.addTab(self._ocr_tab(), "OCR")
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._storage_tab(), "Storage")
        outer.addWidget(tabs, 1)

        self.save_hint = muted("")
        outer.addWidget(self.save_hint)

    def on_show(self, **_params) -> None:
        pass

    # ------------------------------------------------------------------
    def _general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = Card()
        form = QFormLayout()

        self.output_dir_input = QLineEdit(str(self.ctx.config.paths.output_dir))
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_output_dir)
        row = QHBoxLayout()
        row.addWidget(self.output_dir_input, 1)
        row.addWidget(browse_btn)
        row_widget = QWidget()
        row_widget.setLayout(row)
        form.addRow("Default output directory", row_widget)

        db_label = QLabel(str(self.ctx.db_path))
        db_label.setProperty("cls", "mono")
        form.addRow("Database location", db_label)
        form.addRow("", muted("To use a different database file, restart with: python app.py --db <path>"))

        card.body.addLayout(form)
        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _grading_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = Card()
        form = QFormLayout()

        self.strictness_combo = QComboBox()
        for level in StrictnessLevel:
            self.strictness_combo.addItem(level.value.replace("_", " ").title(), userData=level)
        idx = self.strictness_combo.findData(self.ctx.config.grading.strictness)
        if idx >= 0:
            self.strictness_combo.setCurrentIndex(idx)
        self.strictness_combo.currentIndexChanged.connect(self._save)
        form.addRow("Default strictness", self.strictness_combo)

        self.contradiction_checkbox = QCheckBox("Enable contradiction detection by default")
        self.contradiction_checkbox.setChecked(self.ctx.config.grading.enable_contradiction_detection)
        self.contradiction_checkbox.toggled.connect(self._save)
        form.addRow("", self.contradiction_checkbox)

        self.suggestions_checkbox = QCheckBox("Include suggested/model answers in results")
        self.suggestions_checkbox.setChecked(self.ctx.config.grading.enable_suggestions)
        self.suggestions_checkbox.toggled.connect(self._save)
        form.addRow("", self.suggestions_checkbox)

        card.body.addLayout(form)
        card.body.addWidget(muted("The default here pre-selects a strictness level in New Grading — you can still change it per exam."))
        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _ai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = Card()
        form = QFormLayout()

        self.backend_combo = QComboBox()
        for value, label in [("auto", "Auto-detect"), ("sentence_transformer", "Sentence Transformer (semantic)"), ("tfidf", "TF-IDF (offline fallback)")]:
            self.backend_combo.addItem(label, userData=value)
        idx = self.backend_combo.findData(self.ctx.config.embedding.backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self.backend_combo.currentIndexChanged.connect(self._save)
        form.addRow("Backend", self.backend_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(_MODEL_PRESETS)
        self.model_combo.setCurrentText(self.ctx.config.embedding.model_name)
        self.model_combo.currentTextChanged.connect(self._save)
        form.addRow("Model", self.model_combo)

        browse_model_btn = QPushButton("Use a local model folder…")
        browse_model_btn.clicked.connect(self._browse_local_model)
        form.addRow("", browse_model_btn)

        card.body.addLayout(form)
        card.body.addWidget(muted(
            "If sentence-transformers/torch aren't installed, the app automatically falls back to TF-IDF "
            "and clearly labels results as reduced-accuracy — it never silently presents the fallback as equivalent."
        ))
        card.body.addWidget(muted(
            "For fully offline use: run download_model.py once on a machine with internet, then point "
            "\"Model\" at the resulting local folder (or use the button above). A local folder is loaded "
            "with zero network access, even to check for updates."
        ))
        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _ocr_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = Card()
        form = QFormLayout()

        engine_label = QLabel(self.ctx.config.ocr.engine)
        form.addRow("OCR engine", engine_label)

        self.ocr_languages_input = QLineEdit(", ".join(self.ctx.config.ocr.languages))
        self.ocr_languages_input.setPlaceholderText("eng, fas")
        self.ocr_languages_input.editingFinished.connect(self._save)
        form.addRow("Languages (Tesseract codes)", self.ocr_languages_input)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(self.ctx.config.ocr.dpi)
        self.dpi_spin.valueChanged.connect(self._save)
        form.addRow("Rasterization DPI (scanned PDFs)", self.dpi_spin)

        self.min_conf_spin = QDoubleSpinBox()
        self.min_conf_spin.setRange(0.0, 1.0)
        self.min_conf_spin.setSingleStep(0.05)
        self.min_conf_spin.setValue(self.ctx.config.ocr.min_confidence)
        self.min_conf_spin.valueChanged.connect(self._save)
        form.addRow("Minimum OCR confidence", self.min_conf_spin)

        card.body.addLayout(form)
        card.body.addWidget(muted("Tesseract must be installed and on PATH for OCR to work on scanned documents."))
        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = Card()
        self.dark_radio = QRadioButton("Dark (default)")
        self.light_radio = QRadioButton("Light")
        if self.ctx.theme == "light":
            self.light_radio.setChecked(True)
        else:
            self.dark_radio.setChecked(True)
        self.dark_radio.toggled.connect(self._on_theme_changed)
        card.body.addWidget(self.dark_radio)
        card.body.addWidget(self.light_radio)
        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _storage_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = Card()
        form = QFormLayout()
        db_label = QLabel(str(self.ctx.db_path))
        db_label.setProperty("cls", "mono")
        form.addRow("Database file", db_label)
        out_label = QLabel(str(self.ctx.config.paths.output_dir))
        out_label.setProperty("cls", "mono")
        form.addRow("Report output folder", out_label)
        card.body.addLayout(form)

        open_db_btn = QPushButton("Open database folder")
        open_db_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ctx.db_path.parent.resolve()))))
        card.body.addWidget(open_db_btn)
        open_out_btn = QPushButton("Open output folder")
        open_out_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ctx.config.paths.output_dir.resolve()))))
        card.body.addWidget(open_out_btn)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    def _browse_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_dir_input.text())
        if chosen:
            self.output_dir_input.setText(chosen)
            self._save()

    def _browse_local_model(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose a pre-downloaded model folder")
        if chosen:
            self.model_combo.setCurrentText(chosen)
            self._save()

    def _on_theme_changed(self, _checked: bool) -> None:
        self.ctx.set_theme("light" if self.light_radio.isChecked() else "dark")

    def _save(self, *_args) -> None:
        cfg = self.ctx.config
        cfg.paths.output_dir = Path(self.output_dir_input.text().strip() or "Results")
        cfg.grading.strictness = self.strictness_combo.currentData()
        cfg.grading.enable_contradiction_detection = self.contradiction_checkbox.isChecked()
        cfg.grading.enable_suggestions = self.suggestions_checkbox.isChecked()
        cfg.embedding.backend = self.backend_combo.currentData()
        cfg.embedding.model_name = self.model_combo.currentText().strip() or cfg.embedding.model_name
        langs = [x.strip() for x in self.ocr_languages_input.text().split(",") if x.strip()]
        cfg.ocr.languages = langs or ["eng"]
        cfg.ocr.dpi = self.dpi_spin.value()
        cfg.ocr.min_confidence = self.min_conf_spin.value()
        self.ctx.save_config()
        self.save_hint.setText("Saved.")
