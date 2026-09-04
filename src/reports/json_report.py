from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.models.domain import GradingResult


def write_grading_json(result: GradingResult, output_path: Path) -> None:
    payload = asdict(result)
    payload["total_score"] = result.total_score
    payload["max_total_score"] = result.max_total_score
    payload["percentage"] = result.percentage
    payload["graded_at"] = result.graded_at.isoformat()

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
