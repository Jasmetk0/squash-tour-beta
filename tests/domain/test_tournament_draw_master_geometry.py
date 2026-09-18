"""Master §15.2–15.4 canonical classic-bracket geometry."""

from __future__ import annotations

import pytest

from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthorityBuilder,
    _idealized_slot_order,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    canonical_classic_seed_count,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity


def _input(
    *,
    bracket_size: int,
    actual_players: int | None = None,
    byes: int = 0,
    draw_seed: int = 20260918,
    schema_version: str = "tournament_draw_input_authority.v2",
    explicit_seed_count: int | None = None,
) -> TournamentDrawInputAuthority:
    player_count = bracket_size - byes if actual_players is None else actual_players
    player_ids = tuple(f"P{index:03d}" for index in range(1, player_count + 1))
    canonical = canonical_classic_seed_count(
        bracket_capacity=bracket_size,
        actual_player_count=player_count,
    )
    seed_count = canonical if explicit_seed_count is None else explicit_seed_count
    return TournamentDrawInputAuthority(
        schema_version=schema_version,
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input",
        draw_seed=draw_seed,
        main_seed_count=seed_count,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=bracket_size,
            qualification_draw_size=0,
            qualifier_spots=0,
            bye_slots=byes,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=player_ids,
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=player_ids[:seed_count],
        qualification_seed_player_ids=(),
    )


@pytest.mark.parametrize(
    ("capacity", "expected"),
    (
        (2, 1),
        (4, 1),
        (8, 2),
        (16, 4),
        (32, 8),
        (64, 16),
        (128, 32),
    ),
)
def test_master_seed_count_for_full_classic_bracket(capacity, expected):
    assert canonical_classic_seed_count(
        bracket_capacity=capacity,
        actual_player_count=capacity,
    ) == expected


def test_master_seed_count_is_limited_by_real_players():
    assert canonical_classic_seed_count(
        bracket_capacity=32,
        actual_player_count=6,
    ) == 6
    assert canonical_classic_seed_count(
        bracket_capacity=8,
        actual_player_count=1,
    ) == 1
    assert canonical_classic_seed_count(
        bracket_capacity=8,
        actual_player_count=0,
    ) == 0


def test_eight_slot_idealized_order_matches_master_exactly():
    assert _idealized_slot_order(8) == (1, 8, 5, 4, 3, 6, 7, 2)


def test_thirty_two_draw_keeps_seed_tiers_inside_master_sectors():
    draw_input = _input(bracket_size=32, draw_seed=777)
    authority = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )

    assert authority.schema_version == "tournament_draw_authority.v2"
    assert authority.algorithm_version == "idealized_seed_tiers.v2"
    positions = dict(authority.main.seed_positions)
    assert positions[1] == 1
    assert positions[2] == 32
    assert {positions[3], positions[4]} == {16, 17}
    assert {positions[5], positions[6], positions[7], positions[8]} == {
        8,
        9,
        24,
        25,
    }

    # Different randomness can permute identities inside a tier, never escape it.
    other = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(bracket_size=32, draw_seed=778),
        command_id="draw",
    )
    other_positions = dict(other.main.seed_positions)
    assert other_positions[1] == 1
    assert other_positions[2] == 32
    assert {other_positions[3], other_positions[4]} == {16, 17}
    assert {
        other_positions[5],
        other_positions[6],
        other_positions[7],
        other_positions[8],
    } == {8, 9, 24, 25}


def test_twenty_eight_players_in_32_put_byes_in_idealized_29_to_32():
    draw_input = _input(bracket_size=32, actual_players=28, byes=4)
    authority = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    idealized = _idealized_slot_order(32)

    assert draw_input.main_seed_count == 8
    assert len(authority.main.bye_slot_indexes) == 4
    assert {
        idealized[physical_slot - 1]
        for physical_slot in authority.main.bye_slot_indexes
    } == {29, 30, 31, 32}


def test_same_v2_seed_and_input_replay_identical_draw():
    draw_input = _input(bracket_size=16, draw_seed=991)
    first = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    second = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    assert second == first
    assert second.fingerprint == first.fingerprint


def test_v2_rejects_non_master_seed_count():
    with pytest.raises(ValueError, match="Master §15.2"):
        _input(
            bracket_size=4,
            actual_players=4,
            explicit_seed_count=2,
        )


def test_historical_v1_contract_remains_readable_with_old_seed_count():
    player_ids = ("A", "B", "C", "D")
    historical = TournamentDrawInputAuthority(
        schema_version="tournament_draw_input_authority.v1",
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="historical",
        draw_seed=11,
        main_seed_count=2,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=player_ids,
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=("A", "B"),
        qualification_seed_player_ids=(),
    )
    authority = TournamentDrawAuthorityBuilder.build(
        draw_input=historical,
        command_id="draw",
    )

    assert authority.schema_version == "tournament_draw_authority.v1"
    assert authority.algorithm_version == "protected_seed_shuffle.v1"
    assert authority.main.seed_positions == ((1, 1), (2, 4))
