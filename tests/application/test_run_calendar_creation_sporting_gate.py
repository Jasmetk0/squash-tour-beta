"""Real custom-Run roots cannot enter still-FAX sporting writers."""

import pytest

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.standalone_match_service import (
    StandaloneMatchService,
    StandaloneMatchSimulateCommand,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from tests.application.test_authoritative_slot_matches import session_at

pytestmark = pytest.mark.pr_critical


def _setup(tmp_path, clock):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'new-run.db'}"))
    factory = create_session_factory(engine)
    repo = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    repo.bootstrap_schema()
    ids = iter(("new-run", "new-branch", "new-revision", "new-draft"))
    RunContainerCreationService(repo, lambda _: next(ids)).create_empty_run(
        display_name="Reviewed calendar", calendar=clock,
    )
    # Reuse real, valid profiles; the source fixture belongs to another database.
    with session_at(tmp_path / "profiles.db") as source:
        world = get_initial_world(source, run_id="run", branch_id="branch")
        assert world is not None
        world = world.model_copy(update={"run_id": "new-run", "branch_id": "new-branch"})
    return engine, factory, repo, world


def _dump(engine):
    connection = engine.raw_connection()
    try:
        return tuple(connection.driver_connection.iterdump())
    finally:
        connection.close()


def _ranking():
    return RankingBootstrapCommand(
        command_id="initial-ranking", run_id="new-run", branch_id="new-branch",
        policy=OfficialRankingPolicy(policy_id="initial-policy"), players=(), discipline="none",
    )


def _slot(session):
    return AuthoritativeSlotMatchExecutor(session).create_slot(
        run_id="new-run", branch_id="new-branch", week=RankingWeek(season_index=0, week=1),
        slot_id="opening", ordinal=1, group_ids=(), match_events=(),
    )


@pytest.mark.parametrize("clock", [
    RunCalendar.earth_default(), RunCalendar(52, 35, 2030, 3),
    RunCalendar.fax_default(season_count=51),
])
def test_custom_creation_rejects_initial_world_ranking_and_slot_without_partial_writes(tmp_path, clock):
    engine, factory, repo, world = _setup(tmp_path, clock)
    try:
        before = _dump(engine)
        with pytest.raises(ValueError, match="Initial world adoption cannot execute"):
            repo.adopt_initial_world(world)
        assert _dump(engine) == before
        runner = RankingWeekCommandRunner(factory)
        for operation in (runner.preview, runner.execute):
            with pytest.raises(ValueError, match="Ranking preparation cannot execute"):
                operation(_ranking())
            assert _dump(engine) == before
        with pytest.raises(ValueError, match="Standalone match simulation cannot execute"):
            StandaloneMatchService(factory).simulate(
                run_id="new-run", branch_id="new-branch",
                command=StandaloneMatchSimulateCommand(
                    command_id="match", expected_workspace_fingerprint="a" * 64,
                    seed=1, operator_label="Admin", audit_reason="Calendar protection",
                ),
            )
        assert _dump(engine) == before
        with factory.begin() as session:  # noqa: SIM117
            # Catch inside the transaction: committing afterwards must write nothing.
            with pytest.raises(ValueError, match="Match slot creation cannot execute"):
                _slot(session)
        assert _dump(engine) == before
        assert repo.verify_branch_saved_revision_hash(revision_id="new-revision")
    finally:
        engine.dispose()


def test_actual_default_creation_still_adopts_and_prepares_with_exact_replay(tmp_path):
    engine, factory, repo, world = _setup(tmp_path, RunCalendar.fax_default())
    try:
        assert repo.adopt_initial_world(world) == world
        before = _dump(engine)
        assert repo.adopt_initial_world(world) == world
        assert _dump(engine) == before
        runner = RankingWeekCommandRunner(factory)
        ranking = runner.execute(_ranking())
        assert runner.preview(_ranking()) == ranking
        assert runner.execute(_ranking()) == ranking
        # The initial Saved head was not implicitly changed by sporting work.
        assert repo.verify_branch_saved_revision_hash(revision_id="new-revision")
    finally:
        engine.dispose()
