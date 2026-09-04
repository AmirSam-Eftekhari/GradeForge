from __future__ import annotations

import logging

from src.ai.embedding_backend import EmbeddingBackend
from src.config.strictness import StrictnessPolicy
from src.grading.policy import score_answer
from src.models.domain import AnswerKey, GradingResult, StudentPaper

logger = logging.getLogger(__name__)


class GradingEngine:
    """The single entry point the UI/CLI/dashboard call to grade one paper.

    Dependency-injected on purpose: the backend and policy are passed in
    rather than constructed here, so a caller (tests, the UI settings
    panel, a batch job) can swap either without touching this class.
    """

    def __init__(self, backend: EmbeddingBackend, policy: StrictnessPolicy, enable_contradiction_detection: bool = True):
        self._backend = backend
        self._policy = policy
        self._enable_contradiction_detection = enable_contradiction_detection

    def grade_paper(self, answer_key: AnswerKey, paper: StudentPaper) -> GradingResult:
        answers_by_question = {a.question_number: a for a in paper.answers}
        per_question = []

        for question in answer_key.questions:
            student_answer = answers_by_question.get(question.number)
            student_text = student_answer.raw_text if student_answer else ""
            feedback = score_answer(
                question=question,
                student_text=student_text,
                backend=self._backend,
                policy=self._policy,
                enable_contradiction_detection=self._enable_contradiction_detection,
            )
            per_question.append(feedback)

        unmatched = set(answers_by_question) - {q.number for q in answer_key.questions}
        if unmatched:
            logger.warning(
                "Paper %s contains answers for unrecognized question number(s) %s "
                "— check that question numbering matches the answer key.",
                paper.source_path, sorted(unmatched),
            )

        return GradingResult(
            student=paper.identity,
            source_path=paper.source_path,
            per_question=per_question,
        )

    def grade_batch(self, answer_key: AnswerKey, papers: list[StudentPaper]) -> list[GradingResult]:
        return [self.grade_paper(answer_key, p) for p in papers]
