from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from src.models.domain import GradingResult


@dataclass
class QuestionDifficulty:
    question_number: str
    average_score_pct: float
    times_missed: int  # scored below 40% of max


@dataclass
class ClassAnalytics:
    count: int
    average_pct: float
    median_pct: float
    highest_pct: float
    lowest_pct: float
    pass_rate_pct: float
    histogram: dict[str, int]              # bucket label -> count
    question_difficulty: list[QuestionDifficulty] = field(default_factory=list)


def _bucket_label(pct: float) -> str:
    lo = int(pct // 10) * 10
    hi = min(lo + 10, 100)
    return f"{lo}-{hi}"


def compute_class_analytics(results: list[GradingResult], pass_threshold_pct: float = 60.0) -> ClassAnalytics:
    if not results:
        return ClassAnalytics(0, 0.0, 0.0, 0.0, 0.0, 0.0, {})

    percentages = [r.percentage for r in results]

    histogram: dict[str, int] = {}
    for pct in percentages:
        label = _bucket_label(pct)
        histogram[label] = histogram.get(label, 0) + 1
    histogram = dict(sorted(histogram.items(), key=lambda kv: int(kv[0].split("-")[0])))

    passed = sum(1 for p in percentages if p >= pass_threshold_pct)

    per_question_scores: dict[str, list[float]] = {}
    for result in results:
        for fb in result.per_question:
            pct = (fb.score / fb.max_score * 100) if fb.max_score else 0.0
            per_question_scores.setdefault(fb.question_number, []).append(pct)

    difficulty = [
        QuestionDifficulty(
            question_number=qnum,
            average_score_pct=round(statistics.mean(scores), 1),
            times_missed=sum(1 for s in scores if s < 40.0),
        )
        for qnum, scores in per_question_scores.items()
    ]
    difficulty.sort(key=lambda d: d.average_score_pct)  # hardest first

    return ClassAnalytics(
        count=len(results),
        average_pct=round(statistics.mean(percentages), 2),
        median_pct=round(statistics.median(percentages), 2),
        highest_pct=round(max(percentages), 2),
        lowest_pct=round(min(percentages), 2),
        pass_rate_pct=round(100 * passed / len(results), 2),
        histogram=histogram,
        question_difficulty=difficulty,
    )
