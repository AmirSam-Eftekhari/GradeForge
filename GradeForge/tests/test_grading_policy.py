import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.embedding_backend import TFIDFBackend
from src.config.strictness import StrictnessLevel, get_policy
from src.grading.policy import score_answer, split_concepts
from src.models.domain import Question


def make_question():
    return Question(
        number="1",
        text="What is photosynthesis?",
        official_answer=(
            "Photosynthesis converts light energy into chemical energy. "
            "It uses carbon dioxide and water as inputs. "
            "It produces glucose and oxygen as outputs."
        ),
        max_score=3.0,
    )


def test_split_concepts_splits_on_sentence_boundaries():
    concepts = split_concepts(make_question().official_answer)
    assert len(concepts) == 3


def test_full_correct_answer_scores_near_max_on_balanced():
    q = make_question()
    backend = TFIDFBackend()
    policy = get_policy(StrictnessLevel.BALANCED)
    fb = score_answer(q, q.official_answer, backend, policy)
    assert fb.score >= q.max_score * 0.9


def test_empty_answer_scores_zero():
    q = make_question()
    backend = TFIDFBackend()
    policy = get_policy(StrictnessLevel.BALANCED)
    fb = score_answer(q, "", backend, policy)
    assert fb.score == 0.0
    assert "No answer" in fb.reasoning


def test_irrelevant_answer_scores_zero():
    q = make_question()
    backend = TFIDFBackend()
    policy = get_policy(StrictnessLevel.BALANCED)
    fb = score_answer(q, "The French Revolution began in 1789 in Paris.", backend, policy)
    assert fb.score == 0.0


def test_very_strict_is_harsher_than_very_lenient_on_partial_answer():
    q = make_question()
    backend = TFIDFBackend()
    partial = "Photosynthesis converts light energy into chemical energy."

    lenient_fb = score_answer(q, partial, backend, get_policy(StrictnessLevel.VERY_LENIENT))
    strict_fb = score_answer(q, partial, backend, get_policy(StrictnessLevel.VERY_STRICT))

    assert strict_fb.score <= lenient_fb.score


def test_contradiction_reduces_score():
    q = make_question()
    backend = TFIDFBackend()
    policy = get_policy(StrictnessLevel.BALANCED)
    contradicting = (
        "Photosynthesis does not convert light energy into chemical energy. "
        "It uses carbon dioxide and water as inputs. "
        "It produces glucose and oxygen as outputs."
    )
    fb_with = score_answer(q, contradicting, backend, policy, enable_contradiction_detection=True)
    fb_without = score_answer(q, contradicting, backend, policy, enable_contradiction_detection=False)
    assert fb_with.score <= fb_without.score
