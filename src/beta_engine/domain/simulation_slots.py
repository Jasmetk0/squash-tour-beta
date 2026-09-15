"""Pure contracts for Run/Branch-owned match slots and sporting effects."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.matches import MatchInputSnapshot
from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_GROUPS
from beta_engine.domain.players.models import HiddenCareerTraits, Player
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CanonicalMatchInputProjectionPolicy(FrozenInput):
    """Versioned compatibility adapter; the seven projected values are not canon."""

    policy_id: str = "canonical-57-to-legacy-match-engine.provisional.v1"
    source_min: int = 0
    source_max: int = 200
    engine_min: int = 1
    engine_max: int = 99
    form_modifier_divisor: int = 400
    sharpness_modifier_divisor: int = 500
    fatigue_modifier_divisor: int = 300
    provenance: str = "Compatibility/calibration adapter for match_engine_v9; canonical 57-value input is retained"

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class CanonicalPlayerMatchProjection(FrozenInput):
    player_id: str
    canonical_attributes: tuple[tuple[str, int], ...]
    current_form: int
    match_sharpness: int
    long_term_fatigue: int
    source_sporting_fingerprint: str
    projection_policy_id: str
    projection_policy_fingerprint: str
    legacy_engine_values: tuple[tuple[str, int], ...]
    form_modifier: float
    sharpness_modifier: float
    fatigue_modifier: float
    profile_source_fingerprint: str
    profile_provenance: str
    age: int
    name: str
    nationality: str
    play_style: str
    archetype: str
    hidden_career_traits: HiddenCareerTraits

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


def project_player(
    record: PlayerSportingRecord,
    *,
    source_sporting_fingerprint: str,
    policy: CanonicalMatchInputProjectionPolicy,
    profile_source_fingerprint: str,
    profile_provenance: str,
    age: int,
    name: str,
    nationality: str,
    play_style: str,
    archetype: str,
    hidden_career_traits: HiddenCareerTraits,
) -> CanonicalPlayerMatchProjection:
    values = dict(record.attributes)

    def average(group: str) -> int:
        raw = sum(values[name] for name in ATTRIBUTE_GROUPS[group]) / len(
            ATTRIBUTE_GROUPS[group]
        )
        scaled = round(
            raw * (policy.engine_max - policy.engine_min) / policy.source_max
        )
        return min(
            policy.engine_max, max(policy.engine_min, policy.engine_min + scaled)
        )

    legacy = {
        "technique": average("Technical"),
        "movement": average("Move"),
        "physical": average("Physical"),
        "mental": average("Mental"),
        "consistency": round((average("Mental") + average("Tactics")) / 2),
        "clutch": round((average("Mental") + average("Creativity")) / 2),
        "recovery": round((average("Physical") + average("Move")) / 2),
    }
    # Sharpness remains separately protected and auditable. The legacy engine has
    # no native field, so its modifier is carried through form_modifier while the
    # independent component remains explicit here. This is compatibility only.
    form_modifier = (record.current_form - 100) / policy.form_modifier_divisor
    sharpness_modifier = (
        record.match_sharpness - 50
    ) / policy.sharpness_modifier_divisor
    fatigue_modifier = -record.long_term_fatigue / policy.fatigue_modifier_divisor
    return CanonicalPlayerMatchProjection(
        player_id=record.player_id,
        canonical_attributes=record.attributes,
        current_form=record.current_form,
        match_sharpness=record.match_sharpness,
        long_term_fatigue=record.long_term_fatigue,
        source_sporting_fingerprint=source_sporting_fingerprint,
        projection_policy_id=policy.policy_id,
        projection_policy_fingerprint=policy.fingerprint,
        legacy_engine_values=tuple(legacy.items()),
        form_modifier=round(form_modifier, 6),
        sharpness_modifier=round(sharpness_modifier, 6),
        fatigue_modifier=round(fatigue_modifier, 6),
        profile_source_fingerprint=profile_source_fingerprint,
        profile_provenance=profile_provenance,
        age=age,
        name=name,
        nationality=nationality,
        play_style=play_style,
        archetype=archetype,
        hidden_career_traits=hidden_career_traits,
    )


def projected_engine_player(projection: CanonicalPlayerMatchProjection) -> Player:
    values = dict(projection.legacy_engine_values)
    return Player(
        player_id=projection.player_id,
        name=projection.name,
        age=projection.age,
        nationality=projection.nationality,
        **values,
        play_style=projection.play_style,
        archetype=projection.archetype,
        hidden_career_traits=projection.hidden_career_traits,
    )


class AuthoritativeMatchInput(FrozenInput):
    schema_version: Literal["authoritative_match_input.v1"] = (
        "authoritative_match_input.v1"
    )
    run_id: str
    branch_id: str
    week: RankingWeek
    slot_id: str
    slot_start_fingerprint: str
    group_id: str
    event_id: str
    match_id: str
    player_projections: tuple[
        CanonicalPlayerMatchProjection, CanonicalPlayerMatchProjection
    ]
    engine_input: MatchInputSnapshot

    @model_validator(mode="after")
    def validate_identity(self):
        if self.engine_input.match_id != self.match_id:
            raise ValueError("authoritative and engine match identities differ")
        if tuple(p.player_id for p in self.player_projections) != (
            self.engine_input.context.player_a.player.player_id,
            self.engine_input.context.player_b.player.player_id,
        ):
            raise ValueError("canonical projections and engine participants differ")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class MatchSportingEffectsPolicy(FrozenInput):
    policy_id: str = "match-sporting-effects.provisional.v1"
    form_response: float = 18.0
    expectation_sensitivity: float = 1.0
    minimum_played_weight: float = 0.15
    full_evidence_rallies: int = 100
    sharpness_duration_per_hour: float = 8.0
    sharpness_workload_divisor: float = 30.0
    fatigue_duration_per_hour: float = 5.0
    fatigue_workload_divisor: float = 18.0
    form_min: int = 0
    form_max: int = 200
    sharpness_min: int = 0
    sharpness_max: int = 100
    fatigue_min: int = 0
    fatigue_max: int = 100
    provenance: str = "Provisional deterministic calibration, not product canon"

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class PlayerMatchSportingEffect(FrozenInput):
    schema_version: Literal["player_match_sporting_effect.v1"] = (
        "player_match_sporting_effect.v1"
    )
    run_id: str
    branch_id: str
    week: RankingWeek
    slot_id: str
    group_id: str
    match_id: str
    player_id: str
    pre_match_sporting_fingerprint: str
    match_input_fingerprint: str
    authoritative_result_fingerprint: str
    form_before: int
    form_delta: int
    form_after: int
    sharpness_before: int
    sharpness_delta: int
    sharpness_after: int
    fatigue_before: int
    fatigue_delta: int
    fatigue_after: int
    policy_id: str
    policy_fingerprint: str
    provenance: str

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


def provisional_form_delta(
    *,
    expected_point_share: float,
    actual_point_share: float,
    played_rallies: int,
    policy: MatchSportingEffectsPolicy,
) -> int:
    """CALIBRATION seam: performance versus pre-match expectation, weighted by evidence."""
    evidence_weight = max(
        policy.minimum_played_weight,
        min(1.0, played_rallies / policy.full_evidence_rallies),
    )
    return round(
        policy.form_response
        * (actual_point_share - expected_point_share * policy.expectation_sensitivity)
        * evidence_weight
    )


def provisional_load_deltas(
    *,
    duration_seconds: float,
    workload_units: float,
    policy: MatchSportingEffectsPolicy,
) -> tuple[int, int]:
    """Return independent non-negative Sharpness and long-term Fatigue loads."""
    duration_hours = duration_seconds / 3600
    return (
        max(
            0,
            round(
                duration_hours * policy.sharpness_duration_per_hour
                + workload_units / policy.sharpness_workload_divisor
            ),
        ),
        max(
            0,
            round(
                duration_hours * policy.fatigue_duration_per_hour
                + workload_units / policy.fatigue_workload_divisor
            ),
        ),
    )


def calculate_match_effects(
    authoritative_input: AuthoritativeMatchInput,
    result: MatchResult,
    *,
    result_fingerprint: str,
    policy: MatchSportingEffectsPolicy,
) -> tuple[PlayerMatchSportingEffect, PlayerMatchSportingEffect]:
    """Derive effects from pre-match inputs and authoritative played evidence."""
    if (
        result.rally_log is None
        or result.timeline_log is None
        or result.stamina_log is None
    ):
        raise ValueError(
            "played authoritative match requires rally, timeline, and stamina logs"
        )
    rallies = len(result.rally_log.events)
    if rallies == 0:
        raise ValueError("pre-start abnormal result has no played sporting effect")
    total_points = {
        projection.player_id: 0 for projection in authoritative_input.player_projections
    }
    for event in result.rally_log.events:
        if event.score_mutations:
            total_points[event.score_mutations[-1].player_id] += 1
    total = sum(total_points.values())
    strengths = {
        p.player_id: sum(dict(p.legacy_engine_values).values()) / 7
        + p.form_modifier * 35
        + p.sharpness_modifier * 35
        + p.fatigue_modifier * 30
        for p in authoritative_input.player_projections
    }
    workload = {p.player_id: 0.0 for p in authoritative_input.player_projections}
    for transition in result.stamina_log.transitions:
        if transition.player_workloads:
            for item in transition.player_workloads:
                workload[item.player_id] += item.workload_units
        else:
            for player_id in workload:
                workload[player_id] += transition.workload_units
    effects = []
    projections = {p.player_id: p for p in authoritative_input.player_projections}
    for player_id, projection in projections.items():
        opponent_id = next(pid for pid in projections if pid != player_id)
        expected = strengths[player_id] / (
            strengths[player_id] + strengths[opponent_id]
        )
        actual = total_points[player_id] / total
        form_delta = provisional_form_delta(
            expected_point_share=expected,
            actual_point_share=actual,
            played_rallies=rallies,
            policy=policy,
        )
        sharpness_delta, fatigue_delta = provisional_load_deltas(
            duration_seconds=result.timeline_log.total_elapsed_seconds,
            workload_units=workload[player_id],
            policy=policy,
        )
        form_after = min(
            policy.form_max, max(policy.form_min, projection.current_form + form_delta)
        )
        sharpness_after = min(
            policy.sharpness_max,
            max(policy.sharpness_min, projection.match_sharpness + sharpness_delta),
        )
        fatigue_after = min(
            policy.fatigue_max,
            max(policy.fatigue_min, projection.long_term_fatigue + fatigue_delta),
        )
        effects.append(
            PlayerMatchSportingEffect(
                run_id=authoritative_input.run_id,
                branch_id=authoritative_input.branch_id,
                week=authoritative_input.week,
                slot_id=authoritative_input.slot_id,
                group_id=authoritative_input.group_id,
                match_id=authoritative_input.match_id,
                player_id=player_id,
                pre_match_sporting_fingerprint=projection.source_sporting_fingerprint,
                match_input_fingerprint=authoritative_input.fingerprint,
                authoritative_result_fingerprint=result_fingerprint,
                form_before=projection.current_form,
                form_delta=form_after - projection.current_form,
                form_after=form_after,
                sharpness_before=projection.match_sharpness,
                sharpness_delta=sharpness_after - projection.match_sharpness,
                sharpness_after=sharpness_after,
                fatigue_before=projection.long_term_fatigue,
                fatigue_delta=fatigue_after - projection.long_term_fatigue,
                fatigue_after=fatigue_after,
                policy_id=policy.policy_id,
                policy_fingerprint=policy.fingerprint,
                provenance="authoritative rally/timeline/stamina logs and frozen pre-match expectation",
            )
        )
    return tuple(effects)  # type: ignore[return-value]


class SimulationSlotPlan(FrozenInput):
    schema_version: Literal["simulation_slot_plan.v1"] = "simulation_slot_plan.v1"
    run_id: str
    branch_id: str
    week: RankingWeek
    slot_id: str
    ordinal: int = Field(ge=1)
    ordered_dependency_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...]
    match_events: tuple["SimulationMatchEventPlan", ...]
    slot_start_fingerprint: str
    provenance: str

    @model_validator(mode="after")
    def canonical_groups(self):
        if tuple(sorted(set(self.group_ids))) != self.group_ids:
            raise ValueError("slot groups require canonical unique identity")
        if tuple(event.group_id for event in self.match_events) != self.group_ids:
            raise ValueError("slot match events must exactly cover canonical groups")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class SimulationMatchEventPlan(FrozenInput):
    schema_version: Literal["simulation_match_event_plan.v1"] = (
        "simulation_match_event_plan.v1"
    )
    group_id: str
    event_id: str
    match_id: str
    execution_kind: Literal["competitive_match_engine_simulation"] = (
        "competitive_match_engine_simulation"
    )
    direct_player_ids: tuple[str, str] | None = None
    feeder_group_ids: tuple[str, str] | None = None

    @model_validator(mode="after")
    def exactly_one_participant_source(self):
        if (self.direct_player_ids is None) == (self.feeder_group_ids is None):
            raise ValueError("match plan requires direct players or two feeder groups")
        return self


class PlayerSportingCheckpoint(FrozenInput):
    schema_version: Literal["player_sporting_checkpoint.v1"] = (
        "player_sporting_checkpoint.v1"
    )
    run_id: str
    branch_id: str
    week: RankingWeek
    slot_id: str
    slot_ordinal: int
    opening_week_fingerprint: str
    slot_start_fingerprint: str
    predecessor_checkpoint_fingerprint: str | None
    applied_effect_fingerprints: tuple[str, ...]
    players: tuple[PlayerSportingRecord, ...]

    @model_validator(mode="after")
    def canonical_content(self):
        if (
            tuple(sorted(set(self.applied_effect_fingerprints)))
            != self.applied_effect_fingerprints
        ):
            raise ValueError("checkpoint effects require canonical unique identity")
        if tuple(p.player_id for p in self.players) != tuple(
            sorted({p.player_id for p in self.players})
        ):
            raise ValueError("checkpoint players require canonical unique identity")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))
