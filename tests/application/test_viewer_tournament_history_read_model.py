from __future__ import annotations

import pytest

from beta_engine.application.viewer_tournament_history_read_model import (
    resolve_viewer_tournament_history,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)
from tests.application.test_viewer_tournament_result_read_model import _source


pytestmark = pytest.mark.pr_critical


def fp(char: str) -> str:
    return char * 64


def _calendar_entities(
    *,
    package_id: str,
    version_char: str,
    first_local_id: int,
    season: str,
    event_id: str,
    week: int,
    event_name: str,
) -> tuple[tuple[RunPackageEntity, ...], AppliedPackageVersion]:
    source_fingerprint = fp(version_char)
    metadata = RunPackageEntity(
        run_local_id=first_local_id,
        source_package_id=package_id,
        source_package_version=1,
        source_package_fingerprint=source_fingerprint,
        source_entity_id="calendar.metadata",
        entity_kind="calendar.metadata.v1",
        entity_schema_version=1,
        scope="season_calendar",
        payload={
            "season": season,
            "metadata": None,
            "validation_warnings": [],
            "validation_errors": [],
        },
        source_baseline_fingerprint=fp("e"),
    )
    event = RunPackageEntity(
        run_local_id=first_local_id + 1,
        source_package_id=package_id,
        source_package_version=1,
        source_package_fingerprint=source_fingerprint,
        source_entity_id=event_id,
        entity_kind="calendar.event.v1",
        entity_schema_version=1,
        scope="season_calendar",
        payload={
            "event_id": event_id,
            "season": season,
            "season_week": week,
            "template_id": f"TPL-{event_id}",
            "event_name": event_name,
            "category": "DIAMOND",
            "tour_level": "WORLD_TOUR",
            "host_country": "CZE",
            "host_city": "Prague",
            "region": "EUROPE",
            "main_draw_size": 16,
            "qualification_draw_size": 8,
            "seeds_count": 4,
            "qualifier_spots": 4,
            "wild_cards": 2,
            "byes": 0,
            "ranking_status": "ranked",
        },
        source_baseline_fingerprint=fp("f"),
    )
    version = AppliedPackageVersion(
        package_type=PackageType.CALENDAR,
        package_id=package_id,
        source_version=1,
        source_fingerprint=source_fingerprint,
        document_explicit_scope=("season_calendar",),
        applied_entity_ids=("calendar.metadata", event_id),
        provenance={"test": "viewer-history"},
    )
    return (metadata, event), version


def _state(*, run_id: str = "run", branch_id: str = "branch") -> RunPackageState:
    first_entities, first_version = _calendar_entities(
        package_id="calendar-2000-2001",
        version_char="a",
        first_local_id=1,
        season="2000/2001",
        event_id="EVENT-OLD",
        week=5,
        event_name="Old Open",
    )
    second_entities, second_version = _calendar_entities(
        package_id="calendar-2002-2003",
        version_char="b",
        first_local_id=3,
        season="2002/2003",
        event_id="event",
        week=17,
        event_name="Current Open",
    )
    return RunPackageState(
        run_id=run_id,
        branch_id=branch_id,
        entities=first_entities + second_entities,
        package_versions=(first_version, second_version),
    )


def test_viewer_tournament_history_projects_multi_season_calendar_and_result() -> None:
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(_source(),),
    )

    history = resolve_viewer_tournament_history(
        run_package_state=_state(),
        ranking=ranking,
        run_id="run",
        branch_id="branch",
    )

    assert history.schema_version == "viewer_tournament_history.v1"
    assert history.tournament_count == 2
    assert history.published_result_count == 1
    assert [
        (item.season, item.season_week, item.event_id)
        for item in history.tournaments
    ] == [
        ("2000/2001", 5, "EVENT-OLD"),
        ("2002/2003", 17, "event"),
    ]

    old, current = history.tournaments
    assert old.event_name == "Old Open"
    assert old.result_published is False
    assert old.champion_player_id is None

    assert current.event_name == "Current Open"
    assert current.category == "DIAMOND"
    assert current.tour_level == "WORLD_TOUR"
    assert current.host_country == "CZE"
    assert current.main_draw_size == 16
    assert current.qualification_draw_size == 8
    assert current.result_published is True
    assert current.champion_player_id == "A"
    assert current.finalist_player_id == "B"


def test_viewer_tournament_history_requires_saved_calendar_package() -> None:
    with pytest.raises(KeyError, match="Calendar Package"):
        resolve_viewer_tournament_history(
            run_package_state=RunPackageState(run_id="run", branch_id="branch"),
            ranking=None,
            run_id="run",
            branch_id="branch",
        )


def test_viewer_tournament_history_fails_closed_for_orphan_result() -> None:
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(
            _source(event_id="not-in-calendar"),
        ),
    )
    with pytest.raises(ValueError, match="no matching saved Calendar event"):
        resolve_viewer_tournament_history(
            run_package_state=_state(),
            ranking=ranking,
            run_id="run",
            branch_id="branch",
        )
