"""Initial ranking through the production command and real SQLite persistence."""

import pytest
from sqlalchemy import select, text
from test_official_ranking_storage import database  # noqa: F401

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.domain.rankings.official import OfficialRankingPlayer, OfficialRankingPolicy, RankingWeek
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel, RunBranchModel
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner, stage_ranking_week_command


def command():
    return RankingBootstrapCommand(
        command_id="initial-ranking", run_id="run", branch_id="branch",
        policy=OfficialRankingPolicy(policy_id="initial-policy"), discipline="none",
        players=tuple(OfficialRankingPlayer(
            player_id=p, tie_break_token=p, tour_entry_week=RankingWeek(season_index=0, week=1)
        ) for p in ("a", "b")),
    )


@pytest.mark.smoke
def test_bootstrap_replay_and_first_week_transition(database):
    request = command()
    runner = RankingWeekCommandRunner(database)
    first = runner.execute(request)
    assert first.week.ordinal == 0
    assert first.previous_fingerprint is None
    # Players entering this week remain NR until the following snapshot.
    assert first.rows == ()
    assert runner.execute(request.model_copy(update={"players": tuple(reversed(request.players))})) == first
    next_week = RankingWeekCommand(
        command_id="next-week", tournaments=(),
        context=RankingTransitionContext(
            run_id=request.run_id, branch_id=request.branch_id,
            completed_week=first.week, target_week=RankingWeek(season_index=0, week=2),
            policy=request.policy, players=request.players, discipline="none",
        ),
    )
    second = runner.execute(next_week)
    assert second.previous_fingerprint == first.fingerprint
    assert [r.player_id for r in second.rows] == ["a", "b"]
    assert all(r.points == 0 for r in second.rows)
    assert runner.execute(request) == first
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch") == (first, second)
        assert len(session.scalars(select(OfficialRankingCommandModel)).all()) == 2


@pytest.mark.smoke
def test_bootstrap_conflicting_id_or_target_cannot_replace_initial_ranking(database):
    request = command()
    runner = RankingWeekCommandRunner(database)
    first = runner.execute(request)
    with pytest.raises(ValueError, match="different request"):
        runner.execute(request.model_copy(update={"players": ()}))
    with pytest.raises(ValueError, match="already staged"):
        runner.execute(request.model_copy(update={"command_id": "another"}))
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch") == (first,)


@pytest.mark.smoke
def test_bootstrap_outer_rollback_removes_candidate_and_receipt(database):
    with pytest.raises(RuntimeError, match="later failure"):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            stage_ranking_week_command(session, None, command())
            raise RuntimeError("later failure")
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch") == ()
        assert session.scalars(select(OfficialRankingCommandModel)).all() == []


@pytest.mark.parametrize("damage", ["week", "duplicate", "read_only", "fork", "scope"])
def test_bootstrap_rejects_invalid_initial_context(database, damage):
    request = command()
    if damage == "week":
        request = request.model_copy(update={"target_week": RankingWeek(season_index=1, week=1)})
    elif damage == "duplicate":
        request = request.model_copy(update={"players": (request.players[0], request.players[0])})
    elif damage == "scope":
        request = request.model_copy(update={"run_id": "missing"})
    else:
        with database.begin() as session:
            branch = session.get(RunBranchModel, "branch")
            if damage == "read_only":
                branch.read_only = True
            else:
                branch.forked_from_branch_id = "other"
    with pytest.raises(ValueError):
        RankingWeekCommandRunner(database).execute(request)
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch") == ()
        assert session.scalars(select(OfficialRankingCommandModel)).all() == []


def test_empty_initial_roster_is_explicitly_supported(database):
    snapshot = RankingWeekCommandRunner(database).execute(command().model_copy(update={"players": ()}))
    assert snapshot.rows == ()


def test_bootstrap_manifest_keeps_nr_roster(database):
    from beta_engine.domain.rankings.input_manifest import RankingInputManifest

    request = command()
    snapshot = RankingWeekCommandRunner(database).execute(request)
    assert snapshot.rows == ()
    with database() as session:
        receipt = session.get(OfficialRankingCommandModel, ("run", "branch", request.command_id))
        manifest = RankingInputManifest.model_validate_json(receipt.input_manifest_json)
        assert manifest.players == request.players
        manifest.verify(snapshot, None)


@pytest.mark.smoke
def test_legacy_receipt_schema_upgrade_preserves_receipt_and_is_repeatable(database):
    from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository

    engine = database.kw["bind"]
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE official_ranking_commands DROP COLUMN input_manifest_version"))
        connection.execute(text("ALTER TABLE official_ranking_commands DROP COLUMN input_manifest_json"))
        connection.execute(text("INSERT INTO official_ranking_commands (run_id, branch_id, command_id, request_fingerprint, target_ordinal, snapshot_fingerprint) VALUES ('run', 'branch', 'legacy', 'request', 0, 'snapshot')"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=database)
    repository.bootstrap_schema()
    repository.bootstrap_schema()
    with database() as session:
        receipt = session.get(OfficialRankingCommandModel, ("run", "branch", "legacy"))
        assert receipt.request_fingerprint == "request"
        assert receipt.snapshot_fingerprint == "snapshot"
        assert receipt.input_manifest_version is None
        assert receipt.input_manifest_json is None


def test_legacy_receipt_without_manifest_remains_replayable(database):
    request = command()
    runner = RankingWeekCommandRunner(database)
    snapshot = runner.execute(request)
    with database.begin() as session:
        receipt = session.get(OfficialRankingCommandModel, ("run", "branch", request.command_id))
        receipt.input_manifest_version = None
        receipt.input_manifest_json = None
    assert runner.execute(request) == snapshot
