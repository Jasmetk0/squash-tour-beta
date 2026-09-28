from __future__ import annotations

import pytest
from sqlalchemy import text

from test_run_owned_tournament_points import _authorities, _event

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND,
    CALENDAR_METADATA_ENTITY_ID,
    CALENDAR_METADATA_ENTITY_KIND,
    CALENDAR_SCOPE,
    CalendarPackageRunAdapter,
)
from beta_engine.application.world_tour_finals_race_service import (
    WorldTourFinalsRaceService,
)
from beta_engine.domain.finals.race import (
    WorldTourFinalsRaceEventAwards,
    WorldTourFinalsRacePlayerAward,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
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
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.ranking_revision_state import (
    capture_ranking_revision_state,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from beta_engine.infrastructure.db.saved_revision_rankings import (
    restore_saved_ranking_component,
)
from beta_engine.infrastructure.db.world_tour_finals_race import (
    WorldTourFinalsRaceConflict,
    WorldTourFinalsRaceSnapshotStore,
)


def _award(player_id: str, points: int, marker: str):
    return WorldTourFinalsRacePlayerAward(
        player_id=player_id,
        race_points=points,
        award_fingerprint=marker * 64,
    )


@pytest.mark.pr_critical
def test_race_best_n_tie_profile_then_stored_token_is_deterministic():
    cutoff = RankingWeek(season_index=0, week=20)
    sources = (
        WorldTourFinalsRaceEventAwards(
            event_id="e1",
            completed_week=RankingWeek(season_index=0, week=4),
            first_publication_week=RankingWeek(season_index=0, week=5),
            source_fingerprint="1" * 64,
            awards=(
                _award("A", 60, "a"),
                _award("B", 50, "b"),
                _award("C", 100, "c"),
                _award("D", 100, "d"),
            ),
        ),
        WorldTourFinalsRaceEventAwards(
            event_id="e2",
            completed_week=RankingWeek(season_index=0, week=8),
            first_publication_week=RankingWeek(season_index=0, week=9),
            source_fingerprint="2" * 64,
            awards=(
                _award("A", 40, "e"),
                _award("B", 50, "f"),
                _award("D", 0, "0"),
            ),
        ),
        WorldTourFinalsRaceEventAwards(
            event_id="e3",
            completed_week=RankingWeek(season_index=0, week=12),
            first_publication_week=RankingWeek(season_index=0, week=13),
            source_fingerprint="3" * 64,
            awards=(
                _award("A", 5, "1"),
                _award("B", 1, "2"),
            ),
        ),
    )
    snapshot = calculate_world_tour_finals_race(
        run_id="run",
        branch_id="branch",
        season_index=0,
        cutoff_week=cutoff,
        cutoff_ranking_fingerprint="f" * 64,
        best_result_count=2,
        eligible_event_ids=("e1", "e2", "e3"),
        calendar_projection_fingerprint="c" * 64,
        event_sources=sources,
        command_id="race",
    )
    by_id = {row.player_id: row for row in snapshot.rows}
    assert by_id["A"].race_points == 100
    assert [item.points for item in by_id["A"].counted_results] == [60, 40]
    assert by_id["B"].race_points == 100
    assert [item.points for item in by_id["B"].counted_results] == [50, 50]
    assert by_id["A"].rank < by_id["B"].rank

    # C has [100] and D has [100, 0]. Missing results are zero for the
    # point-profile comparison, so only the stored deterministic token breaks it.
    assert by_id["C"].race_points == by_id["D"].race_points == 100
    expected = sorted(
        ("C", "D"), key=lambda player_id: by_id[player_id].tie_break_token
    )
    actual = [
        row.player_id for row in snapshot.rows if row.player_id in {"C", "D"}
    ]
    assert actual == expected
    replay = calculate_world_tour_finals_race(
        run_id="run",
        branch_id="branch",
        season_index=0,
        cutoff_week=cutoff,
        cutoff_ranking_fingerprint="f" * 64,
        best_result_count=2,
        eligible_event_ids=("e3", "e1", "e2"),
        calendar_projection_fingerprint="c" * 64,
        event_sources=tuple(reversed(sources)),
        command_id="race",
    )
    assert replay == snapshot


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals-race.db'}")
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
    yield factory
    engine.dispose()


def _install_calendar(session) -> None:
    event = _event()
    package_id = CalendarPackageRunAdapter.package_id_for_season("2000/2001")
    source_fingerprint = "a" * 64
    entities = (
        RunPackageEntity(
            run_local_id=1,
            source_package_id=package_id,
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
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
        ),
        RunPackageEntity(
            run_local_id=2,
            source_package_id=package_id,
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id=event.event_id,
            entity_kind=CALENDAR_EVENT_ENTITY_KIND,
            entity_schema_version=1,
            scope=CALENDAR_SCOPE,
            payload=event.model_dump(mode="json"),
            source_baseline_fingerprint="c" * 64,
        ),
    )
    version = AppliedPackageVersion(
        package_type=PackageType.CALENDAR,
        package_id=package_id,
        source_version=1,
        source_fingerprint=source_fingerprint,
        document_explicit_scope=(CALENDAR_SCOPE,),
        applied_entity_ids=(CALENDAR_METADATA_ENTITY_ID, event.event_id),
        provenance={"test": "canonical-finals-race"},
    )
    put_run_package_state(
        session,
        RunPackageState(
            run_id="run",
            branch_id="branch",
            entities=entities,
            package_versions=(version,),
        ),
    )


def _install_ranking_and_source(session):
    cutoff_week = RankingWeek(season_index=0, week=2)
    ranking = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=cutoff_week,
        policy=OfficialRankingPolicy(policy_id="race-cutoff", best_n=15),
        players=(),
        results=(),
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=cutoff_week.ordinal,
            snapshot_fingerprint=ranking.fingerprint,
            payload_json=ranking.model_dump_json(),
        )
    )
    result, _, awards, _, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result,
        canonical_awards=awards,
        adopted_by_command_id="canonical-close",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )
    OwnedTournamentRankingSourceStore(session).append(source)
    return cutoff_week, ranking, source


