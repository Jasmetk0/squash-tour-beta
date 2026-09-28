"""Admin HTTP acceptance for Tournament Format and group topology authority."""

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


@pytest.mark.pr_critical
def test_admin_configures_finals_groups_and_generates_canonical_topology(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'format-topology-api.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Tournament Format API",
        )
        factory = server.app.state.runtime.repository._session_factory
        config = WorldTourFinalsParticipantSelectionConfiguration(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=0,
            finals_event_id="FINALS",
            participant_capacity=6,
            direct_entry_event_ids=(),
            race_snapshot_fingerprint=fp("a"),
            calendar_content_fingerprint=fp("b"),
            adopted_by_command_id="participants-config",
        )
        selected = WorldTourFinalsParticipantSelectionSnapshot(
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
            store.put_snapshot(selected)

        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        )
        tournament = root + "/tournaments/FINALS"

        status, field = _request(
            "POST",
            tournament + "/entry-field/from-finals-participant-selection",
            {
                "target_season_index": 0,
                "command_id": "entry-field",
            },
        )
        assert status == 201
        assert field["source_kind"] == "finals_participant_selection"

        status, policy = _request(
            "POST",
            root + "/tournament-group-rules/versions",
            {
                "command_id": "group-rules-s0",
                "effective_from_season_index": 0,
                "default_match_best_of": 5,
            },
        )
        assert status == 201
        assert policy["effective_from_season_index"] == 0
        assert policy["default_match_best_of"] == 5

        status, format_authority = _request(
            "POST",
            tournament + "/format/configure",
            {
                "command_id": "format-groups",
                "format_kind": "groups",
                "group_count": 2,
                "group_size": 3,
                "seeded_slots_per_group": 1,
                "group_seed_placements": [
                    {"seed_number": 1, "group_index": 1, "slot_index": 1},
                    {"seed_number": 2, "group_index": 2, "slot_index": 1},
                ],
                "advancing_per_group": 0,
                "knockout_crossings": [],
            },
        )
        assert status == 201
        assert format_authority["format_kind"] == "groups"
        assert (
            format_authority["group_configuration"]["group_rules_policy_fingerprint"]
            == policy["authority_fingerprint"]
        )

        status, preparation = _request("GET", tournament + "/preparation")
        assert status == 200
        assert preparation["phase"] == "tournament_topology_required"
        assert preparation["next_required_action"] == "generate_tournament_topology"
        assert preparation["format_authority_ready"] is True
        assert preparation["topology_ready"] is False

        status, topology = _request(
            "POST",
            tournament + "/format/topology/generate",
            {
                "command_id": "topology-groups",
                "topology_seed": 20260928,
            },
        )
        assert status == 201
        assert topology["format_kind"] == "groups"
        assert topology["participant_order_player_ids"] == [
            f"p{index}" for index in range(1, 7)
        ]
        assert len(topology["group_slots"]) == 6
        assert len(topology["group_matches"]) == 6
        assert topology["group_slots"][0]["player_id"] == "p1"
        assert topology["group_slots"][3]["player_id"] == "p2"

        status, preparation = _request("GET", tournament + "/preparation")
        assert status == 200
        assert preparation["phase"] == "group_match_schedule_required"
        assert preparation["next_required_action"] == "prepare_group_match_schedule"
        assert preparation["blockers"] == ["group_match_schedule_authority_required"]
        assert preparation["topology_ready"] is True
        assert preparation["topology_group_match_count"] == 6
        assert preparation["group_match_schedule_ready"] is False
        assert preparation["ready_for_match_schedule"] is False

        status, schedule = _request(
            "POST",
            tournament + "/format/group-match-schedule/generate",
            {"command_id": "group-match-schedule"},
        )
        assert status == 201
        assert schedule["group_count"] == 2
        assert schedule["group_size"] == 3
        assert schedule["match_day_count"] == 3
        assert len(schedule["matches"]) == 6
        assert all(
            match["effective_match_format"]["format"]["best_of"] == 5
            for match in schedule["matches"]
        )

        for day in (1, 2, 3):
            players = []
            for match in schedule["matches"]:
                if match["match_day_ordinal"] != day:
                    continue
                players.extend(
                    (match["top_player_id"], match["bottom_player_id"])
                )
            assert len(players) == len(set(players))

        status, replay = _request(
            "GET",
            tournament + "/format/group-match-schedule",
        )
        assert status == 200
        assert replay == schedule

        status, preparation = _request("GET", tournament + "/preparation")
        assert status == 200
        assert preparation["phase"] == "group_match_execution_adapter_required"
        assert preparation["next_required_action"] == "none"
        assert preparation["blockers"] == ["group_match_execution_adapter_required"]
        assert preparation["group_match_schedule_ready"] is True
        assert preparation["group_match_count"] == 6
        assert preparation["group_match_day_count"] == 3
        assert (
            preparation["group_match_schedule_fingerprint"]
            == schedule["authority_fingerprint"]
        )
        assert preparation["ready_for_match_schedule"] is False

        status, effective = _request(
            "GET",
            root + "/tournament-group-rules?target_season_index=0",
        )
        assert status == 200
        assert (
            effective["effective"]["authority_fingerprint"]
            == policy["authority_fingerprint"]
        )
        assert len(effective["versions"]) == 1
