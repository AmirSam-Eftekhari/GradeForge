from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.database.dto import (
    REASON_BORDERLINE_SIMILARITY,
    REASON_CONTRADICTION,
    REASON_LOW_CONFIDENCE,
    REASON_MISSING_CONCEPTS,
    REASON_UNCERTAIN_IDENTITY,
    DashboardStats,
    ExamDetail,
    ExamSummary,
    FeedbackRecord,
    ReviewInfo,
    ReviewItem,
    StudentRecord,
    StudentSummary,
)
from src.models.domain import AnswerKey, GradingResult, Question, QuestionFeedback, StudentIdentity

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Confidence/similarity bands used to flag a result for human review.
# Kept here (not in grading/policy.py) because these are *review*
# thresholds, not scoring thresholds -- they never change a score, only
# whether the Review Center surfaces it. See dto.py for the reason codes.
_LOW_CONFIDENCE_THRESHOLD = 0.6
_BORDERLINE_SIMILARITY_BAND = (0.20, 0.45)
_UNCERTAIN_IDENTITY_THRESHOLD = 0.6

# (table, column, DDL-type-and-default) columns added after the original
# schema shipped. SQLite has no "ADD COLUMN IF NOT EXISTS", so we check
# PRAGMA table_info ourselves and add whatever's missing -- this lets a
# database created by an older build of this app upgrade in place.
_MIGRATIONS: list[tuple[str, str, str]] = [
    ("exams", "description", "TEXT"),
    ("students", "graded_at", "TEXT"),
    ("students", "needs_review", "INTEGER NOT NULL DEFAULT 0"),
    ("question_feedback", "flag_reasons", "TEXT"),
    ("question_feedback", "needs_review", "INTEGER NOT NULL DEFAULT 0"),
    ("question_feedback", "review_status", "TEXT NOT NULL DEFAULT 'pending'"),
    ("question_feedback", "human_score", "REAL"),
    ("question_feedback", "review_note", "TEXT"),
    ("question_feedback", "reviewed_at", "TEXT"),
]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExamRepository:
    """All SQL lives here. Every other module talks to grading results
    through dataclasses, never through raw SQL -- this is the only class
    allowed to import sqlite3."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA_PATH.read_text())
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        cur = self._conn.cursor()
        for table, column, ddl in _MIGRATIONS:
            cur.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cur.fetchall()}
            if column not in existing:
                logger.info("Migrating database: adding %s.%s", table, column)
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    # ------------------------------------------------------------------
    # Writing (grading pipeline -> DB). Signature unchanged from the
    # original build so main.py's CLI keeps working without modification.
    # ------------------------------------------------------------------

    def save_exam(self, answer_key: AnswerKey, strictness: str, results: list[GradingResult]) -> int:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO exams (title, language, strictness, description) VALUES (?, ?, ?, ?)",
            (answer_key.exam_title, answer_key.language, strictness, getattr(answer_key, "description", "")),
        )
        exam_id = cur.lastrowid

        for q in answer_key.questions:
            cur.execute(
                "INSERT INTO questions (exam_id, number, text, official_answer, max_score) "
                "VALUES (?, ?, ?, ?, ?)",
                (exam_id, q.number, q.text, q.official_answer, q.max_score),
            )

        for result in results:
            identity_flag = result.student.identity_confidence < _UNCERTAIN_IDENTITY_THRESHOLD
            cur.execute(
                "INSERT INTO students (exam_id, name, student_id, class_name, "
                "identity_confidence, source_path, graded_at, needs_review) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    exam_id, result.student.name, result.student.student_id,
                    result.student.class_name, result.student.identity_confidence,
                    result.source_path, result.graded_at.isoformat(), int(identity_flag),
                ),
            )
            student_row_id = cur.lastrowid
            for fb in result.per_question:
                reasons = self._flag_reasons(fb, identity_uncertain=identity_flag)
                cur.execute(
                    "INSERT INTO question_feedback (student_id, question_number, score, "
                    "max_score, similarity, coverage, missing_concepts, incorrect_concepts, "
                    "contradictions_detected, reasoning, suggested_answer, confidence, "
                    "flag_reasons, needs_review) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        student_row_id, fb.question_number, fb.score, fb.max_score,
                        fb.similarity, fb.coverage, json.dumps(fb.missing_concepts),
                        json.dumps(fb.incorrect_concepts), int(fb.contradictions_detected),
                        fb.reasoning, fb.suggested_answer, fb.confidence,
                        json.dumps(reasons), int(bool(reasons)),
                    ),
                )
        self._conn.commit()
        return exam_id

    @staticmethod
    def _flag_reasons(fb: QuestionFeedback, identity_uncertain: bool = False) -> list[str]:
        reasons = []
        if fb.confidence < _LOW_CONFIDENCE_THRESHOLD:
            reasons.append(REASON_LOW_CONFIDENCE)
        if fb.contradictions_detected:
            reasons.append(REASON_CONTRADICTION)
        lo, hi = _BORDERLINE_SIMILARITY_BAND
        if lo <= fb.similarity <= hi:
            reasons.append(REASON_BORDERLINE_SIMILARITY)
        if fb.missing_concepts:
            reasons.append(REASON_MISSING_CONCEPTS)
        if identity_uncertain:
            reasons.append(REASON_UNCERTAIN_IDENTITY)
        return reasons

    # ------------------------------------------------------------------
    # Reading (DB -> UI). Reconstructs the same domain dataclasses the
    # grading engine produces, plus review metadata, so report writers
    # and result screens work identically on live and historical data.
    # ------------------------------------------------------------------

    def _row_to_feedback_record(self, row: sqlite3.Row) -> FeedbackRecord:
        feedback = QuestionFeedback(
            question_number=row["question_number"],
            score=row["score"],
            max_score=row["max_score"],
            similarity=row["similarity"] or 0.0,
            coverage=row["coverage"] or 0.0,
            missing_concepts=json.loads(row["missing_concepts"] or "[]"),
            incorrect_concepts=json.loads(row["incorrect_concepts"] or "[]"),
            contradictions_detected=bool(row["contradictions_detected"]),
            reasoning=row["reasoning"] or "",
            suggested_answer=row["suggested_answer"] or "",
            confidence=row["confidence"] or 0.0,
        )
        review = ReviewInfo(
            needs_review=bool(row["needs_review"]),
            reasons=json.loads(row["flag_reasons"]) if row["flag_reasons"] else [],
            review_status=row["review_status"] or "pending",
            human_score=row["human_score"],
            review_note=row["review_note"],
            reviewed_at=row["reviewed_at"],
        )
        return FeedbackRecord(db_id=row["id"], feedback=feedback, review=review)

    def _row_to_student_record(self, row: sqlite3.Row) -> StudentRecord:
        identity = StudentIdentity(
            name=row["name"],
            student_id=row["student_id"],
            class_name=row["class_name"],
            identity_confidence=row["identity_confidence"] if row["identity_confidence"] is not None else 1.0,
        )
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM question_feedback WHERE student_id = ? ORDER BY id", (row["id"],))
        feedback = [self._row_to_feedback_record(r) for r in cur.fetchall()]
        return StudentRecord(
            db_id=row["id"], exam_id=row["exam_id"], identity=identity,
            source_path=row["source_path"], graded_at=row["graded_at"] or "", feedback=feedback,
        )

    def list_exams(self, search: str | None = None) -> list[ExamSummary]:
        cur = self._conn.cursor()
        if search:
            cur.execute(
                "SELECT * FROM exams WHERE title LIKE ? ORDER BY created_at DESC",
                (f"%{search}%",),
            )
        else:
            cur.execute("SELECT * FROM exams ORDER BY created_at DESC")
        exams = cur.fetchall()

        summaries: list[ExamSummary] = []
        for exam in exams:
            cur.execute("SELECT id FROM students WHERE exam_id = ?", (exam["id"],))
            student_ids = [r["id"] for r in cur.fetchall()]
            if not student_ids:
                summaries.append(ExamSummary(
                    id=exam["id"], title=exam["title"], language=exam["language"] or "auto",
                    strictness=exam["strictness"], created_at=exam["created_at"],
                    student_count=0, average_pct=0.0, pass_rate_pct=0.0, pending_review_count=0,
                ))
                continue

            percentages = []
            pending = 0
            for sid in student_ids:
                cur.execute(
                    "SELECT score, max_score, human_score, needs_review, review_status "
                    "FROM question_feedback WHERE student_id = ?", (sid,),
                )
                rows = cur.fetchall()
                total = sum((r["human_score"] if r["human_score"] is not None else r["score"]) for r in rows)
                maxt = sum(r["max_score"] for r in rows)
                percentages.append(round(100 * total / maxt, 2) if maxt else 0.0)
                if any(r["needs_review"] and r["review_status"] == "pending" for r in rows):
                    pending += 1
            avg = round(sum(percentages) / len(percentages), 2) if percentages else 0.0
            pass_rate = round(100 * sum(1 for p in percentages if p >= 60.0) / len(percentages), 2) if percentages else 0.0

            summaries.append(ExamSummary(
                id=exam["id"], title=exam["title"], language=exam["language"] or "auto",
                strictness=exam["strictness"], created_at=exam["created_at"],
                student_count=len(student_ids), average_pct=avg, pass_rate_pct=pass_rate,
                pending_review_count=pending,
            ))
        return summaries

    def get_exam_detail(self, exam_id: int) -> ExamDetail | None:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        exam = cur.fetchone()
        if exam is None:
            return None

        cur.execute("SELECT * FROM questions WHERE exam_id = ? ORDER BY id", (exam_id,))
        questions = [
            Question(number=r["number"], text=r["text"] or "", official_answer=r["official_answer"] or "",
                      max_score=r["max_score"])
            for r in cur.fetchall()
        ]

        cur.execute("SELECT * FROM students WHERE exam_id = ? ORDER BY id", (exam_id,))
        students = [self._row_to_student_record(r) for r in cur.fetchall()]

        return ExamDetail(
            id=exam["id"], title=exam["title"], language=exam["language"] or "auto",
            strictness=exam["strictness"], created_at=exam["created_at"],
            questions=questions, students=students,
            description=(exam["description"] if "description" in exam.keys() else "") or "",
        )

    def delete_exam(self, exam_id: int) -> None:
        self._conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        self._conn.commit()

    @staticmethod
    def _student_key(name: str | None, student_id: str | None) -> str:
        if student_id:
            return f"id:{student_id}"
        return f"name:{(name or 'unknown').strip().lower()}"

    def list_all_students(self) -> list[StudentSummary]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT s.id, s.name, s.student_id, s.graded_at, e.title AS exam_title, e.created_at "
            "FROM students s JOIN exams e ON s.exam_id = e.id ORDER BY e.created_at DESC"
        )
        rows = cur.fetchall()

        grouped: dict[str, list[sqlite3.Row]] = {}
        for r in rows:
            key = self._student_key(r["name"], r["student_id"])
            grouped.setdefault(key, []).append(r)

        summaries = []
        for key, group in grouped.items():
            percentages = []
            for r in group:
                cur.execute(
                    "SELECT score, max_score, human_score FROM question_feedback WHERE student_id = ?",
                    (r["id"],),
                )
                fb_rows = cur.fetchall()
                total = sum((f["human_score"] if f["human_score"] is not None else f["score"]) for f in fb_rows)
                maxt = sum(f["max_score"] for f in fb_rows)
                percentages.append(round(100 * total / maxt, 2) if maxt else 0.0)

            latest = group[0]  # ordered by created_at DESC
            summaries.append(StudentSummary(
                key=key, name=latest["name"] or "(unnamed)", student_id=latest["student_id"],
                exams_taken=len(group),
                average_pct=round(sum(percentages) / len(percentages), 2) if percentages else 0.0,
                last_exam_title=latest["exam_title"], last_graded_at=latest["graded_at"] or "",
            ))
        summaries.sort(key=lambda s: s.name.lower())
        return summaries

    def get_student_history(self, key: str) -> list[StudentRecord]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT s.* FROM students s "
            "WHERE (s.student_id IS NOT NULL AND s.student_id != '' AND ('id:' || s.student_id) = ?) "
            "   OR (('name:' || LOWER(TRIM(COALESCE(s.name, 'unknown')))) = ?) "
            "ORDER BY s.id",
            (key, key),
        )
        rows = cur.fetchall()
        return [self._row_to_student_record(r) for r in rows]

    def list_review_items(
        self, exam_id: int | None = None, reason: str | None = None,
        status: str = "pending", search: str | None = None,
    ) -> list[ReviewItem]:
        cur = self._conn.cursor()
        query = (
            "SELECT qf.*, s.name AS student_name, s.exam_id AS exam_id, "
            "e.title AS exam_title "
            "FROM question_feedback qf "
            "JOIN students s ON qf.student_id = s.id "
            "JOIN exams e ON s.exam_id = e.id "
            "WHERE qf.needs_review = 1"
        )
        params: list = []
        if status != "all":
            query += " AND qf.review_status = ?"
            params.append(status)
        if exam_id is not None:
            query += " AND s.exam_id = ?"
            params.append(exam_id)
        if search:
            query += " AND (s.name LIKE ? OR e.title LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY qf.id DESC"

        cur.execute(query, params)
        items = []
        for r in cur.fetchall():
            reasons = json.loads(r["flag_reasons"]) if r["flag_reasons"] else []
            if reason and reason not in reasons:
                continue
            items.append(ReviewItem(
                feedback_db_id=r["id"], exam_id=r["exam_id"], exam_title=r["exam_title"],
                student_db_id=r["student_id"], student_name=r["student_name"] or "(unnamed)",
                question_number=r["question_number"], reasons=reasons,
                score=r["score"], max_score=r["max_score"], similarity=r["similarity"] or 0.0,
                coverage=r["coverage"] or 0.0, confidence=r["confidence"] or 0.0,
                contradictions_detected=bool(r["contradictions_detected"]),
                missing_concepts=json.loads(r["missing_concepts"] or "[]"),
                reasoning=r["reasoning"] or "", review_status=r["review_status"] or "pending",
                human_score=r["human_score"], review_note=r["review_note"],
            ))
        return items

    def dashboard_stats(self) -> DashboardStats:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM exams")
        total_exams = cur.fetchone()[0]
        cur.execute("SELECT id FROM students")
        student_ids = [r["id"] for r in cur.fetchall()]

        percentages = []
        for sid in student_ids:
            cur.execute(
                "SELECT score, max_score, human_score FROM question_feedback WHERE student_id = ?", (sid,),
            )
            rows = cur.fetchall()
            total = sum((r["human_score"] if r["human_score"] is not None else r["score"]) for r in rows)
            maxt = sum(r["max_score"] for r in rows)
            percentages.append(round(100 * total / maxt, 2) if maxt else 0.0)

        avg = round(sum(percentages) / len(percentages), 2) if percentages else 0.0
        pass_rate = round(100 * sum(1 for p in percentages if p >= 60.0) / len(percentages), 2) if percentages else 0.0

        histogram: dict[str, int] = {}
        for p in percentages:
            lo = int(p // 10) * 10
            hi = min(lo + 10, 100)
            label = f"{lo}-{hi}"
            histogram[label] = histogram.get(label, 0) + 1
        histogram = dict(sorted(histogram.items(), key=lambda kv: int(kv[0].split("-")[0])))

        return DashboardStats(
            total_exams=total_exams, total_students=len(student_ids), average_pct=avg,
            pass_rate_pct=pass_rate, pending_review_count=self.count_pending_review(), histogram=histogram,
        )

    def hardest_questions(self, limit: int = 5) -> list[tuple[str, str, float]]:
        """Returns (exam_title, question_number, average_pct), lowest first."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT e.title AS exam_title, qf.question_number, "
            "AVG(CASE WHEN qf.max_score > 0 THEN 100.0 * COALESCE(qf.human_score, qf.score) / qf.max_score ELSE 0 END) AS avg_pct "
            "FROM question_feedback qf "
            "JOIN students s ON qf.student_id = s.id "
            "JOIN exams e ON s.exam_id = e.id "
            "GROUP BY s.exam_id, qf.question_number "
            "ORDER BY avg_pct ASC LIMIT ?",
            (limit,),
        )
        return [(r["exam_title"], r["question_number"], round(r["avg_pct"], 1)) for r in cur.fetchall()]

    def count_pending_review(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM question_feedback WHERE needs_review = 1 AND review_status = 'pending'")
        return cur.fetchone()[0]

    def update_review(
        self, feedback_db_id: int, status: str,
        human_score: float | None = None, note: str | None = None,
    ) -> None:
        """status: 'accepted' (keep AI score, mark reviewed) or 'adjusted'
        (teacher supplied human_score). The original AI score/reasoning is
        never overwritten -- human_score is a separate column."""
        self._conn.execute(
            "UPDATE question_feedback SET review_status = ?, human_score = ?, "
            "review_note = ?, reviewed_at = ? WHERE id = ?",
            (status, human_score, note, _utcnow_iso(), feedback_db_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # App settings (flat key/value store; see src/config/settings.py)
    # ------------------------------------------------------------------

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        cur = self._conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