@pytest.mark.pr_critical
def test_service_builds_persists_and_saved_revision_restores_canonical_race(database):
    with database.begin() as session:
        _install_calendar(session)
        cutoff_week, ranking, source = _install_ranking_and_source(session)

    service = WorldTourFinalsRaceService(database)
    snapshot = service.create(
        run_id="run",
        branch_id="branch",
        season_index=0,
        cutoff_week=cutoff_week,
        best_result_count=1,
        eligible_event_ids=("event",),
        command_id="freeze-race",
    )
    assert snapshot.cutoff_ranking_fingerprint == ranking.fingerprint
    assert snapshot.source_tournament_fingerprints == (
        ("event", source.fingerprint),
    )
    expected = {
        award.player_id: award.race_points_awarded
        for award in source.canonical_awards.awards
    }
    assert {row.player_id: row.race_points for row in snapshot.rows} == expected
    assert service.create(
        run_id="run",
        branch_id="branch",
        season_index=0,
        cutoff_week=cutoff_week,
        best_result_count=1,
        eligible_event_ids=("event",),
        command_id="freeze-race",
    ) == snapshot
    with pytest.raises(WorldTourFinalsRaceConflict):
        service.create(
            run_id="run",
            branch_id="branch",
            season_index=0,
            cutoff_week=cutoff_week,
            best_result_count=2,
            eligible_event_ids=("event",),
            command_id="different-race",
        )

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        captured = capture_ranking_revision_state(
            session, run_id="run", branch_id="branch"
        )
        assert captured.schema_version == "ranking_revision_state.v8"
        assert captured.world_tour_finals_race_snapshots == (snapshot,)
        saved = {
            "content": {
                "ranking_preparation": {
                    "fingerprint": captured.fingerprint,
                    "state": captured.model_dump(mode="json"),
                }
            }
        }

    empty = {"content": {}}
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restore_saved_ranking_component(
            session,
            current_payload=saved,
            target_payload=empty,
            run_id="run",
            branch_id="branch",
            command_id="drop-race",
        )
        assert WorldTourFinalsRaceSnapshotStore(session).history(
            run_id="run", branch_id="branch"
        ) == ()

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restore_saved_ranking_component(
            session,
            current_payload=empty,
            target_payload=saved,
            run_id="run",
            branch_id="branch",
            command_id="restore-race",
        )
        assert WorldTourFinalsRaceSnapshotStore(session).get(
            run_id="run", branch_id="branch", season_index=0
        ) == snapshot


@pytest.mark.pr_critical
def test_service_rejects_unpublished_cutoff_and_non_calendar_event(database):
    with database.begin() as session:
        _install_calendar(session)
        cutoff_week, _, _ = _install_ranking_and_source(session)

    service = WorldTourFinalsRaceService(database)
    with pytest.raises(ValueError, match="published Official Ranking"):
        service.create(
            run_id="run",
            branch_id="branch",
            season_index=0,
            cutoff_week=RankingWeek(season_index=0, week=3),
            best_result_count=1,
            eligible_event_ids=("event",),
            command_id="unpublished-cutoff",
        )
    with pytest.raises(ValueError, match="absent from Run-owned Calendar"):
        service.create(
            run_id="run",
            branch_id="branch",
            season_index=0,
            cutoff_week=cutoff_week,
            best_result_count=1,
            eligible_event_ids=("not-in-calendar",),
            command_id="bad-event",
        )
