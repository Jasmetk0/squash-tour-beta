"""Real native Season Transition through HTTP, signed SQLite and immutable Save.

Small W=4 is intentional: this tests the *entire* actual terminal-season
transition, without a 52/80-week wait in ordinary PR feedback. Domain tests
exercise exact W52/W61/W80 and their offsets separately.
"""
import copy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
from tests.api.test_calendar_tour_flow import (
    command, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize("override_policy", [False, True])
def test_real_native_last_week_to_new_season_save_restart_restore_and_retry(
    tmp_path, monkeypatch, override_policy,
):
    from beta_engine.application import calendar_tour_service as tour_app

    path = tmp_path / "native-season.db"
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        repo, _initial_saved = setup(server, RunCalendar(4, 2, 2030, 3))
        early = inspect(server)
        assert early["state"]["week"]["week"] == 2
        assert "season_transition_requires_last_week" in early["season_transition_blockers"]
        bad = command(early, "season-transition", name="too-early")
        assert _request("POST", tour_url(server) + "/preview", bad)[0] == 409

        # Two genuine Official Week Transitions and their distinct manual
        # immutable Saves bring the actually played population to terminal W.
        for completed_week in (2, 3):
            view = inspect(server)
            assert view["state"]["week"]["week"] == completed_week
            receipt, _ = execute(
                server, command(view, "transition", name=f"finish-{completed_week}")
            )
            assert receipt["impact"]["target_week"]["week"] == completed_week + 1
            save_tour(server)

        terminal = inspect(server)
        assert terminal["state"]["week"]["week"] == 4
        assert terminal["transition_blockers"] == ["season_transition_required"]
        assert terminal["season_transition_blockers"] == []
        assert terminal["saved"]
        if override_policy:
            week = terminal["state"]["week"]
            effective_week = {**week, "season_index": 1, "week": 1}
            staged, _ = execute(
                server,
                command(
                    terminal, "policy", name="incoming-ranking-policy",
                    data={
                        "effective_week": effective_week,
                        "ranking": {"policy_id": "incoming-best-12", "best_n": 12},
                    },
                ),
            )
            assert staged["manual_save_required"]
            save_tour(server)
            terminal = inspect(server)
        previous_head = terminal["saved_head_revision_id"]
        cmd = command(terminal, "season-transition", name="real-new-season")
        code, review = _request("POST", tour_url(server) + "/preview", cmd)
        assert code == 200, review
        assert review["impact"]["target_week"]["season_index"] == 1
        assert review["impact"]["target_week"]["week"] == 1
        assert review["impact"]["ranking"]["policy"]["best_n"] == (
            12 if override_policy else 15
        )
        request = {
            "command": cmd, "expected_preview_fingerprint": review["preview_fingerprint"],
            "explicit_confirmation": True,
        }
        before = _dump(path)
        original_fault = tour_app._fault_injection_point

        def fail_late(name):
            if name == "after_ranking_and_public_event_staging":
                raise ValueError("Injected season-publication rollback")
            return original_fault(name)

        monkeypatch.setattr(tour_app, "_fault_injection_point", fail_late)
        assert _request("POST", tour_url(server) + "/execute", request)[0] == 409
        assert _dump(path) == before
        monkeypatch.setattr(tour_app, "_fault_injection_point", original_fault)

        status, result = _request("POST", tour_url(server) + "/execute", request)
        assert status == 201, result
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
        working = inspect(server)
        assert not working["saved"]
        assert working["state"]["schema_version"] == "calendar_tour_authority.v2"
        assert working["state"]["week"]["season_index"] == 1
        assert working["state"]["week"]["week"] == 1
        assert working["state"]["transitions"][-1]["public_event"]["kind"] == "season_transition_completed"
        assert working["state"]["rankings"][-1]["policy"]["best_n"] == (
            12 if override_policy else 15
        )
        assert working["transition_blockers"] == []
        saved_receipt = save_tour(server)
        signed_head = saved_receipt["revision_id"]
        signed = repo.get_branch_saved_revision(revision_id=signed_head)
        cp = signed.payload["content"]["calendar_player_sporting_checkpoint"]
        assert cp["state"]["schema_version"] == "calendar_sporting_checkpoint.v10"
        assert cp["state"]["week_events"][-1]["schema_version"] == "calendar_sporting_week_advance.v3"
        assert repo.verify_branch_saved_revision_hash(revision_id=previous_head)
        assert repo.verify_branch_saved_revision_hash(revision_id=signed_head)
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)

        for fault in ("downgrade", "foreign", "fake-week"):
            forged = copy.deepcopy(signed.payload)
            cp = forged["content"]["calendar_player_sporting_checkpoint"]
            if fault == "downgrade":
                cp["state"]["week_events"][-1]["schema_version"] = "calendar_sporting_week_advance.v2"
            elif fault == "foreign":
                cp["state"]["week_events"][-1]["branch_id"] = "outsider"
            else:
                cp["state"]["week_events"][-1]["target_week"]["week"] = 2
            cp["fingerprint"] = canonical_hash(cp["state"])
            with pytest.raises(ValueError):
                load_saved_calendar_match(forged, run_id="run", branch_id="branch")

    with ApiServer(database_url=db) as restarted:
        current = inspect(restarted)
        assert current["saved"] and current["state"]["week"]["season_index"] == 1
        assert current["state"]["week"]["week"] == 1
        # Exact lost-response retry must not replay a transition after restart.
        assert _request("POST", tour_url(restarted) + "/execute", request) == (201, result)
        backward = restore(restarted, previous_head)
        assert backward["payload"]["content"]["calendar_tour_authority"]["state"]["week"]["week"] == 4
        back_view = inspect(restarted)
        assert back_view["saved"] and back_view["state"]["week"]["week"] == 4
        forward = restore(restarted, signed_head)
        assert forward["payload"]["content"]["calendar_tour_authority"]["state"]["week"]["season_index"] == 1
        assert inspect(restarted)["state"]["rankings"][-1]["policy"]["best_n"] == (
            12 if override_policy else 15
        )
