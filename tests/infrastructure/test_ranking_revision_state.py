"""Capture real persisted ranking components and verify without a database."""

import json
import pytest
from sqlalchemy import text
from test_official_ranking_storage import database  # noqa: F401
from test_ranking_bootstrap_command import command

from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.official import OfficialRankingResult, RankingWeek
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.revision_state import load_ranking_revision_state
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel, RunBranchModel
from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner, stage_ranking_week_command
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state


@pytest.fixture
def captured(database):
    initial = command()
    runner = RankingWeekCommandRunner(database)
    first = runner.execute(initial)
    version = RankingResultVersion(
        run_id="run", branch_id="branch", effective_week=RankingWeek(season_index=0, week=2), previous_fingerprint=None,
        result=OfficialRankingResult(edition_id="edition", player_id="a", source_fingerprint="award",
            completed_week=first.week, first_publication_week=RankingWeek(season_index=0, week=2), main_points=100),
    )
    correction = version.model_copy(update={
        "effective_week": RankingWeek(season_index=0, week=3), "previous_fingerprint": version.fingerprint,
        "result": version.result.model_copy(update={"main_points": 300, "source_fingerprint": "corrected"}),
    })
    with database.begin() as session:
        store = OfficialRankingResultStore(session)
        store.append(version)
        store.append(correction)
    previous = first
    for week in (2, 3):
        previous = runner.execute(RankingWeekCommand(
            command_id=f"week-{week}", tournaments=(), context=RankingTransitionContext(
                run_id="run", branch_id="branch", completed_week=previous.week,
                target_week=RankingWeek(season_index=0, week=week), policy=first.policy,
                players=initial.players, discipline="none",
            ),
        ))
    with database.begin() as session:
        session.execute(text("BEGIN"))
        state = capture_ranking_revision_state(session, run_id="run", branch_id="branch")
    return state


@pytest.mark.smoke
def test_capture_roundtrip_preserves_history_and_corrections(database, captured):
    restored = load_ranking_revision_state(captured.model_dump_json(), expected_fingerprint=captured.fingerprint, run_id="run", branch_id="branch")
    assert restored == captured
    assert [e.snapshot.rows[0].points for e in restored.entries[1:]] == [100, 300]
    assert len(restored.sources) == 2
    assert restored.entries[0].inputs.players == command().players
    with database.begin() as session:
        session.execute(text("BEGIN"))
        again = capture_ranking_revision_state(session, run_id="run", branch_id="branch")
        assert again.fingerprint == captured.fingerprint
        assert not session.new and not session.dirty and not session.deleted


@pytest.mark.smoke
@pytest.mark.parametrize("damage", ["token", "source", "gap", "receipt", "scope"])
def test_bundle_damage_is_rejected(captured, damage):
    payload = captured.model_dump(mode="json")
    if damage == "token":
        payload["entries"][0]["inputs"]["players"][0]["tie_break_token"] = "changed"
    elif damage == "source":
        payload["sources"].pop(0)
    elif damage == "gap":
        payload["entries"].pop(1)
    elif damage == "receipt":
        payload["entries"][0]["receipts"][0]["request_fingerprint"] = "0" * 64
    else:
        payload["branch_id"] = "other"
    with pytest.raises(ValueError):
        load_ranking_revision_state(json.dumps(payload), expected_fingerprint=captured.fingerprint, run_id="run", branch_id="branch")


@pytest.mark.smoke
def test_capture_in_outer_transaction_does_not_commit(database):
    with pytest.raises(RuntimeError):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            stage_ranking_week_command(session, None, command())
            state = capture_ranking_revision_state(session, run_id="run", branch_id="branch")
            assert len(state.entries) == 1
            raise RuntimeError("later revision stage failed")
    with database.begin() as session:
        session.execute(text("BEGIN"))
        assert capture_ranking_revision_state(session, run_id="run", branch_id="branch").entries == ()


def test_capture_rejects_legacy_inputs(database):
    request = command()
    RankingWeekCommandRunner(database).execute(request)
    with database.begin() as session:
        receipt = session.get(OfficialRankingCommandModel, ("run", "branch", request.command_id))
        receipt.input_manifest_version = None
        receipt.input_manifest_json = None
    with database.begin() as session:
        session.execute(text("BEGIN"))
        with pytest.raises(ValueError, match="Legacy"):
            capture_ranking_revision_state(session, run_id="run", branch_id="branch")


@pytest.mark.parametrize("autobegin", [False, True])
def test_capture_requires_physical_transaction(database, autobegin):
    with database() as session:
        if autobegin:
            session.execute(text("SELECT 1"))
        with pytest.raises(ValueError, match="transaction"):
            capture_ranking_revision_state(session, run_id="run", branch_id="branch")


def test_capture_readonly_and_fork_guards(database, captured):
    with database.begin() as session:
        session.get(RunBranchModel, "branch").read_only = True
    with database.begin() as session:
        session.execute(text("BEGIN"))
        assert capture_ranking_revision_state(session, run_id="run", branch_id="branch") == captured
    with database.begin() as session:
        session.get(RunBranchModel, "branch").forked_from_branch_id = "other"
    with database.begin() as session:
        session.execute(text("BEGIN"))
        with pytest.raises(ValueError, match="fork"):
            capture_ranking_revision_state(session, run_id="run", branch_id="branch")
