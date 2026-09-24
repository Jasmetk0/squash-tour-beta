from __future__ import annotations

from urllib.parse import quote

import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    DefinitiveWildCardAssignmentStore,
)
from test_simulation_api import ApiServer, _request
from tests.api.viewer_saved_revision_helpers import (
    canonical_product_run as _canonical_run,
    save_simulation,
)
from tests.api.test_viewer_tournament_entry_field_api import (
    _repository,
    _install_viewer_entry_field,
)


def _assignment(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    player_id: str,
    wildcard_index: int,
    source: str,
    reserve_ordinal: int | None = None,
) -> DefinitiveWildCardAssignmentAuthority:
    return DefinitiveWildCardAssignmentAuthority(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        player_id=player_id,
        wildcard_index=wildcard_index,
        assignment_source=source,
        reserve_ordinal=reserve_ordinal,
        assignment_week=RankingWeek(season_index=0, week=3),
        decision_slot_ordinal=7,
        source_wild_card_command_id=f"wc-{event_id}",
        source_wild_card_authority_fingerprint="a" * 64,
        source_entry_field_fingerprint="b" * 64,
        source_field_sequence=1,
        provenance="canonical test authority",
    )


@pytest.mark.pr_critical
def test_viewer_wild_cards_expose_only_public_definitive_assignments_for_selected_event(
    tmp_path,
) -> None:
    path = tmp_path / "viewer-wild-cards.sqlite"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, run_id = _canonical_run(server, "run")
        _install_viewer_entry_field(
            database_url=f"sqlite:///{path}",
            run_id=run_id,
            branch_id=branch_id,
            event_id="event-a",
        )
        repository = _repository(f"sqlite:///{path}")
        with repository._session_factory.begin() as session:
            store = DefinitiveWildCardAssignmentStore(session)
            store.append(
                _assignment(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id="event-a",
                    player_id="PLAYER-WC",
                    wildcard_index=1,
                    source="original_wc",
                )
            )
            store.append(
                _assignment(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id="event-a",
                    player_id="PLAYER-RWC",
                    wildcard_index=2,
                    source="reserve_wc",
                    reserve_ordinal=3,
                )
            )
            store.append(
                _assignment(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id="other-event",
                    player_id="OTHER",
                    wildcard_index=1,
                    source="original_wc",
                )
            )

        # Definitive live assignments do not bypass the Saved Revision boundary.
        assert (
            _request(
                "GET",
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event-a/wild-cards",
            )[0]
            == 409
        )
        save_simulation(server, run_id, branch_id)

        status, payload = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                "/tournaments/event-a/wild-cards"
            ),
        )

        assert status == 200
        assert payload == {
            "schema_version": "viewer_tournament_wild_cards.v1",
            "product_run_id": run_id,
            "viewer_branch_id": branch_id,
            "event_id": "event-a",
            "assignment_count": 2,
            "assignments": [
                {
                    "wildcard_index": 1,
                    "player_id": "PLAYER-WC",
                    "source": "original_wc",
                    "reserve_ordinal": None,
                },
                {
                    "wildcard_index": 2,
                    "player_id": "PLAYER-RWC",
                    "source": "reserve_wc",
                    "reserve_ordinal": 3,
                },
            ],
        }

        serialized = str(payload)
        for forbidden in (
            "source_wild_card_command_id",
            "source_wild_card_authority_fingerprint",
            "source_entry_field_fingerprint",
            "source_field_sequence",
            "decision_slot_ordinal",
            "provenance",
            "assignment_week",
        ):
            assert forbidden not in serialized

        with repository._session_factory.begin() as session:
            DefinitiveWildCardAssignmentStore(session).append(
                _assignment(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id="event-a",
                    player_id="PLAYER-WC-NEW",
                    wildcard_index=3,
                    source="reserve_wc",
                    reserve_ordinal=4,
                )
            )

        # Live assignment B remains invisible until the next Save.
        assert (
            _request(
                "GET",
                (
                    f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                    "/tournaments/event-a/wild-cards"
                ),
            )[1]
            == payload
        )
        status, inspected = _request(
            "GET",
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/tournaments/event-a/entry-field",
        )
        assert status == 200
        status, repaired = _request(
            "POST",
            (
                f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
                "/tournaments/event-a/entry-field/pre-draw-withdrawal"
            ),
            {
                "schema_version": "canonical_pre_draw_withdrawal_command.v1",
                "command_id": "viewer-wc-save-boundary",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": "event-a",
                "expected_field_fingerprint": inspected["field_fingerprint"],
                "withdrawn_player_ids": ["D"],
            },
        )
        assert status == 200, repaired
        save_simulation(server, run_id, branch_id)
        status, published = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                "/tournaments/event-a/wild-cards"
            ),
        )
        assert status == 200
        assert published["assignment_count"] == 3
        assert published["assignments"][-1]["player_id"] == "PLAYER-WC-NEW"
        assert published != payload


@pytest.mark.pr_critical
def test_viewer_wild_cards_return_empty_public_projection_before_any_definitive_assignment(
    tmp_path,
) -> None:
    path = tmp_path / "viewer-wild-cards-empty.sqlite"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, run_id = _canonical_run(server, "run")

        status, payload = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event/wild-cards",
        )
        assert status == 409
        assert payload["detail"]["code"] == "viewer_tournament_wild_cards_unavailable"
