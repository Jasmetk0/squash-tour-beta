"""The initial pool excludes players turning fifteen in opening Week 1."""

import pytest

from beta_engine.domain.calendar.season_weeks import (
    completed_weeks_at_calendar_position,
)
from beta_engine.domain.players.initial_pool import (
    InitialPlayerPoolGenerator,
    initial_pool_birth_year_weights,
)
from tests.domain.initial_player_pool_contract_suite import country

pytestmark = pytest.mark.pr_critical


def test_seed_315_fifteenth_birthday_is_before_opening_week_and_replays():
    generator = InitialPlayerPoolGenerator()
    inputs = {
        "country": country(
            "BOG", population=1_000_000, system=3, popularity=3, tradition=3
        ),
        "season": "2000/2001",
        "seed": 315,
        "sequence": 1,
    }
    player = generator._generate_player(**inputs)
    assert player.age_at_generation == 15
    assert player.birth_year_week != 37  # Previously 1985/W37: fifteen only in Week 1.
    assert (
        completed_weeks_at_calendar_position(
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            calendar_year=2000,
            year_week=37,
        )
        > 15 * 61
    )
    assert generator._generate_player(**inputs) == player


def test_birth_cohort_weights_exclude_opening_week_fifteenth_birthday():
    weights = initial_pool_birth_year_weights(2000)
    # Junior stage 14%, four ages. Age 15 has 36 eligible weeks in 1985 out of 60.
    assert weights[1985] == pytest.approx(0.14 / 4 * 36 / 60)
    assert sum(weights.values()) == pytest.approx(1)
    assert min(weights) == 1954
