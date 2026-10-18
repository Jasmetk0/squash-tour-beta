"""A real later sporting knockout may freeze prepared (not Official) awards.

The signed scored event must survive manual Save, deterministic replay,
forward weekly recovery, cold restart and backward/forward revision restore.
"""
import copy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_followup_knockout import CalendarFollowupKnockout
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import COMPONENT_KEY
from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
from tests.api.test_calendar_continuation_flow import root, save_continuation
from tests.api.test_calendar_followup_knockout_flow import command, tournament_url
from tests.api.test_calendar_population_sporting_checkpoint import play, prepare, restore, save
from tests.api.test_calendar_sporting_week_flow import advance, weekly_command
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def scored_command(view):
    return {
        **command(view, tournament_id="scored-four", command_id="scored-command", seed=919),
        "point_policy": {
            "category_label": "Operator-reviewed native exhibition only",
            "champion": 100, "finalist": 60, "semifinal": 30,
            "validity_weeks": view["sporting_week"]["calendar"]["weeks_per_year"],
        },
        "explicit_point_confirmation": True,
    }


@pytest.mark.parametrize("width", [52, 80])
def test_scored_later_knockout_authentic_points_save_and_recovery(tmp_path, width):
    database = f"sqlite:///{tmp_path / 'later-scored.db'}"
    with ApiServer(database_url=database) as server:
        repo, head = prepare(server, RunCalendar(width, width, 2030, 3))
        opening, _ = play(server, head)
        save(server, opening)
        _, view = _request("GET", root(server))
        week, _ = advance(server, weekly_command(view))
        save_continuation(server, week)
        _, ready = _request("GET", root(server))
        request = scored_command(ready)
        scored_url = tournament_url(server).replace("/simulate", "/simulate-scored")

        assert _request("POST", scored_url, {**request, "explicit_point_confirmation": False})[0] == 422
        assert _request("POST", scored_url, {**request,
            "point_policy": {**request["point_policy"], "validity_weeks": width - 1}})[0] == 409

        code, played = _request("POST", scored_url, request)
        assert code == 201, played
        assert played["tournament"]["schema_version"] == "calendar_followup_knockout.v2"
        assert played["publication_status"] == "prepared_not_official"
        assert played["official_ranking_published"] is False
        awards = played["prepared_awards"]
        assert sorted(a["main_points"] for a in awards) == [30, 30, 60, 100]
        final = played["tournament"]["matches"][-1]["result"]
        assert next(a for a in awards if a["main_points"] == 100)["player_id"] == final["winner_player_id"]
        assert all(a["source_policy_fingerprint"] == played["prepared_policy_fingerprint"] for a in awards)
        assert all(a["source_tournament_fingerprint"] == awards[0]["source_tournament_fingerprint"] for a in awards)
        assert _request("POST", scored_url, request) == (201, played)

        _, pending = _request("GET", root(server))
        assert pending["saved"] is False
        assert pending["tournaments"][-1]["prepared_points_status"] == "prepared_not_official"
        assert sorted(a["main_points"] for a in pending["tournaments"][-1]["prepared_awards"]) == [30, 30, 60, 100]
        saved = save_continuation(server, played)
        state = saved["payload"]["content"][COMPONENT_KEY]["state"]
        assert state["schema_version"] == "calendar_sporting_checkpoint.v5"
        event = state["week_events"][-1]
        assert event["schema_version"] == "calendar_followup_knockout.v2"
        assert len(event["prepared_awards"]) == 4
        assert _request("POST", scored_url, request) == (201, played)

        for corruption in ("points", "source", "policy", "downgrade", "schema"):
            forged = copy.deepcopy(saved["payload"])
            component = forged["content"][COMPONENT_KEY]
            stored = component["state"]
            last = stored["week_events"][-1]
            if corruption == "points":
                last["prepared_awards"][0]["main_points"] += 1
            elif corruption == "source":
                last["prepared_awards"][0]["source_tournament_fingerprint"] = "f" * 64
            elif corruption == "policy":
                last["prepared_policy"]["champion"] = 200
            elif corruption == "downgrade":
                stored["schema_version"] = "calendar_sporting_checkpoint.v4"
            else:
                last["schema_version"] = "calendar_followup_knockout.v1"
            component["fingerprint"] = canonical_hash(stored)
            with pytest.raises(ValueError):
                load_saved_calendar_match(forged, run_id="run", branch_id="branch")

        _, ready_week3 = _request("GET", root(server))
        next_week, _ = advance(server, weekly_command(ready_week3, name="after-scored"))
        assert sum(n for _, n in next_week["advance"]["played_counts"]) == 6
        final_saved = save_continuation(server, next_week)
        assert final_saved["payload"]["content"][COMPONENT_KEY]["state"]["schema_version"] == "calendar_sporting_checkpoint.v5"
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])

    with ApiServer(database_url=database) as restarted:
        _, inspection = _request("GET", root(restarted))
        assert inspection["saved"] and inspection["sporting_week"]["week"] == 3
        assert inspection["tournaments"][-1]["prepared_points_status"] == "prepared_not_official"
        for match in played["tournament"]["matches"]:
            assert _request("GET", root(restarted) + f"/{match['match_id']}/replay")[1]["exact_replay"]
        assert _request("POST", scored_url.replace(str(server.port), str(restarted.port)), request)[0] == 201
        restore(restarted, saved["revision_id"])
        assert _request("GET", root(restarted))[1]["sporting_week"]["week"] == 2
        restore(restarted, final_saved["revision_id"])
        assert _request("GET", root(restarted))[1]["sporting_week"]["week"] == 3
