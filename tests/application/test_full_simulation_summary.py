"""Frozen terminal summaries over actual HTTP, SQLite and MatchEngine receipts."""
import json

import pytest
from sqlalchemy import text

from beta_engine.application.authoritative_run_simulation_driver import AuthoritativeRunSimulationDriver
from beta_engine.infrastructure.db.models import AuthoritativeSimulationCommandModel
from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
from tests.api.test_saved_revision_history_api import _request
from tests.support.full_simulation_http_flow import initialize, make_server, snapshot
from test_full_simulation_http_flow import reviewed_command


@pytest.mark.pr_critical
@pytest.mark.parametrize("terminal", ["stopped", "target_reached"])
def test_terminal_summary_is_frozen_scoped_and_does_not_read_later_position(tmp_path, monkeypatch, terminal):
    server, factory, _gate = make_server(tmp_path)
    with server:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        root = server.base_url + flow["scope"]
        assert _request("POST", root + "/simulate-full-simulation", command)[0] == 201
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert len(before["groups"]) == 3
        summary_url = root + f"/full-simulation/parents/{command['command_id']}/summary"
        assert _request("GET", summary_url)[1]["available"] is False
        control = {"target_command_id": command["command_id"], "control_command_id": "end-summary",
            "operator_label": "Operator", "audit_reason": "Freeze a truthful terminal summary"}
        if terminal == "stopped":
            assert _request("POST", root + "/full-simulation/control", control | {"action":"stop"})[0] == 200
        else:
            week = _request("GET", root + "/position")[1]["current_week"]
            assert _request("POST", root + "/full-simulation/target", control | {"target_week":week})[0] == 200
            assert _request("POST", root + "/simulate-full-simulation", command)[1]["status"] == terminal
        status, response = _request("GET", summary_url)
        assert status == 200 and response["available"] is True, response
        summary = response["summary"]
        assert summary["status"] == terminal
        assert summary["start_week"] == command["expected_start_week"]
        assert summary["end_week"] == summary["position"]["current_week"]
        assert summary["target_reached"] is (terminal == "target_reached")
        assert summary["terminal_audit_reason"] == control["audit_reason"]
        assert summary["terminal_control_command_id"] == control["control_command_id"]
        assert summary["persisted_child_command_count"] > 0
        assert len(summary["completed_tournaments"]) == 1
        tournament = summary["completed_tournaments"][0]
        with factory() as session:
            source = OwnedTournamentRankingSourceStore(session).get(run_id=flow["run_id"],
                branch_id=flow["branch_id"], edition_id=tournament["edition_id"])
            result = source.canonical_result or source.result.summary
            assert tournament["champion_player_id"] == result.champion_player_id
            assert tournament["source_command_id"] == source.adopted_by_command_id
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == before["groups"] and after["saved"] == before["saved"]
        # A later, explicitly confirmed Save changes the current head but must
        # not rewrite the Saved Revision recorded at this operation's endpoint.
        preview = _request("GET", root + "/save/preview")[1]
        status, saved = _request("POST", root + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_simulation_fingerprint": preview["simulation_fingerprint"]})
        assert status == 201, saved
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["saved_head"] != summary["terminal_saved_revision_id"]
        # If either GET or terminal replay tries today's Position, fail the test.
        def no_current_position(*args, **kwargs):
            raise ValueError("A later Branch position must not rewrite terminal history")
        monkeypatch.setattr(AuthoritativeRunSimulationDriver, "_position", no_current_position)
        assert _request("GET", summary_url) == (200, response)
        status, replay = _request("POST", root + "/simulate-full-simulation", command)
        assert status == 201 and replay["current_week"] == summary["end_week"], replay
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
        other_url = server.base_url + flow["other_scope"] + f"/full-simulation/parents/{command['command_id']}/summary"
        assert _request("GET", other_url)[0] == 409
        # Valid-looking but altered data cannot silently become a new digest.
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(AuthoritativeSimulationCommandModel,(flow["run_id"],flow["branch_id"],command["command_id"]))
            frozen = json.loads(row.result_json)
            frozen["terminal_summary"]["end_week"] = {"season_index":1,"week":1}
            row.result_json = json.dumps(frozen)
        assert _request("GET", summary_url)[0] == 409


@pytest.mark.pr_critical
def test_legacy_terminal_summary_is_unavailable_without_fabricated_current_fallback(tmp_path):
    server, factory, _gate = make_server(tmp_path)
    with server:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        root = server.base_url + flow["scope"]
        assert _request("POST", root + "/simulate-full-simulation", command)[0] == 201
        assert _request("POST", root + "/full-simulation/control", {
            "control_command_id":"stop","target_command_id":command["command_id"],"action":"stop",
            "operator_label":"Operator","audit_reason":"Legacy proof"})[0] == 200
        with factory.begin() as session:
            row=session.get(AuthoritativeSimulationCommandModel,(flow["run_id"],flow["branch_id"],command["command_id"]))
            frozen=json.loads(row.result_json);del frozen["terminal_summary"];row.result_json=json.dumps(frozen)
        before=snapshot(factory,flow["run_id"],flow["branch_id"])
        response=_request("GET",root+f"/full-simulation/parents/{command['command_id']}/summary")[1]
        assert response["available"] is False and response["summary"] is None
        assert snapshot(factory,flow["run_id"],flow["branch_id"]) == before
