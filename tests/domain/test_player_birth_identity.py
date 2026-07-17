from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.players import HiddenCareerTraits, Player


def _traits() -> HiddenCareerTraits:
    return HiddenCareerTraits(
        potential_ceiling=90,
        growth_curve="balanced",
        professionalism=0.7,
        ambition=0.7,
        travel_tolerance=0.6,
        schedule_aggression=0.55,
        injury_proneness=0.3,
        resilience=0.68,
    )


def _player_payload(**updates):
    payload = {
        "player_id": "P-A",
        "name": "Player A",
        "age": 27,
        "nationality": "ENG",
        "technique": 72,
        "movement": 72,
        "physical": 72,
        "mental": 72,
        "consistency": 72,
        "clutch": 72,
        "recovery": 72,
        "play_style": "counterpuncher",
        "archetype": "balanced",
        "hidden_career_traits": _traits(),
    }
    payload.update(updates)
    return payload


@pytest.mark.parametrize("age", [15, 45, 46])
def test_run_scoped_player_accepts_lifecycle_age_bounds(age: int) -> None:
    assert Player(**_player_payload(age=age)).age == age


@pytest.mark.parametrize("age", [14, 47])
def test_run_scoped_player_rejects_age_outside_lifecycle_bounds(age: int) -> None:
    with pytest.raises(ValidationError):
        Player(**_player_payload(age=age))


def test_run_scoped_player_accepts_birth_identity_bounds() -> None:
    assert Player(**_player_payload(birth_year=2000, birth_year_week=1)).birth_year_week == 1
    assert Player(**_player_payload(birth_year=2000, birth_year_week=61)).birth_year_week == 61


@pytest.mark.parametrize("birth_year_week", [0, 62])
def test_run_scoped_player_rejects_birth_year_week_outside_fax_range(birth_year_week: int) -> None:
    with pytest.raises(ValidationError):
        Player(**_player_payload(birth_year=2000, birth_year_week=birth_year_week))


def test_run_scoped_player_loads_legacy_payload_without_birth_identity() -> None:
    player = Player(**_player_payload())

    assert player.birth_year is None
    assert player.birth_year_week is None
