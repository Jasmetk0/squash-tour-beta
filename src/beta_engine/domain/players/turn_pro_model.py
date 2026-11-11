"""Pre-alpha player-AI model for the Master v87 Turn Pro week (pure, deterministic).

Each Week Transition, every eligible prospect has a weekly chance to turn pro. The
chance comes from an annual base by age, scaled in hazard space by strength relative
to current Tour Players ("readiness") and by an opportunity such as a small upcoming
event of the Run's association in the player's country. The annual chance is turned
into a weekly one with the Run's own weeks-per-year W, so W52 and W61 Runs turn pro
at the same rate per year of age.

There is no age condition (owner decision): the annual base rises towards certainty,
which realises the decided rule that every generated prospect eventually turns pro.
All numbers in ``default_turn_pro_model_policy`` are provisional calibration.

Randomness: one uniform draw per (seed, Run, Branch, player, target week), derived by
hashing. It does not depend on processing order or on how many other players are
evaluated, so logically simultaneous decisions stay order-independent.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.turn_pro import PlayerTurnProDecision
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash

FIRST_TURN_PRO_AGE = 15


class TurnProModelPolicy(FrozenInput):
    """Versioned, fingerprinted parameters; never read from current defaults on replay."""

    schema_version: Literal["turn_pro_model.v1"] = "turn_pro_model.v1"
    model_id: str = Field(min_length=1)
    # Annual chance by completed age, starting at 15; the last value applies beyond.
    annual_base_by_age: tuple[float, ...] = Field(min_length=1)
    # Hazard multiplier exp(readiness_weight * (readiness - readiness_reference)).
    readiness_weight: float = Field(ge=0)
    readiness_reference: float = Field(ge=0, le=1)
    home_opportunity_multiplier: float = Field(ge=1)
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bases(self):
        bases = self.annual_base_by_age
        if any(not 0 < b < 1 for b in bases):
            raise ValueError("Annual Turn Pro bases must be strictly between 0 and 1")
        if list(bases) != sorted(bases):
            raise ValueError("Annual Turn Pro bases must not fall with age")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def default_turn_pro_model_policy() -> TurnProModelPolicy:
    """Provisional pre-alpha calibration (Master v87); tune by testing."""
    return TurnProModelPolicy(
        model_id="pre-alpha-turn-pro.v1",
        annual_base_by_age=(0.05, 0.20, 0.40, 0.55, 0.65, 0.75, 0.85, 0.95),
        readiness_weight=2.0,
        readiness_reference=0.3,
        home_opportunity_multiplier=1.5,
        provenance=(
            "Provisional pre-alpha calibration; research 'Přechod mezi profesionály "
            "ve sportu' (2026-11-11): median about 17.5-19, almost all by 22"
        ),
    )


class TurnProCandidate(FrozenInput):
    """One eligible prospect's inputs, known through the end of the completed week."""

    player_id: str = Field(min_length=1)
    age: int = Field(ge=FIRST_TURN_PRO_AGE, le=120)
    # Share of current Tour Players this prospect is stronger than.
    readiness: float = Field(ge=0, le=1)
    home_opportunity: bool = False


def weekly_turn_pro_chance(
    policy: TurnProModelPolicy, candidate: TurnProCandidate, *, weeks_per_year: int
) -> float:
    if weeks_per_year < 1:
        raise ValueError("Run weeks per year must be positive")
    bases = policy.annual_base_by_age
    base = bases[min(candidate.age - FIRST_TURN_PRO_AGE, len(bases) - 1)]
    annual_hazard = -math.log1p(-base)
    annual_hazard *= math.exp(
        policy.readiness_weight * (candidate.readiness - policy.readiness_reference)
    )
    if candidate.home_opportunity:
        annual_hazard *= policy.home_opportunity_multiplier
    return -math.expm1(-annual_hazard / weeks_per_year)


def turn_pro_draw(
    *, seed: int, run_id: str, branch_id: str, player_id: str, target: RunWeekPosition
) -> float:
    """Uniform [0, 1) draw keyed to one player and week, independent of order."""
    digest = canonical_hash(
        {
            "kind": "turn_pro_model.v1",
            "seed": seed,
            "run": run_id,
            "branch": branch_id,
            "player": player_id,
            "week": target.ordinal,
        }
    )
    return int(digest[:13], 16) / 16**13


def decide_turn_pro(
    *,
    predecessor,
    target: RunWeekPosition,
    candidates: Iterable[TurnProCandidate],
    policy: TurnProModelPolicy,
    seed: int,
) -> tuple[PlayerTurnProDecision, ...]:
    """Decide, at the Week Transition into ``target``, who turns pro that week.

    ``predecessor`` is the lifecycle of the completed week; every candidate must be an
    active player in it who has not turned pro. The result can be passed unchanged to
    ``advance_calendar_lifecycle(..., turn_pro=...)``.
    """
    if not predecessor.policy.requires_turn_pro:
        raise ValueError("Turn Pro model requires the v87 lifecycle policy")
    if target.ordinal != predecessor.week.ordinal + 1:
        raise ValueError("Turn Pro is decided only at the consecutive Week Transition")
    by_id = {p.player_id: p for p in predecessor.players}
    ordered = tuple(sorted(candidates, key=lambda c: c.player_id))
    if len({c.player_id for c in ordered}) != len(ordered):
        raise ValueError("Duplicate Turn Pro candidate")
    for candidate in ordered:
        player = by_id.get(candidate.player_id)
        if player is None:
            raise ValueError("Turn Pro candidate is absent from lifecycle")
        if player.status != "active" or getattr(player, "tour_entry_week", None):
            raise ValueError("Turn Pro candidate must be an active prospect")
        if candidate.age < player.age:
            raise ValueError("Turn Pro candidate age predates its lifecycle age")
    source = canonical_hash(
        {
            "kind": "turn_pro_model.v1",
            "lifecycle": predecessor.fingerprint,
            "target": target.ordinal,
            "seed": seed,
            "policy": policy.fingerprint,
            "candidates": [c.model_dump(mode="json") for c in ordered],
        }
    )
    decisions = []
    for candidate in ordered:
        chance = weekly_turn_pro_chance(
            policy, candidate, weeks_per_year=target.calendar.weeks_per_year
        )
        draw = turn_pro_draw(
            seed=seed,
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            player_id=candidate.player_id,
            target=target,
        )
        if draw < chance:
            decisions.append(
                PlayerTurnProDecision(
                    run_id=predecessor.run_id,
                    branch_id=predecessor.branch_id,
                    player_id=candidate.player_id,
                    effective_week=target,
                    decision_source="player_ai",
                    source_state_fingerprint=source,
                    provenance=(
                        f"{policy.schema_version}:{policy.model_id}; "
                        f"weekly_chance={chance:.12f}; draw={draw:.12f}"
                    ),
                )
            )
    return tuple(decisions)
