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
from test_visible_prospects_api import _canonical_run


def _assignment(
    *,
    branch_id: str,
    event_id: str,
    player_id: str,
    wildcard_index: int,
    source: str,
    reserve_ordinal: int | None = None,
) -> DefinitiveWildCardAssignmentAuthority:
    return DefinitiveWildCardAssignmentAuthority(
        run_id="run",
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
        branch_id, _ = _canonical_run(server, "run")
        with server.app.state.runtime.repository._session_factory.begin() as session:
            store = DefinitiveWildCardAssignmentStore(session)
            store.append(
                _assignment(
                    branch_id=branch_id,
                    event_id="event-a",
                    player_id="PLAYER-WC",
                    wildcard_index=1,
                    source="original_wc",
                )
            )
            store.append(
                _assignment(
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
                    branch_id=branch_id,
                    event_id="other-event",
                    player_id="OTHER",
                    wildcard_index=1,
                    source="original_wc",
                )
            )

        status, payload = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote('run', safe='')}"
                "/tournaments/event-a/wild-cards"
            ),
        )

        assert status == 200
        assert payload == {
            "schema_version": "viewer_tournament_wild_cards.v1",
            "product_run_id": "run",
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


@pytest.mark.pr_critical
def test_viewer_wild_cards_return_empty_public_projection_before_any_definitive_assignment(
    tmp_path,
) -> None:
    path = tmp_path / "viewer-wild-cards-empty.sqlite"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server, "run")

        status, payload = _request(
            "GET",
            f"{server.base_url}/viewer/runs/run/tournaments/event/wild-cards",
        )
        assert status == 200
        assert payload["viewer_branch_id"] == branch_id
        assert payload["assignment_count"] == 0
        assert payload["assignments"] == []
