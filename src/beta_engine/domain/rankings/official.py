"""Pure Official Ranking calculation; publication belongs to Week Transition.

Inputs are authoritative, historically resolved records for one Run/Branch.
This module never reads active-player point totals or mutates stored history.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer


class FrozenInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class RankingWeek(FrozenInput):
    season_index: int = Field(ge=0, le=49)
    week: int = Field(ge=1, le=61)

    @property
    def ordinal(self) -> int:
        return self.season_index * 61 + self.week - 1


class DisciplinaryZero(FrozenInput):
    zero_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=1)
    effective_week: RankingWeek
    duration_weeks: int = Field(ge=1)

    def active_at(self, week: RankingWeek) -> bool:
        return 0 <= week.ordinal - self.effective_week.ordinal < self.duration_weeks


class WithDisciplinaryZeros(FrozenInput):
    disciplinary_zeros: tuple[DisciplinaryZero, ...] = ()

    @model_serializer(mode="wrap")
    def serialize_zeros(self, handler):
        data = handler(self)
        if not self.disciplinary_zeros:
            data.pop("disciplinary_zeros", None)
        return data


class OfficialRankingPolicy(FrozenInput):
    policy_id: str = Field(min_length=1)
    best_n: int = Field(default=15, ge=1)
    tie_break_version: Literal["result_profile_age_previous_token.v1"] = (
        "result_profile_age_previous_token.v1"
    )


def propose_next_season_policy(
    *,
    policy_id: str,
    previous_effective: OfficialRankingPolicy,
    best_n_override: int | None = None,
) -> OfficialRankingPolicy:
    """Materialize the next season's initial proposal from its predecessor.

    This does not propagate later edits through already authored future plans.
    The caller supplies the actual previous season's historically effective policy.
    """
    return OfficialRankingPolicy(
        policy_id=policy_id,
        best_n=previous_effective.best_n
        if best_n_override is None
        else best_n_override,
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


class OfficialRankingRow(WithDisciplinaryZeros):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    points: int = Field(ge=0)
    counted_results: tuple[OfficialRankingResult, ...]

    @model_validator(mode="after")
    def validate_counted_results(self) -> OfficialRankingRow:
        if any(z.player_id != self.player_id for z in self.disciplinary_zeros):
            raise ValueError("Disciplinary zero belongs to another player")
        if self.disciplinary_zeros != tuple(sorted(self.disciplinary_zeros, key=lambda z: z.zero_id)) or len({z.zero_id for z in self.disciplinary_zeros}) != len(self.disciplinary_zeros):
            raise ValueError("Disciplinary zeros must have unique canonical identities")
        if any(r.player_id != self.player_id for r in self.counted_results):
            raise ValueError("Counted result belongs to another player")
        editions = [r.edition_id for r in self.counted_results]
        if len(set(editions)) != len(editions):
            raise ValueError("Duplicate counted Edition")
        if self.points != sum(r.points for r in self.counted_results):
            raise ValueError("Ranking total differs from counted results")
        return self


class OfficialRankingSnapshot(FrozenInput):
    schema_version: Literal["official_ranking_calculation.v1"] = (
        "official_ranking_calculation.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    policy: OfficialRankingPolicy
    previous_fingerprint: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: tuple[OfficialRankingRow, ...]

    @model_validator(mode="after")
    def validate_snapshot_structure(self) -> OfficialRankingSnapshot:
        if tuple(row.rank for row in self.rows) != tuple(range(1, len(self.rows) + 1)):
            raise ValueError("Ranking positions must be contiguous and ordered")
        ids = [row.player_id for row in self.rows]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate ranking player")
        if any(a.points < b.points for a, b in zip(self.rows, self.rows[1:])):
            raise ValueError("Ranking points must be descending")
        zero_ids = [z.zero_id for row in self.rows for z in row.disciplinary_zeros]
        if len(set(zero_ids)) != len(zero_ids):
            raise ValueError("Duplicate disciplinary zero identity across ranking rows")
        for row in self.rows:
            for zero in row.disciplinary_zeros:
                if (zero.run_id, zero.branch_id) != (self.run_id, self.branch_id) or not zero.active_at(self.week):
                    raise ValueError("Disciplinary zero has invalid scope or effective week")
            if len(row.counted_results) > max(0, self.policy.best_n - len(row.disciplinary_zeros)):
                raise ValueError("Counted results exceed Best N")
            if row.counted_results != tuple(
                sorted(
                    row.counted_results,
                    key=lambda r: (
                        -r.points,
                        -r.completed_week.ordinal,
                        r.edition_id,
                    ),
                )
            ):
                raise ValueError("Counted result profile is not canonical")
            for result in row.counted_results:
                age = self.week.ordinal - result.first_publication_week.ordinal
                if not result.ranked or not 0 <= age < result.validity_weeks:
                    raise ValueError("Counted result is not eligible at snapshot week")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_official_ranking_snapshot(
    payload: str,
    *,
    expected_fingerprint: str,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
) -> OfficialRankingSnapshot:
    """Validate stored bytes against independently supplied identity and hash.

    Does not rerun ranking, resolve source provenance or authorize publication.
    The expected hash must come from trusted revision/storage metadata, not be
    recalculated from the same untrusted payload by the caller.
    """
    snapshot = OfficialRankingSnapshot.model_validate_json(payload)
    if (snapshot.run_id, snapshot.branch_id, snapshot.week) != (
        run_id,
        branch_id,
        week,
    ):
        raise ValueError("Stored ranking scope or week does not match request")
    if snapshot.fingerprint != expected_fingerprint:
        raise ValueError("Stored ranking fingerprint mismatch")
    return snapshot


def ranking_order_key(player, counted, previous_ranks, best_n):
    """Shared canonical ordering for calculation and historical explanations."""
    point_profile = tuple(-r.points for r in counted)
    point_profile += (0,) * (best_n - len(counted))
    age_profile = tuple(-r.completed_week.ordinal for r in counted)
    age_profile += (1,) * (best_n - len(counted))
    points = sum(r.points for r in counted)
    if points == 0:
        age_profile = ()
    return (
        -points, point_profile, age_profile,
        previous_ranks.get(player.player_id, float("inf")), player.tie_break_token,
    )


def calculate_official_ranking(
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[OfficialRankingPlayer, ...],
    results: tuple[OfficialRankingResult, ...],
    previous: OfficialRankingSnapshot | None = None,
    disciplinary_zeros: tuple[DisciplinaryZero, ...] = (),
) -> OfficialRankingSnapshot:
    """Calculate an immutable candidate; caller validates/commits the transition.

    Previous must be the immediately preceding week in the same scope. A missing
    previous is for explicit bootstrap only, not permission to skip publication.
    Tokens must already be persisted and unique; calculation draws no randomness.
    Resolved mandatory zeros are supported; point deductions and Season Closing Ranking are not.
    """
    if previous is not None:
        # model_copy(update=...) can bypass Pydantic validation. Never propagate
        # a malformed previous row into tie-breaking or the history hash chain.
        previous = OfficialRankingSnapshot.model_validate_json(
            previous.model_dump_json()
        )
    if previous is not None and (
        previous.run_id != run_id
        or previous.branch_id != branch_id
        or previous.week.ordinal + 1 != week.ordinal
    ):
        raise ValueError(
            "Previous snapshot must be the preceding week in the same Run/Branch"
        )
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

    zeros = tuple(DisciplinaryZero.model_validate_json(z.model_dump_json()) for z in disciplinary_zeros)
    if len({z.zero_id for z in zeros}) != len(zeros):
        raise ValueError("Duplicate disciplinary zero identity")
    if any((z.run_id, z.branch_id) != (run_id, branch_id) or z.player_id not in known_players for z in zeros):
        raise ValueError("Disciplinary zero has unknown player or mismatched scope")
    active_zeros = {p: tuple(sorted((z for z in zeros if z.player_id == p and z.active_at(week)), key=lambda z: z.zero_id)) for p in known_players}

    previous_ranks = (
        {row.player_id: row.rank for row in previous.rows} if previous else {}
    )
    by_player: dict[str, list[OfficialRankingResult]] = {
        p.player_id: [] for p in players
    }
    for result in results:
        age = week.ordinal - result.first_publication_week.ordinal
        if result.ranked and 0 <= age < result.validity_weeks:
            by_player[result.player_id].append(result)

    candidates = []
    for player in players:
        # A new Tour entrant becomes classified only in the next week's snapshot.
        if player.retired or player.tour_entry_week.ordinal >= week.ordinal:
            continue
        counted = tuple(
            sorted(
                by_player[player.player_id],
                key=lambda r: (
                    -r.points,
                    -r.completed_week.ordinal,
                    r.edition_id,
                ),
            )[: max(0, policy.best_n - len(active_zeros[player.player_id]))]
        )
        points = sum(r.points for r in counted)
        key = ranking_order_key(player, counted, previous_ranks, policy.best_n)
        candidates.append((key, player.player_id, points, counted))
    candidates.sort(key=lambda item: item[0])
    return OfficialRankingSnapshot(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        policy=policy,
        previous_fingerprint=previous.fingerprint if previous else None,
        input_fingerprint=_fingerprint(
            {
                **({"disciplinary_zeros": [z.model_dump(mode="json") for z in sorted(zeros, key=lambda z: z.zero_id)]} if zeros else {}),
                "players": [
                    p.model_dump(mode="json")
                    for p in sorted(players, key=lambda p: p.player_id)
                ],
                "results": [
                    r.model_dump(mode="json")
                    for r in sorted(results, key=lambda r: (r.edition_id, r.player_id))
                ],
            }
        ),
        rows=tuple(
            OfficialRankingRow(
                rank=i, player_id=pid, points=points, counted_results=counted, disciplinary_zeros=active_zeros[pid]
            )
            for i, (_, pid, points, counted) in enumerate(candidates, start=1)
        ),
    )
