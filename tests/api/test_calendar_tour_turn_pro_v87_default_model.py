"""Real HTTP/SQLite: a genuine prospect turns pro under the *default* v2 model.

No test calibration is injected while the decision is made. The prospect then
applies in normal Saved commands, plays a real Edition and is ranked; after a
restart with a different default model the recorded history still verifies and
an exact retry returns the original result.
"""

import pytest

from beta_engine.application import calendar_tour_service as service
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players import turn_pro_model
from beta_engine.domain.players.turn_pro_model import default_turn_pro_model_policy
from tests.api import test_calendar_population_sporting_checkpoint as population
from tests.api.test_calendar_initial_world_adoption import request as population_request
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_calendar_tour_turn_pro_v87_flow import (
    EAGER,
    V87,
    _opening_pros,
    _play_edition,
)
from tests.api.test_player_generation_calendar_gate import _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

MAX_WEEKS = 12


def _create_edition(server):
    view = inspect(server)
    week = view["state"]["week"]
    data = {
        "edition_id": "first",
        "name": "Default-model Turn Pro Edition",
        "week": {**week, "week": week["week"] + 2},
        "announcement_week": {**week, "week": week["week"] + 1},
        "start_slot": 1,
        "main_entrant_count": 4,
        "ranked": True,
        "validity_weeks": week["calendar"]["weeks_per_year"],
        "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
    }
    execute(server, command(view, "create-edition", name="first:create", data=data))
    save_tour(server)


def test_genuine_prospect_turns_pro_under_the_default_model_and_plays(tmp_path, monkeypatch):
    monkeypatch.setattr(
        population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}),
    )
    monkeypatch.setattr(
        population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 17, "max_age": 19}),
    )
    default = default_turn_pro_model_policy()
    db = f"sqlite:///{tmp_path / 'v87-default.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=40)
        pros, everyone = _opening_pros(repo)
        assert len(pros) >= 3 and len(everyone - pros) >= 10, (len(pros), len(everyone))
        newcomer, observation = None, None
        for index in range(MAX_WEEKS):
            result, _ = execute(
                server, command(inspect(server), "transition", name=f"default-week-{index}")
            )
            impact = result["impact"]
            assert impact["turn_pro_model"] == default.model_dump(mode="json")
            save_tour(server)
            if impact["turn_pro_decisions"]:
                decision = sorted(impact["turn_pro_decisions"], key=lambda d: d["player_id"])[0]
                newcomer = decision["player_id"]
                break
        assert newcomer is not None, "the default model made no decision in the fixture window"
        assert newcomer not in pros
        # The recorded decision carries what the prospect knew about itself only.
        transition = inspect(server)["state"]["transitions"][-1]
        assert transition["public_event"]["turned_pro_player_ids"][0] == newcomer
        _create_edition(server)
        for name in ("announce", "open-play-week"):
            execute(server, command(inspect(server), "transition", name=name))
            save_tour(server)
        _play_edition(server, [newcomer, *sorted(pros)[:3]])
        final, request = execute(
            server, command(inspect(server), "transition", name="after-first")
        )
        ranked = {r["player_id"] for r in final["impact"]["ranking"]["rows"]}
        assert newcomer in ranked
        saved = save_tour(server)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])
        view = inspect(server)
    # A different default model must not change or break recorded history.
    monkeypatch.setattr(turn_pro_model, "default_turn_pro_model_policy", lambda: EAGER)
    monkeypatch.setattr(service, "default_turn_pro_model_policy", lambda: EAGER)
    with ApiServer(database_url=db) as restarted:
        assert inspect(restarted) == view
        assert _request("POST", tour_url(restarted) + "/execute", request) == (201, final)
