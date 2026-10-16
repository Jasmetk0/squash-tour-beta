"""Read-only target math for the selected Run/Branch Saved calendar.

Never changes the live sporting Position, starts a Full Simulation task, extends
the Run, modifies a Working Draft or touches immutable history. An explicit
requested origin is a planning input, not a claimed current sporting week.
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import (
    require_supported_full_simulation_calendar,
    resolve_saved_run_calendar,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition


def _planned_week(calendar: RunCalendar, position: RunCalendarPosition) -> dict:
    return {
        **asdict(position),
        "season_label": calendar.label(position.season_index),
        "week_ordinal": calendar.ordinal(position.season_index, position.season_week),
    }


def preview_run_calendar_configuration(calendar: RunCalendar) -> dict:
    """Preview creation inputs without reading or creating any world state."""

    try:
        require_supported_full_simulation_calendar(calendar)
    except ValueError:
        supported = False
    else:
        supported = True
    return {
        "schema_version": "run_calendar_configuration_preview.v1",
        "read_only": True,
        "run_created": False,
        "run_calendar": calendar.to_metadata(),
        "first_week": _planned_week(calendar, calendar.season_to_calendar(0, 1)),
        "last_week": _planned_week(calendar, calendar.season_to_calendar(
            calendar.season_count - 1, calendar.weeks_per_year
        )),
        "sporting_calendar_supported": supported,
        "limitations": [] if supported else ["sporting_calendar_execution_not_supported_yet"],
    }


def preview_saved_run_calendar_target(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    season_index: int,
    week: int,
    advance_weeks: int = 0,
) -> dict:
    """Project a future week using the hash-verified Run clock, not RankingWeek."""

    calendar = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
    start = calendar.season_to_calendar(season_index, week)
    target = calendar.advance_weeks(season_index, week, advance_weeks)
    last = calendar.season_to_calendar(
        calendar.season_count - 1, calendar.weeks_per_year
    )
    try:
        require_supported_full_simulation_calendar(calendar)
    except ValueError:
        full_simulation_preview_supported = False
    else:
        full_simulation_preview_supported = True

    return {
        "schema_version": "run_calendar_target_preview.v1",
        "run_id": run_id,
        "branch_id": branch_id,
        "source": "selected_branch_saved_run_calendar",
        "planning_only": True,
        "current_sporting_position_claimed": False,
        "full_simulation_preview_supported": full_simulation_preview_supported,
        "run_calendar": {
            "schema_version": calendar.schema_version,
            "weeks_per_year": calendar.weeks_per_year,
            "season_start_year_week": calendar.season_start_year_week,
            "start_year": calendar.start_year,
            "season_count": calendar.season_count,
        },
        "start": _planned_week(calendar, start),
        "advance_weeks": advance_weeks,
        "target": _planned_week(calendar, target),
        "last_run_week": _planned_week(calendar, last),
        "remaining_weeks_including_current": (
            calendar.remaining_weeks_including_current(season_index, week)
        ),
    }
