"""Persistence contract for canonical World Tour Finals Race authority."""

import pytest

from beta_engine.domain.finals import (
    FinalsRaceConfiguration,
    FinalsRaceSnapshot,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    FinalsRaceAuthorityConflict,
    FinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.models import Base


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals-race.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def configuration(best_n: int = 2) -> FinalsRaceConfiguration:
    return FinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        season_index=0,
        best_n_results=best_n,
        eligible_categories=("DIAMOND",),
        cutoff_ranking_week=RankingWeek(season_index=0, week=10),
        cutoff_ranking_snapshot_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="config-command",
    )


def snapshot(config: FinalsRaceConfiguration, *, marker: str = "d") -> FinalsRaceSnapshot:
    return FinalsRaceSnapshot(
        run_id=config.run_id,
        branch_id=config.branch_id,
        season_index=config.season_index,
        cutoff_ranking_week=config.cutoff_ranking_week,
        configuration_fingerprint=config.fingerprint,
        cutoff_ranking_snapshot_fingerprint=config.cutoff_ranking_snapshot_fingerprint,
        cutoff_transition_fingerprint=config.cutoff_transition_fingerprint,
        calendar_content_fingerprint=config.calendar_content_fingerprint,
        source_event_ids=(f"E-{marker}",),
        source_fingerprints=(fp(marker),),
        rows=(),
    )


@pytest.mark.pr_critical
def test_configuration_and_snapshot_are_idempotent_and_conflicts_fail_closed(database):
    first = configuration()
    with database.begin() as session:
        store = FinalsRaceAuthorityStore(session)
        assert store.put_configuration(first).fingerprint == first.fingerprint
        assert store.put_configuration(first).fingerprint == first.fingerprint
        stored = store.get_configuration(
            run_id="run", branch_id="branch", season_index=0
        )
        assert stored is not None and stored.fingerprint == first.fingerprint

        with pytest.raises(FinalsRaceAuthorityConflict, match="configuration"):
            store.put_configuration(configuration(best_n=3))

        race = snapshot(first)
        assert store.put_snapshot(race).fingerprint == race.fingerprint
        assert store.put_snapshot(race).fingerprint == race.fingerprint
        loaded = store.get_snapshot(
            run_id="run", branch_id="branch", season_index=0
        )
        assert loaded is not None and loaded.fingerprint == race.fingerprint

        with pytest.raises(FinalsRaceAuthorityConflict, match="snapshot"):
            store.put_snapshot(snapshot(first, marker="e"))


@pytest.mark.pr_critical
def test_snapshot_requires_matching_persisted_configuration(database):
    config = configuration()
    with database.begin() as session:
        store = FinalsRaceAuthorityStore(session)
        with pytest.raises(ValueError, match="requires persisted season configuration"):
            store.put_snapshot(snapshot(config))
