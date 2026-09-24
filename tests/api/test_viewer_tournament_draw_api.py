from __future__ import annotations

from urllib.parse import quote

import pytest

from beta_engine.application.authoritative_tournament_draw import (
    CanonicalDrawGenerateCommand,
    CanonicalDrawInputCommitCommand,
    CanonicalTournamentDrawService,
)
from test_simulation_api import ApiServer, _request
from tests.api.viewer_saved_revision_helpers import (
    canonical_product_run as _canonical_run,
)
from tests.api.test_viewer_tournament_entry_field_api import (
    _install_viewer_entry_field,
    _repository,
)
from tests.api.viewer_saved_revision_helpers import save_simulation
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)


@pytest.mark.pr_critical
def test_viewer_draw_projects_effective_selected_branch_bracket_without_internal_authority(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-draw.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run_id = "run"
        branch_id, run_id = _canonical_run(server, run_id)
        event_id = "viewer-event"
        field = _install_viewer_entry_field(
            database_url=database_url,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )

        repository = _repository(database_url)
        service = CanonicalTournamentDrawService(repository._session_factory)
        committed = service.commit_input(
            CanonicalDrawInputCommitCommand(
                command_id="viewer-draw-input",
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                expected_field_fingerprint=field.fingerprint,
                draw_seed=4242,
            )
        )
        service.generate(
            CanonicalDrawGenerateCommand(
                command_id="viewer-draw-generate",
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                expected_draw_input_fingerprint=committed.draw_input_fingerprint,
            )
        )
        # The live Draw is not public until the canonical simulation Save.
        assert (
            _request(
                "GET",
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/{event_id}/draw",
            )[0]
            == 404
        )
        save_simulation(server, run_id, branch_id)

        status, payload = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                f"/tournaments/{quote(event_id, safe='')}/draw"
            ),
        )

        assert status == 200
        assert payload["schema_version"] == "viewer_tournament_draw.v1"
        assert payload["product_run_id"] == run_id
        assert payload["viewer_branch_id"] == branch_id
        assert payload["event_id"] == event_id
        assert payload["revision_count"] == 0
        assert payload["main"]["draw_type"] == "main"
        assert payload["main"]["bracket_size"] == 4
        assert len(payload["main"]["slots"]) == 4
        assert {slot["entrant_kind"] for slot in payload["main"]["slots"]} <= {
            "player",
            "qualifier_placeholder",
            "lucky_loser_placeholder",
            "bye",
        }
        assert len(payload["qualification_sections"]) == 1
        assert payload["qualification_sections"][0]["draw_type"] == "qualification"

        serialized = str(payload)
        for forbidden in (
            "generated_by_command_id",
            "draw_input_fingerprint",
            "fingerprint",
            "algorithm_version",
            "draw_seed",
            "idealized_slot_number",
            "is_seed_protected",
            "nodes",
        ):
            assert forbidden not in serialized

        with repository._session_factory.begin() as session:
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="viewer-live-process",
                main_process_window_count=5,
                qualification_process_window_count=3,
            )
            revision = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="viewer-live-redraw",
                withdrawn_player_ids=("C",),
                main_process_window_ordinal=1,
                qualification_process_window_ordinal=1,
                repair_draw_seed=987654,
            )

        # The live effective Draw B cannot cross the saved boundary.
        assert (
            _request(
                "GET",
                (
                    f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                    f"/tournaments/{event_id}/draw"
                ),
            )[1]
            == payload
        )
        save_simulation(server, run_id, branch_id)
        status, revised = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                f"/tournaments/{event_id}/draw"
            ),
        )
        assert status == 200
        assert revised["revision_count"] == 1
        assert revised != payload
        assert (
            revision.successor_draw.fingerprint != revision.predecessor_draw_fingerprint
        )


@pytest.mark.pr_critical
def test_viewer_draw_returns_not_found_before_canonical_draw_exists(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-draw-missing.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run_id = "run"
        branch_id, run_id = _canonical_run(server, run_id)
        _install_viewer_entry_field(
            database_url=database_url,
            run_id=run_id,
            branch_id=branch_id,
            event_id="event",
        )

        status, _ = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event/draw",
        )
        assert status == 404
