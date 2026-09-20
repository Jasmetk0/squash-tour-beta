"""Real HTTP/SQLite coverage for canonical initial Tournament Draw Admin routes."""

from __future__ import annotations

import pytest

from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)

from tests.api.test_admin_tournament_entry_fields_api import (
    _command as _withdrawal_payload,
    _install_entry_field,
    _root as _entry_root,
)
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request


pytestmark = pytest.mark.smoke


def _root(server, run_id: str, branch_id: str, event_id: str) -> str:
    return (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        f"/tournaments/{event_id}/draw"
    )


def _commit_payload(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    command_id: str,
    expected_field_fingerprint: str,
    draw_seed: int,
) -> dict:
    return {
        "schema_version": "canonical_tournament_draw_input_commit_command.v1",
        "command_id": command_id,
        "run_id": run_id,
        "branch_id": branch_id,
        "event_id": event_id,
        "expected_field_fingerprint": expected_field_fingerprint,
        "draw_seed": draw_seed,
    }


def _generate_payload(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    command_id: str,
    expected_draw_input_fingerprint: str,
) -> dict:
    return {
        "schema_version": "canonical_tournament_draw_generate_command.v1",
        "command_id": command_id,
        "run_id": run_id,
        "branch_id": branch_id,
        "event_id": event_id,
        "expected_draw_input_fingerprint": expected_draw_input_fingerprint,
    }


@pytest.mark.pr_critical
def test_canonical_draw_input_commit_and_initial_generation_over_http(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'canonical-draw.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Draw HTTP"
        )
        event_id = "event"
        field = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        status, before = _request("GET", root)
        assert status == 200
        assert before["schema_version"] == "canonical_tournament_draw_state.v1"
        assert before["field_sequence"] == 1
        assert before["field_fingerprint"] == field.fingerprint
        assert before["main_draw_capacity"] == 4
        assert before["active_main_entrant_count"] == 4
        assert before["effective_main_bye_count"] == 0
        assert before["draw_input_committed"] is False
        assert before["draw_input_fingerprint"] is None
        assert before["initial_draw_generated"] is False
        assert before["draw_authority_fingerprint"] is None
        assert before["main_diagnostics"] == []
        assert _request("GET", root + "/authority")[0] == 404

        commit = _commit_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="commit-canonical-draw-input",
            expected_field_fingerprint=field.fingerprint,
            draw_seed=424242,
        )
        status, committed = _request("POST", root + "/commit-input", commit)
        assert status == 200
        assert committed["draw_input_committed"] is True
        assert committed["draw_input_fingerprint"]
        assert committed["draw_seed"] == 424242
        assert committed["main_seed_count"] == 1
        assert committed["qualification_seed_count"] == 1
        assert committed["initial_draw_generated"] is False

        # Exact command retry is idempotent and returns the same frozen state.
        assert _request("POST", root + "/commit-input", commit) == (200, committed)

        # Committing Draw Input through the canonical HTTP boundary hard-locks
        # subsequent pre-draw field mutation through the existing Entry Field API.
        withdrawal = _withdrawal_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="withdraw-after-draw-input",
            expected_field_fingerprint=field.fingerprint,
            withdrawn_player_ids=("D",),
        )
        status, body = _request(
            "POST",
            _entry_root(server, run_id, branch_id, event_id)
            + "/pre-draw-withdrawal",
            withdrawal,
        )
        assert status == 409
        assert "locked after Tournament Draw Input authority is committed" in body[
            "detail"
        ]["message"]

        generate = _generate_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="generate-canonical-draw",
            expected_draw_input_fingerprint=committed["draw_input_fingerprint"],
        )
        status, generated = _request("POST", root + "/generate", generate)
        assert status == 200
        assert generated["draw_input_fingerprint"] == committed["draw_input_fingerprint"]
        assert generated["initial_draw_generated"] is True
        assert generated["draw_authority_fingerprint"]
        assert generated["draw_algorithm_version"] == "idealized_seed_tiers.v2"
        assert generated["main_slot_count"] == 4
        assert generated["main_node_count"] == 3
        assert generated["main_bye_count"] == 0
        assert generated["qualification_section_count"] == 1
        assert generated["qualification_section_sizes"] == [2]
        assert generated["main_diagnostics"] == []

        status, authority = _request("GET", root + "/authority")
        assert status == 200
        assert authority["schema_version"] == "tournament_draw_authority.v1"
        assert authority["algorithm_version"] == "idealized_seed_tiers.v2"
        assert authority["main"]["bracket_size"] == 4
        assert len(authority["main"]["slots"]) == 4
        assert len(authority["main"]["nodes"]) == 3
        assert authority["main"]["seed_positions"] == [[1, 1]]
        assert authority["main"]["bye_slot_indexes"] == []
        assert authority["main"]["qualifier_placeholder_slots"][0][0] == "Q1"
        assert authority["qualification"]["bracket_size"] == 2
        assert len(authority["qualification"]["nodes"]) == 1

        # Initial Draw generation retries exactly against the frozen Draw Input.
        assert _request("POST", root + "/generate", generate) == (200, generated)
        assert _request("GET", root) == (200, generated)


