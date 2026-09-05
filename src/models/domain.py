"""
Domain model. These dataclasses are the contract every other layer
(OCR -> parser -> grading -> reports -> dashboard) is built against.
Keeping them framework-free means the grading engine can be unit tested
with zero UI, OCR, or database dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    OK = "ok"
    NEEDS_REVIEW = "needs_review"       # low OCR confidence, ambiguous match, etc.


@dataclass
class Question:
    number: str                 # "1", "2b", ... (kept as str: papers use "3a", "3b")
    text: str
    official_answer: str
    max_score: float
    rubric_concepts: list[str] = field(default_factory=list)  # optional, teacher-defined later


@dataclass
class AnswerKey:
    exam_title: str
    questions: list[Question]
    language: str = "auto"
    description: str = ""  # optional teacher-facing note; no effect on grading


@dataclass
class StudentAnswer:
    question_number: str
    raw_text: str
    ocr_confidence: float = 1.0


@dataclass
class StudentIdentity:
    name: str | None
    student_id: str | None = None
    class_name: str | None = None
    exam_date: str | None = None
    identity_confidence: float = 1.0

    @property
    def status(self) -> ReviewStatus:
        return (
            ReviewStatus.OK
            if self.name and self.identity_confidence >= 0.6
            else ReviewStatus.NEEDS_REVIEW
        )


@dataclass
class StudentPaper:
    source_path: str
    identity: StudentIdentity
    answers: list[StudentAnswer]


@dataclass
class QuestionFeedback:
    question_number: str
    score: float
    max_score: float
    similarity: float
    coverage: float
    missing_concepts: list[str]
    incorrect_concepts: list[str]
    contradictions_detected: bool
    reasoning: str
    suggested_answer: str
    confidence: float


@dataclass
class GradingResult:
    student: StudentIdentity
    source_path: str
    per_question: list[QuestionFeedback]
    graded_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_score(self) -> float:
        return round(sum(q.score for q in self.per_question), 2)

    @property
    def max_total_score(self) -> float:
        return round(sum(q.max_score for q in self.per_question), 2)

    @property
    def percentage(self) -> float:
        if self.max_total_score == 0:
            return 0.0
        return round(100 * self.total_score / self.max_total_score, 2)
