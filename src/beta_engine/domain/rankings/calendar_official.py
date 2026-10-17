"""Calendar-scoped Official Ranking candidate, never a publication command.

This schema is intentionally separate from historical FAX v1 snapshots. Saved
v1 hashes, old 61-week ordinals and RankingWeek validators remain unchanged.
No score/match is simulated; inputs must be resolved by a trusted caller.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.official import (
    FrozenInput, OfficialRankingPolicy,
)


def _hash(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CalendarRankingWeek(FrozenInput):
    season_index: int = Field(ge=0)
    week: int = Field(ge=1)


class CalendarRankingPlayer(FrozenInput):
    player_id: str = Field(min_length=1)
    tie_break_token: str = Field(min_length=1)
    tour_entry_week: CalendarRankingWeek
    retired: bool = False


class CalendarRankingResult(FrozenInput):
    """A resolved result, with publication/age controlled by its Run clock."""

    edition_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=1)
    completed_week: CalendarRankingWeek
    first_publication_week: CalendarRankingWeek
    qualification_points: int = Field(default=0, ge=0)
    main_points: int = Field(default=0, ge=0)
    validity_weeks: int | None = Field(default=None, ge=1)
    ranked: bool = True
    terminal_status: Literal["completed", "abandoned"] = "completed"

    @property
    def points(self) -> int:
        return self.qualification_points + self.main_points


class CalendarDisciplinaryZero(FrozenInput):
    zero_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=1)
    effective_week: CalendarRankingWeek
    duration_weeks: int = Field(ge=1)


class CalendarRankingRow(FrozenInput):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    points: int = Field(ge=0)
    counted_results: tuple[CalendarRankingResult, ...]
    disciplinary_zeros: tuple[CalendarDisciplinaryZero, ...] = ()

    @model_validator(mode="after")
    def validate_local_consistency(self):
        if self.points != sum(result.points for result in self.counted_results):
            raise ValueError("Calendar ranking row points do not equal counted results")
        if len({result.edition_id for result in self.counted_results}) != len(self.counted_results):
            raise ValueError("Duplicate counted Edition")
        if any(result.player_id != self.player_id for result in self.counted_results):
            raise ValueError("Counted result belongs to another player")
        if any(zero.player_id != self.player_id for zero in self.disciplinary_zeros):
            raise ValueError("Disciplinary zero belongs to another player")
        if (
            self.disciplinary_zeros != tuple(sorted(self.disciplinary_zeros, key=lambda z: z.zero_id))
            or len({zero.zero_id for zero in self.disciplinary_zeros}) != len(self.disciplinary_zeros)
        ):
            raise ValueError("Invalid canonical disciplinary zero IDs")
        return self


class CalendarOfficialRankingSnapshot(FrozenInput):
    """Versioned candidate; separately signed from historical v1 publications."""

    schema_version: Literal["calendar_official_ranking_candidate.v1"] = (
        "calendar_official_ranking_candidate.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    run_calendar: dict[str, int | str]
    week: CalendarRankingWeek
    policy: OfficialRankingPolicy
    previous_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: tuple[CalendarRankingRow, ...]

    @model_validator(mode="after")
    def validate_snapshot(self):
        calendar = RunCalendar.from_metadata(self.run_calendar)
        clock = _ordinal(calendar, self.week)
        if tuple(row.rank for row in self.rows) != tuple(range(1, len(self.rows) + 1)):
            raise ValueError("Calendar ranking positions are not canonical")
        if len({row.player_id for row in self.rows}) != len(self.rows):
            raise ValueError("Duplicate ranked player")
        if any(a.points < b.points for a, b in zip(self.rows, self.rows[1:])):
            raise ValueError("Calendar ranking points are not descending")
        all_zero_ids: set[str] = set()
        for row in self.rows:
            if len(row.counted_results) > max(0, self.policy.best_n - len(row.disciplinary_zeros)):
                raise ValueError("Counted results exceed Best N after zeros")
            ordering = tuple(sorted(
                row.counted_results,
                key=lambda r: (-r.points, -_ordinal(calendar, r.completed_week), r.edition_id),
            ))
            if ordering != row.counted_results:
                raise ValueError("Counted result profile is not canonical")
            for result in row.counted_results:
                age = clock - _ordinal(calendar, result.first_publication_week)
                if (
                    _ordinal(calendar, result.completed_week)
                    >= _ordinal(calendar, result.first_publication_week)
                    or not result.ranked or not 0 <= age < _validity(calendar, result)
                ):
                    raise ValueError("Counted result is ineligible for this calendar week")
            for zero in row.disciplinary_zeros:
                age = clock - _ordinal(calendar, zero.effective_week)
                if (
                    (zero.run_id, zero.branch_id) != (self.run_id, self.branch_id)
                    or zero.zero_id in all_zero_ids
                    or not 0 <= age < zero.duration_weeks
                ):
                    raise ValueError("Disciplinary zero is ineligible or has duplicate identity")
                all_zero_ids.add(zero.zero_id)
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def _ordinal(calendar: RunCalendar, week: CalendarRankingWeek) -> int:
    return calendar.ordinal(week.season_index, week.week)


def _validity(calendar: RunCalendar, result: CalendarRankingResult) -> int:
    return result.validity_weeks if result.validity_weeks is not None else calendar.weeks_per_year


def load_calendar_official_ranking_candidate(
    payload: str, *, expected_fingerprint: str, run_id: str,
    branch_id: str, week: CalendarRankingWeek, run_calendar: RunCalendar,
) -> CalendarOfficialRankingSnapshot:
    """Validate external immutable identity/hash; never trust a self-supplied hash."""
    snapshot = CalendarOfficialRankingSnapshot.model_validate_json(payload)
    if (
        snapshot.run_id != run_id or snapshot.branch_id != branch_id
        or snapshot.week != week or snapshot.run_calendar != run_calendar.to_metadata()
    ):
        raise ValueError("Stored calendar ranking candidate scope/clock mismatch")
    if snapshot.fingerprint != expected_fingerprint:
        raise ValueError("Stored calendar ranking candidate fingerprint mismatch")
    return snapshot


def calculate_calendar_official_ranking(
    *,
    run_id: str, branch_id: str, run_calendar: RunCalendar,
    week: CalendarRankingWeek, policy: OfficialRankingPolicy,
    players: tuple[CalendarRankingPlayer, ...],
    results: tuple[CalendarRankingResult, ...],
    previous: CalendarOfficialRankingSnapshot | None = None,
    disciplinary_zeros: tuple[CalendarDisciplinaryZero, ...] = (),
) -> CalendarOfficialRankingSnapshot:
    """Calculate a pure, deterministic Best N candidate with Run W time.

    The caller is responsible for authoritative resolution/provenance of
    players, Edition corrections and disciplinary facts. No publication,
    transition, Save, or writer permissions are granted here.
    """
    if run_calendar.schema_version != "run_calendar.v1":
        raise ValueError("Calendar ranking requires explicit versioned Run clock")
    target = _ordinal(run_calendar, week)
    if previous is not None:
        previous = CalendarOfficialRankingSnapshot.model_validate_json(previous.model_dump_json())
        previous_clock = RunCalendar.from_metadata(previous.run_calendar)
        same_time_basis = (
            previous_clock.schema_version == run_calendar.schema_version
            and previous_clock.weeks_per_year == run_calendar.weeks_per_year
            and previous_clock.season_start_year_week == run_calendar.season_start_year_week
            and previous_clock.start_year == run_calendar.start_year
        )
        # A Run may be extended, never shortened or re-based. The old immutable
        # candidate retains its exact original horizon and fingerprint.
        if (
            (previous.run_id, previous.branch_id) != (run_id, branch_id)
            or not same_time_basis
            or previous_clock.season_count > run_calendar.season_count
            or _ordinal(run_calendar, previous.week) + 1 != target
        ):
            raise ValueError("Previous calendar ranking candidate must be exact preceding week and scope")
    ids = [p.player_id for p in players]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate ranking player identity")
    tokens = [p.tie_break_token for p in players]
    if len(tokens) != len(set(tokens)):
        raise ValueError("Duplicate ranking tie-break token")
    known = set(ids)
    for player in players:
        if _ordinal(run_calendar, player.tour_entry_week) > target:
            raise ValueError("Future Tour entrant is not valid input for this week")
    keys = [(r.edition_id, r.player_id) for r in results]
    if len(keys) != len(set(keys)):
        raise ValueError("One resolved result per Edition/player required")
    if any(r.player_id not in known for r in results):
        raise ValueError("Unknown ranking result player")
    for result in results:
        completed = _ordinal(run_calendar, result.completed_week)
        published = _ordinal(run_calendar, result.first_publication_week)
        if not completed < published <= target:
            raise ValueError("Ranking publication must follow completion without future leakage")
        _validity(run_calendar, result)

    verified_zeros = tuple(
        CalendarDisciplinaryZero.model_validate_json(z.model_dump_json())
        for z in disciplinary_zeros
    )
    if len({z.zero_id for z in verified_zeros}) != len(verified_zeros):
        raise ValueError("Duplicate disciplinary zero identity")
    if any(
        (z.run_id, z.branch_id) != (run_id, branch_id) or z.player_id not in known
        for z in verified_zeros
    ):
        raise ValueError("Disciplinary zero has foreign scope or unknown player")
    active: dict[str, tuple[CalendarDisciplinaryZero, ...]] = {}
    for player in players:
        found = []
        for zero in verified_zeros:
            effective = _ordinal(run_calendar, zero.effective_week)
            if effective > target:
                raise ValueError("Future disciplinary zero cannot enter this snapshot")
            if zero.player_id == player.player_id and target - effective < zero.duration_weeks:
                found.append(zero)
        active[player.player_id] = tuple(sorted(found, key=lambda z: z.zero_id))

    prior_ranks = {r.player_id: r.rank for r in previous.rows} if previous else {}
    by_player = {p: [] for p in ids}
    for result in results:
        age = target - _ordinal(run_calendar, result.first_publication_week)
        if result.ranked and 0 <= age < _validity(run_calendar, result):
            by_player[result.player_id].append(result)

    candidates = []
    for player in players:
        # Same as historical Official Ranking: retiree not classified;
        # newly entering player becomes eligible in the *next* snapshot.
        if player.retired or _ordinal(run_calendar, player.tour_entry_week) >= target:
            continue
        counted = tuple(sorted(
            by_player[player.player_id],
            key=lambda r: (-r.points, -_ordinal(run_calendar, r.completed_week), r.edition_id),
        )[:max(0, policy.best_n - len(active[player.player_id]))])
        profile = tuple(-r.points for r in counted) + (0,) * (policy.best_n - len(counted))
        age_profile = tuple(-_ordinal(run_calendar, r.completed_week) for r in counted)
        age_profile += (1,) * (policy.best_n - len(counted))
        points = sum(r.points for r in counted)
        if points == 0:
            age_profile = ()
        key = (
            -points, profile, age_profile,
            prior_ranks.get(player.player_id, float("inf")),
            player.tie_break_token,
        )
        candidates.append((key, player.player_id, points, counted))
    candidates.sort(key=lambda item: item[0])

    return CalendarOfficialRankingSnapshot(
        run_id=run_id, branch_id=branch_id, run_calendar=run_calendar.to_metadata(),
        week=week, policy=policy,
        previous_fingerprint=previous.fingerprint if previous else None,
        input_fingerprint=_hash({
            **({"disciplinary_zeros": [
                z.model_dump(mode="json") for z in sorted(verified_zeros, key=lambda x: x.zero_id)
            ]} if verified_zeros else {}),
            "players": [p.model_dump(mode="json") for p in sorted(players, key=lambda x: x.player_id)],
            "results": [r.model_dump(mode="json") for r in sorted(results, key=lambda x: (x.edition_id, x.player_id))],
            "run_calendar": run_calendar.to_metadata(),
        }),
        rows=tuple(CalendarRankingRow(
            rank=i, player_id=pid, points=points,
            counted_results=counted, disciplinary_zeros=active[pid],
        ) for i, (_, pid, points, counted) in enumerate(candidates, start=1)),
    )
