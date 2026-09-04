from __future__ import annotations

import logging

from src.ai.language_detect import detect_language
from src.models.domain import AnswerKey, Question
from src.parser.common import extract_score, split_into_question_blocks, split_question_and_answer

logger = logging.getLogger(__name__)

_DEFAULT_MAX_SCORE = 1.0  # used only if no score marker is found; caller is warned


def parse_answer_key(raw_text: str, exam_title: str = "Untitled Exam") -> AnswerKey:
    blocks = split_into_question_blocks(raw_text)
    questions: list[Question] = []

    for block in blocks:
        question_text, answer_text = split_question_and_answer(block.body_lines)
        score = extract_score(block.header_line, *block.body_lines[:2])
        if score is None:
            logger.warning(
                "No max-score marker found for question %s — defaulting to %.1f. "
                "Expected formats: '(3 points)', '[5]', '- 2 Marks', 'Score: 4'.",
                block.number, _DEFAULT_MAX_SCORE,
            )
            score = _DEFAULT_MAX_SCORE

        if not answer_text:
            # No explicit "Answer:" marker — assume the whole block IS the
            # official answer (common when answer keys skip restating the
            # question and just list model answers).
            answer_text = question_text
            question_text = f"Question {block.number}"

        questions.append(
            Question(
                number=block.number,
                text=question_text,
                official_answer=answer_text,
                max_score=score,
            )
        )

    language = detect_language(raw_text)
    return AnswerKey(exam_title=exam_title, questions=questions, language=language)
