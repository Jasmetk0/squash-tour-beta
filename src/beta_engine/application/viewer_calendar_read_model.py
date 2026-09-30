"""Canonical read-only Viewer Calendar projected from Saved Run Package state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.calendar_package_run_adapter import (
    CalendarPackageRunAdapter,
)
from beta_engine.domain.run_packages import PackageType, RunPackageState


class ViewerCalendarEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    season: str | int
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = None
    year_week: int | None = Field(default=None, ge=1, le=61)
    template_id: str = Field(min_length=1)
    event_name: str
    category: str
    tour_level: Literal["WORLD_TOUR", "ELITE_TOUR"] | None = None
    host_country: str = Field(min_length=3, max_length=3)
    host_city: str | None = None
    region: str
    duration_in_season_weeks: int = Field(ge=1)
    start_season_week: int = Field(ge=1, le=61)
    end_season_week: int = Field(ge=1)
    status: Literal["planned", "active", "completed", "cancelled", "scheduled"]
    main_draw_size: int = Field(ge=0, le=128)
    qualification_draw_size: int = Field(ge=0)
    seeds_count: int = Field(ge=0)
    qualifier_spots: int = Field(ge=0)
    wild_cards: int = Field(ge=0)
    byes: int = Field(ge=0)
    prestige: float = Field(ge=0)


class ViewerCalendarSeason(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    season: str | int
    event_count: int = Field(ge=0)
    events: tuple[ViewerCalendarEvent, ...]


class ViewerRunCalendar(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["viewer_run_calendar.v1"] = "viewer_run_calendar.v1"
    product_run_id: str
    viewer_branch_id: str
    season_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    seasons: tuple[ViewerCalendarSeason, ...]


def _season_sort_key(value: str | int) -> tuple[int, int, str]:
    text = str(value)
    first = text.split("/", 1)[0]
    try:
        return (0, int(first), text)
    except ValueError:
        return (1, 0, text)


def resolve_viewer_run_calendar(
    state: RunPackageState | None,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerRunCalendar:
    if state is None:
        raise KeyError("Viewer Saved Revision has no Run Package state")
    if (state.run_id, state.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Run Package state scope differs from Viewer Branch")

    package_ids = tuple(
        sorted(
            {
                version.package_id
                for version in state.package_versions
                if version.package_type == PackageType.CALENDAR
            }
        )
    )
    if not package_ids:
        raise KeyError("Viewer Saved Revision has no applied Calendar Package")

    seasons: list[ViewerCalendarSeason] = []
    seen_seasons: set[str] = set()
    seen_event_ids: set[str] = set()

    for package_id in package_ids:
        projection = CalendarPackageRunAdapter.project_calendar(
            state,
            package_id=package_id,
        )
        if (projection.run_id, projection.branch_id) != (run_id, branch_id):
            raise ValueError("Run Calendar projection scope differs from Viewer Branch")

        season_key = str(projection.season)
        if season_key in seen_seasons:
            raise ValueError("Viewer Calendar contains ambiguous duplicate season identity")
        seen_seasons.add(season_key)

        events: list[ViewerCalendarEvent] = []
        for event in projection.calendar.events:
            if event.event_id in seen_event_ids:
                raise ValueError(
                    "Viewer Calendar contains duplicate event identity across seasons"
                )
            seen_event_ids.add(event.event_id)
            if event.start_season_week is None or event.end_season_week is None:
                raise ValueError("Canonical Calendar event week bounds are missing")
            events.append(
                ViewerCalendarEvent(
                    event_id=event.event_id,
                    season=event.season,
                    season_week=event.season_week,
                    calendar_year=event.calendar_year,
                    year_week=event.year_week,
                    template_id=event.template_id,
                    event_name=event.event_name,
                    category=event.category,
                    tour_level=event.tour_level,
                    host_country=event.host_country,
                    host_city=event.host_city,
                    region=event.region,
                    duration_in_season_weeks=event.duration_in_season_weeks,
                    start_season_week=event.start_season_week,
                    end_season_week=event.end_season_week,
                    status=event.status,
                    main_draw_size=event.main_draw_size,
                    qualification_draw_size=event.qualification_draw_size,
                    seeds_count=event.seeds_count,
                    qualifier_spots=event.qualifier_spots,
                    wild_cards=event.wild_cards,
                    byes=event.byes,
                    prestige=event.prestige,
                )
            )

        ordered_events = tuple(
            sorted(events, key=lambda item: (item.season_week, item.event_id))
        )
        seasons.append(
            ViewerCalendarSeason(
                season=projection.calendar.season,
                event_count=len(ordered_events),
                events=ordered_events,
            )
        )

    ordered_seasons = tuple(
        sorted(seasons, key=lambda item: _season_sort_key(item.season))
    )
    return ViewerRunCalendar(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        season_count=len(ordered_seasons),
        event_count=sum(item.event_count for item in ordered_seasons),
        seasons=ordered_seasons,
    )
