"""Actual FastAPI/SQLite native-calendar rally -> manual Save -> restart replay.

Positive acceptance never re-signs a Saved payload or installs synthetic outcomes.
"""
from __future__ import annotations

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_initial_world_adoption import (
    _world, request as population_request, review as population_review,
    confirm as population_confirm, root as population_root,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def base(server):
    return server.base_url + "/admin/runs/run/branches/branch/authoritative-simulation/calendar-standalone-match"


def prepare_saved_world(server, clock):
    repository, _ = _world(server, clock)
    request = population_request(server)
    reviewed = population_review(server, request)
    code, adopted = population_confirm(server, request, reviewed)
    assert code == 201, adopted
    code, preview = _request("GET", population_root(server) + "/save/preview")
    assert code == 200 and preview["can_save"], preview
    code, saved = _request(
        "POST", population_root(server) + "/save",
        {"expected_draft_version": preview["draft_version"],
         "expected_initial_world_fingerprint": adopted["fingerprint"]},
    )
    assert code == 201, saved
    return repository, saved["saved_revision"]["revision_id"]


@pytest.mark.parametrize("clock", [
    RunCalendar(52, 1, 2030, 3),
    RunCalendar(80, 37, 2100, 3),
])
def test_real_calendar_match_manual_save_restart_and_exact_engine_replay(tmp_path, clock):
    path = tmp_path / "real-calendar-match.db"
    database_url = f"sqlite:///{path}"
    with ApiServer(database_url=database_url) as server:
        repository, saved_head = prepare_saved_world(server, clock)
        code, before = _request("GET", base(server))
        assert code == 200, before
        assert before["match"] is None
        assert before["saved_head_revision_id"] == saved_head
        players = before["player_ids"]
        assert len(players) == 4
        command = {
            "command_id": "play-calendar-match-1",
            "match_id": "first-calendar-match",
            "expected_saved_head": saved_head,
            "expected_initial_world_fingerprint": before["initial_world_fingerprint"],
            "player_a_id": players[0],
            "player_b_id": players[1],
            "seed": 418,
            "operator_label": "Admin",
            "audit_reason": "Real opening-week Run calendar match",
        }
        code, completed = _request("POST", base(server) + "/simulate", command)
        assert code == 201, completed
        match = completed["match"]
        assert match["week"]["calendar"] == clock.to_metadata()
        assert (match["week"]["season_index"], match["week"]["week"]) == (0, 1)
        assert match["source_saved_head"] == saved_head
        assert match["result"]["winner_player_id"] in players[:2]
        assert len(match["result"]["rally_log"]["events"]) > 20
        assert match["result"]["timeline_log"]["events"]
        assert match["result"]["stamina_log"]
        assert _request("POST", base(server) + "/simulate", command) == (201, completed)
        assert _request("POST", base(server) + "/simulate", {**command, "seed": 419})[0] == 409
        assert _request("POST", base(server) + "/simulate",
                        {**command, "command_id": "duplicate", "seed": 420})[0] == 409

        code, replay = _request("GET", base(server) + "/first-calendar-match/replay")
        assert code == 200 and replay["exact_replay"], replay
        assert replay["result"] == match["result"]
        assert replay["rally_count"] == len(match["result"]["rally_log"]["events"])
        code, preview = _request("GET", base(server) + "/save/preview")
        assert code == 200 and preview["can_save"], preview
        assert preview["calendar_match_fingerprint"] == completed["fingerprint"]
        code, saved = _request(
            "POST", base(server) + "/save",
            {"expected_draft_version": preview["draft_version"],
             "expected_calendar_match_fingerprint": preview["calendar_match_fingerprint"]},
        )
        assert code == 201, saved
        revision = saved["saved_revision"]
        component = revision["payload"]["content"]["calendar_standalone_match"]
        assert component["fingerprint"] == completed["fingerprint"]
        assert component["state"] == match
        assert repository.verify_branch_saved_revision_hash(
            revision_id=revision["revision_id"]
        )
        assert repository.verify_branch_saved_revision_hash(revision_id=saved_head)
        code, inspected = _request("GET", base(server))
        assert code == 200 and inspected["saved"] is True, inspected
        code, second_preview = _request("GET", base(server) + "/save/preview")
        assert code == 200 and not second_preview["can_save"], second_preview
        assert _request("POST", base(server) + "/save",
                        {"expected_draft_version": preview["draft_version"],
                         "expected_calendar_match_fingerprint": completed["fingerprint"]})[0] == 409
        saved_id = revision["revision_id"]

    with ApiServer(database_url=database_url) as server:
        code, after = _request("GET", base(server))
        assert code == 200 and after["saved"], after
        assert after["match"] == match
        assert after["match_fingerprint"] == completed["fingerprint"]
        code, replay = _request("GET", base(server) + "/first-calendar-match/replay")
        assert code == 200 and replay["exact_replay"] and replay["result"] == match["result"]
        assert server.app.state.runtime.repository.verify_branch_saved_revision_hash(
            revision_id=saved_id
        )


def test_calendar_match_refuses_missing_saved_world_and_foreign_scope(tmp_path):
    path = tmp_path / "no-match.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default())
        url = base(server)
        assert _request("GET", url)[0] == 409
        assert _request("GET", url + "/not-found/replay")[0] == 404
