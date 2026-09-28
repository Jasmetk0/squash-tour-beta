"""Real persistence integration for the Finals Race season authority service."""

import pytest

from beta_engine.application.finals_race_authority import (
    WorldTourFinalsRaceAuthorityService,
    WorldTourFinalsRaceConfigurationCommand,
)
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
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
from beta_engine.infrastructure.db.models import (
    Base,
    PublishedOfficialRankingModel,
    RankingTransitionAuthorityModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state


@pytest.fixture
def authority(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals-race-service.db'}")
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
    yield WorldTourFinalsRaceAuthorityService(factory=factory), factory
    engine.dispose()


def _install_calendar(factory) -> None:
    source_fingerprint = "a" * 64
    entities = (
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
            source_baseline_fingerprint="b" * 64,
        ),
        RunPackageEntity(
            run_local_id=2,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="event-1",
            entity_kind="calendar.event.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "event_id": "event-1",
                "season": "2000/2001",
                "season_week": 1,
                "template_id": "tpl-1",
                "event_name": "Diamond One",
                "category": "DIAMOND",
                "tour_level": "WORLD_TOUR",
                "host_country": "CZE",
                "region": "EUROPE",
                "main_draw_size": 4,
            },
            source_baseline_fingerprint="c" * 64,
        ),
        RunPackageEntity(
            run_local_id=3,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="FINALS",
            entity_kind="calendar.event.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "event_id": "FINALS",
                "season": "2000/2001",
                "season_week": 20,
                "template_id": "finals-tpl",
                "event_name": "World Tour Finals",
                "category": "FINALS",
                "tour_level": "WORLD_TOUR",
                "host_country": "CZE",
                "region": "EUROPE",
                "main_draw_size": 8,
            },
            source_baseline_fingerprint="d" * 64,
        ),
    )
    version = AppliedPackageVersion(
        package_type=PackageType.CALENDAR,
        package_id="calendar-2000-2001",
        source_version=1,
        source_fingerprint=source_fingerprint,
        document_explicit_scope=("season_calendar",),
        applied_entity_ids=("calendar.metadata", "event-1", "FINALS"),
        provenance={"test": "finals-race-season-authority"},
    )
    with factory.begin() as session:
        put_run_package_state(
            session,
            RunPackageState(
                run_id="run",
                branch_id="branch",
                entities=entities,
                package_versions=(version,),
            ),
        )


def _install_cutoff(factory) -> RankingWeek:
    week_one = RankingWeek(season_index=0, week=1)
    week_two = RankingWeek(season_index=0, week=2)
    players = (
        OfficialRankingPlayer(
            player_id="p1",
            tie_break_token="token-b",
            tour_entry_week=week_one,
            retired=False,
        ),
        OfficialRankingPlayer(
            player_id="p2",
            tie_break_token="token-a",
            tour_entry_week=week_one,
            retired=False,
        ),
    )
    policy = OfficialRankingPolicy(policy_id="official", best_n=15)
    first = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week_one,
        policy=policy,
        players=players,
        results=(),
        previous=None,
    )
    cutoff = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week_two,
        policy=policy,
        players=players,
        results=(),
        previous=first,
    )
    transition = RankingTransitionAuthority(
        run_id="run",
        branch_id="branch",
        base_revision_id="revision-1",
        completed_week=week_one,
        target_week=week_two,
        players=players,
        policy=policy,
        provenance="Finals Race integration test",
        adopted_by_command_id="transition-week-two",
        audit=RankingCommandAudit(actor_label="test", reason="Race cutoff"),
    )
    with factory.begin() as session:
        session.add(
            PublishedOfficialRankingModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=week_two.ordinal,
                snapshot_fingerprint=cutoff.fingerprint,
                payload_json=cutoff.model_dump_json(),
            )
        )
        session.add(
            RankingTransitionAuthorityModel(
                run_id="run",
                branch_id="branch",
                target_ordinal=week_two.ordinal,
                fingerprint=transition.fingerprint,
                payload_json=transition.model_dump_json(),
            )
        )
    return week_two


@pytest.mark.pr_critical
def test_service_requires_real_published_cutoff_then_persists_exact_snapshot(authority):
    service, factory = authority
    _install_calendar(factory)

    command = WorldTourFinalsRaceConfigurationCommand(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        best_n=2,
        eligible_categories=("DIAMOND",),
        cutoff_week=RankingWeek(season_index=0, week=2),
        command_id="configure-finals-race",
    )

    with pytest.raises(ValueError, match="published Official Ranking"):
        service.create_configuration(command)

    cutoff_week = _install_cutoff(factory)
    configured = service.create_configuration(command)
    assert configured.cutoff_week == cutoff_week
    assert configured.best_n == 2
    assert configured.eligible_categories == ("DIAMOND",)

    race = service.build_snapshot(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
    )
    assert [(row.rank, row.player_id, row.race_points) for row in race.rows] == [
        (1, "p2", 0),
        (2, "p1", 0),
    ]
    assert race.eligible_result_count == 0

    assert (
        service.build_snapshot(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        )
        == race
    )
    stored_configuration, stored_race = service.inspect(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
    )
    assert stored_configuration == configured
    assert stored_race == race
