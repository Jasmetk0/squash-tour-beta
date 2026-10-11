"""Persistence contract for canonical World Tour Finals Race season authority."""

import pytest

from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityConflict,
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals-race-authority.db'}")
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


def configuration(*, best_n: int = 2) -> WorldTourFinalsRaceConfiguration:
    return WorldTourFinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        eligible_categories=("DIAMOND",),
        best_n=best_n,
        cutoff_week=RankingWeek(season_index=0, week=10),
        cutoff_official_ranking_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="configure-race",
    )


def snapshot(
    config: WorldTourFinalsRaceConfiguration,
    *,
    players: tuple[str, ...] = ("p1",),
):
    source = WorldTourFinalsRaceInput(
        run_id=config.run_id,
        branch_id=config.branch_id,
        target_season_index=config.target_season_index,
        cutoff_week=config.cutoff_week,
        cutoff_official_ranking_fingerprint=(
            config.cutoff_official_ranking_fingerprint
        ),
        eligibility_fingerprint=config.eligibility_fingerprint,
        policy_id=config.policy_id,
        best_n=config.best_n,
        players=tuple(
            WorldTourFinalsRacePlayer(
                player_id=player_id,
                tie_break_token=f"token-{player_id}",
            )
            for player_id in players
        ),
        eligible_results=(),
    )
    return calculate_world_tour_finals_race(source)


@pytest.mark.pr_critical
def test_configuration_and_snapshot_are_idempotent_and_conflicts_fail_closed(database):
    config = configuration()
    with database.begin() as session:
        store = WorldTourFinalsRaceAuthorityStore(session)
        assert store.put_configuration(config) == config
        assert store.put_configuration(config) == config

        reopened = store.get_configuration(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        )
        assert reopened == config

        with pytest.raises(
            WorldTourFinalsRaceAuthorityConflict,
            match="configuration",
        ):
            store.put_configuration(configuration(best_n=3))

        first_snapshot = snapshot(config)
        assert store.put_snapshot(first_snapshot) == first_snapshot
        assert store.put_snapshot(first_snapshot) == first_snapshot

        reopened_snapshot = store.get_snapshot(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        )
        assert reopened_snapshot == first_snapshot

        with pytest.raises(
            WorldTourFinalsRaceAuthorityConflict,
            match="snapshot",
        ):
            store.put_snapshot(snapshot(config, players=("p1", "p2")))


@pytest.mark.pr_critical
def test_snapshot_requires_matching_persisted_configuration(database):
    config = configuration()
    with database.begin() as session:
        store = WorldTourFinalsRaceAuthorityStore(session)
        with pytest.raises(
            ValueError,
            match="requires persisted season configuration",
        ):
            store.put_snapshot(snapshot(config))

        store.put_configuration(config)
        mismatched = snapshot(config).model_copy(
            update={"eligibility_fingerprint": fp("d")}
        )
        with pytest.raises(
            ValueError,
            match="does not match stored configuration",
        ):
            store.put_snapshot(mismatched)


@pytest.mark.pr_critical
def test_store_rejects_missing_run_branch_scope(database):
    config = configuration().model_copy(update={"branch_id": "missing"})
    with database.begin() as session:
        store = WorldTourFinalsRaceAuthorityStore(session)
        with pytest.raises(ValueError, match="scope does not exist"):
            store.put_configuration(config)
