from __future__ import annotations

import pytest

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND,
    CALENDAR_METADATA_ENTITY_ID,
    CALENDAR_METADATA_ENTITY_KIND,
    CALENDAR_SCOPE,
)
from beta_engine.application.viewer_calendar_read_model import (
    resolve_viewer_run_calendar,
)
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)


pytestmark = pytest.mark.pr_critical


def calendar_state(
    *,
    run_id: str = "run",
    branch_id: str = "branch",
    package_id: str = "calendar-2030-2031",
    season: str = "2030/2031",
    event_id: str = "EVENT-1",
) -> RunPackageState:
    metadata = PackageEntity(
        source_entity_id=CALENDAR_METADATA_ENTITY_ID,
        entity_kind=CALENDAR_METADATA_ENTITY_KIND,
        entity_schema_version=1,
        scope=CALENDAR_SCOPE,
        payload={
            "season": season,
            "metadata": None,
            "validation_warnings": [],
            "validation_errors": [],
        },
    )
    event = PackageEntity(
        source_entity_id=event_id,
        entity_kind=CALENDAR_EVENT_ENTITY_KIND,
        entity_schema_version=1,
        scope=CALENDAR_SCOPE,
        payload={
            "event_id": event_id,
            "season": season,
            "season_week": 7,
            "calendar_year": 2030,
            "year_week": 43,
            "template_id": "WT-PLAT",
            "event_name": "Czech Open",
            "category": "Platinum",
            "tour_level": "WORLD_TOUR",
            "host_country": "CZE",
            "host_city": "Brno",
            "region": "Europe",
            "duration_in_season_weeks": 1,
            "status": "planned",
            "main_draw_size": 32,
            "qualification_draw_size": 16,
            "seeds_count": 8,
            "qualifier_spots": 4,
            "wild_cards": 2,
            "byes": 0,
            "prestige": 8.5,
            "ranking_status": "ranked",
            "ranking_points_table": {"champion": 1000},
            "prize_money_currency": "EUR",
            "prize_money_table": {"champion": 25000},
        },
    )
    document = CanonicalPackageDocument(
        package_type=PackageType.CALENDAR,
        package_id=package_id,
        source_version=1,
        provenance={"source": "test-calendar"},
        explicit_scope=(CALENDAR_SCOPE,),
        entities=(metadata, event),
    )
    version = AppliedPackageVersion(
        package_type=PackageType.CALENDAR,
        package_id=package_id,
        source_version=1,
        source_fingerprint=document.source_fingerprint,
        document_explicit_scope=(CALENDAR_SCOPE,),
        applied_entity_ids=(metadata.source_entity_id, event.source_entity_id),
        provenance={"source": "test-calendar"},
    )
    entities = tuple(
        RunPackageEntity(
            run_local_id=index,
            source_package_id=package_id,
            source_package_version=1,
            source_package_fingerprint=document.source_fingerprint,
            source_entity_id=source.source_entity_id,
            entity_kind=source.entity_kind,
            entity_schema_version=source.entity_schema_version,
            scope=source.scope,
            payload=source.payload,
            source_baseline_fingerprint=source.fingerprint,
            references=source.references,
        )
        for index, source in enumerate((metadata, event), start=1)
    )
    return RunPackageState(
        run_id=run_id,
        branch_id=branch_id,
        entities=entities,
        package_versions=(version,),
    )


def test_viewer_calendar_projects_saved_package_schedule_without_internal_metadata() -> None:
    state = calendar_state()

    calendar = resolve_viewer_run_calendar(
        state,
        run_id="run",
        branch_id="branch",
    )

    assert calendar.schema_version == "viewer_run_calendar.v1"
    assert calendar.season_count == 1
    assert calendar.event_count == 1
    season = calendar.seasons[0]
    assert season.season == "2030/2031"
    assert season.event_count == 1
    event = season.events[0]
    assert event.event_id == "EVENT-1"
    assert event.season_week == 7
    assert event.template_id == "WT-PLAT"
    assert event.event_name == "Czech Open"
    assert event.category == "Platinum"
    assert event.tour_level == "WORLD_TOUR"
    assert event.host_country == "CZE"
    assert event.host_city == "Brno"
    assert event.main_draw_size == 32
    assert event.qualification_draw_size == 16
    assert event.seeds_count == 8
    assert event.qualifier_spots == 4
    assert event.wild_cards == 2
    assert event.prestige == 8.5

    rendered = str(calendar.model_dump(mode="json"))
    for forbidden in (
        "package_id",
        "source_package",
        "fingerprint",
        "provenance",
        "run_local_id",
        "ranking_points",
        "point_distribution",
        "prize_money",
        "source_template_fingerprint",
        "calendar_fingerprint",
    ):
        assert forbidden not in rendered


def test_viewer_calendar_requires_saved_calendar_package() -> None:
    empty = RunPackageState(run_id="run", branch_id="branch")
    with pytest.raises(KeyError, match="Calendar Package"):
        resolve_viewer_run_calendar(empty, run_id="run", branch_id="branch")


def test_viewer_calendar_rejects_wrong_saved_branch_scope() -> None:
    with pytest.raises(ValueError, match="scope"):
        resolve_viewer_run_calendar(
            calendar_state(),
            run_id="run",
            branch_id="other",
        )
