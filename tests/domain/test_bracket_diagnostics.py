from __future__ import annotations

import pytest

from beta_engine.domain.tournaments.bracket_diagnostics import (
    main_bracket_diagnostics,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity


def codes(*, entrants: int, capacity: int, byes: int) -> set[str]:
    return {
        item.code
        for item in main_bracket_diagnostics(
            entrant_count=entrants,
            bracket_capacity=capacity,
            bye_count=byes,
        )
    }


def test_odd_main_field_always_warns_even_when_nearly_full() -> None:
    assert codes(entrants=31, capacity=32, byes=1) == {
        "odd_main_entrant_count"
    }


def test_normal_even_non_power_of_two_field_can_be_warning_free() -> None:
    assert codes(entrants=28, capacity=32, byes=4) == set()


def test_majority_of_first_round_byes_warns_without_blocking() -> None:
    diagnostics = main_bracket_diagnostics(
        entrant_count=22,
        bracket_capacity=32,
        bye_count=10,
    )

    assert {item.code for item in diagnostics} == {
        "majority_first_round_byes"
    }
    warning = diagnostics[0]
    assert warning.severity == "warning"
    assert warning.first_round_match_count == 16
    assert warning.first_round_bye_match_count == 10
    assert warning.first_round_bye_share == pytest.approx(0.625)
    assert warning.message.startswith("!")


def test_more_than_64_main_entrants_is_exceptional_warning() -> None:
    diagnostics = main_bracket_diagnostics(
        entrant_count=66,
        bracket_capacity=128,
        bye_count=62,
    )

    assert {item.code for item in diagnostics} == {
        "majority_first_round_byes",
        "large_main_draw_over_64",
    }
    assert all(item.severity == "warning" for item in diagnostics)


def test_automatic_capacity_exposes_same_non_authoritative_diagnostics() -> None:
    capacity = TournamentEntryFieldCapacity.for_main_entrant_count(
        main_entrant_count=23
    )

    assert capacity.main_draw_size == 32
    assert capacity.bye_slots == 9
    assert {item.code for item in capacity.main_diagnostics} == {
        "odd_main_entrant_count",
        "majority_first_round_byes",
    }
    # Derived diagnostics are properties, not persisted identity/fingerprint data.
    assert "main_diagnostics" not in capacity.model_dump(mode="json")


def test_diagnostics_reject_incoherent_counts() -> None:
    with pytest.raises(
        ValueError,
        match="entrants plus BYEs to equal capacity",
    ):
        main_bracket_diagnostics(
            entrant_count=28,
            bracket_capacity=32,
            bye_count=3,
        )
