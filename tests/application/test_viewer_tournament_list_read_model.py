from __future__ import annotations

import pytest

from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.viewer_tournament_list_read_model import (
    resolve_viewer_tournament_list,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import PackageType
from tests.application.test_run_package_snapshot import apply, doc, empty, entity, repo
from tests.application.test_viewer_tournament_result_read_model import _source


pytestmark = pytest.mark.pr_critical


def _calendar_document(
    *,
    package_id: str,
    season: str,
    event_id: str,
    season_week: int,
    calendar_year: int,
    year_week: int,
    event_name: str,
):
    return doc(
        PackageType.CALENDAR,
        package_id,
        entities=(
            entity(
                "calendar.metadata",
                {
                    "season": season,
                    "metadata": None,
                    "validation_warnings": [],
                    "validation_errors": [],
                },
                "calendar.metadata.v1",
                "season_calendar",
            ),
            entity(
                event_id,
                {
                    "event_id": event_id,
                    "season": season,
                    "season_week": season_week,
                    "calendar_year": calendar_year,
                    "year_week": year_week,
                    "template_id": f"template-{event_id}",
                    "event_name": event_name,
                    "category": "PLATINUM",
                    "tour_level": "WORLD_TOUR",
                    "host_country": "CZE",
                    "host_city": "Prague",
                    "region": "Europe",
                    "main_draw_size": 8,
                    "qualification_draw_size": 4,
                },
                "calendar.event.v1",
                "season_calendar",
            ),
        ),
    )


def test_viewer_tournament_list_projects_saved_calendars_and_canonical_results() -> None:
    repository = repo()
    empty(repository)
    service = RunPackageService(repository)

    first = apply(
        service,
        _calendar_document(
            package_id="calendar-2000-2001",
            season="2000/2001",
            event_id="event-a",
            season_week=2,
            calendar_year=2000,
            year_week=38,
            event_name="Prague Open",
        ),
    )
    second = apply(
        service,
        _calendar_document(
            package_id="calendar-2001-2002",
            season="2001/2002",
            event_id="event-b",
            season_week=1,
            calendar_year=2001,
            year_week=37,
            event_name="Brno Open",
        ),
        command="calendar-two",
        draft=1,
        state=first.state.fingerprint,
    )

    ranking = RankingRevisionState(
        run_id="run",
        branch_id="a",
        entries=(),
        sources=(),
        tournament_sources=(
            _source(run_id="run", branch_id="a", event_id="event-a"),
        ),
    )

    result = resolve_viewer_tournament_list(
        second.state,
        ranking,
        run_id="run",
        branch_id="a",
    )

    assert result.schema_version == "viewer_tournament_list.v1"
    assert result.tournament_count == 2
    assert result.completed_count == 1
    assert [item.event_id for item in result.tournaments] == ["event-a", "event-b"]

    completed, scheduled = result.tournaments
    assert completed.event_name == "Prague Open"
    assert completed.season == "2000/2001"
    assert completed.season_week == 2
    assert completed.tour_level == "WORLD_TOUR"
    assert completed.sporting_status == "completed"
    assert completed.result_available
    assert completed.champion_player_id == "A"
    assert completed.finalist_player_id == "B"

    assert scheduled.event_name == "Brno Open"
    assert scheduled.sporting_status == "scheduled"
    assert not scheduled.result_available
    assert scheduled.champion_player_id is None

    rendered = str(result.model_dump(mode="json"))
    for forbidden in (
        "fingerprint",
        "provenance",
        "source_package",
        "run_local_id",
        "command_id",
        "canonical_result",
        "point_distribution",
    ):
        assert forbidden not in rendered


def test_viewer_tournament_list_is_empty_without_saved_package_state() -> None:
    result = resolve_viewer_tournament_list(
        None,
        None,
        run_id="run",
        branch_id="branch",
    )
    assert result.tournament_count == 0
    assert result.completed_count == 0
    assert result.tournaments == ()


def test_viewer_tournament_list_rejects_duplicate_event_identity_across_calendars() -> None:
    repository = repo()
    empty(repository)
    service = RunPackageService(repository)
    first = apply(
        service,
        _calendar_document(
            package_id="calendar-one",
            season="2000/2001",
            event_id="same-event",
            season_week=1,
            calendar_year=2000,
            year_week=37,
            event_name="First",
        ),
    )
    second = apply(
        service,
        _calendar_document(
            package_id="calendar-two",
            season="2001/2002",
            event_id="same-event",
            season_week=1,
            calendar_year=2001,
            year_week=37,
            event_name="Second",
        ),
        command="calendar-two",
        draft=1,
        state=first.state.fingerprint,
    )

    with pytest.raises(ValueError, match="duplicate event"):
        resolve_viewer_tournament_list(
            second.state,
            None,
            run_id="run",
            branch_id="a",
        )
