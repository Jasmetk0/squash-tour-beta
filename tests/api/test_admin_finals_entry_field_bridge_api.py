"""Admin acceptance for Finals participant selection -> Tournament Entry Field."""

import pytest

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsSelectedPlayer,
)
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from tests.api.test_saved_revision_history_api import (
    ApiServer,
    _create_run,
    _request,
)


def fp(char: str) -> str:
    return char * 64


def _install_selection(factory, *, run_id: str, branch_id: str):
    config = WorldTourFinalsParticipantSelectionConfiguration(
        run_id=run_id,
        branch_id=branch_id,
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=6,
        direct_entry_event_ids=(),
        race_snapshot_fingerprint=fp("a"),
        calendar_content_fingerprint=fp("b"),
        adopted_by_command_id="configure-finals-participants",
    )
    snapshot = WorldTourFinalsParticipantSelectionSnapshot(
        run_id=run_id,
        branch_id=branch_id,
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=6,
        configuration_fingerprint=config.fingerprint,
        race_snapshot_fingerprint=config.race_snapshot_fingerprint,
        direct_entry_winner_event_ids=(),
        participants=tuple(
            WorldTourFinalsSelectedPlayer(
                player_id=f"p{index}",
                race_rank=index,
                race_points=1000 - index,
                seed=index,
                qualification_source="race",
            )
            for index in range(1, 7)
        ),
    )
    with factory.begin() as session:
        store = WorldTourFinalsParticipantSelectionStore(session)
        store.put_configuration(config)
        store.put_snapshot(snapshot)
    return snapshot


@pytest.mark.pr_critical
def test_admin_bridge_moves_finals_preparation_from_entry_field_to_format_blocker(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'finals-entry-field-api.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Finals Entry Field Bridge",
        )
        factory = server.app.state.runtime.repository._session_factory
        selected = _install_selection(
            factory,
            run_id=run_id,
            branch_id=branch_id,
        )

        tournament_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/tournaments/FINALS"
        )
        preparation_root = tournament_root + "/preparation"
        entry_root = tournament_root + "/entry-field"

        status, before = _request("GET", preparation_root)
        assert status == 200
        assert before["phase"] == "entry_field_required"
        assert before["next_required_action"] == "build_entry_field"
        assert before["ranking_snapshot_ready"] is False
        assert before["entry_source_kind"] == "finals_participant_selection"
        assert (
            before["entry_source_authority_fingerprint"]
            == selected.fingerprint
        )

        status, field = _request(
            "POST",
            entry_root + "/from-finals-participant-selection",
            {
                "target_season_index": 0,
                "command_id": "bridge-finals-entry-field",
            },
        )
        assert status == 201
        assert field["schema_version"] == "tournament_entry_field.v2"
        assert field["source_kind"] == "finals_participant_selection"
        assert field["capacity"]["geometry_kind"] == "fixed_participant_field"
        assert field["capacity"]["main_draw_size"] == 6
        assert field["direct_main_player_ids"] == [
            f"p{index}" for index in range(1, 7)
        ]

        status, after = _request("GET", preparation_root)
        assert status == 200
        assert after["phase"] == "tournament_format_required"
        assert after["next_required_action"] == "configure_tournament_format"
        assert after["blockers"] == ["tournament_format_authority_required"]
        assert after["entry_field_ready"] is True
        assert after["main_draw_size"] == 6
        assert after["entry_seed_order_player_ids"] == [
            f"p{index}" for index in range(1, 7)
        ]
        assert after["can_apply_pre_draw_withdrawal"] is False
        assert after["can_commit_draw_input"] is False
        assert after["ready_for_match_schedule"] is False

        # Exact command retry is idempotent.
        status, replay = _request(
            "POST",
            entry_root + "/from-finals-participant-selection",
            {
                "target_season_index": 0,
                "command_id": "bridge-finals-entry-field",
            },
        )
        assert status == 201
        assert replay == field
