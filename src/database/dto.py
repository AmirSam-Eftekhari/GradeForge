"""
Read-side data-transfer objects for the desktop UI.

These are deliberately separate from `src.models.domain` — the domain
dataclasses (`GradingResult`, `QuestionFeedback`, ...) are the grading
engine's contract and stay untouched. Everything here is *review/history*
metadata (needs_review, human_score, review_note, ...) that only makes
sense once a result has been persisted, so it lives on the database side
of the boundary, not in the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models.domain import Question, QuestionFeedback, StudentIdentity

# Flag reasons, computed once at save time and stored so the Review
# Center can filter/sort without recomputing anything.
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_CONTRADICTION = "contradiction"
REASON_BORDERLINE_SIMILARITY = "borderline_similarity"
REASON_UNCERTAIN_IDENTITY = "uncertain_identity"
REASON_MISSING_CONCEPTS = "missing_concepts"

REASON_LABELS = {
    REASON_LOW_CONFIDENCE: "Low grading confidence",
    REASON_CONTRADICTION: "Contradiction detected",
    REASON_BORDERLINE_SIMILARITY: "Borderline semantic similarity",
    REASON_UNCERTAIN_IDENTITY: "Uncertain student identity",
    REASON_MISSING_CONCEPTS: "Missing concepts in answer",
}


@dataclass
class ReviewInfo:
    needs_review: bool = False
    reasons: list[str] = field(default_factory=list)
    review_status: str = "pending"  # "pending" | "accepted" | "adjusted"
    human_score: float | None = None
    review_note: str | None = None
    reviewed_at: str | None = None


@dataclass
class FeedbackRecord:
    """One graded question, plus its review state."""

    db_id: int
    feedback: QuestionFeedback
    review: ReviewInfo

    @property
    def effective_score(self) -> float:
        return self.review.human_score if self.review.human_score is not None else self.feedback.score

    @property
    def is_adjusted(self) -> bool:
        return self.review.human_score is not None


@dataclass
class StudentRecord:
    db_id: int
    exam_id: int
    identity: StudentIdentity
    source_path: str
    graded_at: str
    feedback: list[FeedbackRecord]

    @property
    def needs_review(self) -> bool:
        return any(f.review.needs_review and f.review.review_status == "pending" for f in self.feedback) or (
            self.identity.identity_confidence < 0.6
        )

    @property
    def total_score(self) -> float:
        return round(sum(f.effective_score for f in self.feedback), 2)

    @property
    def max_total_score(self) -> float:
        return round(sum(f.feedback.max_score for f in self.feedback), 2)

    @property
    def percentage(self) -> float:
        if self.max_total_score == 0:
            return 0.0
        return round(100 * self.total_score / self.max_total_score, 2)


@dataclass
class ExamDetail:
    id: int
    title: str
    language: str
    strictness: str
    created_at: str
    questions: list[Question]
    students: list[StudentRecord]
    description: str = ""

    @property
    def pending_review_count(self) -> int:
        return sum(1 for s in self.students if s.needs_review)


@dataclass
class ExamSummary:
    id: int
    title: str
    language: str
    strictness: str
    created_at: str
    student_count: int
    average_pct: float
    pass_rate_pct: float
    pending_review_count: int


@dataclass
class StudentSummary:
    key: str
    name: str
    student_id: str | None
    exams_taken: int
    average_pct: float
    last_exam_title: str
    last_graded_at: str


@dataclass
class DashboardStats:
    total_exams: int
    total_students: int
    average_pct: float
    pass_rate_pct: float
    pending_review_count: int
    histogram: dict[str, int]


@dataclass
class ReviewItem:
    feedback_db_id: int
    exam_id: int
    exam_title: str
    student_db_id: int
    student_name: str
    question_number: str
    reasons: list[str]
    score: float
    max_score: float
    similarity: float
    coverage: float
    confidence: float
    contradictions_detected: bool
    missing_concepts: list[str]
    reasoning: str
    review_status: str
    human_score: float | None
    review_note: str | None
