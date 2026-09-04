from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.models.domain import AnswerKey, GradingResult

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class ExamRepository:
    """All SQL lives here. Every other module talks to grading results
    through dataclasses, never through raw SQL — this is the only class
    allowed to import sqlite3."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA_PATH.read_text())
        self._conn.commit()

    def save_exam(self, answer_key: AnswerKey, strictness: str, results: list[GradingResult]) -> int:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO exams (title, language, strictness) VALUES (?, ?, ?)",
            (answer_key.exam_title, answer_key.language, strictness),
        )
        exam_id = cur.lastrowid

        for q in answer_key.questions:
            cur.execute(
                "INSERT INTO questions (exam_id, number, text, official_answer, max_score) "
                "VALUES (?, ?, ?, ?, ?)",
                (exam_id, q.number, q.text, q.official_answer, q.max_score),
            )

        for result in results:
            cur.execute(
                "INSERT INTO students (exam_id, name, student_id, class_name, "
                "identity_confidence, source_path) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    exam_id, result.student.name, result.student.student_id,
                    result.student.class_name, result.student.identity_confidence,
                    result.source_path,
                ),
            )
            student_row_id = cur.lastrowid
            for fb in result.per_question:
                cur.execute(
                    "INSERT INTO question_feedback (student_id, question_number, score, "
                    "max_score, similarity, coverage, missing_concepts, incorrect_concepts, "
                    "contradictions_detected, reasoning, suggested_answer, confidence) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        student_row_id, fb.question_number, fb.score, fb.max_score,
                        fb.similarity, fb.coverage, json.dumps(fb.missing_concepts),
                        json.dumps(fb.incorrect_concepts), int(fb.contradictions_detected),
                        fb.reasoning, fb.suggested_answer, fb.confidence,
                    ),
                )
        self._conn.commit()
        return exam_id

    def close(self) -> None:
        self._conn.close()
