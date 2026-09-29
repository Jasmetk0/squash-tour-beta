"""Immutable Run-owned tournament point-award authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


class TournamentPhasePointComponent(FrozenInput):
    """One explicitly configured additive phase component inside one player award."""

    component_id: Literal["group_played_wins", "knockout_finish"]
    distribution_key: str = Field(min_length=1)
    units: int = Field(ge=0)
    points_per_unit: int = Field(ge=0)
    points_awarded: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_component(self) -> "TournamentPhasePointComponent":
        if self.points_awarded != self.units * self.points_per_unit:
            raise ValueError("Tournament phase point component multiplication mismatch")
        if self.component_id == "group_played_wins":
            if self.distribution_key != "group:played_win":
                raise ValueError("Group phase component uses wrong distribution key")
        else:
            if self.units != 1 or not self.distribution_key.startswith("knockout:"):
                raise ValueError("Knockout phase component requires one finishing-stage unit")
        return self


class TournamentPlayerPointAwardAuthority(FrozenInput):
    player_id: str = Field(min_length=1)
    reached_stage: str = Field(min_length=1)
    point_stage: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    qualification_point_stage: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    qualification_points_awarded: int | None = Field(
        default=None,
        ge=0,
        exclude_if=lambda value: value is None,
    )
    qualifier: bool = False
    seed_number: int | None = Field(default=None, ge=1)
    ranking_points_awarded: int = Field(ge=0)
    race_points_awarded: int = Field(ge=0)
    phase_components: tuple[TournamentPhasePointComponent, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )
    source_player_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentPointAwardAuthority(FrozenInput):
    """Canonical event-level ranking/race point awards for one tournament."""

    schema_version: Literal[
        "tournament_point_award_authority.v1",
        "tournament_point_award_authority.v2",
        "tournament_point_award_authority.v3",
        "tournament_point_award_authority.v4",
    ] = "tournament_point_award_authority.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    seed: int
    ranking_status: Literal["ranked"]
    tournament_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    point_distribution: tuple[tuple[str, int], ...]
    point_distribution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    point_distribution_source: str = Field(min_length=1)
    awards: tuple[TournamentPlayerPointAwardAuthority, ...]
    total_ranking_points: int = Field(ge=0)
    total_race_points: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_authority(self) -> "TournamentPointAwardAuthority":
        player_ids = tuple(award.player_id for award in self.awards)
        if not player_ids:
            raise ValueError("Tournament Point Award authority requires player awards")
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Tournament Point Award authority has duplicate players")
        if self.point_distribution_source.startswith("fallback"):
            raise ValueError(
                "Canonical ranked Point Award authority cannot use fallback distribution"
            )
        if self.point_distribution_source == "calendar_event.unranked":
            raise ValueError(
                "Canonical ranked Point Award authority cannot use unranked distribution"
            )
        has_point_override = any(
            award.point_stage is not None for award in self.awards
        )
        has_qualification_component = any(
            award.qualification_point_stage is not None
            or award.qualification_points_awarded is not None
            for award in self.awards
        )
        has_phase_components = any(
            bool(award.phase_components) for award in self.awards
        )
        if self.schema_version == "tournament_point_award_authority.v1":
            if has_point_override or has_qualification_component or has_phase_components:
                raise ValueError(
                    "Historical Point Award v1 cannot carry later point metadata"
                )
        elif self.schema_version == "tournament_point_award_authority.v2":
            if has_qualification_component or has_phase_components:
                raise ValueError(
                    "Historical Point Award v2 cannot carry later component metadata"
                )
            if not has_point_override:
                raise ValueError(
                    "Point Award v2 requires at least one point-stage override"
                )
        elif self.schema_version == "tournament_point_award_authority.v3":
            if has_phase_components:
                raise ValueError(
                    "Historical Point Award v3 cannot carry hybrid phase components"
                )
            if not has_qualification_component:
                raise ValueError(
                    "Point Award v3 requires at least one additive Qualification component"
                )
        else:
            if has_point_override or has_qualification_component:
                raise ValueError(
                    "Hybrid Point Award v4 cannot mix Draw/Qualification component metadata"
                )
            if not all(award.phase_components for award in self.awards):
                raise ValueError(
                    "Hybrid Point Award v4 requires explicit phase components for every player"
                )

        distribution = dict(self.point_distribution)
        if (
            not self.point_distribution
            or len(distribution) != len(self.point_distribution)
            or tuple(sorted(distribution.items())) != self.point_distribution
            or any(value < 0 for value in distribution.values())
            or _hash(distribution) != self.point_distribution_fingerprint
        ):
            raise ValueError("Tournament Point Award distribution snapshot mismatch")
        for award in self.awards:
            if self.schema_version == "tournament_point_award_authority.v4":
                component_ids = tuple(
                    component.component_id for component in award.phase_components
                )
                if len(component_ids) != len(set(component_ids)):
                    raise ValueError(
                        "Hybrid Point Award cannot double count one phase component"
                    )
                if "group_played_wins" not in component_ids:
                    raise ValueError(
                        "Hybrid Point Award requires an explicit group phase component"
                    )
                knockout_components = tuple(
                    component
                    for component in award.phase_components
                    if component.component_id == "knockout_finish"
                )
                if award.reached_stage == "group_stage":
                    if knockout_components:
                        raise ValueError(
                            "Group-only hybrid award cannot carry knockout finish points"
                        )
                elif (
                    len(knockout_components) != 1
                    or knockout_components[0].distribution_key
                    != f"knockout:{award.reached_stage}"
                ):
                    raise ValueError(
                        "Hybrid knockout award stage differs from reached stage"
                    )
                expected_points = 0
                for component in award.phase_components:
                    configured = distribution.get(component.distribution_key)
                    if configured is None:
                        raise ValueError(
                            "Hybrid phase component is absent from frozen distribution"
                        )
                    if component.points_per_unit != configured:
                        raise ValueError(
                            "Hybrid phase component amount differs from frozen distribution"
                        )
                    expected_points += component.points_awarded
                if (
                    award.ranking_points_awarded != expected_points
                    or award.race_points_awarded != expected_points
                ):
                    raise ValueError(
                        "Hybrid Tournament Point Award total differs from phase components"
                    )
                award_fingerprint_payload = {
                    "schema_version": "tournament_player_point_award_authority.v4",
                    "event_id": self.event_id,
                    "seed": self.seed,
                    "player_id": award.player_id,
                    "reached_stage": award.reached_stage,
                    "qualifier": award.qualifier,
                    "seed_number": award.seed_number,
                    "ranking_points_awarded": award.ranking_points_awarded,
                    "race_points_awarded": award.race_points_awarded,
                    "phase_components": [
                        component.model_dump(mode="json")
                        for component in award.phase_components
                    ],
                    "source_tournament_result_fingerprint": self.tournament_result_fingerprint,
                    "source_player_result_fingerprint": award.source_player_result_fingerprint,
                }
                if award.award_fingerprint != _hash(award_fingerprint_payload):
                    raise ValueError("Hybrid Tournament Point Award fingerprint mismatch")
                continue

            has_q_stage = award.qualification_point_stage is not None
            has_q_points = award.qualification_points_awarded is not None
            if has_q_stage != has_q_points:
                raise ValueError(
                    "Qualification point component requires both stage and amount"
                )

            effective_point_stage = award.point_stage or award.reached_stage
            main_points = distribution.get(effective_point_stage)
            if main_points is None:
                raise ValueError(
                    "Tournament Point Award stage is absent from frozen distribution"
                )

            expected_points = main_points
            if has_q_stage:
                assert award.qualification_point_stage is not None
                assert award.qualification_points_awarded is not None
                if not award.qualifier:
                    raise ValueError(
                        "Qualification point component requires Qualification provenance"
                    )
                if award.reached_stage.startswith("qualification_"):
                    raise ValueError(
                        "Qualification-only result cannot carry an additive Qualification component"
                    )
                qualification_points = distribution.get(
                    award.qualification_point_stage
                )
                if qualification_points is None:
                    raise ValueError(
                        "Qualification point component stage is absent from frozen distribution"
                    )
                if award.qualification_points_awarded != qualification_points:
                    raise ValueError(
                        "Qualification point component amount differs from frozen distribution"
                    )
                expected_points += qualification_points

            if (
                award.ranking_points_awarded != expected_points
                or award.race_points_awarded != expected_points
            ):
                raise ValueError(
                    "Tournament Point Award amount differs from frozen distribution"
                )

            player_schema = (
                "tournament_player_point_award_authority.v3"
                if has_q_stage
                else (
                    "tournament_player_point_award_authority.v2"
                    if award.point_stage is not None
                    else "tournament_player_point_award_authority.v1"
                )
            )
            award_fingerprint_payload = {
                "schema_version": player_schema,
                "event_id": self.event_id,
                "seed": self.seed,
                "player_id": award.player_id,
                "reached_stage": award.reached_stage,
                "qualifier": award.qualifier,
                "seed_number": award.seed_number,
                "ranking_points_awarded": award.ranking_points_awarded,
                "race_points_awarded": award.race_points_awarded,
                "source_tournament_result_fingerprint": self.tournament_result_fingerprint,
                "source_player_result_fingerprint": award.source_player_result_fingerprint,
            }
            if award.point_stage is not None:
                award_fingerprint_payload["point_stage"] = award.point_stage
            if has_q_stage:
                award_fingerprint_payload["qualification_point_stage"] = (
                    award.qualification_point_stage
                )
                award_fingerprint_payload["qualification_points_awarded"] = (
                    award.qualification_points_awarded
                )
            expected_award_fingerprint = _hash(award_fingerprint_payload)
            if award.award_fingerprint != expected_award_fingerprint:
                raise ValueError("Tournament Point Award fingerprint mismatch")
        if self.total_ranking_points != sum(
            award.ranking_points_awarded for award in self.awards
        ):
            raise ValueError("Tournament Point Award ranking total mismatch")
        if self.total_race_points != sum(
            award.race_points_awarded for award in self.awards
        ):
            raise ValueError("Tournament Point Award race total mismatch")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
