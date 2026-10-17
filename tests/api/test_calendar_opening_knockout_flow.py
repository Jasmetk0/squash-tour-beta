"""Production SQLite/FastAPI: four-player real MatchEngine knockout and manual Save."""
from __future__ import annotations

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_standalone_match_flow import prepare_saved_world, base as exhibition_base
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def base(server):
    return server.base_url + "/admin/runs/run/branches/branch/authoritative-simulation/calendar-opening-knockout"


@pytest.mark.parametrize("calendar", [RunCalendar(52, 1, 2030, 3), RunCalendar(80, 37, 2100, 3)])
def test_real_w52_w80_knockout_atomic_save_cold_replay_and_old_head(tmp_path, calendar):
    url = f"sqlite:///{tmp_path / 'knockout.db'}"
    with ApiServer(database_url=url) as server:
        repository, head = prepare_saved_world(server, calendar)
        status, view = _request("GET", base(server))
        assert status == 200, view
        assert view["knockout"] is None
        players = view["player_ids"]
        assert len(players) == 4
        command = {
            "command_id": "four-player-play", "match_id": "real-bracket",
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": view["initial_world_fingerprint"],
            "entrant_ids": players,
            "seed": 522,
            "operator_label": "Admin",
            "audit_reason": "Play full first-week main-only four-player bracket",
        }
        status, played = _request("POST", base(server) + "/simulate", command)
        assert status == 201, played
        bracket = played["knockout"]
        assert bracket["schema_version"] == "calendar_opening_knockout.v1"
        assert bracket["week"]["calendar"] == calendar.to_metadata()
        assert len(bracket["matches"]) == 3
        first, second, final = bracket["matches"]
        assert [m["slot"] for m in bracket["matches"]] == [1, 1, 2]
        assert [m["round"] for m in bracket["matches"]] == [
            "semifinal_1", "semifinal_2", "final"
        ]
        assert final["input_context"]["player_a"]["player"]["player_id"] == first["result"]["winner_player_id"]
        assert final["input_context"]["player_b"]["player"]["player_id"] == second["result"]["winner_player_id"]
        assert len({m["result"]["match_id"] for m in bracket["matches"]}) == 3
        assert all(len(m["result"]["rally_log"]["events"]) > 0 for m in bracket["matches"])
        assert _request("POST", base(server) + "/simulate", command) == (201, played)
        assert _request("POST", base(server) + "/simulate", {**command, "seed": 523})[0] == 409
        assert _request("POST", exhibition_base(server) + "/simulate", {
            "command_id": "conflict", "match_id": "other",
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": view["initial_world_fingerprint"],
            "player_a_id": players[0], "player_b_id": players[1],
            "seed": 54, "operator_label": "Admin", "audit_reason": "Must reject",
        })[0] == 409
        status, replay = _request("GET", base(server) + "/real-bracket/replay")
        assert status == 200 and replay["exact_replay"], replay
        assert replay["winner_player_id"] == final["result"]["winner_player_id"]
        assert len(replay["rally_counts"]) == 3
        status, preview = _request("GET", base(server) + "/save/preview")
        assert status == 200 and preview["can_save"], preview
        assert preview["calendar_match_fingerprint"] == played["fingerprint"]
        status, saved = _request("POST", base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": played["fingerprint"],
        })
        assert status == 201, saved
        revision = saved["saved_revision"]
        assert revision["payload"]["content"]["calendar_standalone_match"]["state"] == bracket
        assert repository.verify_branch_saved_revision_hash(revision_id=head)
        assert repository.verify_branch_saved_revision_hash(revision_id=revision["revision_id"])
        assert _request("POST", base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": played["fingerprint"],
        })[0] == 409
        assert _request("POST", server.base_url + "/run-containers/run/branches", {
            "source_branch_id": "branch", "source_saved_revision_id": revision["revision_id"]
        })[0] == 409
        saved_id = revision["revision_id"]
    with ApiServer(database_url=url) as restarted:
        status, view = _request("GET", base(restarted))
        assert status == 200 and view["saved"], view
        assert view["knockout"] == bracket
        status, replay = _request("GET", base(restarted) + "/real-bracket/replay")
        assert status == 200 and replay["exact_replay"], replay
        assert restarted.app.state.runtime.repository.verify_branch_saved_revision_hash(
            revision_id=saved_id
        )


def test_knockout_rejects_invalid_source_and_duplicate_players(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'negative.db'}") as server:
        repository, head = prepare_saved_world(server, RunCalendar.earth_default())
        _, view = _request("GET", base(server))
        ids = view["player_ids"]
        command = {
            "command_id": "negative", "match_id": "negative-bracket",
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": view["initial_world_fingerprint"],
            "entrant_ids": ids, "seed": 1, "operator_label": "Admin",
            "audit_reason": "Fail closed",
        }
        assert _request("POST", base(server) + "/simulate", {
            **command, "entrant_ids": [ids[0], ids[1], ids[2], ids[2]],
        })[0] == 422
        assert _request("POST", base(server) + "/simulate", {
            **command, "entrant_ids": [ids[0], ids[1], ids[2], "foreign"],
        })[0] == 409
        assert _request("POST", base(server) + "/simulate", {
            **command, "expected_saved_head": "stale",
        })[0] == 409
        assert _request("GET", base(server) + "/save/preview")[0] == 409
        assert repository.verify_branch_saved_revision_hash(revision_id=head)
