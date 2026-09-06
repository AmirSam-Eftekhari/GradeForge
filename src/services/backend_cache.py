"""
The actual fix for "grading feels slow to start every time": before this,
GradingWorker constructed a fresh EmbeddingBackend on every run, so a
sentence-transformers model got reloaded from disk from scratch on every
single "Start Grading" click -- the spec's performance section explicitly
calls this out ("do not reload the embedding model for every student";
"initialized once per grading session/application lifecycle where
appropriate"). This module is that cache.

Thread-safe: a background prewarm (see GradingExecutionPage/wizard) and
the grading thread itself can both call get_cached_backend() -- the lock
makes the second caller simply wait for the first construction to finish
and reuse the same instance, instead of loading the model twice.
"""

from __future__ import annotations

import threading

from src.ai.embedding_backend import EmbeddingBackend, get_backend

_lock = threading.Lock()
_cache: dict[tuple[str, str], EmbeddingBackend] = {}


def get_cached_backend(preference: str, model_name: str) -> EmbeddingBackend:
    key = (preference, model_name)
    with _lock:
        if key not in _cache:
            _cache[key] = get_backend(preference=preference, model_name=model_name)
        return _cache[key]


def clear_cache() -> None:
    """Called when the person changes the AI backend/model in Settings,
    so the next grading run picks up the new choice instead of reusing
    a stale cached one."""
    with _lock:
        _cache.clear()
