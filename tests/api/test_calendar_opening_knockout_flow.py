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
        assert bracket["schema_version"] == "calendar_opening_knockout.v4"
        sporting = bracket["sporting"]
        assert len(sporting["effects"]) == 6
        assert not sporting["health_effects_applied"]
        after = {p["player_id"]: p for p in sporting["after_semifinals"]}
        terminal = {p["player_id"]: p for p in sporting["terminal"]}
        for ctx in (bracket["matches"][2]["input_context"]["player_a"], bracket["matches"][2]["input_context"]["player_b"]):
            pid = ctx["player"]["player_id"]
            assert after[pid]["long_term_fatigue"] > 0
            assert ctx["fatigue_modifier"] == round(-after[pid]["long_term_fatigue"] / 300, 6)
            assert terminal[pid]["long_term_fatigue"] >= after[pid]["long_term_fatigue"]
        losers = {m["result"]["loser_player_id"] for m in bracket["matches"][:2]}
        assert all(terminal[pid] == after[pid] for pid in losers)
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


def test_saved_knockout_restore_rewinds_live_evidence_not_signed_history(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'knockout-restore.db'}") as server:
        repository, old_head = prepare_saved_world(server, RunCalendar(52, 1, 2030, 3))
        _, view = _request("GET", base(server))
        command = {
            "command_id": "restore-knockout", "match_id": "knockout-restore",
            "expected_saved_head": old_head,
            "expected_initial_world_fingerprint": view["initial_world_fingerprint"],
            "entrant_ids": view["player_ids"], "seed": 773,
            "operator_label": "Admin", "audit_reason": "Verify immutable tournament history",
        }
        status, played = _request("POST", base(server) + "/simulate", command)
        assert status == 201, played
        _, preview = _request("GET", base(server) + "/save/preview")
        status, saved = _request("POST", base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": played["fingerprint"],
        })
        assert status == 201, saved
        played_head = saved["saved_revision"]["revision_id"]
        restore_url = (server.base_url + "/run-containers/run/branches/branch/"
                       f"saved-revisions/{old_head}/restore")
        status, preflight = _request("GET", restore_url + "-preflight")
        assert status == 200 and preflight["can_restore"], preflight
        assert _request("POST", restore_url, {
            "expected_head_saved_revision_id": played_head,
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": "branch",
            "explicit_confirmation": False,
        })[0] == 409
        status, restored = _request("POST", restore_url, {
            "expected_head_saved_revision_id": played_head,
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": "branch",
            "explicit_confirmation": True,
        })
        assert status == 201, restored
        status, view = _request("GET", base(server))
        assert status == 200 and view["knockout"] is None, view
        assert _request("GET", base(server) + "/knockout-restore/replay")[0] == 404
        assert repository.verify_branch_saved_revision_hash(revision_id=old_head)
        assert repository.verify_branch_saved_revision_hash(revision_id=played_head)
        assert repository.verify_branch_saved_revision_hash(
            revision_id=restored["saved_revision"]["revision_id"]
        )


def test_knockout_row_tamper_blocks_inspection_and_replay(tmp_path):
    import json
    from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'knockout-tamper.db'}") as server:
        repository, head = prepare_saved_world(server, RunCalendar(80, 37, 2100, 3))
        _, view = _request("GET", base(server))
        command = {
            "command_id": "tamper-knockout", "match_id": "knockout-tamper",
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": view["initial_world_fingerprint"],
            "entrant_ids": view["player_ids"], "seed": 300,
            "operator_label": "Admin", "audit_reason": "Detect corrupted bracket input",
        }
        assert _request("POST", base(server) + "/simulate", command)[0] == 201
        with repository._session_factory.begin() as session:
            row = session.get(CalendarStandaloneMatchModel, ("run", "branch", "knockout-tamper"))
            assert row is not None
            payload = json.loads(row.payload_json)
            payload["matches"][2]["result"]["winner_player_id"] = "forged"
            row.payload_json = json.dumps(payload)
        assert _request("GET", base(server))[0] == 409
        assert _request("GET", base(server) + "/knockout-tamper/replay")[0] == 409
        assert repository.verify_branch_saved_revision_hash(revision_id=head)


def test_rehashed_sporting_delta_corruption_blocks_read_replay_save_and_extension(tmp_path):
    import json
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'effect-tamper.db'}") as server:
        repo, head = prepare_saved_world(server, RunCalendar(52, 1, 2030, 3))
        _, view = _request('GET', base(server))
        status, played = _request('POST', base(server) + '/simulate', {
            'command_id': 'effect-tamper', 'match_id': 'effect-tamper',
            'expected_saved_head': head,
            'expected_initial_world_fingerprint': view['initial_world_fingerprint'],
            'entrant_ids': view['player_ids'], 'seed': 222,
            'operator_label': 'Admin', 'audit_reason': 'Check semantic corruption',
        })
        assert status == 201, played
        with repo._session_factory.begin() as session:
            row = session.get(CalendarStandaloneMatchModel, ('run', 'branch', 'effect-tamper'))
            raw = json.loads(row.payload_json)
            raw['sporting']['terminal'][0]['current_form'] += 1
            row.payload_json = json.dumps(raw)
            row.fingerprint = canonical_hash(raw)
        assert _request('GET', base(server))[0] == 409
        assert _request('GET', base(server) + '/effect-tamper/replay')[0] == 409
        assert _request('GET', base(server) + '/save/preview')[0] == 409
        status, review = _request('GET', server.base_url
            + '/run-containers/run/calendar/extension-review?new_season_count=4')
        assert status == 200 and not review['can_save'], review
        assert repo.verify_branch_saved_revision_hash(revision_id=head)
