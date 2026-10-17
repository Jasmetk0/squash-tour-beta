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
from tests.api.test_player_generation_calendar_gate import _dump

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
        # The new branch-owned match provenance is deliberately not yet
        # transferable; unlike a fork from the pre-match Saved head, forking
        # the played match must fail closed rather than fabricate ownership.
        fork_code, fork_error = _request(
            "POST", server.base_url + "/run-containers/run/branches",
            {"source_branch_id": "branch", "source_saved_revision_id": revision["revision_id"]},
        )
        assert fork_code == 409, fork_error
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


def test_calendar_match_restore_removes_live_result_but_not_immutable_history(tmp_path):
    path = tmp_path / "restore-calendar-match.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository, population_head = prepare_saved_world(server, RunCalendar.earth_default(start_year=2030, season_count=3))
        _, inspected = _request("GET", base(server))
        command = {
            "command_id": "restore-play", "match_id": "one-exhibition",
            "expected_saved_head": population_head,
            "expected_initial_world_fingerprint": inspected["initial_world_fingerprint"],
            "player_a_id": inspected["player_ids"][0],
            "player_b_id": inspected["player_ids"][1],
            "seed": 18,
            "operator_label": "Admin",
            "audit_reason": "Verify restored Saved revision is an earlier truthful history",
        }
        status, played = _request("POST", base(server) + "/simulate", command)
        assert status == 201, played
        status, preview = _request("GET", base(server) + "/save/preview")
        assert status == 200 and preview["can_save"], preview
        status, saved = _request("POST", base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": played["fingerprint"],
        })
        assert status == 201, saved
        played_head = saved["saved_revision"]["revision_id"]
        restore_url = server.base_url + (
            f"/run-containers/run/branches/branch/saved-revisions/{population_head}/restore"
        )
        status, preflight = _request("GET", restore_url + "-preflight")
        assert status == 200 and preflight["can_restore"], preflight
        assert preflight["saved_head_revision_id"] == played_head
        request = {
            "expected_head_saved_revision_id": played_head,
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": "branch",
            "explicit_confirmation": True,
        }
        assert _request("POST", restore_url, {**request, "explicit_confirmation": False})[0] == 409
        status, restored = _request("POST", restore_url, request)
        assert status == 201, restored
        restored_id = restored["saved_revision"]["revision_id"]
        restored_revision = repository.get_branch_saved_revision(revision_id=restored_id)
        assert restored_revision is not None
        assert "calendar_standalone_match" not in restored_revision.payload["content"]
        status, after = _request("GET", base(server))
        assert status == 200 and after["match"] is None, after
        assert _request("GET", base(server) + "/one-exhibition/replay")[0] == 404
        assert repository.verify_branch_saved_revision_hash(revision_id=population_head)
        assert repository.verify_branch_saved_revision_hash(revision_id=played_head)
        assert repository.verify_branch_saved_revision_hash(
            revision_id=restored["saved_revision"]["revision_id"]
        )


def test_calendar_match_rejects_stale_source_and_detects_sqlite_tamper(tmp_path):
    import json

    from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel

    path = tmp_path / "tamper-calendar-match.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, head = prepare_saved_world(server, RunCalendar(80, 37, 2100, 3))
        _, inspected = _request("GET", base(server))
        command = {
            "command_id": "tamper-play", "match_id": "unforgeable-match",
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": inspected["initial_world_fingerprint"],
            "player_a_id": inspected["player_ids"][0],
            "player_b_id": inspected["player_ids"][1],
            "seed": 811,
            "operator_label": "Admin",
            "audit_reason": "Attack stale, duplicate and forged sporting writes",
        }
        before = _dump(path)
        for changed in (
            {"expected_saved_head": "other-head"},
            {"expected_initial_world_fingerprint": "0" * 64},
            {"player_b_id": command["player_a_id"]},
            {"player_b_id": "unknown-player"},
        ):
            assert _request("POST", base(server) + "/simulate", {**command, **changed})[0] == 409
        assert _dump(path) == before
        status, played = _request("POST", base(server) + "/simulate", command)
        assert status == 201, played
        with repo._session_factory.begin() as session:
            row = session.get(
                CalendarStandaloneMatchModel,
                ("run", "branch", "unforgeable-match"),
            )
            assert row is not None
            raw = json.loads(row.payload_json)
            raw["seed"] += 1
            row.payload_json = json.dumps(raw)
        assert _request("GET", base(server))[0] == 409
        assert _request("GET", base(server) + "/unforgeable-match/replay")[0] == 409
        assert repo.verify_branch_saved_revision_hash(revision_id=head)
