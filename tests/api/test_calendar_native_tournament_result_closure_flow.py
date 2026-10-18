"""Real scored 8-player results close into one independent, signed Saved event."""
import copy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import COMPONENT_KEY
from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
from tests.api.test_calendar_continuation_flow import root, save_continuation
from tests.api.test_calendar_followup_eight_scored_knockout_flow import scored_url, scored_command
from tests.api.test_calendar_population_sporting_checkpoint import prepare, play, save, restore
from tests.api.test_calendar_sporting_week_flow import advance, weekly_command
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def close_url(server):
    return root(server) + "/knockouts/close-result"


def close_command(view, tournament_id):
    return {
        "command_id": "close-eight-native",
        "tournament_id": tournament_id,
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "operator_label": "Admin",
        "audit_reason": "Reviewed all seven authentic played MatchEngine outcomes",
        "explicit_result_confirmation": True,
    }


@pytest.mark.parametrize("width", [52, 80])
def test_close_native_eight_results_from_signed_saved_player_history(tmp_path, width):
    db = f"sqlite:///{tmp_path / 'result-close.db'}"
    with ApiServer(database_url=db) as server:
        repo, root_head = prepare(server, RunCalendar(width, width, 2030, 3))
        opening, _ = play(server, root_head)
        original_saved = save(server, opening)
        _, start = _request("GET", root(server))
        week2, _ = advance(server, weekly_command(start))
        save_continuation(server, week2)
        _, ready = _request("GET", root(server))
        event_command = scored_command(ready)
        assert _request("POST", scored_url(server), event_command)[0] == 201
        _, pending = _request("GET", root(server))
        early = close_command(pending, event_command["tournament_id"])
        assert _request("POST", close_url(server), early)[0] == 409
        played_save = save_continuation(server, {"checkpoint_fingerprint": pending["checkpoint_fingerprint"]})
        _, saved = _request("GET", root(server))
        assert saved["saved"] and saved["tournaments"][-1]["match_count"] == 7
        command = close_command(saved, event_command["tournament_id"])
        assert _request("POST", close_url(server), {**command, "explicit_result_confirmation": False})[0] == 422
        assert _request("POST", close_url(server), {**command, "expected_checkpoint_fingerprint": "f" * 64})[0] == 409
        assert _request("POST", close_url(server), {**command, "tournament_id": "unknown"})[0] == 409
        code, closed = _request("POST", close_url(server), command)
        assert code == 201, closed
        assert closed["publication_status"] == "native_result_closed_not_official"
        assert closed["official_ranking_published"] is False
        event = closed["closure"]
        assert event["schema_version"] == "calendar_native_tournament_closure.v1"
        assert event["source_week_event_count"] == 2
        assert event["source_tournament_fingerprint"] == saved["tournaments"][-1]["fingerprint"]
        assert len(event["players"]) == 8
        assert sum(p["wins"] for p in event["players"]) == 7
        assert sum(p["losses"] for p in event["players"]) == 7
        assert sorted(p["prepared_points"] for p in event["players"]) == [15] * 4 + [30] * 2 + [60, 100]
        assert sorted(p["reached_stage"] for p in event["players"]) == sorted(["quarterfinal"]*4+["semifinal"]*2+["finalist","champion"])
        assert next(p for p in event["players"] if p["reached_stage"] == "champion")["player_id"] == event["champion_player_id"]
        assert _request("POST", close_url(server), command) == (201, closed)
        _, after = _request("GET", root(server))
        assert not after["saved"] and not after["can_play"]
        assert after["tournaments"][-1]["result_closed"]
        assert not after["tournaments"][-1]["result_closure_saved"]
        assert after["closures"][-1]["fingerprint"] == closed["fingerprint"]
        assert not after["closures"][-1]["saved"]
        assert len(after["matches"]) == len(saved["matches"]) == 7
        assert after["sporting_week"] == saved["sporting_week"]
        assert _request("POST", close_url(server), {**command, "command_id": "double-close"})[0] == 409

        closure_save = save_continuation(server, closed)
        state = closure_save["payload"]["content"][COMPONENT_KEY]["state"]
        assert state["schema_version"] == "calendar_sporting_checkpoint.v8"
        assert len(state["closures"]) == 1 and len(state["week_events"]) == 2
        assert state["players"] == played_save["payload"]["content"][COMPONENT_KEY]["state"]["players"]
        assert closure_save["payload"]["content"]["calendar_standalone_match"] == original_saved["payload"]["content"]["calendar_standalone_match"]
        assert repo.verify_branch_saved_revision_hash(revision_id=closure_save["revision_id"])
        assert _request("POST", close_url(server), command) == (201, closed)

        for corruption in ("award", "wins", "wrong-origin", "unplayed-event", "downgrade"):
            forged = copy.deepcopy(closure_save["payload"])
            component = forged["content"][COMPONENT_KEY]
            cp = component["state"]
            one = cp["closures"][0]
            if corruption == "award":
                one["players"][0]["prepared_points"] += 1
            elif corruption == "wins":
                one["players"][0]["wins"] += 1
            elif corruption == "wrong-origin":
                one["source_tournament_fingerprint"] = "f" * 64
            elif corruption == "unplayed-event":
                one["source_week_event_count"] = 1
            else:
                cp["schema_version"] = "calendar_sporting_checkpoint.v7"
            component["fingerprint"] = canonical_hash(cp)
            with pytest.raises(ValueError):
                load_saved_calendar_match(forged, run_id="run", branch_id="branch")

        _, present = _request("GET", root(server))
        next_week, _ = advance(server, weekly_command(present, name="week-after-closed"))
        assert sum(n for _, n in next_week["advance"]["played_counts"]) == 14
        final_save = save_continuation(server, next_week)
        assert final_save["payload"]["content"][COMPONENT_KEY]["state"]["schema_version"] == "calendar_sporting_checkpoint.v8"
        assert _request("POST", close_url(server), command) == (201, closed)

    with ApiServer(database_url=db) as restarted:
        _, restored = _request("GET", root(restarted))
        assert restored["saved"] and restored["sporting_week"]["week"] == 3
        assert restored["closures"][-1]["saved"]
        assert restored["closures"][-1]["players"] == event["players"]
        assert _request("POST", close_url(restarted), command) == (201, closed)
        restore(restarted, played_save["revision_id"])
        assert not _request("GET", root(restarted))[1]["closures"]
        restore(restarted, closure_save["revision_id"])
        assert _request("GET", root(restarted))[1]["closures"][-1]["saved"]
        restore(restarted, final_save["revision_id"])
        assert _request("GET", root(restarted))[1]["sporting_week"]["week"] == 3
