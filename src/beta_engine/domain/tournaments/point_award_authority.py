"""Immutable Run-owned tournament point-award authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


class TournamentPlayerPointAwardAuthority(FrozenInput):
    player_id: str = Field(min_length=1)
    reached_stage: str = Field(min_length=1)
    qualifier: bool = False
    seed_number: int | None = Field(default=None, ge=1)
    ranking_points_awarded: int = Field(ge=0)
    race_points_awarded: int = Field(ge=0)
    source_player_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentPointAwardAuthority(FrozenInput):
    """Canonical event-level ranking/race point awards for one tournament."""

    schema_version: Literal["tournament_point_award_authority.v1"] = (
        "tournament_point_award_authority.v1"
    )
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
            expected_points = distribution.get(award.reached_stage)
            if expected_points is None:
                raise ValueError(
                    "Tournament Point Award stage is absent from frozen distribution"
                )
            if (
                award.ranking_points_awarded != expected_points
                or award.race_points_awarded != expected_points
            ):
                raise ValueError(
                    "Tournament Point Award amount differs from frozen distribution"
                )
            expected_award_fingerprint = _hash(
                {
                    "schema_version": "tournament_player_point_award_authority.v1",
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
            )
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
