"""Real HTTP/SQLite Master v87 path: opening pros -> gated entry -> Turn Pro week."""

import pytest

from beta_engine.application import calendar_tour_service as service
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.turn_pro_model import default_turn_pro_model_policy
from tests.api import test_calendar_population_sporting_checkpoint as population
from tests.api.test_calendar_continuation_flow import root
from tests.api.test_calendar_initial_world_adoption import request as population_request
from tests.api.test_calendar_tour_flow import (
    command,
    create_edition,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_player_generation_calendar_gate import _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

# Long production acceptance, like test_calendar_tour_flow.
pytestmark = pytest.mark.smoke

V87 = {
    "policy_id": "pre-alpha-turn-pro-lifecycle.v1",
    "automatic_retirement_age": 46,
    "provenance": "Explicit Master v87 Turn Pro lifecycle",
    "tour_entry_rule": "turn_pro.v87",
}
# Test-only calibration so the remaining prospect turns pro within the fixture's
# few weeks; it is recorded in each transition exactly like the default one.
EAGER = default_turn_pro_model_policy().model_copy(
    update={
        "model_id": "test-eager-turn-pro.v1",
        "annual_base_by_age": (1 - 1e-12,),
        "readiness_weight": 0.0,
        "provenance": "Acceptance-test calibration",
    }
)


def _v87_population(monkeypatch):
    monkeypatch.setattr(
        population,
        "population_request",
        lambda server, **changes: population_request(
            server, **{**changes, "lifecycle_policy": V87}
        ),
    )
    monkeypatch.setattr(
        population,
        "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 19}),
    )


def _opening_pros(repo):
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world

    with repo._session_factory() as session:
        world = get_initial_world(session, run_id="run", branch_id="branch")
    assert world.lifecycle_policy.requires_turn_pro
    return set(world.initial_turn_pro.professional_player_ids), {
        p.player_id for p in world.players
    }


def _submit(server, name, ids):
    return _request(
        "POST", tour_url(server) + "/preview",
        command(inspect(server), "submit", name=name, edition_id="first",
                data={"player_ids": ids}),
    )


def _play_edition(server, ids):
    execute(server, command(inspect(server), "submit", name="first:applications",
                            edition_id="first", data={"player_ids": ids}))
    for action in ("approve", "draw"):
        execute(server, command(inspect(server), action, name="first:" + action,
                                edition_id="first"))
    save_tour(server)
    for action in ("play", "confirm-result"):
        execute(server, command(inspect(server), action, name="first:" + action,
                                edition_id="first"))
        save_tour(server)


def test_v87_run_gates_entry_by_turn_pro_and_records_transitions(tmp_path, monkeypatch):
    _v87_population(monkeypatch)
    db = f"sqlite:///{tmp_path / 'v87.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=20)
        pros, everyone = _opening_pros(repo)
        prospects = sorted(everyone - pros)
        assert len(pros) >= 3 and prospects, (pros, prospects)
        create_edition(server, "first", 4)

        decided = {}
        with monkeypatch.context() as eager:
            eager.setattr(service, "default_turn_pro_model_policy", lambda: EAGER)
            for name in ("open-announcements", "open-first-play-week"):
                result, _ = execute(
                    server, command(inspect(server), "transition", name=name)
                )
                impact = result["impact"]
                # Every v87 transition records the exact model it ran.
                assert impact["turn_pro_model"] == EAGER.model_dump(mode="json")
                for decision in impact["turn_pro_decisions"]:
                    assert decision["player_id"] in prospects
                    assert decision["player_id"] not in decided
                    decided[decision["player_id"]] = decision["effective_week"]
                save_tour(server)
        assert decided, "the eager calibration must turn a prospect pro"
        remaining = [p for p in prospects if p not in decided]
        assert remaining, "the fixture must keep someone who has not turned pro"
        # In the Edition's week, a first application from a player who has not
        # turned pro is refused without writing anything.
        before = inspect(server)
        code, refused = _submit(server, "prospect-entry", remaining[:1])
        assert code == 409 and "turned pro" in str(refused), refused
        assert inspect(server) == before
        newcomer = sorted(decided)[0]
        # The new professional applies in its Turn Pro week and plays real matches.
        field = [newcomer, *sorted(pros)[:3]]
        _play_edition(server, field)
        # Back on the default calibration, which this transition records instead.
        transition, request = execute(
            server, command(inspect(server), "transition", name="first-to-next")
        )
        assert transition["impact"]["turn_pro_model"]["model_id"] == "pre-alpha-turn-pro.v1"
        ranked = {r["player_id"] for r in transition["impact"]["ranking"]["rows"]}
        assert newcomer in ranked and ranked <= pros | set(decided) | {
            d["player_id"] for d in transition["impact"]["turn_pro_decisions"]
        }
        final = save_tour(server)
        code, replay = _request("GET", root(server) + "/first:final/replay")
        assert code == 200 and replay["exact_replay"], replay
        assert repo.verify_branch_saved_revision_hash(revision_id=final["revision_id"])
    with ApiServer(database_url=db) as restarted:
        # Saved verification rebuilds the v87 lifecycle from recorded decisions,
        # even though the default model is no longer the eager one.
        assert inspect(restarted)["saved"]
        assert _request("POST", tour_url(restarted) + "/execute", request) == (
            201, transition,
        )
