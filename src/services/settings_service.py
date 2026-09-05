"""
Persists src.config.settings.AppConfig across app launches.

Stored as a single JSON blob under one key in the `app_settings` table
(see ExamRepository) rather than a separate file, so Settings live next
to the same database the rest of the app already opens -- one file to
back up, one place a "reset to defaults" has to touch.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from src.config.settings import AppConfig, EmbeddingConfig, GradingConfig, OCRConfig, PathsConfig
from src.config.strictness import StrictnessLevel
from src.database.repository import ExamRepository

logger = logging.getLogger(__name__)

_SETTINGS_KEY = "app_config"
_THEME_KEY = "theme"  # "dark" | "light" | "system"


def load_config(repo: ExamRepository) -> AppConfig:
    raw = repo.get_setting(_SETTINGS_KEY)
    if not raw:
        return AppConfig()
    try:
        data = json.loads(raw)
        return AppConfig(
            ocr=OCRConfig(**data.get("ocr", {})),
            embedding=EmbeddingConfig(**data.get("embedding", {})),
            grading=GradingConfig(
                strictness=StrictnessLevel(data.get("grading", {}).get("strictness", "balanced")),
                enable_contradiction_detection=data.get("grading", {}).get("enable_contradiction_detection", True),
                enable_suggestions=data.get("grading", {}).get("enable_suggestions", True),
            ),
            paths=PathsConfig(
                answer_key_path=None, students_dir=None,
                output_dir=Path(data.get("paths", {}).get("output_dir", "Results")),
                database_path=Path(data.get("paths", {}).get("database_path", "exam_grader.db")),
            ),
        )
    except Exception:
        logger.exception("Failed to parse stored settings -- using defaults")
        return AppConfig()


def save_config(repo: ExamRepository, config: AppConfig) -> None:
    payload = {
        "ocr": asdict(config.ocr),
        "embedding": asdict(config.embedding),
        "grading": {
            "strictness": config.grading.strictness.value
            if isinstance(config.grading.strictness, StrictnessLevel) else config.grading.strictness,
            "enable_contradiction_detection": config.grading.enable_contradiction_detection,
            "enable_suggestions": config.grading.enable_suggestions,
        },
        "paths": {
            "output_dir": str(config.paths.output_dir),
            "database_path": str(config.paths.database_path),
        },
    }
    repo.set_setting(_SETTINGS_KEY, json.dumps(payload))


def load_theme(repo: ExamRepository) -> str:
    return repo.get_setting(_THEME_KEY, "dark") or "dark"


def save_theme(repo: ExamRepository, theme: str) -> None:
    repo.set_setting(_THEME_KEY, theme)