@pytest.mark.pr_critical
def test_effective_draw_authority_tracks_latest_append_only_revision(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'effective-draw.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Effective Canonical Draw"
        )
        event_id = "event"
        field = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        status, committed = _request(
            "POST",
            root + "/commit-input",
            _commit_payload(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="commit-effective-draw-input",
                expected_field_fingerprint=field.fingerprint,
                draw_seed=4242,
            ),
        )
        assert status == 200
        status, generated = _request(
            "POST",
            root + "/generate",
            _generate_payload(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="generate-effective-draw",
                expected_draw_input_fingerprint=committed["draw_input_fingerprint"],
            ),
        )
        assert status == 200

        status, initial = _request("GET", root + "/authority")
        assert status == 200
        assert _request("GET", root + "/effective-authority") == (200, initial)
        status, empty_history = _request("GET", root + "/revisions")
        assert status == 200
        assert empty_history["initial_draw_fingerprint"] == generated[
            "draw_authority_fingerprint"
        ]
        assert empty_history["effective_draw_fingerprint"] == generated[
            "draw_authority_fingerprint"
        ]
        assert empty_history["revisions"] == []
        assert {
            slot["player_id"]
            for slot in initial["main"]["slots"]
            if slot["player_id"] is not None
        } == {"A", "C", "D"}

        with server.app.state.runtime.repository._session_factory.begin() as session:
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="configure-effective-draw-process",
                main_process_window_count=5,
                qualification_process_window_count=3,
            )
            revision = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="withdraw-c-effective-redraw",
                withdrawn_player_ids=("C",),
                main_process_window_ordinal=1,
                qualification_process_window_ordinal=1,
                repair_draw_seed=987654,
            )

        # Immutable initial authority remains historical truth.
        assert _request("GET", root + "/authority") == (200, initial)

        status, effective = _request("GET", root + "/effective-authority")
        assert status == 200
        assert effective["draw_input_fingerprint"] == (
            revision.successor_draw_input.fingerprint
        )
        assert effective["draw_input_fingerprint"] != initial["draw_input_fingerprint"]
        effective_main_players = {
            slot["player_id"]
            for slot in effective["main"]["slots"]
            if slot["player_id"] is not None
        }
        assert "C" not in effective_main_players
        assert {"A", "B", "D"} <= effective_main_players
        assert {
            placeholder_id
            for placeholder_id, _ in effective["main"]["qualifier_placeholder_slots"]
        } == {"Q1"}

        status, history = _request("GET", root + "/revisions")
        assert status == 200
        assert history["initial_draw_fingerprint"] == generated[
            "draw_authority_fingerprint"
        ]
        assert history["effective_draw_fingerprint"] == revision.successor_draw.fingerprint
        assert len(history["revisions"]) == 1
        summary = history["revisions"][0]
        assert summary["sequence"] == 1
        assert summary["schema_version"] == revision.schema_version
        assert summary["command_id"] == "withdraw-c-effective-redraw"
        assert summary["repair_kind"] == "full_redraw"
        assert summary["affected_draw_types"] == ["main", "qualification"]
        assert summary["withdrawn_player_ids"] == ["C"]
        assert summary["main_process_window_ordinal"] == 1
        assert summary["qualification_process_window_ordinal"] == 1
        assert summary["repair_draw_seed"] == 987654
        assert summary["predecessor_draw_fingerprint"] == generated[
            "draw_authority_fingerprint"
        ]
        assert summary["successor_draw_input_fingerprint"] == (
            revision.successor_draw_input.fingerprint
        )
        assert summary["successor_draw_fingerprint"] == (
            revision.successor_draw.fingerprint
        )


