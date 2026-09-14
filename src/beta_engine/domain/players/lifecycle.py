"""Pure, historically fingerprinted player lifecycle week state."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingPlayer,
    RankingWeek,
)
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
    season_week_to_year_week,
)

MIN_RUNTIME_PLAYER_AGE = 15
MAX_ACTIVE_TOUR_AGE = 45
MAX_RUNTIME_PLAYER_AGE = 46


def derive_birth_year_from_age(season_start_year: int, age: int) -> int:
    return season_start_year - age


def synthesize_birth_year_week(*, player_id: str, birth_year: int) -> int:
    digest = hashlib.blake2b(
        f"birth-year-week|{player_id}|{birth_year}".encode(), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % 61 + 1


class PlayerLifecycleIdentity(FrozenInput):
    player_id: str = Field(min_length=1)
    birth_year: int = Field(ge=1900, le=2100)
    birth_year_week: int = Field(ge=1, le=61)
    tie_break_token: str = Field(min_length=1)
    tie_break_provenance: str = Field(min_length=1)
    tour_entry_week: RankingWeek | None = None
    age: int = Field(ge=0, le=120)
    status: Literal["active", "retired"]
    retirement_effective_week: RankingWeek | None = None
    origin: str = Field(min_length=1)

    @model_validator(mode="after")
    def retirement_is_coherent(self):
        if (self.status == "retired") != (self.retirement_effective_week is not None):
            raise ValueError("Retirement status and effective week must agree")
        return self


class PlayerLifecycleWeekState(FrozenInput):
    schema_version: Literal["player_lifecycle_week_state.v1"] = (
        "player_lifecycle_week_state.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    players: tuple[PlayerLifecycleIdentity, ...]
    source_initial_world_fingerprint: str = Field(min_length=1)
    predecessor_fingerprint: str | None = None

    @model_validator(mode="after")
    def canonical_roster(self):
        ids = [p.player_id for p in self.players]
        tokens = [p.tie_break_token for p in self.players]
        if ids != sorted(set(ids)) or len(tokens) != len(set(tokens)):
            raise ValueError("Lifecycle players require canonical unique identities")
        if any(
            p.tour_entry_week is not None
            and p.tour_entry_week.ordinal > self.week.ordinal
            for p in self.players
        ):
            raise ValueError("Lifecycle state contains a future Tour entrant")
        position = season_week_to_calendar_position(
            2000 + self.week.season_index, self.week.week
        )
        for player in self.players:
            expected_age = age_at_calendar_position(
                birth_year=player.birth_year,
                birth_year_week=player.birth_year_week,
                calendar_year=position.calendar_year,
                year_week=position.year_week,
            )
            if player.age != expected_age:
                raise ValueError("Lifecycle age differs from canonical birth identity")
            if player.status == "active" and player.age >= 46:
                raise ValueError("Active lifecycle player cannot be age 46 or older")
            if (
                player.retirement_effective_week is not None
                and player.retirement_effective_week.ordinal > self.week.ordinal
            ):
                raise ValueError("Retirement effective week cannot be in the future")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()

    def ranking_roster(self) -> tuple[OfficialRankingPlayer, ...]:
        if any(p.tour_entry_week is None for p in self.players):
            raise ValueError("Player lifecycle has no authoritative Tour-entry week")
        roster = []
        for player in self.players:
            tour_entry_week = player.tour_entry_week
            if tour_entry_week is None:  # narrowed after the complete-state guard
                raise ValueError(
                    "Player lifecycle has no authoritative Tour-entry week"
                )
            roster.append(
                OfficialRankingPlayer(
                    player_id=player.player_id,
                    tie_break_token=player.tie_break_token,
                    tour_entry_week=tour_entry_week,
                    retired=player.status == "retired",
                )
            )
        return tuple(roster)


def advance_lifecycle(
    predecessor: PlayerLifecycleWeekState, target: RankingWeek
) -> PlayerLifecycleWeekState:
    if (
        target.season_index != predecessor.week.season_index
        or target.ordinal != predecessor.week.ordinal + 1
    ):
        raise ValueError(
            "Player lifecycle supports only ordinary same-season Week Transition"
        )
    players = []
    for player in predecessor.players:
        if player.birth_year_week == season_week_to_year_week(target.week):
            age = player.age + 1
            newly_retired = player.status == "active" and age == 46
            player = player.model_copy(
                update={
                    "age": age,
                    "status": "retired" if newly_retired else player.status,
                    "retirement_effective_week": (
                        target if newly_retired else player.retirement_effective_week
                    ),
                }
            )
        players.append(player)
    return PlayerLifecycleWeekState(
        run_id=predecessor.run_id,
        branch_id=predecessor.branch_id,
        week=target,
        players=tuple(players),
        source_initial_world_fingerprint=predecessor.source_initial_world_fingerprint,
        predecessor_fingerprint=predecessor.fingerprint,
    )
