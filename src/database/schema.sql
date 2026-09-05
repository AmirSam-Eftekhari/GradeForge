-- Exam Grader database schema.
-- Kept intentionally normalized and small: this app's real "source of
-- truth" documents are the generated PDFs/JSON per student; SQLite here
-- exists to power the dashboard's cross-exam analytics and history,
-- not as the only copy of any grading decision.

CREATE TABLE IF NOT EXISTS exams (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    language      TEXT,
    strictness    TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id       INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    number        TEXT NOT NULL,
    text          TEXT,
    official_answer TEXT,
    max_score     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id       INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    name          TEXT,
    student_id    TEXT,
    class_name    TEXT,
    identity_confidence REAL,
    source_path   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    question_number TEXT NOT NULL,
    score           REAL NOT NULL,
    max_score       REAL NOT NULL,
    similarity      REAL,
    coverage        REAL,
    missing_concepts TEXT,     -- JSON-encoded list
    incorrect_concepts TEXT,   -- JSON-encoded list
    contradictions_detected INTEGER,
    reasoning       TEXT,
    suggested_answer TEXT,
    confidence      REAL
);

CREATE INDEX IF NOT EXISTS idx_students_exam ON students(exam_id);
CREATE INDEX IF NOT EXISTS idx_feedback_student ON question_feedback(student_id);

-- Application settings (GradeForge desktop UI). Kept as a flat key/value
-- store, mirroring src/config/settings.py's dataclasses, so the Settings
-- screen doesn't need its own schema migrations every time a new option
-- is added.
CREATE TABLE IF NOT EXISTS app_settings (
    key           TEXT PRIMARY KEY,
    value         TEXT NOT NULL
);
