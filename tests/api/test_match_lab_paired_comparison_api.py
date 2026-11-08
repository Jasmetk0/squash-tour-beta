"""Real production FastAPI + SQLite Match Lab comparison boundary.

The endpoint simulates only isolated Lab results and cannot create Runs, Sessions,
Saved Revisions, or mutate the two pinned Session snapshots.
"""
from __future__ import annotations

import copy

import pytest

from test_simulation_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def _scenario(server):
    status, entries = _request("GET", f"{server.base_url}/admin/labs/match/scenarios")
    assert status == 200, entries
    return entries[0]["scenario"]


def _candidate(baseline):
    candidate = copy.deepcopy(baseline)
    candidate["scenario_id"] = "alternate-technique-91"
    candidate["context"]["player_a"]["player"]["technique"] = 91
    return candidate


def _body(base, candidate, seeds=(101, 102)):
    return {
        "baseline": {"scenario": base},
        "candidate": {"scenario": candidate},
        "batch_seeds": list(seeds),
    }


def test_real_http_comparison_replays_and_preserves_match_lab_scope(tmp_path):
    db = f"sqlite:///{tmp_path / 'compare.db'}"
    with ApiServer(database_url=db) as server:
        baseline = _scenario(server)
        candidate = _candidate(baseline)
        url = f"{server.base_url}/admin/labs/match/compare"
        data = _body(baseline, candidate)
        before_status, before = _request("POST", url, data)
        after_status, after = _request("POST", url, data)
        assert before_status == after_status == 200, before
        assert before == after
        assert before["schema_version"] == "match_lab_paired_comparison.v1"
        assert before["compared_seeds"] == [101, 102]
        assert before["summary"]["compared_seeds"] == 2
        assert before["summary"]["winner_flip_count"] == sum(
            row["winner_changed"] for row in before["rows"]
        )
        assert all(row["baseline"]["seed"] == row["candidate"]["seed"] == row["seed"]
                   for row in before["rows"])
        assert before["mutations_performed"] is False
        assert before["source_equivalence_proven"] is False
        assert before["baseline_source"]["kind"] == "inline"
        assert before["candidate_source"]["kind"] == "inline"
        status, sessions = _request("GET", f"{server.base_url}/admin/labs/match/sessions")
        assert status == 200 and sessions == []

    with ApiServer(database_url=db) as restarted:
        code, again = _request("POST", f"{restarted.base_url}/admin/labs/match/compare", data)
        assert code == 200 and again == before


def test_real_pinned_saved_session_comparison_survives_sqlite_restart(tmp_path):
    db = f"sqlite:///{tmp_path / 'compare-sessions.db'}"
    with ApiServer(database_url=db) as server:
        baseline = _scenario(server)
        status, session = _request(
            "POST", f"{server.base_url}/admin/labs/match/sessions",
            {"display_name": "Reference to compare", "scenario": baseline},
        )
        assert status == 201, session
        source = {"session_id": session["session_id"],
                  "expected_session_fingerprint": session["session_fingerprint"]}
        body = _body(baseline, _candidate(baseline), seeds=(7,))
        body["baseline"] = source
        status, compared = _request("POST", f"{server.base_url}/admin/labs/match/compare", body)
        assert status == 200, compared
        assert compared["baseline_source"]["kind"] == "saved_session"
        assert compared["baseline_source"]["session_id"] == session["session_id"]
        assert compared["baseline_source"]["session_fingerprint"] == session["session_fingerprint"]
        status, unchanged = _request(
            "GET", f"{server.base_url}/admin/labs/match/sessions/{session['session_id']}"
        )
        assert status == 200 and unchanged == session

    with ApiServer(database_url=db) as restarted:
        status, replay = _request("POST", f"{restarted.base_url}/admin/labs/match/compare", body)
        assert status == 200, replay
        assert replay == compared
        status, read = _request(
            "GET", f"{restarted.base_url}/admin/labs/match/sessions/{session['session_id']}"
        )
        assert status == 200 and read == session


def test_http_rejects_unpinned_or_stale_session_and_invalid_participant_changes(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'invalid.db'}") as server:
        baseline = _scenario(server)
        candidate = _candidate(baseline)
        url = f"{server.base_url}/admin/labs/match/compare"

        status, _ = _request("POST", url, _body(baseline, candidate, seeds=(4, 4)))
        assert status == 422
        status, _ = _request("POST", url, _body(baseline, candidate, seeds=(True,)))
        assert status == 422

        invalid_source = _body(baseline, candidate)
        invalid_source["baseline"] = {"session_id": "none"}
        status, _ = _request("POST", url, invalid_source)
        assert status == 422

        stale = _body(baseline, candidate)
        stale["baseline"] = {
            "session_id": "unknown", "expected_session_fingerprint": "0" * 64
        }
        status, _ = _request("POST", url, stale)
        assert status == 404

        status, saved = _request(
            "POST", f"{server.base_url}/admin/labs/match/sessions",
            {"display_name": "Pinned", "scenario": baseline},
        )
        assert status == 201
        stale["baseline"]["session_id"] = saved["session_id"]
        status, _ = _request("POST", url, stale)
        assert status == 409

        swapped = _candidate(baseline)
        swapped["context"]["player_a"], swapped["context"]["player_b"] = (
            swapped["context"]["player_b"], swapped["context"]["player_a"]
        )
        status, _ = _request("POST", url, _body(baseline, swapped))
        assert status == 409

        wrong = _candidate(baseline)
        wrong["context"]["best_of"] = 3
        status, _ = _request("POST", url, _body(baseline, wrong))
        assert status == 409
