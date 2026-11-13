"""Real HTTP/SQLite: under Master v87 a Saved FAX Draw may contain only professionals."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api import test_calendar_population_sporting_checkpoint as population
from tests.api import test_native_canonical_knockout as canonical
from tests.api.test_calendar_initial_world_adoption import request as population_request
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_calendar_tour_turn_pro_v87_flow import V87, _opening_pros
from tests.api.test_player_generation_calendar_gate import _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

fax_source = canonical.fax_source


def _v87(monkeypatch, *, min_age, max_age):
    monkeypatch.setattr(
        population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}),
    )
    monkeypatch.setattr(
        population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": min_age, "max_age": max_age}),
    )


def _adoption(plan):
    return {
        "season": "2000/2001",
        "event_id": plan.source.draw.event_id,
        "source_plan_fingerprint": plan.fingerprint,
        "schedule": {"qualification": [1, 2], "main": [4, 5, 6, 7, 8]},
    }


def _participants(plan):
    d = plan.source.draw_input
    return {*d.direct_main_player_ids, *d.wild_card_player_ids, *d.qualification_player_ids}


@pytest.mark.parametrize("ranked", [False, True], ids=["unranked", "ranked"])
@pytest.mark.parametrize("min_age,max_age,all_pro", [
    pytest.param(15, 19, False, id="prospects-in-draw"),
    pytest.param(26, 30, True, id="professionals-only"),
])
def test_v87_saved_fax_draw_admits_only_professionals(
    tmp_path, fax_source, monkeypatch, min_age, max_age, all_pro, ranked
):
    _v87(monkeypatch, min_age=min_age, max_age=max_age)
    db = f"sqlite:///{tmp_path / 'v87-fax.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(61, 37, 2000, 3), count=40)
        pros, _ = _opening_pros(repo)
        plan = canonical.authored_source(server, repo, fax_source, 24, ranked=ranked)
        not_pro = _participants(plan) - pros
        assert bool(not_pro) is not all_pro, (len(not_pro), len(pros))
        before = inspect(server)
        cmd = command(before, "adopt-saved-draw", data=_adoption(plan))
        status, body = _request("POST", tour_url(server) + "/preview", cmd)
        if not all_pro:
            # Unranked too: Turn Pro is what lets a player enter association events.
            assert status == 409, body
            message = body["detail"]["message"]
            assert f"{len(not_pro)} Saved Draw participant(s) have not turned pro" in message
            after = inspect(server)
            for field in ("saved_head_revision_id", "checkpoint_fingerprint",
                          "tour_fingerprint", "draft_version"):
                assert after[field] == before[field]
            return
        assert status == 200, body
        execute(server, cmd)
        saved = save_tour(server)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])
        state = inspect(server)["state"]
        assert plan.source.draw.event_id in {a["edition"]["edition_id"] for a in state["editions"]}


@pytest.mark.parametrize("ranked", [False, True], ids=["unranked", "ranked"])
def test_v87_actual_q_to_main_played_confirmed_saved_and_reopened(
    tmp_path, fax_source, monkeypatch, ranked
):
    """Real Saved Draw -> adoption -> actual Q and Main MatchEngine matches -> result
    confirmation -> published ranking -> explicit Save -> cold restart, under v87.

    Participants are opening professionals (ages 26-30); no prior native Entry is
    needed. Scope: opening professionals only; a player who turned pro through the
    player AI is covered by the normal Entry/Edition flow, not by this Saved-Draw path.
    """
    _v87(monkeypatch, min_age=26, max_age=30)
    canonical.run_actual_q_main(tmp_path, fax_source, 24, ranked, monkeypatch, v87=True)


@pytest.mark.parametrize("ranked", [False, True], ids=["unranked", "ranked"])
def test_v87_saved_fax_draw_accepts_players_who_turned_pro_through_the_ai(
    tmp_path, fax_source, monkeypatch, ranked
):
    """A Saved Draw of prospects is rejected (see the test above); once the player AI has
    really turned them pro, the very same kind of Draw is admitted.

    The pre-Tour week uses the test-only eager calibration, recorded like the default one,
    so the participants are professionals from recorded AI decisions, not opening pros.
    """
    from beta_engine.application import calendar_pre_tour_turn_pro as pre_tour
    from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER

    # Test-only calibration: a prospect's weekly chance is practically certain, whatever
    # its self-view, so every prospect turns pro in the one pre-Tour week.
    certain = EAGER.model_copy(update={
        "model_id": "test-certain-turn-pro.v1", "readiness_weight": 400.0,
        "readiness_reference": 0.0,
    })
    _v87(monkeypatch, min_age=15, max_age=19)
    monkeypatch.setattr(pre_tour, "default_turn_pro_model_policy", lambda: certain)
    db = f"sqlite:///{tmp_path / 'v87-fax-ai.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(61, 37, 2000, 3), count=40)
        pros, _ = _opening_pros(repo)
        plan = canonical.authored_source(server, repo, fax_source, 24, ranked=ranked)
        state = inspect(server)["state"]
        by_ai = {
            d["player_id"]
            for w in state["pre_tour_turn_pro"]["weeks"]
            for d in w["decisions"]
        }
        participants = _participants(plan)
        # Real AI professionals are in the Draw, and not all participants are opening pros.
        assert participants & by_ai, "the Draw must contain players the AI turned pro"
        assert participants - pros, "the Draw must contain more than opening professionals"
        assert participants <= pros | by_ai, "everyone in the Draw is a recorded professional"
        before = inspect(server)
        cmd = command(before, "adopt-saved-draw", data=_adoption(plan))
        status, body = _request("POST", tour_url(server) + "/preview", cmd)
        assert status == 200, body
        execute(server, cmd)
        saved = save_tour(server)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])
        edition_ids = {a["edition"]["edition_id"] for a in inspect(server)["state"]["editions"]}
        assert plan.source.draw.event_id in edition_ids
    # Cold restart keeps the adopted Edition and the recorded evidence.
    with ApiServer(database_url=db) as restarted:
        again = inspect(restarted)["state"]
        assert plan.source.draw.event_id in {a["edition"]["edition_id"] for a in again["editions"]}
        assert again["pre_tour_turn_pro"]["weeks"][0]["decisions"]
