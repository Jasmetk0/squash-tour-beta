"""Verified Saved-Run clock gateway for read-only calendar ranking candidates.

The other inputs are already resolved authoritative facts supplied by the caller;
this module never accepts user-authored match outcomes as durable Official facts.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarDisciplinaryZero,
    CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.models import RunBranchModel


def preview_calendar_official_ranking_from_saved_run(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    expected_saved_head_revision_id: str,
    week: CalendarRankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[CalendarRankingPlayer, ...],
    results: tuple[CalendarRankingResult, ...],
    previous: CalendarOfficialRankingSnapshot | None = None,
    disciplinary_zeros: tuple[CalendarDisciplinaryZero, ...] = (),
) -> CalendarOfficialRankingSnapshot:
    """Read only, fail-closed under the caller's coherent SQLite read snapshot.

    This does NOT persist, publish, resolve sporting input provenance or grant
    non-FAX writer permissions. Only a validated Saved clock may be used.
    """
    if not expected_saved_head_revision_id:
        raise ValueError("Expected Saved HEAD is required")
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError("Run/Branch is unavailable for calendar ranking inspection")
    if branch.saved_head_revision_id != expected_saved_head_revision_id:
        raise ValueError("Calendar ranking inspection uses a stale Saved HEAD")

    calendar = resolve_saved_run_calendar(
        session, run_id=run_id, branch_id=branch_id,
    )
    return calculate_calendar_official_ranking(
        run_id=run_id,
        branch_id=branch_id,
        run_calendar=calendar,
        week=week,
        policy=policy,
        players=players,
        results=results,
        previous=previous,
        disciplinary_zeros=disciplinary_zeros,
    )
