"""
Language detection.

Production deployments should install `langdetect` or `fasttext`'s
lid.176 model for high-accuracy detection across 170+ languages — swap
it in by replacing `detect_language` below, the rest of the pipeline
only depends on this function's signature (str -> str ISO code).

This module ships a dependency-free Unicode-block heuristic so the
application still runs (and correctly separates at least Latin /
Persian-Arabic / CJK / Cyrillic / Devanagari script papers) in
environments where downloading a language-ID model isn't possible.
"""

from __future__ import annotations

import re

_SCRIPT_RANGES: list[tuple[str, tuple[int, int]]] = [
    ("fas", (0x0600, 0x06FF)),   # Arabic + Persian share this block; refined below
    ("zho", (0x4E00, 0x9FFF)),   # CJK unified ideographs
    ("jpn", (0x3040, 0x30FF)),   # Hiragana/Katakana
    ("kor", (0xAC00, 0xD7A3)),   # Hangul syllables
    ("rus", (0x0400, 0x04FF)),   # Cyrillic
    ("hin", (0x0900, 0x097F)),   # Devanagari
]

# Persian-only letters absent from standard Arabic (پ چ ژ گ)
_PERSIAN_MARKERS = {"\u067e", "\u0686", "\u0698", "\u06af"}


def detect_language(text: str) -> str:
    """Return a best-effort ISO 639-2-ish code. Falls back to 'eng'."""
    if not text or not text.strip():
        return "eng"

    counts: dict[str, int] = {}
    persian_hits = 0
    for ch in text:
        cp = ord(ch)
        if ch in _PERSIAN_MARKERS:
            persian_hits += 1
        for code, (lo, hi) in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break

    if not counts:
        return "eng"

    top = max(counts, key=counts.get)
    if top == "fas":
        # Arabic block matched; disambiguate Persian vs Arabic proper.
        return "fas" if persian_hits > 0 else "ara"
    return top


def is_rtl(language_code: str) -> bool:
    return language_code in {"fas", "ara", "urd", "heb"}
