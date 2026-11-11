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


@pytest.mark.parametrize("min_age,max_age,all_pro", [
    pytest.param(15, 19, False, id="prospects-in-draw"),
    pytest.param(26, 30, True, id="professionals-only"),
])
def test_v87_saved_fax_draw_admits_only_professionals(
    tmp_path, fax_source, monkeypatch, min_age, max_age, all_pro
):
    _v87(monkeypatch, min_age=min_age, max_age=max_age)
    db = f"sqlite:///{tmp_path / 'v87-fax.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(61, 37, 2000, 3), count=40)
        pros, _ = _opening_pros(repo)
        plan = canonical.authored_source(server, repo, fax_source, 24)
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
