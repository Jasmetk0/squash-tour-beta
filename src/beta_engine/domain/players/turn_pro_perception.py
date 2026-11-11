"""Master v87 Turn Pro: what a prospect's AI knows about itself (pure, deterministic).

Owner direction (11 November 2026): the weekly Turn Pro decision must not read
hidden true strength of opponents, and a player estimates even their own
attributes imperfectly. This module turns a player's true attributes into a
*self-perception* the player AI may use:

* every one of the 57 attributes is perceived, so a player usually knows that
  their forehand is stronger than their backhand or that endurance is a strength;
* the error has three layers: an overall level (largest, biased by
  ``Confidence``), an attribute group, and the single attribute (smallest), so
  relative comparisons are far more reliable than the absolute level;
* better self-reflection (``Analysis`` and ``Self Control``) shrinks the error,
  a player knows their strongest group better, and some groups are harder to
  judge than others;
* background (``Financial Level``) is part of the record but is explicitly
  unknown until the engine models it, and then has no effect.

Readiness compares the perceived overall level with a fixed professional
threshold stored in the policy, never with other players' hidden strength.

Randomness: hashed standard normals. Persistent components (the player's own
tendencies) are keyed only by Run, player and policy, so they are identical in
every week and in every fork; the small weekly fluctuation is keyed by the
command seed and the target week. Processing order never matters.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.attribute_catalog import (
    ATTRIBUTE_TO_GROUP,
    CANONICAL_PLAYER_ATTRIBUTES,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash

ATTRIBUTE_GROUPS = tuple(dict.fromkeys(ATTRIBUTE_TO_GROUP[a] for a in CANONICAL_PLAYER_ATTRIBUTES))
REFLECTION_ATTRIBUTES = ("Analysis", "Self Control")
CONFIDENCE_ATTRIBUTE = "Confidence"


class SelfPerceptionPolicy(FrozenInput):
    """Versioned, fingerprinted calibration; recorded with every model use."""

    schema_version: Literal["turn_pro_self_perception.v1"] = "turn_pro_self_perception.v1"
    model_id: str = Field(min_length=1)
    # Standard deviations on the 0-200 attribute scale before the accuracy factor.
    level_error_sd: float = Field(ge=0)
    group_error_sd: tuple[tuple[str, float], ...]
    attribute_error_sd: float = Field(ge=0)
    weekly_error_sd: float = Field(ge=0)
    # Bias of the whole level per Confidence point away from 100 (the scale mid).
    confidence_bias_per_point: float = Field(ge=0)
    # Accuracy factor = max_factor - (max_factor - min_factor) * reflection / 200.
    min_accuracy_factor: float = Field(gt=0)
    max_accuracy_factor: float = Field(gt=0)
    strongest_group_factor: float = Field(gt=0, le=1)
    # Readiness = logistic((perceived overall - threshold) / scale).
    professional_threshold: float = Field(ge=0, le=200)
    readiness_scale: float = Field(gt=0)
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_groups(self):
        names = tuple(name for name, _ in self.group_error_sd)
        if names != ATTRIBUTE_GROUPS or any(sd < 0 for _, sd in self.group_error_sd):
            raise ValueError("Self-perception needs a non-negative error for every group")
        if self.min_accuracy_factor > self.max_accuracy_factor:
            raise ValueError("Self-perception accuracy factors are inverted")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def default_self_perception_policy() -> SelfPerceptionPolicy:
    """Provisional pre-alpha calibration; tune by testing."""
    return SelfPerceptionPolicy(
        model_id="pre-alpha-self-perception.v1",
        # Generated OVR medians (0-200 scale): age 15 ~78, 18 ~103, pros 24-30
        # ~140-150. The threshold is roughly a typical 18-year-old.
        level_error_sd=10.0,
        group_error_sd=tuple(
            (group, {"Physical": 5.0, "Move": 5.0, "Technical": 7.0}.get(group, 10.0))
            for group in ATTRIBUTE_GROUPS
        ),
        attribute_error_sd=4.0,
        weekly_error_sd=2.0,
        confidence_bias_per_point=0.12,
        min_accuracy_factor=0.6,
        max_accuracy_factor=1.4,
        strongest_group_factor=0.6,
        professional_threshold=100.0,
        readiness_scale=12.0,
        provenance=(
            "Provisional owner-directed self-perception (Master v87, 11 Nov 2026); "
            "calibration to be tuned"
        ),
    )


class TurnProObservation(FrozenInput):
    """What one prospect's AI knew about itself at a Week Transition."""

    schema_version: Literal["turn_pro_observation.v1"] = "turn_pro_observation.v1"
    player_id: str = Field(min_length=1)
    source: Literal["self_perception.v1"] = "self_perception.v1"
    perceived_overall: float
    perceived_groups: tuple[tuple[str, float], ...]
    # Every canonical attribute as the player perceives it (relative self-knowledge).
    perceived_attributes: tuple[tuple[str, float], ...]
    # Master 19.2 Financial Level is not modelled yet: explicitly unknown.
    financial_level: int | None = Field(default=None, ge=0, le=10)
    # Own personality is self-known; None when the source has no traits.
    ambition: float | None = Field(default=None, ge=0, le=1)
    professionalism: float | None = Field(default=None, ge=0, le=1)
    readiness: float = Field(ge=0, le=1)
    policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def _normal(*key) -> float:
    """Deterministic standard normal from a hashed key (Box-Muller)."""
    digest = canonical_hash({"kind": "turn_pro_self_perception.v1", "key": list(key)})
    u1 = (int(digest[:13], 16) + 1) / (16**13 + 1)
    u2 = int(digest[13:26], 16) / 16**13
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def perceive_self(
    *,
    policy: SelfPerceptionPolicy,
    run_id: str,
    player_id: str,
    attributes: tuple[tuple[str, int], ...],
    seed: int,
    week_ordinal: int,
    ambition: float | None = None,
    professionalism: float | None = None,
    financial_level: int | None = None,
) -> TurnProObservation:
    names = tuple(name for name, _ in attributes)
    if names != CANONICAL_PLAYER_ATTRIBUTES:
        raise ValueError("Self-perception requires the canonical 57 attributes")
    true = dict(attributes)
    reflection = sum(true[name] for name in REFLECTION_ATTRIBUTES) / len(REFLECTION_ATTRIBUTES)
    factor = policy.max_accuracy_factor - (
        policy.max_accuracy_factor - policy.min_accuracy_factor
    ) * min(max(reflection, 0.0), 200.0) / 200.0
    if financial_level is not None:
        raise ValueError("Financial Level is not modelled yet; record it as unknown")
    persistent = (policy.fingerprint, run_id, player_id)
    group_true = {
        group: sum(true[a] for a in CANONICAL_PLAYER_ATTRIBUTES if ATTRIBUTE_TO_GROUP[a] == group)
        / sum(1 for a in CANONICAL_PLAYER_ATTRIBUTES if ATTRIBUTE_TO_GROUP[a] == group)
        for group in ATTRIBUTE_GROUPS
    }
    strongest = max(ATTRIBUTE_GROUPS, key=lambda g: (group_true[g], g))
    level = (
        policy.confidence_bias_per_point * (true[CONFIDENCE_ATTRIBUTE] - 100)
        + factor * policy.level_error_sd * _normal(*persistent, "level")
        + factor * policy.weekly_error_sd * _normal(*persistent, "week", seed, week_ordinal)
    )
    group_sd = dict(policy.group_error_sd)
    group_error = {
        group: factor
        * group_sd[group]
        * (policy.strongest_group_factor if group == strongest else 1.0)
        * _normal(*persistent, "group", group)
        for group in ATTRIBUTE_GROUPS
    }
    perceived = {
        name: true[name]
        + level
        + group_error[ATTRIBUTE_TO_GROUP[name]]
        + factor * policy.attribute_error_sd * _normal(*persistent, "attribute", name)
        for name in CANONICAL_PLAYER_ATTRIBUTES
    }
    overall = sum(perceived.values()) / len(perceived)
    groups = tuple(
        (
            group,
            round(
                sum(perceived[a] for a in CANONICAL_PLAYER_ATTRIBUTES if ATTRIBUTE_TO_GROUP[a] == group)
                / sum(1 for a in CANONICAL_PLAYER_ATTRIBUTES if ATTRIBUTE_TO_GROUP[a] == group),
                6,
            ),
        )
        for group in ATTRIBUTE_GROUPS
    )
    readiness = 1.0 / (
        1.0 + math.exp(-(overall - policy.professional_threshold) / policy.readiness_scale)
    )
    return TurnProObservation(
        player_id=player_id,
        perceived_overall=round(overall, 6),
        perceived_groups=groups,
        perceived_attributes=tuple(
            (name, round(perceived[name], 6)) for name in CANONICAL_PLAYER_ATTRIBUTES
        ),
        financial_level=None,
        ambition=ambition,
        professionalism=professionalism,
        readiness=round(readiness, 12),
        policy_fingerprint=policy.fingerprint,
    )
