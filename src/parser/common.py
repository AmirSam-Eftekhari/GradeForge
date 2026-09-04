"""
Question-boundary and score detection.

Real answer sheets are inconsistent ("Question 1 (3 points)", "Q3 - 2
Marks", "2) [5]", "Score: 4" on its own line, etc.) so detection is done
with a small library of patterns tried in order rather than one clever
regex — this keeps each pattern testable and lets new formats be added
without touching the others.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Two patterns, tried in order:
#   A) explicit "Q"/"Question" prefix — punctuation after the number is
#      optional, since answer keys often write "Question 1 (3 points)"
#      with no colon/period between the number and the score.
#   B) a bare leading number — punctuation right after the number is
#      REQUIRED here ("1)", "2.", "3:", "3-") so that a body sentence
#      which merely starts with a number ("1990 was a pivotal year...")
#      is never mistaken for a question header.
_QUESTION_HEADER_PREFIXED_RE = re.compile(
    r"^\s*Q(?:uestion)?\.?\s*(\d{1,3}[a-zA-Z]?)\s*[\.\)\:\-]?\s*(.*)$",
    re.IGNORECASE,
)
_QUESTION_HEADER_BARE_RE = re.compile(
    r"^\s*(\d{1,3}[a-zA-Z]?)\s*[\.\)\:\-]\s*(.*)$",
)


def _match_question_header(line: str) -> re.Match | None:
    return _QUESTION_HEADER_PREFIXED_RE.match(line) or _QUESTION_HEADER_BARE_RE.match(line)

# Score patterns, tried in order against the header line and the following
# ~2 lines. Group 1 is always the numeric max score.
_SCORE_PATTERNS = [
    re.compile(r"\((\d+(?:\.\d+)?)\s*(?:points?|pts?|marks?)\)", re.IGNORECASE),
    re.compile(r"\[(\d+(?:\.\d+)?)\]"),
    re.compile(r"-\s*(\d+(?:\.\d+)?)\s*(?:marks?|points?|pts?)\b", re.IGNORECASE),
    re.compile(r"\bscore\s*:?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE),
    re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:points?|pts?|marks?)\b", re.IGNORECASE),
]

_ANSWER_MARKER_RE = re.compile(r"^\s*(?:Answer|Official Answer|Model Answer|Ans\.?)\s*:\s*(.*)$", re.IGNORECASE)


@dataclass
class QuestionBlock:
    number: str
    header_line: str
    body_lines: list[str]


def extract_score(*lines: str) -> float | None:
    for line in lines:
        for pattern in _SCORE_PATTERNS:
            m = pattern.search(line)
            if m:
                return float(m.group(1))
    return None


def split_into_question_blocks(text: str) -> list[QuestionBlock]:
    """Split raw document text into one block per detected question number.

    See `_match_question_header` for exactly what counts as a header line.
    """
    lines = text.splitlines()
    blocks: list[QuestionBlock] = []
    current: QuestionBlock | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        m = _match_question_header(line)
        if m:
            if current is not None:
                blocks.append(current)
            current = QuestionBlock(number=m.group(1), header_line=line, body_lines=[])
            remainder = m.group(2).strip()
            if remainder:
                current.body_lines.append(remainder)
        elif current is not None:
            current.body_lines.append(line)

    if current is not None:
        blocks.append(current)
    return blocks


def split_question_and_answer(body_lines: list[str]) -> tuple[str, str]:
    """Within a question block, split question text from the official/
    student answer using an 'Answer:' style marker if present; otherwise
    treat the whole block as answer text (used for student papers, which
    rarely restate the question)."""
    for i, line in enumerate(body_lines):
        m = _ANSWER_MARKER_RE.match(line)
        if m:
            question_text = " ".join(body_lines[:i]).strip()
            answer_text = " ".join([m.group(1)] + body_lines[i + 1:]).strip()
            return question_text, answer_text
    return " ".join(body_lines).strip(), ""
