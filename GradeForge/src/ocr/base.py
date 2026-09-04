from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OCRPage:
    text: str
    mean_confidence: float  # 0-1


@dataclass
class OCRDocument:
    pages: list[OCRPage]

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def mean_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.mean_confidence for p in self.pages) / len(self.pages)


class OCREngine(ABC):
    @abstractmethod
    def extract(self, file_path: Path, languages: list[str]) -> OCRDocument:
        """Extract text (+ per-page confidence) from a PDF/image/scan."""
