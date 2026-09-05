"""
Embedding backend abstraction.

The grading engine never imports torch/sentence-transformers directly —
it only depends on the `EmbeddingBackend` interface below. This is what
lets the whole application run (in a degraded but honest mode) on a
machine that has no GPU and no internet access, while still being a
one-line config change (`EmbeddingConfig.backend = "sentence_transformer"`)
away from state-of-the-art multilingual semantic grading once
`sentence-transformers` + a model like `intfloat/multilingual-e5-large`
or `BAAI/bge-m3` is installed.

get_backend() auto-selects the best available backend and logs which
one it picked, so nobody is silently graded by a weaker model.
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class EmbeddingBackend(ABC):
    name: str = "base"

    @abstractmethod
    def similarity(self, text_a: str, text_b: str) -> float:
        """Return semantic similarity in [0, 1]."""

    def similarity_many(self, text: str, candidates: list[str]) -> list[float]:
        return [self.similarity(text, c) for c in candidates]


class SentenceTransformerBackend(EmbeddingBackend):
    """
    True multilingual semantic-embedding backend. Requires:
        pip install sentence-transformers torch

    Recommended models (per product spec): 'intfloat/multilingual-e5-large'
    or 'BAAI/bge-m3'. Both support 100+ languages without translation.

    `model_name` accepts either a HuggingFace model ID (needs internet on
    first use; cached by the library afterward) or a local folder path
    (see download_model.py) -- a local folder is detected automatically
    and loaded with zero network calls, including the "check for
    updates" request some hub versions otherwise make even when a model
    is already cached.
    """

    name = "sentence_transformer"

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        from sentence_transformers import SentenceTransformer, util  # deferred import

        local_path = Path(model_name).expanduser()
        if local_path.exists():
            # A pre-downloaded model folder -- never touch the network,
            # not even to check for a newer revision of a cached model.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            logger.info("Loading semantic model from local folder (offline): %s", local_path)
            model_name = str(local_path)

        self._model = SentenceTransformer(model_name)
        self._util = util
        self.model_name = model_name

    def similarity(self, text_a: str, text_b: str) -> float:
        emb = self._model.encode([text_a, text_b], normalize_embeddings=True)
        score = float(self._util.cos_sim(emb[0], emb[1])[0][0])
        return max(0.0, min(1.0, (score + 1) / 2 if score < 0 else score))


class TFIDFBackend(EmbeddingBackend):
    """
    Offline fallback used automatically when no embedding model / no
    network access is available. This is NOT the shipped product
    behavior — it is a transparent degraded mode so the pipeline is
    still testable and useful offline. It uses character n-gram TF-IDF
    (not word n-grams) specifically because it degrades more gracefully
    across languages with different morphology (Persian, Arabic, CJK)
    than a pure bag-of-words model would.
    """

    name = "tfidf_fallback"

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer_cls = TfidfVectorizer
        logger.warning(
            "Using offline TF-IDF fallback embedding backend — this is a "
            "reduced-accuracy substitute for the multilingual transformer "
            "backend and should not be used for real grading decisions."
        )

    # Empirically, character n-gram cosine similarity between two
    # *independently worded* passages that mean the same thing tends to
    # land around 0.25-0.45, while genuinely unrelated passages land
    # around 0.05-0.15 (near-identical text approaches ~1.0 but students
    # essentially never submit verbatim-identical answers). These anchors
    # rescale the raw score onto the same rough [0,1] "semantic similarity"
    # scale the strictness policies are calibrated against — this does NOT
    # make the fallback semantically aware, it only keeps its output on a
    # comparable scale to a real embedding backend's output.
    _CALIBRATION_FLOOR = 0.05
    _CALIBRATION_CEILING = 0.50

    def similarity(self, text_a: str, text_b: str) -> float:
        from sklearn.metrics.pairwise import cosine_similarity

        a = text_a.strip()
        b = text_b.strip()
        if not a or not b:
            return 0.0
        vectorizer = self._vectorizer_cls(analyzer="char_wb", ngram_range=(2, 4))
        try:
            matrix = vectorizer.fit_transform([a, b])
        except ValueError:
            return 0.0
        raw = float(cosine_similarity(matrix[0], matrix[1])[0][0])
        calibrated = (raw - self._CALIBRATION_FLOOR) / (self._CALIBRATION_CEILING - self._CALIBRATION_FLOOR)
        return max(0.0, min(1.0, calibrated))


def is_sentence_transformer_available() -> bool:
    """Capability probe used by the UI to show AI/model status without
    actually importing (and thus loading/downloading) a model."""
    import importlib.util

    return importlib.util.find_spec("sentence_transformers") is not None and importlib.util.find_spec("torch") is not None


def get_backend(preference: str = "auto", model_name: str = "intfloat/multilingual-e5-large") -> EmbeddingBackend:
    if preference in ("auto", "sentence_transformer"):
        try:
            return SentenceTransformerBackend(model_name=model_name)
        except ImportError:
            if preference == "sentence_transformer":
                raise
            logger.warning(
                "sentence-transformers/torch not installed — falling back "
                "to offline TF-IDF backend. Install `sentence-transformers` "
                "and `torch` for production-grade multilingual grading."
            )
    return TFIDFBackend()


_NEGATION_MARKERS = [
    r"\bnot\b", r"\bno\b", r"\bnever\b", r"n't\b", r"\bcannot\b",
    r"\u0646\u06cc\u0633\u062a", r"\u0646\u0645\u06cc", r"\u0647\u0631\u06af\u0632",  # nist / nemi / hargez (fa)
]
_NEGATION_RE = re.compile("|".join(_NEGATION_MARKERS), re.IGNORECASE)


def has_negation(text: str) -> bool:
    return bool(_NEGATION_RE.search(text))


def detect_contradiction(official_concept: str, student_text: str, backend: EmbeddingBackend, lexical_overlap_threshold: float = 0.35) -> bool:
    """
    Heuristic contradiction flag: high lexical/semantic overlap (so we know
    the student is talking about the same concept) combined with a mismatch
    in negation polarity between the two texts.

    This is intentionally conservative and explainable rather than a black
    box. Production deployments should replace this with a proper
    cross-lingual NLI model (e.g. an mDeBERTa-v3 NLI checkpoint) for higher
    recall on subtler contradictions — swap the implementation here without
    touching any caller.
    """
    overlap = backend.similarity(official_concept, student_text)
    if overlap < lexical_overlap_threshold:
        return False
    return has_negation(official_concept) != has_negation(student_text)
