from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.config.settings import AppConfig
from src.database.repository import ExamRepository
from src.services import settings_service


class AppSignals(QObject):
    """Cross-page notifications so screens stay in sync without polling."""

    navigate = Signal(str, dict)          # page_key, params
    data_changed = Signal()               # an exam/review/setting changed -- refresh lists
    theme_changed = Signal(str)
    toast_requested = Signal(str, str)    # message, variant


class AppContext:
    """One instance, created in app.py, passed down to every page."""

    def __init__(self, db_path: Path, output_dir: Path):
        self.db_path = db_path
        self.repo = ExamRepository(db_path)
        self.config: AppConfig = settings_service.load_config(self.repo)
        self.config.paths.output_dir = output_dir
        self.theme: str = settings_service.load_theme(self.repo)
        self.signals = AppSignals()

    def save_config(self) -> None:
        settings_service.save_config(self.repo, self.config)

    def set_theme(self, theme: str) -> None:
        self.theme = theme
        settings_service.save_theme(self.repo, theme)
        self.signals.theme_changed.emit(theme)

    def notify_data_changed(self) -> None:
        self.signals.data_changed.emit()

    def navigate(self, page_key: str, **params) -> None:
        self.signals.navigate.emit(page_key, params)

    def toast(self, message: str, variant: str = "success") -> None:
        self.signals.toast_requested.emit(message, variant)

    def shutdown(self) -> None:
        self.repo.close()
