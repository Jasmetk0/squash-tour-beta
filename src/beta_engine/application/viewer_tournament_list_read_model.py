"""Canonical Saved-Revision tournament list for Viewer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import PackageType, RunPackageState


class ViewerTournamentListItem(BaseModel):
    event_id: str = Field(min_length=1)
    season: str = Field(min_length=1)
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = None
    year_week: int | None = Field(default=None, ge=1, le=61)
    template_id: str = Field(min_length=1)
    event_name: str
    category: str
    tour_level: str | None = None
    host_country: str = Field(min_length=3, max_length=3)
    host_city: str | None = None
    sporting_status: Literal["scheduled", "completed"]
    result_available: bool
    champion_player_id: str | None = None
    finalist_player_id: str | None = None


class ViewerTournamentList(BaseModel):
    schema_version: Literal["viewer_tournament_list.v1"] = "viewer_tournament_list.v1"
    product_run_id: str
    viewer_branch_id: str
    tournament_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    tournaments: tuple[ViewerTournamentListItem, ...]


def resolve_viewer_tournament_list(
    package_state: RunPackageState | None,
    ranking: RankingRevisionState | None,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerTournamentList:
    if package_state is None:
        return ViewerTournamentList(
            product_run_id=run_id,
            viewer_branch_id=branch_id,
            tournament_count=0,
            completed_count=0,
            tournaments=(),
        )
    if (package_state.run_id, package_state.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Run Package state scope differs from Viewer Branch")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (
        run_id,
        branch_id,
    ):
        raise ValueError("Saved Ranking scope differs from Viewer Branch")

    calendar_package_ids = tuple(
        sorted(
            {
                version.package_id
                for version in package_state.package_versions
                if version.package_type == PackageType.CALENDAR
            }
        )
    )

    canonical_results = {}
    if ranking is not None:
        for source in ranking.tournament_sources:
            result = source.canonical_result
            if result is None:
                continue
            if (result.run_id, result.branch_id) != (run_id, branch_id):
                raise ValueError(
                    "Canonical Tournament Result scope differs from Viewer Branch"
                )
            if result.event_id in canonical_results:
                raise ValueError(
                    f"Canonical Tournament Result identity is ambiguous for {result.event_id!r}"
                )
            canonical_results[result.event_id] = result

    items: list[ViewerTournamentListItem] = []
    seen_event_ids: set[str] = set()
    for package_id in calendar_package_ids:
        projection = CalendarPackageRunAdapter.project_calendar(
            package_state,
            package_id=package_id,
        )
        if (projection.run_id, projection.branch_id) != (run_id, branch_id):
            raise ValueError("Run Calendar projection scope differs from Viewer Branch")

        for event in projection.calendar.events:
            if event.event_id in seen_event_ids:
                raise ValueError(
                    f"Viewer tournament list contains duplicate event {event.event_id!r}"
                )
            seen_event_ids.add(event.event_id)
            result = canonical_results.get(event.event_id)
            items.append(
                ViewerTournamentListItem(
                    event_id=event.event_id,
                    season=str(event.season),
                    season_week=event.season_week,
                    calendar_year=event.calendar_year,
                    year_week=event.year_week,
                    template_id=event.template_id,
                    event_name=event.event_name,
                    category=event.category,
                    tour_level=(
                        str(event.tour_level.value)
                        if hasattr(event.tour_level, "value")
                        else (str(event.tour_level) if event.tour_level is not None else None)
                    ),
                    host_country=event.host_country,
                    host_city=event.host_city,
                    sporting_status="completed" if result is not None else "scheduled",
                    result_available=result is not None,
                    champion_player_id=(
                        result.champion_player_id if result is not None else None
                    ),
                    finalist_player_id=(
                        result.finalist_player_id if result is not None else None
                    ),
                )
            )

    ordered = tuple(
        sorted(
            items,
            key=lambda item: (
                item.calendar_year if item.calendar_year is not None else 9999,
                item.year_week if item.year_week is not None else 99,
                item.season,
                item.season_week,
                item.event_id,
            ),
        )
    )
    completed_count = sum(item.sporting_status == "completed" for item in ordered)
    return ViewerTournamentList(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        tournament_count=len(ordered),
        completed_count=completed_count,
        tournaments=ordered,
    )
