"""Read-only Viewer projection of Saved Run Calendar Packages."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.calendar.season_labels import season_start_year_from_label
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import PackageType, RunPackageState


class ViewerCalendarResultSummary(BaseModel):
    champion_player_id: str = Field(min_length=1)
    finalist_player_id: str = Field(min_length=1)
    match_count: int = Field(ge=0)


class ViewerCalendarEvent(BaseModel):
    event_id: str = Field(min_length=1)
    season: str = Field(min_length=1)
    season_index: int = Field(ge=0)
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = None
    year_week: int | None = Field(default=None, ge=1, le=61)
    template_id: str = Field(min_length=1)
    event_name: str
    category: str
    tour_level: str | None = None
    host_country: str = Field(min_length=3, max_length=3)
    host_city: str | None = None
    region: str
    main_draw_size: int = Field(ge=0, le=128)
    qualification_draw_size: int = Field(ge=0)
    qualifier_spots: int = Field(ge=0)
    wild_card_slots: int = Field(ge=0)
    bye_slots: int = Field(ge=0)
    ranking_status: str
    source_status: str
    result: ViewerCalendarResultSummary | None = None

    @property
    def completed(self) -> bool:
        return self.result is not None


class ViewerRunCalendar(BaseModel):
    schema_version: Literal["viewer_run_calendar.v1"] = "viewer_run_calendar.v1"
    product_run_id: str
    viewer_branch_id: str
    calendar_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    events: tuple[ViewerCalendarEvent, ...]


def resolve_viewer_run_calendar(
    package_state: RunPackageState | None,
    ranking: RankingRevisionState | None,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerRunCalendar:
    if package_state is None:
        raise KeyError("Viewer Saved Revision has no Run Package state")
    if (package_state.run_id, package_state.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Run Package state scope differs from Viewer Branch")

    package_ids = sorted(
        {
            version.package_id
            for version in package_state.package_versions
            if version.package_type == PackageType.CALENDAR
        }
    )
    if not package_ids:
        raise KeyError("Viewer Saved Revision has no Calendar Package")

    result_by_event: dict[str, ViewerCalendarResultSummary] = {}
    if ranking is not None:
        if (ranking.run_id, ranking.branch_id) != (run_id, branch_id):
            raise ValueError("Saved Ranking scope differs from Viewer Branch")
        for source in ranking.tournament_sources:
            result = source.canonical_result
            if result is None:
                continue
            event_id = source.binding.event_id
            if event_id in result_by_event:
                raise ValueError("Viewer Tournament Result source identity is ambiguous")
            result_by_event[event_id] = ViewerCalendarResultSummary(
                champion_player_id=result.champion_player_id,
                finalist_player_id=result.finalist_player_id,
                match_count=len(result.matches),
            )

    rows: list[ViewerCalendarEvent] = []
    seen_event_ids: set[str] = set()
    for package_id in package_ids:
        projection = CalendarPackageRunAdapter.project_calendar(
            package_state, package_id=package_id
        )
        for event in projection.calendar.events:
            if event.event_id in seen_event_ids:
                raise ValueError(
                    f"Viewer Calendar contains duplicate event identity {event.event_id!r}"
                )
            seen_event_ids.add(event.event_id)
            start_year = season_start_year_from_label(str(event.season))
            season_index = start_year - 2000
            if season_index < 0 or season_index > 49:
                raise ValueError("Viewer Calendar season is outside the Run timeline")
            rows.append(
                ViewerCalendarEvent(
                    event_id=event.event_id,
                    season=str(event.season),
                    season_index=season_index,
                    season_week=event.season_week,
                    calendar_year=event.calendar_year,
                    year_week=event.year_week,
                    template_id=event.template_id,
                    event_name=event.event_name,
                    category=event.category,
                    tour_level=(
                        event.tour_level.value
                        if hasattr(event.tour_level, "value")
                        else event.tour_level
                    ),
                    host_country=event.host_country,
                    host_city=event.host_city,
                    region=event.region,
                    main_draw_size=event.main_draw_size,
                    qualification_draw_size=event.qualification_draw_size,
                    qualifier_spots=event.qualifier_spots,
                    wild_card_slots=event.wild_cards,
                    bye_slots=event.byes,
                    ranking_status=(
                        event.ranking_status.value
                        if hasattr(event.ranking_status, "value")
                        else str(event.ranking_status)
                    ),
                    source_status=event.status,
                    result=result_by_event.get(event.event_id),
                )
            )

    rows.sort(key=lambda row: (row.season_index, row.season_week, row.event_id))
    return ViewerRunCalendar(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        calendar_count=len(package_ids),
        event_count=len(rows),
        events=tuple(rows),
    )
