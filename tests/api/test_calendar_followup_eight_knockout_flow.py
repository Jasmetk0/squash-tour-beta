"""Real eight-player, seven-match knockout from Saved native sporting ownership."""
import copy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import COMPONENT_KEY
from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
from tests.api.test_calendar_continuation_flow import root, save_continuation
from tests.api.test_calendar_population_sporting_checkpoint import play, prepare, restore, save
from tests.api.test_calendar_sporting_week_flow import advance, weekly_command
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def eight_url(server):
    return root(server) + "/knockouts/simulate-eight"


def eight_command(view, name="real-eight", *, seed=841):
    return dict(
        command_id=name,
        tournament_id=name,
        expected_saved_head=view["saved_head_revision_id"],
        expected_checkpoint_fingerprint=view["checkpoint_fingerprint"],
        entrant_ids=view["player_ids"][:8],
        seed=seed,
        operator_label="Admin",
        audit_reason="Actual seven-match eight-entrant sporting tournament",
    )


@pytest.mark.parametrize("width", [52, 80])
def test_real_eight_knockout_save_replay_week_and_restore(tmp_path, width):
    path = tmp_path / "eight-players.db"
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        repo, head = prepare(server, RunCalendar(width, width, 2030, 3))
        opening, _ = play(server, head)
        opening_saved = save(server, opening)
        _, opening_view = _request("GET", root(server))
        week2, _ = advance(server, weekly_command(opening_view))
        week_saved = save_continuation(server, week2)
        _, view = _request("GET", root(server))
        assert view["sporting_week"]["week"] == 2 and view["saved"]
        assert len(view["player_ids"]) >= 8
        command = eight_command(view)
        before = _dump(path)
        assert _request("POST", eight_url(server), {**command, "entrant_ids": command["entrant_ids"][:7]})[0] == 422
        assert _request("POST", eight_url(server), {**command, "expected_checkpoint_fingerprint": "f" * 64})[0] == 409
        assert _dump(path) == before

        code, played = _request("POST", eight_url(server), command)
        assert code == 201, played
        event = played["tournament"]
        assert event["schema_version"] == "calendar_followup_knockout.v3"
        assert event["scope"] == "sporting_exhibition_knockout_not_official"
        assert not played["official_ranking_published"]
        assert "prepared_awards" not in played
        matches = event["matches"]
        assert len(matches) == 7
        assert [m["sequence"] for m in matches] == list(range(1, 8))
        assert [m["match_id"] for m in matches] == [
            f"real-eight:{stage}" for stage in ("qf1", "qf2", "qf3", "qf4", "sf1", "sf2", "final")
        ]
        for i in range(4):
            assert [matches[i]["result"][key] for key in ("player_a_id", "player_b_id")] == command["entrant_ids"][2*i:2*i+2]
        for i in range(2):
            assert [matches[4+i]["result"][key] for key in ("player_a_id", "player_b_id")] == [
                matches[2*i]["result"]["winner_player_id"], matches[2*i+1]["result"]["winner_player_id"]
            ]
        assert [matches[6]["result"][key] for key in ("player_a_id", "player_b_id")] == [
            matches[4]["result"]["winner_player_id"], matches[5]["result"]["winner_player_id"]
        ]
        assert played["winner_player_id"] == matches[6]["result"]["winner_player_id"]
        assert _request("POST", eight_url(server), command) == (201, played)
        _, pending = _request("GET", root(server))
        assert pending["tournaments"][-1]["entrant_count"] == 8
        assert pending["tournaments"][-1]["match_count"] == 7
        assert len(pending["matches"]) == 7 and not pending["saved"]
        assert _request("POST", eight_url(server), {**command, "command_id": "blocked", "tournament_id": "blocked"})[0] == 409

        stored = save_continuation(server, played)
        checkpoint = stored["payload"]["content"][COMPONENT_KEY]
        assert checkpoint["state"]["schema_version"] == "calendar_sporting_checkpoint.v6"
        assert len(checkpoint["state"]["week_events"][-1]["matches"]) == 7
        assert stored["payload"]["content"]["calendar_standalone_match"] == opening_saved["payload"]["content"]["calendar_standalone_match"]
        assert _request("POST", eight_url(server), command) == (201, played)
        assert repo.verify_branch_saved_revision_hash(revision_id=week_saved["revision_id"])
        for m in matches:
            code, replay = _request("GET", root(server) + f"/{m['match_id']}/replay")
            assert code == 200 and replay["exact_replay"], replay

        for mode in ("missing", "fake-champion", "participant", "downgrade"):
            tampered = copy.deepcopy(stored["payload"])
            cp = tampered["content"][COMPONENT_KEY]
            history = cp["state"]
            event = history["week_events"][-1]
            if mode == "missing":
                event["matches"].pop()
            elif mode == "fake-champion":
                result = event["matches"][-1]["result"]
                result["winner_player_id"] = result["loser_player_id"]
            elif mode == "participant":
                event["entrant_ids"][2] = event["entrant_ids"][1]
            else:
                history["schema_version"] = "calendar_sporting_checkpoint.v5"
            cp["fingerprint"] = canonical_hash(history)
            with pytest.raises(ValueError):
                load_saved_calendar_match(tampered, run_id="run", branch_id="branch")

        _, current = _request("GET", root(server))
        next_week, _ = advance(server, weekly_command(current, name="after-eight"))
        assert sum(count for _, count in next_week["advance"]["played_counts"]) == 14
        saved_week3 = save_continuation(server, next_week)
        assert saved_week3["payload"]["content"][COMPONENT_KEY]["state"]["schema_version"] == "calendar_sporting_checkpoint.v6"
        assert _request("POST", eight_url(server), command) == (201, played)
        assert repo.verify_branch_saved_revision_hash(revision_id=stored["revision_id"])

    with ApiServer(database_url=db) as reopened:
        code, state = _request("GET", root(reopened))
        assert code == 200 and state["saved"] and state["sporting_week"]["week"] == 3
        assert len(state["tournaments"]) == 1 and len(state["matches"]) == 7
        for m in matches:
            assert _request("GET", root(reopened) + f"/{m['match_id']}/replay")[1]["exact_replay"]
        assert _request("POST", eight_url(reopened), command) == (201, played)
        restore(reopened, week_saved["revision_id"])
        assert not _request("GET", root(reopened))[1]["tournaments"]
        restore(reopened, saved_week3["revision_id"])
        assert _request("GET", root(reopened))[1]["tournaments"][0]["match_count"] == 7
