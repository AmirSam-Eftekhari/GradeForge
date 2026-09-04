"""
Grading strictness policy.

Design principle (per product spec): the scoring policy must be TRANSPARENT,
not a black box of arbitrary thresholds. Every strictness level is defined by
three explicit, tunable parameters that plug into the same scoring formula
(see grading/policy.py):

    coverage_weight        -> how much of the score tracks semantic coverage
                               of required concepts in the official answer
    full_credit_coverage   -> the coverage level (0-1) at which a fully
                               correct, non-contradictory answer earns 100%
    contradiction_penalty  -> multiplier applied per detected contradiction
                               with the official answer
    grammar_sensitive      -> whether surface-level fluency is allowed to
                               affect the score at all (per spec: grammar
                               should not matter, ever, in this system)

Because every level shares one formula, a school administrator can see
exactly why a 3-point slider move changed a given student's score, rather
than being told "the AI decided."
"""

from dataclasses import dataclass
from enum import Enum


class StrictnessLevel(str, Enum):
    VERY_LENIENT = "very_lenient"
    LENIENT = "lenient"
    BALANCED = "balanced"
    STRICT = "strict"
    VERY_STRICT = "very_strict"


@dataclass(frozen=True)
class StrictnessPolicy:
    level: StrictnessLevel
    full_credit_coverage: float      # coverage needed for 100% credit
    partial_credit_floor: float      # coverage below which score floors near 0
    contradiction_penalty: float     # score multiplier per contradiction (0-1)
    omission_penalty_weight: float   # how harshly missing concepts count
    min_similarity_for_any_credit: float  # below this, treated as non-attempt


POLICIES: dict[StrictnessLevel, StrictnessPolicy] = {
    StrictnessLevel.VERY_LENIENT: StrictnessPolicy(
        level=StrictnessLevel.VERY_LENIENT,
        full_credit_coverage=0.50,
        partial_credit_floor=0.15,
        contradiction_penalty=0.85,
        omission_penalty_weight=0.4,
        min_similarity_for_any_credit=0.20,
    ),
    StrictnessLevel.LENIENT: StrictnessPolicy(
        level=StrictnessLevel.LENIENT,
        full_credit_coverage=0.65,
        partial_credit_floor=0.20,
        contradiction_penalty=0.75,
        omission_penalty_weight=0.6,
        min_similarity_for_any_credit=0.25,
    ),
    StrictnessLevel.BALANCED: StrictnessPolicy(
        level=StrictnessLevel.BALANCED,
        full_credit_coverage=0.80,
        partial_credit_floor=0.25,
        contradiction_penalty=0.60,
        omission_penalty_weight=0.85,
        min_similarity_for_any_credit=0.30,
    ),
    StrictnessLevel.STRICT: StrictnessPolicy(
        level=StrictnessLevel.STRICT,
        full_credit_coverage=0.85,
        partial_credit_floor=0.35,
        contradiction_penalty=0.45,
        omission_penalty_weight=1.0,
        min_similarity_for_any_credit=0.35,
    ),
    StrictnessLevel.VERY_STRICT: StrictnessPolicy(
        level=StrictnessLevel.VERY_STRICT,
        full_credit_coverage=0.92,
        partial_credit_floor=0.45,
        contradiction_penalty=0.25,
        omission_penalty_weight=1.2,
        min_similarity_for_any_credit=0.40,
    ),
}


def get_policy(level: StrictnessLevel | str) -> StrictnessPolicy:
    if isinstance(level, str):
        level = StrictnessLevel(level)
    return POLICIES[level]
