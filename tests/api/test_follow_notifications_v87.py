"""Real HTTP/SQLite: following, grouped alerts and persistent attention state.

A v87 Run plays a real Edition. The Edition's winner and the winner's country are
followed: the first recorded title and its ranking milestone form ONE card whose items
keep their own exact sources; a fact matching both follows is not duplicated; an
unrelated player's milestones stay in career history without an alert. Reading,
hiding and repeating commands never change facts, Saved state or sport, and the state
survives a cold restart. Not covered: a forked Branch (derivation reads one Branch's
Saved Tour, so a sibling's events cannot appear by construction).
"""

import pytest

from beta_engine.application import calendar_pre_tour_turn_pro as pre_tour
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.turn_pro_model import default_turn_pro_model_policy
from tests.api import test_calendar_population_sporting_checkpoint as population
from tests.api.test_calendar_initial_world_adoption import request as population_request
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup
from tests.api.test_calendar_tour_player_career_v87 import career
from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, V87, _opening_pros, _play_edition
from tests.api.test_player_generation_calendar_gate import _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def url(server, path):
    return server.base_url + "/admin/runs/run" + path


def notes(server, query=""):
    code, body = _request("GET", url(server, "/branches/branch/notifications" + query))
    assert code == 200, body
    return body


def test_following_alerts_group_dedupe_persist_and_never_touch_sport(tmp_path, monkeypatch):
    monkeypatch.setattr(
        population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}),
    )
    monkeypatch.setattr(
        population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 19}),
    )
    monkeypatch.setattr(pre_tour, "default_turn_pro_model_policy", lambda: EAGER)
    db = f"sqlite:///{tmp_path / 'follow.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=20)
        pros, _everyone = _opening_pros(repo)
        view = inspect(server)
        newcomers = sorted({d["player_id"] for w in view["state"]["pre_tour_turn_pro"]["weeks"]
                            for d in w["decisions"]})
        monkeypatch.setattr(pre_tour, "default_turn_pro_model_policy", default_turn_pro_model_policy)
        week = view["state"]["week"]
        execute(server, command(view, "create-edition", name="first:create", data={
            "edition_id": "first", "name": "Followed Edition",
            "week": {**week, "week": week["week"] + 2},
            "announcement_week": {**week, "week": week["week"] + 1},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True,
            "validity_weeks": week["calendar"]["weeks_per_year"],
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }))
        save_tour(server)
        for name in ("announce", "open-play-week"):
            execute(server, command(inspect(server), "transition", name=name))
            save_tour(server)
        field = [*newcomers[:2], *sorted(pros)[:2]]
        _play_edition(server, field)
        for name in ("after-first", "after-first-2"):
            execute(server, command(inspect(server), "transition", name=name))
            save_tour(server)
        champion = next(p for p in field if career(server, p)[1]["overview"]["titles"] == 1)
        country = career(server, champion)[1]["player"]["country_code"]
        other = next(p for p in field if p != champion
                     and career(server, p)[1]["player"]["country_code"] != country)
        sport_before = inspect(server)

        # Nothing is followed yet: no alerts, but the career facts exist for everyone.
        assert notes(server)["cards"] == []
        assert career(server, other)[1]["milestones"]

        # Validation and idempotent commands (no duplicate follow, no state drift).
        assert _request("PUT", url(server, "/follows/team/X"), {})[0] == 409
        assert _request("PUT", url(server, "/follows/country/cz"), {})[0] == 409
        assert _request("PUT", "%s/admin/runs/missing/follows/player/x" % server.base_url, {})[0] == 404
        for _ in range(2):
            code, followed = _request("PUT", url(server, f"/follows/player/{champion}"), {})
            assert code == 200 and len(followed["follows"]) == 1
        code, followed = _request("PUT", url(server, f"/follows/country/{country}"), {})
        assert code == 200 and len(followed["follows"]) == 2

        first = notes(server)
        mine = [c for c in first["cards"] if c["player_id"] == champion]
        assert len(mine) == 1, [c["player_id"] for c in first["cards"]]
        card = mine[0]
        kinds = [i["kind"] for i in card["items"]]
        assert "first_recorded_title" in kinds and len(kinds) >= 2, kinds
        assert card["item_count"] == len(card["items"]) and card["state"] == "unread"
        # Matching both follows is one card with both reasons, not two alerts.
        assert f"player:{champion}" in card["reasons"]
        assert any(r.startswith(f"country:{country}") for r in card["reasons"])
        title = next(i for i in card["items"] if i["kind"] == "first_recorded_title")
        assert title["source"]["kind"] == "played_edition"
        # Every grouped item still has its own immutable source and appears in history.
        history = {(m["kind"], m["source"]["fingerprint"]) for m in career(server, champion)[1]["milestones"]}
        assert {(i["kind"], i["source"]["fingerprint"]) for i in card["items"]} <= history
        # An unrelated player of another country has history but no alert.
        assert not [c for c in first["cards"] if c["player_id"] == other]
        # Country-only alerts need a stated criterion (leader or exceptional), never "every milestone".
        for c in first["cards"]:
            if c["player_id"] != champion:
                assert all(r.startswith(f"country:{country}:") for r in c["reasons"]), c["reasons"]
        assert first["criteria"]["status"] == "provisional calibration"

        # Repeated reads are identical (no duplicate delivery).
        assert notes(server) == first

        # A historical view contains neither the title nor later facts.
        edition_week = week["week"] + 2
        past = notes(server, f"?as_of_ordinal={edition_week - 2}")
        assert not [i for c in past["cards"] for i in c["items"] if i["kind"] == "first_recorded_title"]
        assert notes(server, "?as_of_ordinal=0")["cards"] == []
        assert _request("GET", url(server, "/branches/branch/notifications?as_of_ordinal=100000"))[0] == 409

        # Reading: persists, is idempotent, and does not delete any fact.
        key = card["notification_key"]
        for _ in range(2):
            code, after = _request("PUT", url(server, f"/branches/branch/notifications/{key}/state"), {"state": "read"})
            assert code == 200, after
        read_card = next(c for c in notes(server)["cards"] if c["notification_key"] == key)
        assert read_card["state"] == "read" and read_card["unread_items"] == 0
        assert _request("PUT", url(server, f"/branches/branch/notifications/{'0' * 64}/state"), {"state": "read"})[0] == 404
        assert _request("PUT", url(server, f"/branches/branch/notifications/{key}/state"), {"state": "deleted"})[0] == 409

        # Hiding removes it from the default list but never from history.
        _request("PUT", url(server, f"/branches/branch/notifications/{key}/state"), {"state": "hidden"})
        assert key not in {c["notification_key"] for c in notes(server)["cards"]}
        assert key in {c["notification_key"] for c in notes(server, "?include_hidden=true")["cards"]}
        assert career(server, champion)[1]["milestones"]

        # Muting the follow stops derived alerts; the facts remain in career history.
        _request("PUT", url(server, f"/follows/player/{champion}"), {"alerts_enabled": False})
        _request("PUT", url(server, f"/follows/country/{country}"), {"alerts_enabled": False})
        assert notes(server, "?include_hidden=true")["cards"] == []
        assert career(server, champion)[1]["milestones"]
        _request("PUT", url(server, f"/follows/player/{champion}"), {"alerts_enabled": True})
        _request("PUT", url(server, f"/follows/country/{country}"), {"alerts_enabled": True})

        # None of this touched sport, Saved state or the draft.
        sport_after = inspect(server)
        for name in ("saved_head_revision_id", "checkpoint_fingerprint", "tour_fingerprint", "draft_version"):
            assert sport_after[name] == sport_before[name]
        before_restart = notes(server, "?include_hidden=true")
        follows_before = _request("GET", url(server, "/follows"))[1]

    # Cold restart: follows, hidden state and the derived cards are the same, not doubled.
    with ApiServer(database_url=db) as restarted:
        assert _request("GET", url(restarted, "/follows"))[1] == follows_before
        assert notes(restarted, "?include_hidden=true") == before_restart
        restored = next(c for c in before_restart["cards"] if c["notification_key"] == key)
        assert restored["state"] == "hidden"
        assert len([c for c in notes(restarted, "?include_hidden=true")["cards"] if c["player_id"] == champion]) == 1
        # Unfollowing is explicit and does not delete the career history.
        assert _request("DELETE", url(restarted, f"/follows/player/{champion}"))[0] == 200
        assert career(restarted, champion)[1]["milestones"]
