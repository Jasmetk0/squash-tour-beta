"""HTTP/SQLite coverage for canonical Draw process-window Admin authority."""

from __future__ import annotations

import pytest

from tests.api.test_admin_tournament_draw_authority_api import (
    _commit_payload,
    _generate_payload,
    _root as _draw_root,
)
from tests.api.test_admin_tournament_entry_fields_api import _install_entry_field
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request


pytestmark = pytest.mark.smoke


def _root(server, run_id: str, branch_id: str, event_id: str) -> str:
    return (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        f"/tournaments/{event_id}/draw/process"
    )


def _configure_payload(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    command_id: str,
    expected_draw_authority_fingerprint: str,
    main_process_window_count: int,
    qualification_process_window_count: int | None,
) -> dict:
    return {
        "schema_version": "canonical_tournament_draw_process_configure_command.v1",
        "command_id": command_id,
        "run_id": run_id,
        "branch_id": branch_id,
        "event_id": event_id,
        "expected_draw_authority_fingerprint": expected_draw_authority_fingerprint,
        "main_process_window_count": main_process_window_count,
        "qualification_process_window_count": qualification_process_window_count,
    }


def _generate_draw(server, *, run_id: str, branch_id: str, event_id: str):
    field = _install_entry_field(
        server,
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
    )
    draw_root = _draw_root(server, run_id, branch_id, event_id)
    status, committed = _request(
        "POST",
        draw_root + "/commit-input",
        _commit_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="commit-process-test-input",
            expected_field_fingerprint=field.fingerprint,
            draw_seed=777,
        ),
    )
    assert status == 200
    status, generated = _request(
        "POST",
        draw_root + "/generate",
        _generate_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="generate-process-test-draw",
            expected_draw_input_fingerprint=committed["draw_input_fingerprint"],
        ),
    )
    assert status == 200
    return generated


@pytest.mark.pr_critical
def test_canonical_draw_process_configuration_over_http(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'draw-process.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Draw Process HTTP"
        )
        event_id = "event"
        root = _root(server, run_id, branch_id, event_id)

        # Process authority cannot exist before the immutable initial Draw exists.
        assert _request("GET", root)[0] == 404

        generated = _generate_draw(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        status, before = _request("GET", root)
        assert status == 200
        assert before == {
            "schema_version": "canonical_tournament_draw_process_state.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "event_id": event_id,
            "draw_authority_fingerprint": generated["draw_authority_fingerprint"],
            "has_qualification": True,
            "configured": False,
            "authority_fingerprint": None,
            "main": None,
            "qualification": None,
        }

        payload = _configure_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="configure-draw-process",
            expected_draw_authority_fingerprint=generated[
                "draw_authority_fingerprint"
            ],
            main_process_window_count=4,
            qualification_process_window_count=3,
        )
        status, configured = _request("POST", root + "/configure", payload)
        assert status == 200
        assert configured["configured"] is True
        assert configured["authority_fingerprint"]
        assert configured["draw_authority_fingerprint"] == generated[
            "draw_authority_fingerprint"
        ]
        assert configured["main"] == {
            "process_window_count": 4,
            "redraw_cutoff_window_ordinal": 3,
            "draw_freeze_window_ordinal": 4,
        }
        assert configured["qualification"] == {
            "process_window_count": 3,
            "redraw_cutoff_window_ordinal": 2,
            "draw_freeze_window_ordinal": 3,
        }

        # Exact retry is idempotent and read-back is immutable.
        assert _request("POST", root + "/configure", payload) == (200, configured)
        assert _request("GET", root) == (200, configured)


@pytest.mark.pr_critical
def test_canonical_draw_process_configuration_fails_closed(tmp_path):
    server = ApiServer(
        database_url=f"sqlite:///{tmp_path / 'draw-process-guards.sqlite'}"
    )
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Draw Process Guards"
        )
        event_id = "event"
        generated = _generate_draw(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        stale = _configure_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="stale-process",
            expected_draw_authority_fingerprint="0" * 64,
            main_process_window_count=4,
            qualification_process_window_count=3,
        )
        status, body = _request("POST", root + "/configure", stale)
        assert status == 409
        assert body["detail"]["code"] == "canonical_draw_process_conflict"
        assert "changed since" in body["detail"]["message"]

        missing_q = _configure_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="missing-q-process",
            expected_draw_authority_fingerprint=generated[
                "draw_authority_fingerprint"
            ],
            main_process_window_count=4,
            qualification_process_window_count=None,
        )
        status, body = _request("POST", root + "/configure", missing_q)
        assert status == 409
        assert "requires its own configured process-window count" in body["detail"][
            "message"
        ]

        wrong_scope = _configure_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id="other-event",
            command_id="wrong-scope-process",
            expected_draw_authority_fingerprint=generated[
                "draw_authority_fingerprint"
            ],
            main_process_window_count=4,
            qualification_process_window_count=3,
        )
        status, body = _request("POST", root + "/configure", wrong_scope)
        assert status == 409
        assert "scope mismatch" in body["detail"]["message"]

        too_few_windows = _configure_payload(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="invalid-window-count",
            expected_draw_authority_fingerprint=generated[
                "draw_authority_fingerprint"
            ],
            main_process_window_count=1,
            qualification_process_window_count=3,
        )
        assert _request("POST", root + "/configure", too_few_windows)[0] == 422
