"""Conditional first-cohort ages: exactly hard-bounded without replacing the RNG engine."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest,
)
from beta_engine.domain.players.initial_pool import (
    InitialPlayerPoolGenerator, STAGE_AGE_RANGES,
)
from tests.domain.initial_player_pool_contract_suite import country


pytestmark = pytest.mark.pr_critical


def _world():
    return [
        country("BOG", population=8_000_000, system=3, popularity=3, tradition=3),
        country("GER", population=15_000_000, system=4, popularity=4, tradition=4),
    ]


def _generate(**kwargs):
    return InitialPlayerPoolGenerator().generate(
        countries=_world(), seed=4201, season="2000/2001",
        target_pool_size=128, **kwargs,
    )


def test_unconstrained_age_uses_identical_historic_generation_rng_and_ids():
    generator = InitialPlayerPoolGenerator()
    args = {"country": _world()[0], "season": "2000/2001", "seed": 315, "sequence": 1}
    assert generator._generate_player(**args) == generator._generate_player(
        **args, min_age=None, max_age=None
    )
    default = _generate()
    unrestricted_explicit = _generate(min_age=None, max_age=None)
    assert default == unrestricted_explicit
    assert len(default.players) == 128


@pytest.mark.parametrize("min_age,max_age", [
    (15, 15), (18, 25), (20, 20), (25, 30),
    (30, 34), (35, 45), (45, 45), (None, 22), (30, None),
])
def test_constrained_initial_cohort_is_exact_deterministic_and_stage_consistent(min_age, max_age):
    result = _generate(min_age=min_age, max_age=max_age)
    replay = _generate(min_age=min_age, max_age=max_age)
    assert result == replay
    assert len(result.players) == 128
    assert len({p.player_id for p in result.players}) == 128
    for player in result.players:
        assert 15 <= player.age_at_generation <= 45
        if min_age is not None:
            assert player.age_at_generation >= min_age
        if max_age is not None:
            assert player.age_at_generation <= max_age
        assert player.current_age_years == player.age_at_generation
        first, last = STAGE_AGE_RANGES[player.career_stage]
        assert first <= player.age_at_generation <= last
        assert player.potential_ability >= player.current_ability - 4
    assert result.summary.by_country == replay.summary.by_country
    assert result.metadata.population_weighting == "effective_population_birth_year_aggregate"


@pytest.mark.parametrize("bad", [
    {"min_age": 14}, {"max_age": 46},
    {"min_age": 26, "max_age": 25},
    {"min_age": 47, "max_age": 47},
])
def test_domain_age_bounds_fail_closed(bad):
    with pytest.raises(ValueError, match="Initial pool age condition"):
        _generate(**bad)


@pytest.mark.parametrize("bad", [
    {"min_age": 14}, {"max_age": 46},
    {"min_age": 23, "max_age": 22},
])
def test_run_preview_request_rejects_invalid_age_conditions(bad):
    with pytest.raises(ValidationError):
        RunWorldInitialPoolPreviewRequest(
            world_package_id="fifa_earth", season="2000/2001", seed=11,
            target_pool_size=10, **bad,
        )


def test_country_and_age_are_jointly_binding_and_potential_is_not_country_driven():
    generator = InitialPlayerPoolGenerator()
    world = _world()
    result = generator.generate(
        countries=world, seed=77, season="2000/2001",
        target_pool_size=64, country_code="BOG", min_age=18, max_age=22,
    )
    assert len(result.players) == 64
    assert all(p.country_code == "BOG" and 18 <= p.age_at_generation <= 22
               for p in result.players)
    inputs = {"season": "2000/2001", "seed": 77, "sequence": 7,
              "min_age": 18, "max_age": 22}
    first = generator._generate_player(country=world[0], **inputs)
    second = generator._generate_player(country=world[0], **inputs)
    assert first == second
