"""Immutable, revision-scoped Run Tour calendar and Edition read projections.

The existing Viewer tournament history/result resolvers own event/result identity.
This module only adds the selected Admin Branch, reachable Saved Revision and
explicit season boundary. It never reads Working Draft or mutable tournament state.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.viewer_tournament_history_read_model import (
    ViewerTournamentHistoryItem, resolve_viewer_tournament_history,
)
from beta_engine.application.viewer_tournament_result_read_model import (
    ViewerTournamentResult, resolve_viewer_tournament_result,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.application.viewer_tournament_entry_field_read_model import (
    ViewerTournamentEntryField, resolve_viewer_tournament_entry_field,
)
from beta_engine.application.viewer_tournament_draw_read_model import (
    ViewerTournamentDraw, resolve_viewer_tournament_draw,
)


class RunSavedTourCalendar(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_saved_tour_calendar.v1"] = "run_saved_tour_calendar.v1"
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    run_id: str
    branch_id: str
    revision_branch_id: str
    saved_revision_id: str
    season_index: int = Field(ge=0, le=49)
    season: str
    week_count: Literal[61] = 61
    calendar_status: Literal["empty", "ready"]
    edition_count: int = Field(ge=0)
    editions: tuple[ViewerTournamentHistoryItem, ...]


class RunSavedTourEdition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_saved_tour_edition.v1"] = "run_saved_tour_edition.v1"
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    run_id: str
    branch_id: str
    revision_branch_id: str
    saved_revision_id: str
    season_index: int = Field(ge=0, le=49)
    edition: ViewerTournamentHistoryItem
    published_result: ViewerTournamentResult | None
    entry_field: ViewerTournamentEntryField | None = None
    draw: ViewerTournamentDraw | None = None
    # Calendar status is planning data, not a separate lifecycle authority.
    lifecycle_status: Literal["unavailable"] = "unavailable"


def _check_scope(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, season_index: int,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
) -> None:
    if not all((run_id, selected_branch_id, revision_branch_id, saved_revision_id)):
        raise ValueError("Saved Tour requires exact Run/Branch/Revision identities")
    if not 0 <= season_index < 50:
        raise ValueError("Saved Tour season must be between 0 and 49")
    if packages is not None and (packages.run_id, packages.branch_id) != (
        run_id, revision_branch_id,
    ):
        raise ValueError("Saved Tour Calendar belongs to another Run/Branch")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (
        run_id, revision_branch_id,
    ):
        raise ValueError("Saved Tour Ranking belongs to another Run/Branch")


def _season_index(value: str) -> int:
    # Retain both accepted FAX season spellings, never use the World data year.
    for index in range(50):
        first = 2000 + index
        second = first + 1
        if value in (f"{first}/{second}", f"{first}/{second % 100:02d}"):
            return index
    raise ValueError("Saved Calendar Edition has an invalid season identity")


def resolve_run_saved_tour_calendar(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, season_index: int,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
) -> RunSavedTourCalendar:
    _check_scope(
        run_id=run_id, selected_branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        season_index=season_index, packages=packages, ranking=ranking,
    )
    events: tuple[ViewerTournamentHistoryItem, ...] = ()
    status: Literal["empty", "ready"] = "empty"
    if packages is None:
        if ranking is not None and ranking.tournament_sources:
            raise ValueError("Saved Tournament results exist without Saved Calendar")
    else:
        try:
            history = resolve_viewer_tournament_history(
                run_package_state=packages, ranking=ranking,
                run_id=run_id, branch_id=revision_branch_id,
            )
        except KeyError as exc:
            if "no applied Calendar Package" not in str(exc) or (
                ranking is not None and ranking.tournament_sources
            ):
                raise
        else:
            # Validate ALL event identities and source seasons before filtering.
            for item in history.tournaments:
                _season_index(item.season)
            events = tuple(
                item for item in history.tournaments
                if _season_index(item.season) == season_index
            )
            status = "ready"
    return RunSavedTourCalendar(
        run_id=run_id, branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        season_index=season_index, season=f"{2000 + season_index}/{2001 + season_index}",
        calendar_status=status, edition_count=len(events),
        editions=tuple(sorted(events, key=lambda e: (e.season_week, e.event_id))),
    )


def resolve_run_saved_tour_edition(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, season_index: int, event_id: str,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
    simulation_slots: dict | None = None,
) -> RunSavedTourEdition:
    if not event_id or event_id.strip() != event_id or len(event_id) > 128:
        raise ValueError("Saved Tour Edition requires a valid event ID")
    calendar = resolve_run_saved_tour_calendar(
        run_id=run_id, selected_branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        season_index=season_index, packages=packages, ranking=ranking,
    )
    items = [item for item in calendar.editions if item.event_id == event_id]
    if not items:
        raise KeyError("Edition is not present in the requested saved season")
    if len(items) != 1:
        raise ValueError("Saved Edition identity is ambiguous")
    item = items[0]
    published = None
    if item.result_published:
        published = resolve_viewer_tournament_result(
            ranking, run_id=run_id, branch_id=revision_branch_id, event_id=event_id,
        )
        if (
            published.product_run_id != run_id
            or published.viewer_branch_id != revision_branch_id
            or published.event_id != event_id
            or published.completed_season_index != season_index
            or published.completed_week != item.season_week
        ):
            raise ValueError("Published Tournament Result differs from saved Edition time")
    # Optional historical Slot evidence: no Entry or Draw is a truthful absence,
    # but mismatched or corrupted available authority must fail closed.
    entry_field: ViewerTournamentEntryField | None = None
    draw: ViewerTournamentDraw | None = None
    if simulation_slots is not None:
        def scoped_rows(key: str) -> list[dict]:
            rows = [
                row for row in simulation_slots.get(key, ())
                if row.get("event_id") == event_id
            ]
            if any(
                (row.get("run_id"), row.get("branch_id")) !=
                (run_id, revision_branch_id) for row in rows
            ):
                raise ValueError("Saved Edition sporting authority belongs to another Run/Branch")
            return rows

        fields = scoped_rows("entry_fields")
        draws = scoped_rows("draw_authorities")
        revisions = scoped_rows("draw_revisions")
        if revisions and not draws:
            raise ValueError("Saved Edition Draw revisions have no original draw")
        if draws and not fields:
            raise ValueError("Saved Edition Draw has no saved Entry Field")
        if fields:
            entry_field = resolve_viewer_tournament_entry_field(
                simulation_slots, run_id=run_id,
                branch_id=revision_branch_id, event_id=event_id,
            )
        if draws:
            draw = resolve_viewer_tournament_draw(
                simulation_slots, run_id=run_id,
                branch_id=revision_branch_id, event_id=event_id,
            )
        for authority in (entry_field, draw):
            if authority is not None and (
                authority.product_run_id, authority.viewer_branch_id, authority.event_id
            ) != (run_id, revision_branch_id, event_id):
                raise ValueError("Saved Edition Entry/Draw projection scope mismatch")
    return RunSavedTourEdition(
        run_id=run_id, branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        season_index=season_index, edition=item, published_result=published,
        entry_field=entry_field, draw=draw,
    )