@pytest.mark.pr_critical
def test_frozen_main_replacement_preview_commit_and_exact_retry_over_http(tmp_path):
    server = ApiServer(
        database_url=f"sqlite:///{tmp_path / 'frozen-main-replacement.sqlite'}"
    )
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Frozen Main Replacement HTTP"
        )
        event_id = "event"
        field = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        status, committed = _request(
            "POST",
            root + "/commit-input",
            _commit_payload(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="replacement-http-input",
                expected_field_fingerprint=field.fingerprint,
                draw_seed=424242,
            ),
        )
        assert status == 200
        status, _ = _request(
            "POST",
            root + "/generate",
            _generate_payload(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="replacement-http-draw",
                expected_draw_input_fingerprint=committed["draw_input_fingerprint"],
            ),
        )
        assert status == 200

        with server.app.state.runtime.repository._session_factory.begin() as session:
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="replacement-http-process",
                main_process_window_count=3,
                qualification_process_window_count=3,
            )

        preview_request = {
            "withdrawn_player_id": "C",
            "unavailable_player_ids": [],
        }
        status, preview = _request(
            "POST",
            root + "/frozen-main-replacement/preview",
            preview_request,
        )
        assert status == 200, preview
        assert preview["schema_version"] == (
            "authoritative_frozen_main_replacement_preview.v1"
        )
        assert preview["source"] == "qualification_promotion"
        assert preview["selected_player_id"] == "B"
        assert preview["physical_slot_index"] >= 1
        assert preview["cutoff_status"] == "replacement_open"
        assert preview["commit_mode"] == "draw_revision"
        assert len(preview["source_authority_fingerprint"]) == 64
        assert (
            preview["source_authority"]["withdrawn_player_id"]
            == "C"
        )
        assert (
            preview["source_authority"]["selected_player_id"]
            == "B"
        )

        commit = {
            "command_id": "replacement-http-commit",
            "withdrawn_player_id": "C",
            "unavailable_player_ids": [],
            "expected_source_fingerprint": preview[
                "source_authority_fingerprint"
            ],
            "main_process_window_ordinal": 3,
            "qualification_process_window_ordinal": 3,
            "repair_draw_seed": None,
        }
        stale_status, stale = _request(
            "POST",
            root + "/frozen-main-replacement/commit",
            commit | {"expected_source_fingerprint": "0" * 64},
        )
        assert stale_status == 409, stale
        assert stale["detail"]["code"] == (
            "frozen_main_replacement_commit_conflict"
        )
        assert "changed since preview" in stale["detail"]["message"]

        status, result = _request(
            "POST",
            root + "/frozen-main-replacement/commit",
            commit,
        )
        assert status == 201, result
        assert result["schema_version"] == (
            "authoritative_frozen_main_replacement_commit.v1"
        )
        assert result["source"] == "qualification_promotion"
        assert result["source_authority_fingerprint"] == (
            preview["source_authority_fingerprint"]
        )
        assert result["draw_revision_sequences"] == [1]
        assert len(result["draw_revision_fingerprints"]) == 1
        assert len(result["successor_draw_fingerprint"]) == 64

        # Lost-response retry resolves from immutable revision history even though
        # the active Draw no longer contains the withdrawn player.
        assert _request(
            "POST",
            root + "/frozen-main-replacement/commit",
            commit,
        ) == (201, result)

        # The same parent command ID cannot adopt a different reviewed source
        # fingerprint after the first commit.
        changed_status, changed = _request(
            "POST",
            root + "/frozen-main-replacement/commit",
            commit | {"expected_source_fingerprint": "f" * 64},
        )
        assert changed_status == 409, changed

        status, effective = _request("GET", root + "/effective-authority")
        assert status == 200
        main_players = {
            slot["player_id"]
            for slot in effective["main"]["slots"]
            if slot["player_id"] is not None
        }
        assert "C" not in main_players
        assert "B" in main_players

        qualification_brackets = (
            effective.get("qualification_sections")
            or ([effective["qualification"]] if effective.get("qualification") else [])
        )
        qualification_players = {
            slot["player_id"]
            for bracket in qualification_brackets
            for slot in bracket["slots"]
            if slot["player_id"] is not None
        }
        assert qualification_players == {"E", "F"}


@pytest.mark.pr_critical
def test_canonical_draw_http_fails_closed_on_stale_scope_and_missing_authority(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'canonical-draw-guards.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Draw Guards"
        )
        event_id = "event"
        field = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        missing_input = _generate_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="generate-too-early",
            expected_draw_input_fingerprint="1" * 64,
        )
        status, body = _request("POST", root + "/generate", missing_input)
        assert status == 409
        assert body["detail"]["code"] == "canonical_draw_generation_conflict"
        assert "requires committed Draw Input authority" in body["detail"]["message"]

        stale_commit = _commit_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="stale-commit",
            expected_field_fingerprint="0" * 64,
            draw_seed=99,
        )
        status, body = _request("POST", root + "/commit-input", stale_commit)
        assert status == 409
        assert body["detail"]["code"] == "canonical_draw_input_conflict"
        assert "changed since" in body["detail"]["message"]

        wrong_scope = _commit_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id="other-event",
            command_id="wrong-scope",
            expected_field_fingerprint=field.fingerprint,
            draw_seed=99,
        )
        status, body = _request("POST", root + "/commit-input", wrong_scope)
        assert status == 409
        assert "scope mismatch" in body["detail"]["message"]

        valid_commit = _commit_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="valid-commit",
            expected_field_fingerprint=field.fingerprint,
            draw_seed=99,
        )
        status, committed = _request("POST", root + "/commit-input", valid_commit)
        assert status == 200

        stale_generate = _generate_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="stale-generate",
            expected_draw_input_fingerprint="9" * 64,
        )
        status, body = _request("POST", root + "/generate", stale_generate)
        assert status == 409
        assert body["detail"]["code"] == "canonical_draw_generation_conflict"
        assert "changed since" in body["detail"]["message"]

        invalid = {
            "command_id": "bad",
            "run_id": run_id,
            "branch_id": branch_id,
            "event_id": event_id,
            "expected_draw_input_fingerprint": "not-a-fingerprint",
        }
        assert _request("POST", root + "/generate", invalid)[0] == 422
