"""Read-only Run Home events from the selected Branch's verified Saved Revision.

This intentionally does NOT consult the Viewer Branch or legacy SimulationRun.
Calendar slots are scheduled source facts, not AI predictions or completed results.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.viewer_tournament_history_read_model import (
    resolve_viewer_tournament_history,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState


class HomeCalendarEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    event_name: str
    season: str
    season_index: int = Field(ge=0, le=49)
    week: int = Field(ge=1, le=61)
    category: str
    status: str


class HomePublishedResult(HomeCalendarEvent):
    champion_player_id: str
    finalist_player_id: str


class RunHomeActivity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_home_activity.v1"] = "run_home_activity.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    calendar_status: Literal["empty", "ready", "unpositioned"]
    result_status: Literal["empty", "ready"]
    ranking_changes_status: Literal["unsupported"] = "unsupported"
    total_calendar_events: int = Field(ge=0)
    published_result_count: int = Field(ge=0)
    upcoming: tuple[HomeCalendarEvent, ...]
    recent_results: tuple[HomePublishedResult, ...]


def _season_index(value: str | int) -> int:
    text = str(value)
    year = text.split("/", 1)[0]
    if not year.isdecimal():
        raise ValueError("Calendar season is not a canonical numeric season")
    number = int(year)
    if 0 <= number < 50:
        return number
    if 2000 <= number < 2050:
        return number - 2000
    raise ValueError("Calendar season lies outside 2000/01–2049/50")


def resolve_run_home_activity(
    *,
    run_id: str,
    branch_id: str,
    saved_revision_id: str,
    packages: RunPackageState | None,
    ranking: RankingRevisionState | None,
    current_season: int | None,
    current_week: int | None,
) -> RunHomeActivity:
    if packages is None:
        return RunHomeActivity(
            run_id=run_id,
            branch_id=branch_id,
            saved_revision_id=saved_revision_id,
            calendar_status="empty",
            result_status="empty",
            total_calendar_events=0,
            published_result_count=0,
            upcoming=(),
            recent_results=(),
        )
    if (packages.run_id, packages.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Package identity differs from selected Run/Branch")

    try:
        history = resolve_viewer_tournament_history(
            run_package_state=packages,
            ranking=ranking,
            run_id=run_id,
            branch_id=branch_id,
        )
    except KeyError as exc:
        # A World-only Run with no Calendar is a valid empty state.
        if "no applied Calendar Package" not in str(exc):
            raise
        return RunHomeActivity(
            run_id=run_id,
            branch_id=branch_id,
            saved_revision_id=saved_revision_id,
            calendar_status="empty",
            result_status="empty",
            total_calendar_events=0,
            published_result_count=0,
            upcoming=(),
            recent_results=(),
        )

    ordered = sorted(
        history.tournaments,
        key=lambda item: (_season_index(item.season), item.season_week, item.event_id),
    )
    results = [
        HomePublishedResult(
            event_id=item.event_id,
            event_name=item.event_name,
            season=item.season,
            season_index=_season_index(item.season),
            week=item.season_week,
            category=item.category,
            status=item.ranking_status,
            champion_player_id=item.champion_player_id,
            finalist_player_id=item.finalist_player_id,
        )
        for item in ordered
        if item.result_published
        and item.champion_player_id is not None
        and item.finalist_player_id is not None
    ]
    # Never treat a missing time locator as Week 1. Distinguish this explicitly.
    positioned = current_season is not None and current_week is not None
    if positioned:
        index = _season_index(current_season)
        if not 1 <= current_week <= 61:
            raise ValueError("Branch week lies outside canonical Season Weeks")
        upcoming = [
            HomeCalendarEvent(
                event_id=item.event_id,
                event_name=item.event_name,
                season=item.season,
                season_index=_season_index(item.season),
                week=item.season_week,
                category=item.category,
                status=item.ranking_status,
            )
            for item in ordered
            if (_season_index(item.season), item.season_week) >= (index, current_week)
            and not item.result_published
        ][:5]
    else:
        upcoming = []

    return RunHomeActivity(
        run_id=run_id,
        branch_id=branch_id,
        saved_revision_id=saved_revision_id,
        calendar_status=("empty" if not ordered else "ready" if positioned else "unpositioned"),
        result_status="ready" if results else "empty",
        total_calendar_events=len(ordered),
        published_result_count=history.published_result_count,
        upcoming=tuple(upcoming),
        recent_results=tuple(reversed(results[-5:])),
    )
