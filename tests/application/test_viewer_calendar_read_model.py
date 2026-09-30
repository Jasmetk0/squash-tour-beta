from __future__ import annotations

import pytest

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND,
    CALENDAR_METADATA_ENTITY_ID,
    CALENDAR_METADATA_ENTITY_KIND,
    CALENDAR_SCOPE,
)
from beta_engine.application.viewer_calendar_read_model import resolve_viewer_run_calendar
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)
from beta_engine.domain.tournaments.models import CalendarEvent
from test_viewer_tournament_result_read_model import _source


pytestmark = pytest.mark.pr_critical


def _calendar_state(*, event_id: str = "EVENT-1") -> RunPackageState:
    source_fp = "a" * 64
    metadata = RunPackageEntity(
        run_local_id=1,
        source_package_id="calendar-2000-2001",
        source_package_version=1,
        source_package_fingerprint=source_fp,
        source_entity_id=CALENDAR_METADATA_ENTITY_ID,
        entity_kind=CALENDAR_METADATA_ENTITY_KIND,
        entity_schema_version=1,
        scope=CALENDAR_SCOPE,
        payload={
            "season": "2000/2001",
            "metadata": None,
            "validation_warnings": [],
            "validation_errors": [],
        },
        source_baseline_fingerprint="b" * 64,
    )
    event = CalendarEvent(
        event_id=event_id,
        season="2000/2001",
        season_week=7,
        calendar_year=2000,
        year_week=43,
        template_id="WT-GOLD",
        event_name="Canonical Gold Open",
        category="Gold",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        host_city="Brno",
        region="Europe",
        main_draw_size=32,
        qualification_draw_size=16,
        qualifier_spots=4,
        wild_cards=2,
        byes=2,
        status="planned",
    )
    event_entity = RunPackageEntity(
        run_local_id=2,
        source_package_id="calendar-2000-2001",
        source_package_version=1,
        source_package_fingerprint=source_fp,
        source_entity_id=event_id,
        entity_kind=CALENDAR_EVENT_ENTITY_KIND,
        entity_schema_version=1,
        scope=CALENDAR_SCOPE,
        payload=event.model_dump(mode="json"),
        source_baseline_fingerprint="c" * 64,
    )
    return RunPackageState(
        run_id="run",
        branch_id="branch",
        entities=(metadata, event_entity),
        package_versions=(
            AppliedPackageVersion(
                package_type=PackageType.CALENDAR,
                package_id="calendar-2000-2001",
                source_version=1,
                source_fingerprint=source_fp,
                document_explicit_scope=(CALENDAR_SCOPE,),
                applied_entity_ids=(CALENDAR_METADATA_ENTITY_ID, event_id),
                provenance={"source": "test"},
            ),
        ),
    )


def test_viewer_calendar_projects_saved_metadata_and_canonical_result_summary() -> None:
    event_id = "EVENT-1"
    state = _calendar_state(event_id=event_id)
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(
            _source(run_id="run", branch_id="branch", event_id=event_id),
        ),
    )

    result = resolve_viewer_run_calendar(
        state,
        ranking,
        run_id="run",
        branch_id="branch",
    )

    assert result.schema_version == "viewer_run_calendar.v1"
    assert result.calendar_count == 1
    assert result.event_count == 1
    event = result.events[0]
    assert event.event_id == event_id
    assert event.season == "2000/2001"
    assert event.season_index == 0
    assert event.season_week == 7
    assert event.event_name == "Canonical Gold Open"
    assert event.category == "Gold"
    assert event.tour_level == "WORLD_TOUR"
    assert event.host_country == "CZE"
    assert event.main_draw_size == 32
    assert event.qualification_draw_size == 16
    assert event.qualifier_spots == 4
    assert event.wild_card_slots == 2
    assert event.bye_slots == 2
    assert event.result is not None
    assert event.result.champion_player_id == "A"
    assert event.result.finalist_player_id == "B"
    assert event.result.match_count == 4
    assert event.completed

    rendered = str(result.model_dump(mode="json"))
    for forbidden in (
        "fingerprint",
        "run_local_id",
        "source_package_id",
        "provenance",
        "command_id",
        "canonical_awards",
    ):
        assert forbidden not in rendered


def test_viewer_calendar_fails_closed_on_duplicate_event_identity_across_calendars() -> None:
    first = _calendar_state(event_id="DUPLICATE")
    source_fp = "d" * 64
    second_metadata = RunPackageEntity(
        run_local_id=3,
        source_package_id="calendar-2001-2002",
        source_package_version=1,
        source_package_fingerprint=source_fp,
        source_entity_id=CALENDAR_METADATA_ENTITY_ID,
        entity_kind=CALENDAR_METADATA_ENTITY_KIND,
        entity_schema_version=1,
        scope=CALENDAR_SCOPE,
        payload={
            "season": "2001/2002",
            "metadata": None,
            "validation_warnings": [],
            "validation_errors": [],
        },
        source_baseline_fingerprint="e" * 64,
    )
    second_event = CalendarEvent(
        event_id="DUPLICATE",
        season="2001/2002",
        season_week=1,
        template_id="WT-GOLD",
        event_name="Duplicate",
        category="Gold",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
    )
    second_event_entity = RunPackageEntity(
        run_local_id=4,
        source_package_id="calendar-2001-2002",
        source_package_version=1,
        source_package_fingerprint=source_fp,
        source_entity_id="DUPLICATE",
        entity_kind=CALENDAR_EVENT_ENTITY_KIND,
        entity_schema_version=1,
        scope=CALENDAR_SCOPE,
        payload=second_event.model_dump(mode="json"),
        source_baseline_fingerprint="f" * 64,
    )
    state = first.model_copy(
        update={
            "entities": first.entities + (second_metadata, second_event_entity),
            "package_versions": first.package_versions
            + (
                AppliedPackageVersion(
                    package_type=PackageType.CALENDAR,
                    package_id="calendar-2001-2002",
                    source_version=1,
                    source_fingerprint=source_fp,
                    document_explicit_scope=(CALENDAR_SCOPE,),
                    applied_entity_ids=(CALENDAR_METADATA_ENTITY_ID, "DUPLICATE"),
                    provenance={"source": "test"},
                ),
            ),
        }
    )

    with pytest.raises(ValueError, match="duplicate event identity"):
        resolve_viewer_run_calendar(
            state,
            None,
            run_id="run",
            branch_id="branch",
        )
