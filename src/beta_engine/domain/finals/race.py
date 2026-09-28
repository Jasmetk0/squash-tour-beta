"""Canonical World Tour Finals Race calculation and frozen snapshot models."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class WorldTourFinalsRacePlayerAward(FrozenInput):
    player_id: str = Field(min_length=1)
    race_points: int = Field(ge=0)
    award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorldTourFinalsRaceEventAwards(FrozenInput):
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    first_publication_week: RankingWeek
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    awards: tuple[WorldTourFinalsRacePlayerAward, ...]

    @model_validator(mode="after")
    def validate_event(self):
        if self.first_publication_week.ordinal <= self.completed_week.ordinal:
            raise ValueError("Race source publication must follow tournament completion")
        player_ids = tuple(item.player_id for item in self.awards)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Race event source contains duplicate players")
        return self


class WorldTourFinalsRaceCountedResult(FrozenInput):
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    first_publication_week: RankingWeek
    points: int = Field(ge=0)
    award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorldTourFinalsRaceRow(FrozenInput):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    race_points: int = Field(ge=0)
    counted_results: tuple[WorldTourFinalsRaceCountedResult, ...]
    tie_break_token: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorldTourFinalsRaceSnapshot(FrozenInput):
    schema_version: Literal["world_tour_finals_race_snapshot.v1"] = (
        "world_tour_finals_race_snapshot.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    season_index: int = Field(ge=0, le=49)
    cutoff_week: RankingWeek
    cutoff_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    best_result_count: int = Field(ge=1)
    eligible_event_ids: tuple[str, ...]
    calendar_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_tournament_fingerprints: tuple[tuple[str, str], ...]
    rows: tuple[WorldTourFinalsRaceRow, ...]
    command_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_snapshot(self):
        if self.cutoff_week.season_index != self.season_index:
            raise ValueError("Race cutoff week must belong to the configured season")
        if (
            not self.eligible_event_ids
            or tuple(sorted(set(self.eligible_event_ids))) != self.eligible_event_ids
        ):
            raise ValueError("Race eligible event ids must be a non-empty canonical set")
        source_ids = tuple(item[0] for item in self.source_tournament_fingerprints)
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Race source tournament identities are duplicated")
        if tuple(sorted(self.source_tournament_fingerprints)) != self.source_tournament_fingerprints:
            raise ValueError("Race source tournament fingerprints are not canonical")
        if any(event_id not in self.eligible_event_ids for event_id in source_ids):
            raise ValueError("Race source tournament is outside the frozen eligible event set")

        expected_ranks = tuple(range(1, len(self.rows) + 1))
        if tuple(row.rank for row in self.rows) != expected_ranks:
            raise ValueError("Race ranks must be contiguous")
        player_ids = tuple(row.player_id for row in self.rows)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Race snapshot contains duplicate players")

        for row in self.rows:
            if len(row.counted_results) > self.best_result_count:
                raise ValueError("Race row exceeds configured Best-N result count")
            if row.race_points != sum(item.points for item in row.counted_results):
                raise ValueError("Race row total differs from counted results")
            if tuple(
                sorted(
                    row.counted_results,
                    key=lambda item: (-item.points, item.event_id),
                )
            ) != row.counted_results:
                raise ValueError("Race counted results are not canonical")
            for result in row.counted_results:
                if result.event_id not in self.eligible_event_ids:
                    raise ValueError("Race row counts an ineligible tournament")
                if result.completed_week.season_index != self.season_index:
                    raise ValueError("Race row counts a result from another season")
                if result.first_publication_week.ordinal > self.cutoff_week.ordinal:
                    raise ValueError("Race row counts a result after the cutoff publication")

        ordered = tuple(sorted(self.rows, key=_row_sort_key))
        if ordered != self.rows:
            raise ValueError("Race standings are not in canonical order")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def _row_sort_key(row: WorldTourFinalsRaceRow) -> tuple:
    profile = tuple(-item.points for item in row.counted_results)
    return (-row.race_points, profile, row.tie_break_token, row.player_id)


def calculate_world_tour_finals_race(
    *,
    run_id: str,
    branch_id: str,
    season_index: int,
    cutoff_week: RankingWeek,
    cutoff_ranking_fingerprint: str,
    best_result_count: int,
    eligible_event_ids: tuple[str, ...],
    calendar_projection_fingerprint: str,
    event_sources: tuple[WorldTourFinalsRaceEventAwards, ...],
    command_id: str,
) -> WorldTourFinalsRaceSnapshot:
    eligible = tuple(sorted(set(eligible_event_ids)))
    if not eligible:
        raise ValueError("World Tour Finals Race requires at least one eligible event")
    if cutoff_week.season_index != season_index:
        raise ValueError("World Tour Finals Race cutoff belongs to another season")

    seen_events: set[str] = set()
    results_by_player: dict[str, list[WorldTourFinalsRaceCountedResult]] = defaultdict(list)
    source_fingerprints: list[tuple[str, str]] = []

    for source in sorted(event_sources, key=lambda item: item.event_id):
        if source.event_id in seen_events:
            raise ValueError("World Tour Finals Race source event is duplicated")
        seen_events.add(source.event_id)
        if source.event_id not in eligible:
            raise ValueError("World Tour Finals Race source is outside eligible events")
        if source.completed_week.season_index != season_index:
            raise ValueError("World Tour Finals Race source belongs to another season")
        if source.first_publication_week.ordinal > cutoff_week.ordinal:
            raise ValueError("World Tour Finals Race source was not public by cutoff")
        source_fingerprints.append((source.event_id, source.source_fingerprint))
        for award in source.awards:
            results_by_player[award.player_id].append(
                WorldTourFinalsRaceCountedResult(
                    event_id=source.event_id,
                    completed_week=source.completed_week,
                    first_publication_week=source.first_publication_week,
                    points=award.race_points,
                    award_fingerprint=award.award_fingerprint,
                )
            )

    rows: list[WorldTourFinalsRaceRow] = []
    for player_id, results in sorted(results_by_player.items()):
        counted = tuple(
            sorted(results, key=lambda item: (-item.points, item.event_id))[
                :best_result_count
            ]
        )
        token = _hash(
            {
                "schema_version": "world_tour_finals_race_tie_break.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "season_index": season_index,
                "player_id": player_id,
            }
        )
        rows.append(
            WorldTourFinalsRaceRow(
                rank=1,
                player_id=player_id,
                race_points=sum(item.points for item in counted),
                counted_results=counted,
                tie_break_token=token,
            )
        )

    ordered = sorted(rows, key=_row_sort_key)
    ranked = tuple(
        row.model_copy(update={"rank": index})
        for index, row in enumerate(ordered, start=1)
    )
    return WorldTourFinalsRaceSnapshot(
        run_id=run_id,
        branch_id=branch_id,
        season_index=season_index,
        cutoff_week=cutoff_week,
        cutoff_ranking_fingerprint=cutoff_ranking_fingerprint,
        best_result_count=best_result_count,
        eligible_event_ids=eligible,
        calendar_projection_fingerprint=calendar_projection_fingerprint,
        source_tournament_fingerprints=tuple(sorted(source_fingerprints)),
        rows=ranked,
        command_id=command_id,
    )
