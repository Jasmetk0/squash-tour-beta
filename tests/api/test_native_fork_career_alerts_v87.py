"""Real HTTP/SQLite: a sibling Branch neither inherits nor reveals the other's facts.

Two Branches share one Run and one signed prefix. After the fork only the forked Branch
executes a Week Transition in which prospects turn pro. The career read and the follow
alerts of the forked Branch show that Turn Pro (with its decision source); the original
Branch shows neither, although the follow is a Run-level preference shared by both.
Cold restart returns the same views. The eager Turn Pro calibration is test-only.
"""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players import turn_pro_model
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, _opening_pros, _v87_population
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def career(server, branch, player):
    return _request("GET", f"{server.base_url}/admin/runs/run/branches/{branch}/calendar-tour/players/{player}/career")


def alerts(server, branch):
    code, body = _request("GET", f"{server.base_url}/admin/runs/run/branches/{branch}/notifications")
    assert code == 200, body
    return body


def test_forked_branch_career_and_alerts_do_not_leak_between_siblings(tmp_path, monkeypatch):
    _v87_population(monkeypatch)
    db = f"sqlite:///{tmp_path / 'fork-career.db'}"
    clock = RunCalendar(7, 1, 2030, 3)
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, 12)
        pros, everyone = _opening_pros(repo)
        prospects = set(everyone - pros)
        source = sign_prospects(server, repo, clock)
        created = fork(server, source["revision_id"])
        child = created["branch_id"]
        target = Tour(server, child)
        with monkeypatch.context() as patch:
            patch.setattr(turn_pro_model, "default_turn_pro_model_policy", lambda: EAGER)
            birth, _ = target.execute("transition", "v87-fork-career")
        decided = sorted({d["player_id"] for d in birth["impact"]["turn_pro_decisions"]})
        assert decided and set(decided) <= prospects
        target.save()
        newcomer = decided[0]

        # Follow is Run-level: one command, visible to both Branches' alert reads.
        assert _request("PUT", f"{server.base_url}/admin/runs/run/follows/player/{newcomer}", {})[0] == 200

        # The forked Branch has the Turn Pro fact, with its source and week.
        code, mine = career(server, child, newcomer)
        assert code == 200, mine
        assert mine["overview"]["status"] in {"professional", "retired"}
        turn_pro = next(m for m in mine["milestones"] if m["kind"] == "turn_pro")
        assert turn_pro["source"]["kind"] == "player_ai_decision"
        assert turn_pro["source"]["has_recorded_evidence"] is True
        cards = alerts(server, child)["cards"]
        assert [i["kind"] for c in cards for i in c["items"] if i["player_id"] == newcomer] == ["turn_pro"]

        # The original Branch executed nothing: the same player is not a professional there,
        # no Turn Pro milestone and no alert exists, and its Saved Tour is unchanged.
        code, sibling = career(server, "branch", newcomer)
        assert code == 200, sibling
        assert sibling["overview"]["status"] == "not_professional"
        assert not [m for m in sibling["milestones"] if m["kind"] == "turn_pro"]
        assert alerts(server, "branch")["cards"] == []
        assert "turned_pro_player_ids" not in str(Tour(server, "branch").view()["state"])

        # A historical view of the fork before its transition has no Turn Pro either.
        code, earlier = _request(
            "GET", f"{server.base_url}/admin/runs/run/branches/{child}/calendar-tour/players/{newcomer}/career?as_of_ordinal=0")
        assert code == 200 and not [m for m in earlier["milestones"] if m["kind"] == "turn_pro"]
        before_restart = (mine, sibling, alerts(server, child), alerts(server, "branch"))

    with ApiServer(database_url=db) as restarted:
        assert career(restarted, child, newcomer)[1] == before_restart[0]
        assert career(restarted, "branch", newcomer)[1] == before_restart[1]
        assert alerts(restarted, child) == before_restart[2]
        assert alerts(restarted, "branch") == before_restart[3]
