"""Finals participant selection -> shared Tournament Entry Field bridge."""

import hashlib
import json

import pytest

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsSelectedPlayer,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryField,
    TournamentEntryFieldCapacity,
    TournamentEntryFieldResolver,
)


def fp(char: str) -> str:
    return char * 64


def selection(capacity: int = 6) -> WorldTourFinalsParticipantSelectionSnapshot:
    return WorldTourFinalsParticipantSelectionSnapshot(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=capacity,
        configuration_fingerprint=fp("a"),
        race_snapshot_fingerprint=fp("b"),
        direct_entry_winner_event_ids=(),
        participants=tuple(
            WorldTourFinalsSelectedPlayer(
                player_id=f"p{index}",
                race_rank=index,
                race_points=1000 - index,
                seed=index,
                qualification_source="race",
            )
            for index in range(1, capacity + 1)
        ),
    )


@pytest.mark.pr_critical
def test_finals_bridge_accepts_non_power_of_two_participant_capacity_without_fake_bracket():
    selected = selection(6)
    field = TournamentEntryFieldResolver.build_from_finals_participant_selection(
        selection=selected
    )

    assert field.schema_version == "tournament_entry_field.v2"
    assert field.source_kind == "finals_participant_selection"
    assert field.capacity.geometry_kind == "fixed_participant_field"
    assert field.capacity.main_draw_size == 6
    assert field.direct_main_player_ids == tuple(f"p{i}" for i in range(1, 7))
    assert field.seed_order_player_ids == field.direct_main_player_ids
    assert field.tournament_ranking_authority_fingerprint is None
    assert field.ranking_snapshot_fingerprint is None
    assert field.finals_participant_selection_fingerprint == selected.fingerprint
    assert field.finals_race_snapshot_fingerprint == selected.race_snapshot_fingerprint
    assert field.main_diagnostics == ()


@pytest.mark.pr_critical
def test_classic_bracket_capacity_still_rejects_non_power_of_two():
    with pytest.raises(ValueError, match="Classic Main Draw capacity"):
        TournamentEntryFieldCapacity(main_draw_size=6)


@pytest.mark.pr_critical
def test_fixed_participant_field_cannot_smuggle_reserved_slots():
    with pytest.raises(ValueError, match="cannot reserve"):
        TournamentEntryFieldCapacity(
            geometry_kind="fixed_participant_field",
            main_draw_size=6,
            wild_card_slots=1,
        )


@pytest.mark.pr_critical
def test_historical_v1_entry_field_json_keeps_identical_fingerprint():
    payload = {
        "schema_version": "tournament_entry_field.v1",
        "run_id": "run",
        "branch_id": "branch",
        "event_id": "EVENT",
        "mode": "initial",
        "capacity": {
            "main_draw_size": 4,
            "qualification_draw_size": 0,
            "qualifier_spots": 0,
            "wild_card_slots": 0,
            "bye_slots": 0,
        },
        "tournament_ranking_authority_fingerprint": fp("a"),
        "ranking_snapshot_fingerprint": fp("b"),
        "applications_fingerprint": fp("c"),
        "direct_main_player_ids": ["p1", "p2", "p3", "p4"],
        "qualification_player_ids": [],
        "below_qualification_cut_player_ids": [],
        "withdrawn_player_ids": [],
        "base_field_fingerprint": None,
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    reopened = TournamentEntryField.model_validate_json(
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )

    assert reopened.model_dump(mode="json") == payload
    assert reopened.fingerprint == expected
