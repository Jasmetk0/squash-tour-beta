"""Pure Official Ranking calculation; publication belongs to Week Transition.

Inputs are authoritative, historically resolved records for one Run/Branch.
This module never reads active-player point totals or mutates stored history.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class RankingWeek(FrozenInput):
    season_index: int = Field(ge=0, le=49)
    week: int = Field(ge=1, le=61)

    @property
    def ordinal(self) -> int:
        return self.season_index * 61 + self.week - 1


class OfficialRankingPolicy(FrozenInput):
    policy_id: str = Field(min_length=1)
    best_n: int = Field(default=15, ge=1)
    tie_break_version: Literal["result_profile_age_previous_token.v1"] = "result_profile_age_previous_token.v1"


def propose_next_season_policy(
    *, policy_id: str, previous_effective: OfficialRankingPolicy,
    best_n_override: int | None = None,
) -> OfficialRankingPolicy:
    """Materialize the next season's initial proposal from its predecessor.

    This does not propagate later edits through already authored future plans.
    The caller supplies the actual previous season's historically effective policy.
    """
    return OfficialRankingPolicy(
        policy_id=policy_id,
        best_n=previous_effective.best_n if best_n_override is None else best_n_override,
        tie_break_version=previous_effective.tie_break_version,
    )


class OfficialRankingPlayer(FrozenInput):
    player_id: str = Field(min_length=1)
    tie_break_token: str = Field(min_length=1)
    tour_entry_week: RankingWeek
    retired: bool = False


class OfficialRankingResult(FrozenInput):
    """One final Q + main total per Edition/player, with frozen provenance.

    first_publication_week is the actual initial eligibility boundary, retained
    when a later correction replaces this record. The caller resolves corrections
    and Ranked status at the requested historical boundary before calculation.
    """

    edition_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=1)
    completed_week: RankingWeek
    first_publication_week: RankingWeek
    qualification_points: int = Field(default=0, ge=0)
    main_points: int = Field(default=0, ge=0)
    validity_weeks: int = Field(default=61, ge=1)
    ranked: bool = True
    terminal_status: Literal["completed", "abandoned"] = "completed"

    @model_validator(mode="after")
    def publication_follows_completion(self) -> OfficialRankingResult:
        if self.first_publication_week.ordinal <= self.completed_week.ordinal:
            raise ValueError("Official eligibility must follow the completed week")
        return self

    @property
    def points(self) -> int:
        return self.qualification_points + self.main_points


class OfficialRankingRow(FrozenInput):
    rank: int = Field(ge=1)
    player_id: str
    points: int = Field(ge=0)
    counted_results: tuple[OfficialRankingResult, ...]


class OfficialRankingSnapshot(FrozenInput):
    schema_version: Literal["official_ranking_calculation.v1"] = "official_ranking_calculation.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    policy: OfficialRankingPolicy
    previous_fingerprint: str | None
    input_fingerprint: str
    rows: tuple[OfficialRankingRow, ...]

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def _fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def calculate_official_ranking(
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[OfficialRankingPlayer, ...],
    results: tuple[OfficialRankingResult, ...],
    previous: OfficialRankingSnapshot | None = None,
) -> OfficialRankingSnapshot:
    """Calculate an immutable candidate; caller validates/commits the transition.

    Previous must be the immediately preceding week in the same scope. A missing
    previous is for explicit bootstrap only, not permission to skip publication.
    Tokens must already be persisted and unique; calculation draws no randomness.
    Disciplinary changes and Season Closing Ranking are outside this calculator.
    """
    if previous is not None and (
        previous.run_id != run_id or previous.branch_id != branch_id
        or previous.week.ordinal + 1 != week.ordinal
    ):
        raise ValueError("Previous snapshot must be the preceding week in the same Run/Branch")
    player_ids = [p.player_id for p in players]
    known_players = set(player_ids)
    if len(known_players) != len(player_ids):
        raise ValueError("Duplicate player identity")
    tokens = [p.tie_break_token for p in players]
    if len(set(tokens)) != len(tokens):
        raise ValueError("Ranking tie-break tokens must be unique")
    result_keys = [(r.edition_id, r.player_id) for r in results]
    if len(set(result_keys)) != len(result_keys):
        raise ValueError("One resolved result per Edition/player is required")
    if any(r.player_id not in known_players for r in results):
        raise ValueError("Result references an unknown player")

    previous_ranks = {row.player_id: row.rank for row in previous.rows} if previous else {}
    by_player: dict[str, list[OfficialRankingResult]] = {p.player_id: [] for p in players}
    for result in results:
        age = week.ordinal - result.first_publication_week.ordinal
        if result.ranked and 0 <= age < result.validity_weeks:
            by_player[result.player_id].append(result)

    candidates = []
    for player in players:
        # A new Tour entrant becomes classified only in the next week's snapshot.
        if player.retired or player.tour_entry_week.ordinal >= week.ordinal:
            continue
        counted = tuple(sorted(by_player[player.player_id], key=lambda r: (
            -r.points, -r.completed_week.ordinal, r.edition_id,
        ))[:policy.best_n])
        point_profile = tuple(-r.points for r in counted)
        # Pad zero results so a different result count is not a hidden tie-break.
        point_profile += (0,) * (policy.best_n - len(counted))
        age_profile = tuple(-r.completed_week.ordinal for r in counted)
        age_profile += (1,) * (policy.best_n - len(counted))
        points = sum(r.points for r in counted)
        # Zero-point players use previous classification/token, per Master 18.2.
        if points == 0:
            age_profile = ()
        key = (-points, point_profile, age_profile,
               previous_ranks.get(player.player_id, float("inf")), player.tie_break_token)
        candidates.append((key, player.player_id, points, counted))
    candidates.sort(key=lambda item: item[0])
    return OfficialRankingSnapshot(
        run_id=run_id, branch_id=branch_id, week=week, policy=policy,
        previous_fingerprint=previous.fingerprint if previous else None,
        input_fingerprint=_fingerprint({
            "players": [p.model_dump(mode="json") for p in sorted(players, key=lambda p: p.player_id)],
            "results": [r.model_dump(mode="json") for r in sorted(results, key=lambda r: (r.edition_id, r.player_id))],
        }),
        rows=tuple(OfficialRankingRow(rank=i, player_id=pid, points=points, counted_results=counted)
                   for i, (_, pid, points, counted) in enumerate(candidates, start=1)),
    )
