"""W52/W80 actual eight-player prepared awards, immutable Saved v7 and replay."""
import copy
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import COMPONENT_KEY
from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
from tests.api.test_calendar_continuation_flow import root, save_continuation
from tests.api.test_calendar_followup_eight_knockout_flow import eight_command, eight_url
from tests.api.test_calendar_population_sporting_checkpoint import play, prepare, restore, save
from tests.api.test_calendar_sporting_week_flow import advance, weekly_command
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def scored_url(server):
    return eight_url(server).replace("/simulate-eight", "/simulate-eight-scored")


def scored_command(view, *, name="eight-scored"):
    return {
        **eight_command(view, name),
        "point_policy": {
            "category_label": "Operator-reviewed scored native eight-player knockout",
            "champion": 100, "finalist": 60, "semifinal": 30, "quarterfinal": 15,
            "validity_weeks": view["sporting_week"]["calendar"]["weeks_per_year"],
        },
        "explicit_point_confirmation": True,
    }


@pytest.mark.parametrize("width", [52, 80])
def test_real_eight_scored_knockout_signed_points_saved_replay_and_restart(tmp_path, width):
    db = f"sqlite:///{tmp_path / 'eight-points.db'}"
    with ApiServer(database_url=db) as server:
        repo, head = prepare(server, RunCalendar(width, width, 2030, 3))
        opening, _ = play(server, head)
        opening_saved = save(server, opening)
        _, v1 = _request("GET", root(server))
        week2, _ = advance(server, weekly_command(v1))
        week_saved = save_continuation(server, week2)
        _, ready = _request("GET", root(server))
        command = scored_command(ready)
        original_db = _dump(tmp_path / 'eight-points.db')
        assert _request("POST", scored_url(server), {**command, "explicit_point_confirmation": False})[0] == 422
        assert _request("POST", scored_url(server), {**command, "point_policy": {
            **command["point_policy"], "validity_weeks": width - 1,
        }})[0] == 409
        assert _request("POST", scored_url(server), {**command, "point_policy": {
            **command["point_policy"], "quarterfinal": 70,
        }})[0] == 422
        assert _dump(tmp_path / 'eight-points.db') == original_db

        code, played = _request("POST", scored_url(server), command)
        assert code == 201, played
        event = played["tournament"]
        assert event["schema_version"] == "calendar_followup_knockout.v4"
        assert event["prepared_policy"]["schema_version"] == "calendar_followup_point_policy.v2"
        assert played["scope"] == "sporting_exhibition_knockout_not_official"
        assert played["publication_status"] == "prepared_not_official"
        assert played["official_ranking_published"] is False
        awards = played["prepared_awards"]
        assert len(event["matches"]) == 7
        assert len(awards) == 8
        assert sorted(a["main_points"] for a in awards) == [15, 15, 15, 15, 30, 30, 60, 100]
        stages = [a["reached_stage"] for a in awards]
        assert sorted(stages) == sorted(["quarterfinal"] * 4 + ["semifinal"] * 2 + ["finalist", "champion"])
        assert next(a for a in awards if a["reached_stage"] == "champion")["player_id"] == played["winner_player_id"]
        assert all(a["source_policy_fingerprint"] == played["prepared_policy_fingerprint"] for a in awards)
        assert len({a["source_tournament_fingerprint"] for a in awards}) == 1
        assert _request("POST", scored_url(server), command) == (201, played)

        _, unsaved = _request("GET", root(server))
        assert not unsaved["saved"] and not unsaved["can_play"]
        newest = unsaved["tournaments"][-1]
        assert newest["entrant_count"] == 8 and newest["match_count"] == 7
        assert newest["prepared_points_status"] == "prepared_not_official"
        assert newest["prepared_awards"] == awards
        assert _request("POST", scored_url(server), {**command, "command_id": "blocked",
            "tournament_id": "blocked"})[0] == 409

        revision = save_continuation(server, played)
        component = revision["payload"]["content"][COMPONENT_KEY]
        assert component["state"]["schema_version"] == "calendar_sporting_checkpoint.v7"
        assert component["state"]["week_events"][-1]["schema_version"] == "calendar_followup_knockout.v4"
        assert revision["payload"]["content"]["calendar_standalone_match"] == opening_saved["payload"]["content"]["calendar_standalone_match"]
        assert repo.verify_branch_saved_revision_hash(revision_id=revision["revision_id"])
        assert _request("POST", scored_url(server), command) == (201, played)

        for match in event["matches"]:
            code, replay = _request("GET", root(server) + "/" + match["match_id"] + "/replay")
            assert code == 200 and replay["exact_replay"]

        for fault in ("award-value", "award-stage", "award-origin", "policy", "lose-qf", "downgrade"):
            forged = copy.deepcopy(revision["payload"])
            component = forged["content"][COMPONENT_KEY]
            state = component["state"]
            last = state["week_events"][-1]
            if fault == "award-value":
                last["prepared_awards"][0]["main_points"] += 1
            elif fault == "award-stage":
                last["prepared_awards"][0]["reached_stage"] = "champion"
            elif fault == "award-origin":
                last["prepared_awards"][0]["source_tournament_fingerprint"] = "f" * 64
            elif fault == "policy":
                last["prepared_policy"]["quarterfinal"] = 14
            elif fault == "lose-qf":
                result = last["matches"][0]["result"]
                result["winner_player_id"] = result["loser_player_id"]
            else:
                state["schema_version"] = "calendar_sporting_checkpoint.v6"
            component["fingerprint"] = canonical_hash(state)
            with pytest.raises(ValueError):
                load_saved_calendar_match(forged, run_id="run", branch_id="branch")

        _, current = _request("GET", root(server))
        week3, _ = advance(server, weekly_command(current, name="after-eight-points"))
        assert sum(n for _, n in week3["advance"]["played_counts"]) == 14
        week3_saved = save_continuation(server, week3)
        assert week3_saved["payload"]["content"][COMPONENT_KEY]["state"]["schema_version"] == "calendar_sporting_checkpoint.v7"
        assert _request("POST", scored_url(server), command) == (201, played)
        assert repo.verify_branch_saved_revision_hash(revision_id=week_saved["revision_id"])

    with ApiServer(database_url=db) as restarted:
        _, saved_state = _request("GET", root(restarted))
        assert saved_state["saved"] and saved_state["sporting_week"]["week"] == 3
        assert saved_state["tournaments"][-1]["prepared_points_status"] == "prepared_not_official"
        for match in event["matches"]:
            assert _request("GET", root(restarted) + "/" + match["match_id"] + "/replay")[1]["exact_replay"]
        assert _request("POST", scored_url(restarted), command) == (201, played)
        restore(restarted, week_saved["revision_id"])
        assert not _request("GET", root(restarted))[1]["tournaments"]
        restore(restarted, revision["revision_id"])
        assert _request("GET", root(restarted))[1]["tournaments"][-1]["prepared_awards"] == awards
        restore(restarted, week3_saved["revision_id"])
        assert _request("GET", root(restarted))[1]["sporting_week"]["week"] == 3
