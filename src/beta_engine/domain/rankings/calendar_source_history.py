"""Calendar-owned immutable ranking result/discipline source history.

A pure, read-only resolver. These records are NOT legacy RankingResultVersion or
RankingZeroVersion, and do not authorize a sporting writer or publication.
Callers must obtain the versions from a trusted, separately verified source.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarDisciplinaryZero,
    CalendarRankingResult,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import FrozenInput


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CalendarRankingResultVersion(FrozenInput):
    schema_version: Literal["calendar_ranking_result_version.v1"] = (
        "calendar_ranking_result_version.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    effective_week: CalendarRankingWeek
    result: CalendarRankingResult
    previous_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class CalendarRankingZeroVersion(FrozenInput):
    schema_version: Literal["calendar_ranking_zero_version.v1"] = (
        "calendar_ranking_zero_version.v1"
    )
    effective_week: CalendarRankingWeek
    zero: CalendarDisciplinaryZero
    previous_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class ResolvedCalendarRankingSources(FrozenInput):
    """As-of manifest; fingerprint covers effective versions, not future edits."""

    run_id: str
    branch_id: str
    week: CalendarRankingWeek
    results: tuple[CalendarRankingResult, ...]
    disciplinary_zeros: tuple[CalendarDisciplinaryZero, ...]
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def _week(calendar: RunCalendar, week: CalendarRankingWeek) -> int:
    return calendar.ordinal(week.season_index, week.week)


def resolve_calendar_ranking_sources(
    *,
    run_calendar: RunCalendar,
    run_id: str,
    branch_id: str,
    week: CalendarRankingWeek,
    result_versions: tuple[CalendarRankingResultVersion, ...] = (),
    zero_versions: tuple[CalendarRankingZeroVersion, ...] = (),
) -> ResolvedCalendarRankingSources:
    """Verify complete hash-linked correction histories and resolve an exact week.

    All versions, including later ones, must be valid and canonically ordered.
    The returned manifest contains only the latest decisions effective at the
    requested week. No version may move original completion/publication, zero
    origin, scope, or validity. Durations are literal weeks.
    """
    if run_calendar.schema_version != "run_calendar.v1":
        raise ValueError("Calendar ranking sources require a versioned Run clock")
    if not run_id or not branch_id:
        raise ValueError("Calendar ranking source scope is required")
    target = _week(run_calendar, week)

    result_versions = tuple(
        CalendarRankingResultVersion.model_validate_json(v.model_dump_json())
        for v in result_versions
    )
    zero_versions = tuple(
        CalendarRankingZeroVersion.model_validate_json(v.model_dump_json())
        for v in zero_versions
    )
    result_order = tuple(sorted(
        result_versions,
        key=lambda v: (
            v.result.edition_id, v.result.player_id,
            _week(run_calendar, v.effective_week),
        ),
    ))
    if result_versions != result_order:
        raise ValueError("Calendar ranking result source order is not canonical")
    zero_order = tuple(sorted(
        zero_versions,
        key=lambda v: (v.zero.zero_id, _week(run_calendar, v.effective_week)),
    ))
    if zero_versions != zero_order:
        raise ValueError("Calendar ranking zero source order is not canonical")

    latest_results: dict[tuple[str, str], CalendarRankingResultVersion] = {}
    visible_results: dict[tuple[str, str], CalendarRankingResultVersion] = {}
    for version in result_versions:
        if (version.run_id, version.branch_id) != (run_id, branch_id):
            raise ValueError("Calendar ranking result source scope mismatch")
        result = version.result
        key = (result.edition_id, result.player_id)
        completed = _week(run_calendar, result.completed_week)
        published = _week(run_calendar, result.first_publication_week)
        effective = _week(run_calendar, version.effective_week)
        if not completed < published <= effective:
            raise ValueError("Calendar ranking result must follow completion and publication")
        previous = latest_results.get(key)
        if previous is None:
            if version.previous_fingerprint is not None or effective != published:
                raise ValueError("Initial calendar ranking result lacks its publication origin")
        else:
            if (
                version.previous_fingerprint != previous.fingerprint
                or effective <= _week(run_calendar, previous.effective_week)
            ):
                raise ValueError("Calendar ranking result correction lineage is invalid")
            if any(
                getattr(result, field) != getattr(previous.result, field)
                for field in ("completed_week", "first_publication_week", "validity_weeks")
            ):
                raise ValueError("Calendar ranking correction changes original timing")
        latest_results[key] = version
        if effective <= target:
            visible_results[key] = version

    latest_zeros: dict[str, CalendarRankingZeroVersion] = {}
    visible_zeros: dict[str, CalendarRankingZeroVersion] = {}
    for version in zero_versions:
        zero = version.zero
        if (zero.run_id, zero.branch_id) != (run_id, branch_id):
            raise ValueError("Calendar ranking zero source scope mismatch")
        effective = _week(run_calendar, version.effective_week)
        origin = _week(run_calendar, zero.effective_week)
        if effective < origin:
            raise ValueError("Calendar ranking zero version precedes its original week")
        previous = latest_zeros.get(zero.zero_id)
        if previous is None:
            if version.previous_fingerprint is not None or effective != origin:
                raise ValueError("Initial calendar ranking zero lacks its effective origin")
        else:
            if (
                version.previous_fingerprint != previous.fingerprint
                or effective <= _week(run_calendar, previous.effective_week)
            ):
                raise ValueError("Calendar ranking zero correction lineage is invalid")
            if any(
                getattr(zero, field) != getattr(previous.zero, field)
                for field in (
                    "run_id", "branch_id", "zero_id", "player_id", "effective_week"
                )
            ):
                raise ValueError("Calendar ranking zero correction changes original identity")
        latest_zeros[zero.zero_id] = version
        if effective <= target:
            visible_zeros[zero.zero_id] = version

    active_result_versions = [
        visible_results[key] for key in sorted(visible_results)
    ]
    active_zero_versions = [
        visible_zeros[key] for key in sorted(visible_zeros)
    ]
    return ResolvedCalendarRankingSources(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        results=tuple(v.result for v in active_result_versions),
        disciplinary_zeros=tuple(v.zero for v in active_zero_versions),
        source_fingerprint=_fingerprint({
            "run_id": run_id,
            "branch_id": branch_id,
            "week": week.model_dump(mode="json"),
            "run_calendar": run_calendar.to_metadata(),
            "results": [v.model_dump(mode="json") for v in active_result_versions],
            "zeros": [v.model_dump(mode="json") for v in active_zero_versions],
        }),
    )
