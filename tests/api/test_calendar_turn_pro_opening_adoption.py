"""Real HTTP/SQLite: a v87 population adopts recomputable opening professionals."""

import json

import pytest

from beta_engine.application.calendar_initial_world import (
    CalendarInitialWorldState,
    initial_turn_pro_evidence,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.turn_pro_model import true_strength_turn_pro_model_policy_v1
from tests.api.test_calendar_initial_world_adoption import confirm, request, review, root
from tests.api.test_player_generation_calendar_gate import _dump, _generation, _world
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical

V87 = {
    "policy_id": "pre-alpha-turn-pro-lifecycle.v1",
    "automatic_retirement_age": 46,
    "provenance": "Explicit Master v87 Turn Pro lifecycle",
    "tour_entry_rule": "turn_pro.v87",
}


def _payload(server, **changes):
    return request(
        server,
        lifecycle_policy=V87,
        generation=_generation(target_pool_size=12, min_age=15, max_age=30),
        **changes,
    )


def test_v87_adoption_records_saves_and_forks_opening_professionals(tmp_path):
    path = tmp_path / "v87-opening.db"
    clock = RunCalendar(52, 35, 2030, 3)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, clock)
        payload = _payload(server)
        before = _dump(path)
        reviewed = review(server, payload)
        assert _dump(path) == before  # review is read-only
        assert review(server, payload) == reviewed  # deterministic
        code, adopted = confirm(server, payload, reviewed)
        assert code == 201, adopted
        state = adopted["state"]
        evidence = state["initial_turn_pro"]
        world = CalendarInitialWorldState.model_validate_json(json.dumps(state))
        assert world.initial_turn_pro.model == true_strength_turn_pro_model_policy_v1()
        assert evidence["seed"] == payload["generation"]["seed"]
        assert world.initial_turn_pro == initial_turn_pro_evidence(
            run_id="run", run_calendar=world.run_calendar, players=world.players,
            model=true_strength_turn_pro_model_policy_v1(), seed=evidence["seed"],
        )
        pros = set(evidence["professional_player_ids"])
        assert reviewed["opening_professional_count"] == len(pros)
        assert pros and pros != {p["player_id"] for p in state["players"]}, pros

        code, save_preview = _request("GET", root(server) + "/save/preview")
        assert code == 200 and save_preview["can_save"], save_preview
        code, saved = _request("POST", root(server) + "/save", {
            "expected_draft_version": save_preview["draft_version"],
            "expected_initial_world_fingerprint": adopted["fingerprint"],
        })
        assert code == 201, saved
        revision = saved["saved_revision"]
        opening = revision["payload"]["content"]["player_lifecycle"]["states"][0]
        entered = {
            p["player_id"]: p for p in opening["players"] if "tour_entry_week" in p
        }
        assert set(entered) == pros
        assert all(p["tour_entry_week"]["week"] == 1 for p in entered.values())
        assert repo.verify_branch_saved_revision_hash(revision_id=revision["revision_id"])

        code, fork = _request("POST", server.base_url + "/run-containers/run/branches", {
            "source_branch_id": "branch", "source_saved_revision_id": revision["revision_id"],
        })
        assert code == 201, fork
        code, copied = _request("GET", root(server, fork["branch_id"]) + "/calendar-adoption")
        assert code == 200, copied
        # Pre-Run history is shared: a fork keeps exactly the same opening pros.
        assert copied["state"]["initial_turn_pro"] == evidence
        assert repo.verify_branch_saved_revision_hash(revision_id=fork["saved_head_revision_id"])
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("GET", root(server) + "/calendar-adoption") == (200, adopted)


def test_historical_policy_adoption_has_no_opening_turn_pro_evidence(tmp_path):
    path = tmp_path / "v57-opening.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar(52, 35, 2030, 3))
        payload = request(
            server, generation=_generation(target_pool_size=12, min_age=15, max_age=30)
        )
        reviewed = review(server, payload)
        assert "opening_professional_count" not in reviewed
        code, adopted = confirm(server, payload, reviewed)
        assert code == 201, adopted
        assert "initial_turn_pro" not in adopted["state"]
