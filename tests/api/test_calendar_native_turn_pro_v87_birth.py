"""Real HTTP/SQLite Master v87 Turn Pro in native birth weeks, re-run on replay."""

import json

import pytest

from beta_engine.application import calendar_tour_service as service
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players import turn_pro_model
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, _opening_pros, _v87_population
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def _eager(patch):
    # Native weeks import the default lazily from the model module.
    patch.setattr(turn_pro_model, "default_turn_pro_model_policy", lambda: EAGER)


def test_v87_native_birth_weeks_run_record_and_replay_turn_pro(tmp_path, monkeypatch):
    _v87_population(monkeypatch)
    path = tmp_path / "v87-native.db"
    db = f"sqlite:///{path}"
    clock = RunCalendar(52, 1, 2030, 3)
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, 12)
        pros, everyone = _opening_pros(repo)
        prospects = sorted(everyone - pros)
        assert prospects, pros
        sign_prospects(server, repo, clock, target_week=3)
        with monkeypatch.context() as patch:
            _eager(patch)
            birth, _ = execute(
                server, command(inspect(server), "transition", name="v87-native-birth")
            )
        impact = birth["impact"]
        assert impact["native_transition"]
        assert impact["admitted_player_ids"] == ["born-native-15"]
        assert impact["turn_pro_model"] == EAGER.model_dump(mode="json")
        decided = {d["player_id"] for d in impact["turn_pro_decisions"]}
        # A newborn cannot turn pro in its own birth week; opening pros never again.
        assert decided and decided <= set(prospects), decided
        entered = {
            p["player_id"]: p.get("tour_entry_week")
            for p in impact["lifecycle"]["players"]
        }
        assert all(entered[pid]["week"] == 3 for pid in decided)
        assert entered["born-native-15"] is None
        saved = save_tour(server)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])
        event = inspect(server)["state"]["transitions"][-1]["public_event"]
        assert event["turned_pro_player_ids"] == sorted(decided)

        # Saved replay re-runs the *recorded* model: forging a decision fails.
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

        with repo._session_factory.begin() as session:
            row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            original = (row.payload_json, row.fingerprint)
            raw = json.loads(row.payload_json)
            raw["receipts"][-1]["result"]["impact"]["turn_pro_decisions"] = []
            row.payload_json = json.dumps(raw)
            row.fingerprint = canonical_hash(raw)
        try:
            assert _request("GET", tour_url(server))[0] == 409
        finally:
            with repo._session_factory.begin() as session:
                row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
                row.payload_json, row.fingerprint = original
        saved_view = inspect(server)

    # Restart with the default model: verification uses the recorded one.
    with ApiServer(database_url=db) as restarted:
        assert inspect(restarted) == saved_view
        natural, _ = execute(
            restarted,
            command(inspect(restarted), "transition", name="v87-native-after-birth"),
        )
        assert natural["impact"]["turn_pro_model"]["model_id"] == "pre-alpha-turn-pro.v1"
        # The newborn is a candidate from the following week on.
        assert all(
            d["player_id"] not in pros | decided
            for d in natural["impact"]["turn_pro_decisions"]
        )
        save_tour(restarted)
        professionals = pros | decided | {
            d["player_id"] for d in natural["impact"]["turn_pro_decisions"]
        }
        # A real native competition Edition played by professionals only.
        view = inspect(restarted)
        week = {**view["state"]["week"], "calendar": view["run_calendar"]}
        current = week["week"]
        execute(restarted, command(view, "create-edition", name="v87-native:create", data={
            "edition_id": "v87-native",
            "name": "Native v87 Tour",
            "week": {**week, "week": current + 2},
            "announcement_week": {**week, "week": current + 1},
            "start_slot": 1,
            "main_entrant_count": 4,
            "ranked": True,
            "validity_weeks": 52,
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
            "host_country_code": "GER",
        }))
        save_tour(restarted)
        for name in ("v87-native-announce", "v87-native-play-week"):
            moved, _ = execute(restarted, command(inspect(restarted), "transition", name=name))
            professionals |= {d["player_id"] for d in moved["impact"]["turn_pro_decisions"]}
            save_tour(restarted)
        field = sorted(professionals)[:4]
        assert len(field) == 4, professionals
        view = inspect(restarted)
        execute(restarted, command(view, "submit", name="v87-native:applications",
                                   edition_id="v87-native", data={"player_ids": field}))
        for action in ("approve", "draw"):
            execute(restarted, command(inspect(restarted), action,
                                       name="v87-native:" + action, edition_id="v87-native"))
        save_tour(restarted)
        for action in ("play", "confirm-result"):
            execute(restarted, command(inspect(restarted), action,
                                       name="v87-native:" + action, edition_id="v87-native"))
            save_tour(restarted)
        after, _ = execute(
            restarted, command(inspect(restarted), "transition", name="v87-native-after-play")
        )
        assert set(field) <= {r["player_id"] for r in after["impact"]["ranking"]["rows"]}
        assert "turn_pro_model" in after["impact"]
        assert after["impact"]["native_transition"]
        assert inspect(restarted)["state"]["schema_version"] in {
            "calendar_tour_authority.v4", "calendar_tour_authority.v5",
        }
        final = save_tour(restarted)
        assert repo_verify(restarted, final["revision_id"])
        final_view = inspect(restarted)
    with ApiServer(database_url=db) as reopened:
        assert inspect(reopened) == final_view


def repo_verify(server, revision_id):
    return server.app.state.runtime.repository.verify_branch_saved_revision_hash(
        revision_id=revision_id
    )
