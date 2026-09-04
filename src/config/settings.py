"""
Central application configuration.

Kept as plain dataclasses (no framework magic) so the same config object can
be constructed from a CLI, a PySide6 settings dialog, or a JSON/YAML file
without any of the business logic caring which one built it.
"""

from dataclasses import dataclass, field
from pathlib import Path

from src.config.strictness import StrictnessLevel


@dataclass
class OCRConfig:
    engine: str = "tesseract"          # pluggable: "tesseract" today, "paddleocr" etc later
    languages: list[str] = field(default_factory=lambda: ["eng", "fas"])
    dpi: int = 300
    min_confidence: float = 0.55       # below this -> flag for manual confirmation


@dataclass
class EmbeddingConfig:
    backend: str = "auto"              # "auto" | "sentence_transformer" | "tfidf"
    model_name: str = "intfloat/multilingual-e5-large"
    fallback_model_name: str = "tfidf"  # used automatically if backend deps are missing


@dataclass
class GradingConfig:
    strictness: StrictnessLevel = StrictnessLevel.BALANCED
    enable_contradiction_detection: bool = True
    enable_suggestions: bool = True


@dataclass
class PathsConfig:
    answer_key_path: Path | None = None
    students_dir: Path | None = None
    output_dir: Path = Path("Results")
    database_path: Path = Path("exam_grader.db")


@dataclass
class AppConfig:
    ocr: OCRConfig = field(default_factory=OCRConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    grading: GradingConfig = field(default_factory=GradingConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
