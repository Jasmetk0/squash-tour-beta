"""Pure canonical sporting state and provisional weekly development kernels."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.attribute_catalog import (
    ATTRIBUTE_TO_GROUP,
    CANONICAL_PLAYER_ATTRIBUTES,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek

DevelopmentTiming = Literal["Early Bloomer", "Standard", "Late Bloomer"]


class PlayerSportingBootstrapPolicy(FrozenInput):
    policy_id: str = "legacy-7x99-to-canonical-57x200.v1"
    scale_numerator: int = 200
    scale_denominator: int = 99
    deterministic_jitter: int = Field(default=3, ge=0, le=20)
    default_form: int = Field(default=100, ge=0, le=200)
    default_form_norm: int = Field(default=100, ge=0, le=200)
    default_match_sharpness: int = Field(default=100, ge=0, le=100)
    default_fatigue: int = Field(default=0, ge=0, le=100)
    provenance: str = "Provisional calibration adapter from the owned legacy initial pool; not product canon"


class PlayerDevelopmentPolicy(FrozenInput):
    policy_id: str = "weekly-player-development.provisional.v1"
    bootstrap_policy: PlayerSportingBootstrapPolicy = PlayerSportingBootstrapPolicy()
    timing_shift_years: dict[DevelopmentTiming, int] = {
        "Early Bloomer": -3,
        "Standard": 0,
        "Late Bloomer": 3,
    }
    physical_decline_age: int = 30
    other_decline_age: int = 34
    growth_end_age: int = 27
    weekly_change_basis_points: int = Field(default=18, ge=0, le=10000)
    form_influence_basis_points: int = Field(default=4, ge=0, le=10000)
    form_regression_divisor: int = Field(default=8, ge=1)
    inactive_sharpness_decay: int = Field(default=2, ge=0, le=100)
    fatigue_recovery: int = Field(default=8, ge=0, le=100)
    provenance: str = "Provisional deterministic pre-alpha calibration; all numeric values are tuneable"


class CompletedWeekSportingContext(FrozenInput):
    schema_version: Literal["completed_week_sporting_context.v1"] = (
        "completed_week_sporting_context.v1"
    )
    competitive_match_counts: dict[str, int] = {}
    provenance: str = (
        "No Branch-owned completed-match sporting bridge; zero matches only"
    )

    @model_validator(mode="after")
    def non_negative_counts(self):
        if any(count < 0 for count in self.competitive_match_counts.values()):
            raise ValueError("Competitive match counts cannot be negative")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class PlayerSportingRecord(FrozenInput):
    player_id: str = Field(min_length=1)
    attributes: dict[str, int]
    potential_ovr: int = Field(ge=0, le=200)
    potential_identity: str = Field(min_length=1)
    potential_provenance: str = Field(min_length=1)
    development_timing: DevelopmentTiming
    current_form: int = Field(ge=0, le=200)
    long_term_form_norm: int = Field(ge=0, le=200)
    match_sharpness: int = Field(ge=0, le=100)
    long_term_fatigue: int = Field(ge=0, le=100)
    health_state: Literal["unsupported"] = "unsupported"

    @model_validator(mode="after")
    def exact_catalog(self):
        if set(self.attributes) != set(CANONICAL_PLAYER_ATTRIBUTES):
            raise ValueError(
                "Sporting state requires exactly the canonical 57 attributes"
            )
        if any(
            type(value) is not int or not 0 <= value <= 200
            for value in self.attributes.values()
        ):
            raise ValueError("Canonical attributes must be integers from 0 through 200")
        return self

    @property
    def ovr(self) -> int:
        # Provisional display calculation, deliberately separate from stored attributes.
        return round(sum(self.attributes.values()) / len(self.attributes))


class PlayerSportingWeekState(FrozenInput):
    schema_version: Literal["player_sporting_week_state.v1"] = (
        "player_sporting_week_state.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    players: tuple[PlayerSportingRecord, ...]
    policy: PlayerDevelopmentPolicy = PlayerDevelopmentPolicy()
    completed_context_fingerprint: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(min_length=1)
    predecessor_fingerprint: str | None = None
    stage_provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def canonical_players(self):
        ids = [player.player_id for player in self.players]
        if ids != sorted(set(ids)):
            raise ValueError("Sporting players require canonical unique identities")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _roll(*parts: object, modulus: int) -> int:
    value = "|".join(str(part) for part in parts)
    return (
        int.from_bytes(hashlib.blake2b(value.encode(), digest_size=8).digest(), "big")
        % modulus
    )


def weekly_player_development_update(
    predecessor: PlayerSportingWeekState,
    *,
    target: RankingWeek,
    player_ages: dict[str, int],
    context: CompletedWeekSportingContext,
) -> PlayerSportingWeekState:
    """Develop from completed-week inputs; target-week state is intentionally absent."""
    if target.ordinal != predecessor.week.ordinal + 1:
        raise ValueError("Sporting development requires consecutive weeks")
    unknown = set(context.competitive_match_counts) - {
        p.player_id for p in predecessor.players
    }
    if unknown:
        raise ValueError("Completed-week context names an unknown sporting player")
    developed = []
    for player in sorted(predecessor.players, key=lambda item: item.player_id):
        age = player_ages[player.player_id]
        shifted_age = (
            age - predecessor.policy.timing_shift_years[player.development_timing]
        )
        values = {}
        for attribute in CANONICAL_PLAYER_ATTRIBUTES:
            group = ATTRIBUTE_TO_GROUP[attribute]
            decline_age = (
                predecessor.policy.physical_decline_age
                if group in {"Physical", "Move"}
                else predecessor.policy.other_decline_age
            )
            direction = (
                1
                if shifted_age <= predecessor.policy.growth_end_age
                else (-1 if shifted_age >= decline_age else 0)
            )
            form_adjustment = (
                player.current_form - player.long_term_form_norm
            ) * predecessor.policy.form_influence_basis_points
            threshold = max(
                0, predecessor.policy.weekly_change_basis_points + form_adjustment
            )
            roll = _roll(
                predecessor.run_id,
                predecessor.branch_id,
                predecessor.fingerprint,
                predecessor.week.ordinal,
                predecessor.policy.policy_id,
                context.fingerprint,
                player.player_id,
                attribute,
                modulus=10000,
            )
            delta = direction if roll < threshold else 0
            values[attribute] = min(200, max(0, player.attributes[attribute] + delta))
        developed.append(player.model_copy(update={"attributes": values}))
    return PlayerSportingWeekState(
        run_id=predecessor.run_id,
        branch_id=predecessor.branch_id,
        week=target,
        players=tuple(developed),
        policy=predecessor.policy,
        completed_context_fingerprint=context.fingerprint,
        source_initial_world_fingerprint=predecessor.source_initial_world_fingerprint,
        predecessor_fingerprint=predecessor.fingerprint,
        stage_provenance="weekly_player_development_update.v1:pre-between-week",
    )


def between_week_state_update(
    developed: PlayerSportingWeekState,
    *,
    context: CompletedWeekSportingContext,
) -> PlayerSportingWeekState:
    players = []
    for player in developed.players:
        difference = player.long_term_form_norm - player.current_form
        regression = int(difference / developed.policy.form_regression_divisor)
        if regression == 0 and difference:
            regression = 1 if difference > 0 else -1
        played = context.competitive_match_counts.get(player.player_id, 0)
        sharpness = player.match_sharpness
        if played == 0:
            sharpness = max(0, sharpness - developed.policy.inactive_sharpness_decay)
        players.append(
            player.model_copy(
                update={
                    "current_form": player.current_form + regression,
                    "match_sharpness": sharpness,
                    "long_term_fatigue": max(
                        0, player.long_term_fatigue - developed.policy.fatigue_recovery
                    ),
                }
            )
        )
    return developed.model_copy(
        update={
            "players": tuple(players),
            "stage_provenance": "between_week_state_update.v1:post-regression-recovery;health-unsupported",
        }
    )
