"""Canonical multi-season Viewer tournament list/history."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import PackageType, RunPackageState


class ViewerTournamentHistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    season: str = Field(min_length=1)
    season_week: int = Field(ge=1, le=61)
    event_name: str
    template_id: str = Field(min_length=1)
    category: str
    tour_level: str | None = None
    host_country: str = Field(min_length=3, max_length=3)
    host_city: str | None = None
    region: str = Field(min_length=1)
    main_draw_size: int = Field(ge=0)
    qualification_draw_size: int = Field(ge=0)
    seeds_count: int = Field(ge=0)
    qualifier_spots: int = Field(ge=0)
    wild_cards: int = Field(ge=0)
    byes: int = Field(ge=0)
    ranking_status: str
    result_published: bool
    champion_player_id: str | None = None
    finalist_player_id: str | None = None


class ViewerTournamentHistory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["viewer_tournament_history.v1"] = (
        "viewer_tournament_history.v1"
    )
    product_run_id: str
    viewer_branch_id: str
    tournament_count: int = Field(ge=0)
    published_result_count: int = Field(ge=0)
    tournaments: tuple[ViewerTournamentHistoryItem, ...]


def resolve_viewer_tournament_history(
    *,
    run_package_state: RunPackageState | None,
    ranking: RankingRevisionState | None,
    run_id: str,
    branch_id: str,
) -> ViewerTournamentHistory:
    if run_package_state is None:
        raise KeyError("Viewer Saved Revision has no Run Package state")
    if (run_package_state.run_id, run_package_state.branch_id) != (
        run_id,
        branch_id,
    ):
        raise ValueError("Saved Run Package state scope differs from Viewer Branch")

    calendar_package_ids = sorted(
        {
            version.package_id
            for version in run_package_state.package_versions
            if version.package_type == PackageType.CALENDAR
        }
    )
    if not calendar_package_ids:
        raise KeyError("Viewer Saved Revision has no applied Calendar Package")

    result_by_event: dict[str, object] = {}
    if ranking is not None:
        for source in ranking.tournament_sources:
            binding = source.binding
            if (binding.run_id, binding.branch_id) != (run_id, branch_id):
                raise ValueError(
                    "Saved tournament ranking source scope differs from Viewer Branch"
                )
            if source.canonical_result is None:
                continue
            event_id = binding.event_id
            if event_id in result_by_event:
                raise ValueError(
                    f"Canonical Tournament Result identity is duplicated for {event_id!r}"
                )
            result_by_event[event_id] = source.canonical_result

    events: dict[str, ViewerTournamentHistoryItem] = {}
    for package_id in calendar_package_ids:
        projection = CalendarPackageRunAdapter.project_calendar(
            run_package_state,
            package_id=package_id,
        )
        if (projection.run_id, projection.branch_id) != (run_id, branch_id):
            raise ValueError("Run Calendar projection scope differs from Viewer Branch")
        for event in projection.calendar.events:
            if event.event_id in events:
                raise ValueError(
                    f"Viewer Calendar contains duplicate event identity {event.event_id!r}"
                )
            result = result_by_event.get(event.event_id)
            if result is not None and (
                result.run_id,
                result.branch_id,
                result.event_id,
            ) != (run_id, branch_id, event.event_id):
                raise ValueError(
                    "Canonical Tournament Result scope differs from Calendar event"
                )
            events[event.event_id] = ViewerTournamentHistoryItem(
                event_id=event.event_id,
                season=str(event.season),
                season_week=event.season_week,
                event_name=event.event_name,
                template_id=event.template_id,
                category=event.category,
                tour_level=event.tour_level,
                host_country=event.host_country,
                host_city=event.host_city,
                region=event.region,
                main_draw_size=event.main_draw_size,
                qualification_draw_size=event.qualification_draw_size,
                seeds_count=event.seeds_count,
                qualifier_spots=event.qualifier_spots,
                wild_cards=event.wild_cards,
                byes=event.byes,
                ranking_status=str(event.ranking_status.value),
                result_published=result is not None,
                champion_player_id=(
                    result.champion_player_id if result is not None else None
                ),
                finalist_player_id=(
                    result.finalist_player_id if result is not None else None
                ),
            )

    orphan_results = sorted(set(result_by_event) - set(events))
    if orphan_results:
        raise ValueError(
            "Canonical Tournament Result has no matching saved Calendar event: "
            + ", ".join(orphan_results)
        )

    ordered = tuple(
        sorted(
            events.values(),
            key=lambda item: (item.season, item.season_week, item.event_id),
        )
    )
    return ViewerTournamentHistory(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        tournament_count=len(ordered),
        published_result_count=sum(item.result_published for item in ordered),
        tournaments=ordered,
    )
