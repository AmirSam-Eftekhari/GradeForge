from __future__ import annotations

import re

from src.models.domain import StudentAnswer, StudentIdentity, StudentPaper
from src.parser.common import split_into_question_blocks, split_question_and_answer

# Bilingual (+ a few common languages) identity field labels. Extend this
# list as new deployments surface new label conventions.
_NAME_LABELS = r"(?:Student Name|Full Name|Student|Name|\u0646\u0627\u0645|\u0646\u0627\u0645 \u0648 \u0646\u0627\u0645 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc)"
_ID_LABELS = r"(?:Student ID|ID No\.?|ID|\u0634\u0645\u0627\u0631\u0647 \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u06cc)"
_CLASS_LABELS = r"(?:Class|Grade|Section|\u06a9\u0644\u0627\u0633)"

_NAME_RE = re.compile(rf"^\s*{_NAME_LABELS}\s*[:\-]\s*(.+)$", re.IGNORECASE)
_ID_RE = re.compile(rf"^\s*{_ID_LABELS}\s*[:\-]\s*(.+)$", re.IGNORECASE)
_CLASS_RE = re.compile(rf"^\s*{_CLASS_LABELS}\s*[:\-]\s*(.+)$", re.IGNORECASE)

_HEADER_SCAN_LINES = 12  # identity block is expected near the top of page 1


def extract_identity(raw_text: str, ocr_confidence: float = 1.0) -> StudentIdentity:
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()][:_HEADER_SCAN_LINES]

    name, student_id, class_name = None, None, None
    for line in lines:
        if name is None and (m := _NAME_RE.match(line)):
            name = m.group(1).strip()
        elif student_id is None and (m := _ID_RE.match(line)):
            student_id = m.group(1).strip()
        elif class_name is None and (m := _CLASS_RE.match(line)):
            class_name = m.group(1).strip()

    confidence = ocr_confidence
    if name is None and lines:
        # No explicit "Name:" label found — fall back to the first header
        # line, but mark it low-confidence so the UI asks for confirmation
        # (per spec: "If OCR confidence is low, ask for confirmation").
        name = lines[0]
        confidence = min(confidence, 0.45)

    return StudentIdentity(
        name=name,
        student_id=student_id,
        class_name=class_name,
        identity_confidence=confidence,
    )


def parse_student_paper(raw_text: str, source_path: str, ocr_confidence: float = 1.0) -> StudentPaper:
    identity = extract_identity(raw_text, ocr_confidence=ocr_confidence)
    blocks = split_into_question_blocks(raw_text)

    answers: list[StudentAnswer] = []
    for block in blocks:
        _, answer_text = split_question_and_answer(block.body_lines)
        if not answer_text:
            answer_text = " ".join(block.body_lines).strip()
        if answer_text:
            answers.append(
                StudentAnswer(
                    question_number=block.number,
                    raw_text=answer_text,
                    ocr_confidence=ocr_confidence,
                )
            )

    return StudentPaper(source_path=source_path, identity=identity, answers=answers)
