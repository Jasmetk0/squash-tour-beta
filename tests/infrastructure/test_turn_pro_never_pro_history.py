"""A career that ends without Turn Pro stays an explicit, readable exception.

Component + SQLite level (real lifecycle persistence and cold reopen of the database
file, no HTTP server and no fork execution). It uses the deterministic rare-case
fixture of the domain tests, so no production calibration is touched. The player read
in the service/fork reducer calls the same pure ``player_turn_pro_history``.
"""

import pytest

from beta_engine.domain.players.calendar_lifecycle import calendar_lifecycle_history
from beta_engine.domain.tournaments.calendar_tour import player_turn_pro_history
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle, put_lifecycle
from tests.domain.test_turn_pro_lifecycle import bootstrap, decision, week

pytestmark = pytest.mark.pr_critical


def _scope(session):
    session.add(RunContainerModel(
        run_id="r", display_name="Run", storage_kind="custom_local", read_only=0,
        timeline_start_season=2030, timeline_end_season=2032,
        official_branch_id="b", status="working",
    ))
    session.add(RunBranchModel(
        run_id="r", branch_id="b", display_name="Timeline 1", status="active",
        read_only=0, saved_head_revision_id="rev-1",
    ))
    session.add(BranchWorkingDraftModel(
        draft_id="d", run_id="r", branch_id="b", base_revision_id="rev-1", status="clean",
        change_count=0, draft_version=1, draft_schema_version="run_working_draft_v1",
        changes_json="[]",
    ))
    session.flush()


def _identity(state, player_id):
    return next(p for p in state.players if p.player_id == player_id)


def test_never_pro_exception_survives_sqlite_reopen_and_is_not_a_fake_turn_pro(tmp_path):
    url = f"sqlite:///{tmp_path / 'never-pro.db'}"
    # "c" reaches the automatic retirement age at week 3 without ever turning pro;
    # "a" turns pro at week 2 through a recorded player-AI decision.
    made = (decision("a", 2),)
    history = calendar_lifecycle_history(
        bootstrap("turn_pro.v87", retiring_player=True), week(4), (), turn_pro=made
    )
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        _scope(session)
        for state in history:
            put_lifecycle(session, state)
    engine.dispose()

    reopened = create_sqlite_engine(DatabaseSettings(url=url))
    with create_session_factory(reopened)() as session:
        later = get_lifecycle(session, run_id="r", branch_id="b", week=week(4))
        explanation = player_turn_pro_history(_identity(later, "c"), later.policy, made)
        pro = player_turn_pro_history(_identity(later, "a"), later.policy, made)
        waiting = player_turn_pro_history(_identity(later, "b"), later.policy, made)
        # The retired player's earlier (pre-retirement) week is still a prospect.
        before = get_lifecycle(session, run_id="r", branch_id="b", week=week(2))
        earlier = player_turn_pro_history(_identity(before, "c"), before.policy, made)
    reopened.dispose()

    assert explanation["status"] == "retired_without_turn_pro"
    assert explanation["turn_pro_week"] is None and explanation["decision"] is None
    assert explanation["source"] is None
    assert explanation["retired_week"]["week"] == 3
    assert "no Turn Pro event" in explanation["explanation"]
    assert "health" in explanation["explanation"]  # states that no cause is implied
    assert earlier["status"] == "prospect" and earlier["retired_week"] is None
    assert pro["status"] == "professional" and pro["source"] == "player_ai_decision"
    assert pro["decision"]["player_id"] == "a"
    assert waiting["status"] == "prospect"


def test_historical_rule_has_no_turn_pro_explanation():
    history = calendar_lifecycle_history(bootstrap(retiring_player=True), week(4), ())
    identity = _identity(history[-1], "c")
    assert player_turn_pro_history(identity, history[-1].policy, ()) is None
