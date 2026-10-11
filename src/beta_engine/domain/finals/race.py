"""Canonical World Tour Finals Race calculation kernel.

This module deliberately does not decide which tournament categories are eligible or
which published Official Ranking is the seasonal cutoff.  Those are frozen upstream
configuration decisions.  The kernel consumes only already-selected Run/Branch-owned
race-point evidence and produces one immutable, fingerprinted snapshot.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class WorldTourFinalsRacePlayer(FrozenInput):
    player_id: str = Field(min_length=1)
    tie_break_token: str = Field(min_length=1)


class WorldTourFinalsRaceResult(FrozenInput):
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    completed_week: RankingWeek
    race_points: int = Field(ge=0)
    source_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorldTourFinalsRaceInput(FrozenInput):
    schema_version: Literal["world_tour_finals_race_input.v1"] = (
        "world_tour_finals_race_input.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    cutoff_week: RankingWeek
    cutoff_official_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligibility_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str = Field(min_length=1)
    best_n: int = Field(ge=1)
    players: tuple[WorldTourFinalsRacePlayer, ...]
    eligible_results: tuple[WorldTourFinalsRaceResult, ...]

    @model_validator(mode="after")
    def validate_scope(self) -> "WorldTourFinalsRaceInput":
        if self.cutoff_week.season_index != self.target_season_index:
            raise ValueError("Finals Race cutoff must belong to the target season")
        player_ids = tuple(player.player_id for player in self.players)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Finals Race players must be unique")
        tokens = tuple(player.tie_break_token for player in self.players)
        if len(tokens) != len(set(tokens)):
            raise ValueError("Finals Race tie-break tokens must be unique")

        known_players = set(player_ids)
        source_fingerprints: set[str] = set()
        player_editions: set[tuple[str, str]] = set()
        for result in self.eligible_results:
            if (result.run_id, result.branch_id) != (self.run_id, self.branch_id):
                raise ValueError("Finals Race result belongs to another Run/Branch")
            if result.completed_week.season_index != self.target_season_index:
                raise ValueError("Finals Race result belongs to another season")
            if result.completed_week.ordinal > self.cutoff_week.ordinal:
                raise ValueError("Finals Race result is later than the frozen cutoff")
            if result.player_id not in known_players:
                raise ValueError("Finals Race result references an unknown player")
            if result.source_award_fingerprint in source_fingerprints:
                raise ValueError("Finals Race result source fingerprint is duplicated")
            source_fingerprints.add(result.source_award_fingerprint)
            key = (result.player_id, result.edition_id)
            if key in player_editions:
                raise ValueError(
                    "Finals Race cannot contain two point results for one player/Edition"
                )
            player_editions.add(key)
        return self

    @property
    def fingerprint(self) -> str:
        canonical = {
            **self.model_dump(mode="json", exclude={"players", "eligible_results"}),
            "players": sorted(
                (player.model_dump(mode="json") for player in self.players),
                key=lambda item: item["player_id"],
            ),
            "eligible_results": sorted(
                (result.model_dump(mode="json") for result in self.eligible_results),
                key=lambda item: (
                    item["completed_week"]["season_index"],
                    item["completed_week"]["week"],
                    item["edition_id"],
                    item["event_id"],
                    item["player_id"],
                    item["source_award_fingerprint"],
                ),
            ),
        }
        return _hash(canonical)


class WorldTourFinalsRaceCountedResult(FrozenInput):
    edition_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    race_points: int = Field(ge=0)
    source_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorldTourFinalsRaceRow(FrozenInput):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    race_points: int = Field(ge=0)
    counted_results: tuple[WorldTourFinalsRaceCountedResult, ...]
    tie_break_token: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_total(self) -> "WorldTourFinalsRaceRow":
        if self.race_points != sum(result.race_points for result in self.counted_results):
            raise ValueError("Finals Race row total differs from counted results")
        if tuple(
            sorted(
                self.counted_results,
                key=lambda result: (
                    -result.race_points,
                    -result.completed_week.ordinal,
                    result.edition_id,
                    result.event_id,
                    result.source_award_fingerprint,
                ),
            )
        ) != self.counted_results:
            raise ValueError("Finals Race counted results are not canonical")
        return self

    def points_profile(self, best_n: int) -> tuple[int, ...]:
        profile = tuple(result.race_points for result in self.counted_results)
        return profile + (0,) * (best_n - len(profile))


class WorldTourFinalsRaceSnapshot(FrozenInput):
    schema_version: Literal["world_tour_finals_race_snapshot.v1"] = (
        "world_tour_finals_race_snapshot.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    cutoff_week: RankingWeek
    cutoff_official_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligibility_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str = Field(min_length=1)
    best_n: int = Field(ge=1)
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible_result_count: int = Field(ge=0)
    rows: tuple[WorldTourFinalsRaceRow, ...]

    @model_validator(mode="after")
    def validate_snapshot(self) -> "WorldTourFinalsRaceSnapshot":
        if self.cutoff_week.season_index != self.target_season_index:
            raise ValueError("Finals Race snapshot cutoff belongs to another season")
        if tuple(row.rank for row in self.rows) != tuple(range(1, len(self.rows) + 1)):
            raise ValueError("Finals Race ranks must be contiguous")
        player_ids = tuple(row.player_id for row in self.rows)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Finals Race snapshot has duplicate players")
        tokens = tuple(row.tie_break_token for row in self.rows)
        if len(tokens) != len(set(tokens)):
            raise ValueError("Finals Race snapshot tie-break tokens must be unique")
        if any(len(row.counted_results) > self.best_n for row in self.rows):
            raise ValueError("Finals Race row exceeds configured Best-N")
        expected = sorted(
            self.rows,
            key=lambda row: (
                -row.race_points,
                tuple(-points for points in row.points_profile(self.best_n)),
                row.tie_break_token,
            ),
        )
        if tuple(expected) != self.rows:
            raise ValueError("Finals Race rows are not in canonical order")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def calculate_world_tour_finals_race(
    source: WorldTourFinalsRaceInput,
) -> WorldTourFinalsRaceSnapshot:
    """Calculate the Master-v67 seasonal Finals Race from frozen eligible evidence.

    Eligibility/category selection and cutoff publication selection happen upstream.
    This function only applies configured Best-N scoring and the decided Race tie-break:
    total points, highest individual result, second-highest result, and so on, then the
    stored deterministic tie-break token.  Previous Official Ranking order is never used.
    """

    by_player: dict[str, list[WorldTourFinalsRaceResult]] = {
        player.player_id: [] for player in source.players
    }
    for result in source.eligible_results:
        by_player[result.player_id].append(result)

    rows: list[WorldTourFinalsRaceRow] = []
    tokens = {player.player_id: player.tie_break_token for player in source.players}
    for player_id in sorted(by_player):
        ordered = sorted(
            by_player[player_id],
            key=lambda result: (
                -result.race_points,
                -result.completed_week.ordinal,
                result.edition_id,
                result.event_id,
                result.source_award_fingerprint,
            ),
        )
        counted = tuple(
            WorldTourFinalsRaceCountedResult(
                edition_id=result.edition_id,
                event_id=result.event_id,
                completed_week=result.completed_week,
                race_points=result.race_points,
                source_award_fingerprint=result.source_award_fingerprint,
            )
            for result in ordered[: source.best_n]
        )
        rows.append(
            WorldTourFinalsRaceRow(
                rank=1,
                player_id=player_id,
                race_points=sum(result.race_points for result in counted),
                counted_results=counted,
                tie_break_token=tokens[player_id],
            )
        )

    ordered_rows = sorted(
        rows,
        key=lambda row: (
            -row.race_points,
            tuple(-points for points in row.points_profile(source.best_n)),
            row.tie_break_token,
        ),
    )
    ranked = tuple(
        row.model_copy(update={"rank": index + 1})
        for index, row in enumerate(ordered_rows)
    )
    return WorldTourFinalsRaceSnapshot(
        run_id=source.run_id,
        branch_id=source.branch_id,
        target_season_index=source.target_season_index,
        cutoff_week=source.cutoff_week,
        cutoff_official_ranking_fingerprint=source.cutoff_official_ranking_fingerprint,
        eligibility_fingerprint=source.eligibility_fingerprint,
        policy_id=source.policy_id,
        best_n=source.best_n,
        input_fingerprint=source.fingerprint,
        eligible_result_count=len(source.eligible_results),
        rows=ranked,
    )
