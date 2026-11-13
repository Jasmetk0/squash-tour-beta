"""Real HTTP/SQLite Master v87 Turn Pro in a public native fork, re-run on replay."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players import turn_pro_model
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, _opening_pros, _v87_population
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke


def test_v87_native_fork_runs_records_and_replays_turn_pro(tmp_path, monkeypatch):
    _v87_population(monkeypatch)
    db = f"sqlite:///{tmp_path / 'v87-fork.db'}"
    clock = RunCalendar(7, 1, 2030, 3)
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, 12)
        pros, everyone = _opening_pros(repo)
        prospects = set(everyone - pros)
        assert prospects, pros
        source = sign_prospects(server, repo, clock)
        created = fork(server, source["revision_id"])
        target = Tour(server, created["branch_id"])
        with monkeypatch.context() as patch:
            patch.setattr(turn_pro_model, "default_turn_pro_model_policy", lambda: EAGER)
            birth, _ = target.execute("transition", "v87-fork-birth")
        impact = birth["impact"]
        assert impact["native_transition"] and impact["turn_pro_model"] == EAGER.model_dump(
            mode="json"
        )
        decided = {d["player_id"] for d in impact["turn_pro_decisions"]}
        assert decided and decided <= prospects, decided
        assert all(d["branch_id"] == created["branch_id"] for d in impact["turn_pro_decisions"])
        target.save()
        event = target.view()["state"]["transitions"][-1]["public_event"]
        assert event["turned_pro_player_ids"] == sorted(decided)
        # The original Branch is untouched by the fork's Turn Pro decisions.
        assert "turned_pro_player_ids" not in str(Tour(server, "branch").view()["state"])
        later, _ = target.execute("transition", "v87-fork-next")
        assert later["impact"]["turn_pro_model"]["model_id"] == "pre-alpha-turn-pro.v2"
        assert not {d["player_id"] for d in later["impact"]["turn_pro_decisions"]} & (
            pros | decided
        )
        target.save()
        fork_view = target.view()
    # Restart: the fork replays its commands with each recorded model.
    with ApiServer(database_url=db) as restarted:
        assert Tour(restarted, created["branch_id"]).view() == fork_view
