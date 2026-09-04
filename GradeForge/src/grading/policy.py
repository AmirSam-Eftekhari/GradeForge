"""
The actual scoring formula. Deliberately kept in one small, fully-tested
module (see tests/test_grading_policy.py) since this is the piece a
teacher or administrator will ask "why did the AI give this score" about.

Formula (all quantities in [0, 1] except max_score/score):

    coverage   = mean over official-answer concepts of the student
                 text's best-match similarity to that concept
    fraction   = smoothed_ramp(coverage; floor, ceiling) ** omission_weight
    fraction  *= contradiction_penalty  (once per contradiction found)
    score      = fraction * max_score                     [if coverage
                 >= min_similarity_for_any_credit, else score = 0]

`smoothed_ramp` is 0 below `floor`, 1 at/above `ceiling`, and linear in
between — no hidden step functions.
"""

from __future__ import annotations

import re

from src.ai.embedding_backend import EmbeddingBackend, detect_contradiction
from src.config.strictness import StrictnessPolicy
from src.models.domain import Question, QuestionFeedback

_CONCEPT_SPLIT_RE = re.compile(r"[.;\n]+")


def split_concepts(text: str) -> list[str]:
    """Split into sentence-level chunks. Used both to break the official
    answer into gradable concepts, and to break a student's answer into
    candidate spans so each concept can be matched against the specific
    sentence that addresses it, rather than diluted across the whole
    answer (which especially matters for the TF-IDF fallback backend,
    where a short concept vs. one long paragraph under-scores even
    exact substring matches)."""
    parts = [p.strip(" ,") for p in _CONCEPT_SPLIT_RE.split(text)]
    return [p for p in parts if len(p) >= 3]


def _smoothed_ramp(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 1.0 if value >= ceiling else 0.0
    if value <= floor:
        return 0.0
    if value >= ceiling:
        return 1.0
    return (value - floor) / (ceiling - floor)


def score_answer(
    question: Question,
    student_text: str,
    backend: EmbeddingBackend,
    policy: StrictnessPolicy,
    enable_contradiction_detection: bool = True,
) -> QuestionFeedback:
    if not student_text.strip():
        return QuestionFeedback(
            question_number=question.number,
            score=0.0,
            max_score=question.max_score,
            similarity=0.0,
            coverage=0.0,
            missing_concepts=split_concepts(question.official_answer),
            incorrect_concepts=[],
            contradictions_detected=False,
            reasoning="No answer was found for this question.",
            suggested_answer=question.official_answer,
            confidence=1.0,
        )

    overall_similarity = backend.similarity(question.official_answer, student_text)
    concepts = split_concepts(question.official_answer) or [question.official_answer]

    student_spans = split_concepts(student_text) or [student_text]
    if student_text not in student_spans:
        student_spans = student_spans + [student_text]

    concept_scores = [
        max(backend.similarity_many(concept, student_spans)) for concept in concepts
    ]

    covered_threshold = max(0.35, policy.min_similarity_for_any_credit)
    missing = [c for c, s in zip(concepts, concept_scores) if s < covered_threshold]
    coverage = sum(concept_scores) / len(concept_scores) if concept_scores else overall_similarity

    contradictions_detected = False
    if enable_contradiction_detection:
        contradictions_detected = any(
            detect_contradiction(c, student_text, backend) for c in concepts
        )

    if overall_similarity < policy.min_similarity_for_any_credit:
        fraction = 0.0
    else:
        fraction = _smoothed_ramp(coverage, policy.partial_credit_floor, policy.full_credit_coverage)
        fraction = fraction ** policy.omission_penalty_weight
        if contradictions_detected:
            fraction *= policy.contradiction_penalty

    score = round(max(0.0, min(1.0, fraction)) * question.max_score, 2)

    reasoning_parts = [
        f"Semantic coverage of required concepts: {coverage * 100:.0f}%.",
    ]
    if missing:
        reasoning_parts.append(f"{len(missing)} of {len(concepts)} concept(s) were not addressed.")
    if contradictions_detected:
        reasoning_parts.append("A statement contradicting the official answer was detected.")
    if not missing and not contradictions_detected and fraction >= 0.99:
        reasoning_parts.append("Answer fully matches the expected concepts.")

    return QuestionFeedback(
        question_number=question.number,
        score=score,
        max_score=question.max_score,
        similarity=round(overall_similarity, 3),
        coverage=round(coverage, 3),
        missing_concepts=missing,
        incorrect_concepts=[],
        contradictions_detected=contradictions_detected,
        reasoning=" ".join(reasoning_parts),
        suggested_answer=question.official_answer,
        confidence=round(min(1.0, 0.5 + coverage / 2), 2),
    )
