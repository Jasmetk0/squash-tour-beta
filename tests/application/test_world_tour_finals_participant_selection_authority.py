"""Real persistence integration for canonical Finals participant selection."""

import pytest

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.application.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionAuthorityService,
    WorldTourFinalsParticipantSelectionConfigurationCommand,
)
from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def authority(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(
            url=f"sqlite:///{tmp_path / 'finals-participant-service.db'}"
        )
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
            )
        )
    yield WorldTourFinalsParticipantSelectionAuthorityService(factory=factory), factory
    engine.dispose()


def _calendar_state() -> RunPackageState:
    source_fingerprint = fp("a")
    event_specs = (
        ("DIRECT-A", 4, "DIAMOND", 16),
        ("DIRECT-B", 7, "DIAMOND", 16),
        ("FINALS", 20, "FINALS", 4),
    )
    entities = [
        RunPackageEntity(
            run_local_id=1,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="calendar.metadata",
            entity_kind="calendar.metadata.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "season": "2000/2001",
                "metadata": None,
                "validation_warnings": [],
                "validation_errors": [],
            },
            source_baseline_fingerprint=fp("b"),
        )
    ]
    for index, (event_id, week, category, capacity) in enumerate(
        event_specs,
        start=2,
    ):
        entities.append(
            RunPackageEntity(
                run_local_id=index,
                source_package_id="calendar-2000-2001",
                source_package_version=1,
                source_package_fingerprint=source_fingerprint,
                source_entity_id=event_id,
                entity_kind="calendar.event.v1",
                entity_schema_version=1,
                scope="season_calendar",
                payload={
                    "event_id": event_id,
                    "season": "2000/2001",
                    "season_week": week,
                    "template_id": f"TPL-{index}",
                    "event_name": event_id,
                    "category": category,
                    "tour_level": "WORLD_TOUR",
                    "host_country": "CZE",
                    "region": "EUROPE",
                    "main_draw_size": capacity,
                },
                source_baseline_fingerprint=fp(str(index)),
            )
        )

    return RunPackageState(
        run_id="run",
        branch_id="branch",
        entities=tuple(entities),
        package_versions=(
            AppliedPackageVersion(
                package_type=PackageType.CALENDAR,
                package_id="calendar-2000-2001",
                source_version=1,
                source_fingerprint=source_fingerprint,
                document_explicit_scope=("season_calendar",),
                applied_entity_ids=(
                    "calendar.metadata",
                    "DIRECT-A",
                    "DIRECT-B",
                    "FINALS",
                ),
                provenance={"test": "finals-participant-selection"},
            ),
        ),
    )


def _install_calendar_and_race(factory):
    state = _calendar_state()
    projection = CalendarPackageRunAdapter.project_calendar(
        state,
        package_id="calendar-2000-2001",
    )
    race_config = WorldTourFinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        eligible_categories=("DIAMOND",),
        best_n=2,
        cutoff_week=RankingWeek(season_index=0, week=10),
        cutoff_official_ranking_fingerprint=fp("c"),
        cutoff_transition_fingerprint=fp("d"),
        calendar_content_fingerprint=projection.content_fingerprint,
        adopted_by_command_id="configure-race",
    )
    race_snapshot = calculate_world_tour_finals_race(
        WorldTourFinalsRaceInput(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            cutoff_week=race_config.cutoff_week,
            cutoff_official_ranking_fingerprint=(
                race_config.cutoff_official_ranking_fingerprint
            ),
            eligibility_fingerprint=race_config.eligibility_fingerprint,
            policy_id=race_config.policy_id,
            best_n=race_config.best_n,
            players=tuple(
                WorldTourFinalsRacePlayer(
                    player_id=f"p{index}",
                    tie_break_token=f"token-{index:02d}",
                )
                for index in range(1, 7)
            ),
            eligible_results=(),
        )
    )
    with factory.begin() as session:
        put_run_package_state(session, state)
        store = WorldTourFinalsRaceAuthorityStore(session)
        store.put_configuration(race_config)
        store.put_snapshot(race_snapshot)
    return race_snapshot


@pytest.mark.pr_critical
def test_service_derives_capacity_from_finals_edition_and_selects_from_race(authority):
    service, factory = authority
    race_snapshot = _install_calendar_and_race(factory)

    config = service.create_configuration(
        WorldTourFinalsParticipantSelectionConfigurationCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            direct_entry_event_ids=(),
            command_id="configure-participants",
        )
    )
    assert config.participant_capacity == 4
    assert config.finals_event_id == "FINALS"
    assert config.race_snapshot_fingerprint == race_snapshot.fingerprint

    selection = service.build_snapshot(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
    )
    assert [player.player_id for player in selection.participants] == [
        row.player_id for row in race_snapshot.rows[:4]
    ]
    assert [player.seed for player in selection.participants] == [1, 2, 3, 4]
    assert all(
        player.qualification_source == "race"
        for player in selection.participants
    )

    # Exact retry is immutable/idempotent.
    assert (
        service.build_snapshot(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        )
        == selection
    )


@pytest.mark.pr_critical
def test_service_validates_direct_entry_scope_against_frozen_finals_capacity(authority):
    service, factory = authority
    _install_calendar_and_race(factory)

    with pytest.raises(ValueError, match="absent from frozen Run Calendar"):
        service.create_configuration(
            WorldTourFinalsParticipantSelectionConfigurationCommand(
                run_id="run",
                branch_id="branch",
                target_season_index=0,
                direct_entry_event_ids=("MISSING",),
                command_id="bad-direct-entry",
            )
        )

    with pytest.raises(ValueError, match="own direct entry"):
        service.create_configuration(
            WorldTourFinalsParticipantSelectionConfigurationCommand(
                run_id="run",
                branch_id="branch",
                target_season_index=0,
                direct_entry_event_ids=("FINALS",),
                command_id="self-direct-entry",
            )
        )
