"""Real shared player kernel, explicit year units and immutable v1 boundaries."""

from collections import Counter

import pytest
from pydantic import ValidationError

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.season_weeks import (
    completed_weeks_at_calendar_position,
)
from beta_engine.domain.players.calendar_initial_pool import (
    CalendarInitialPlayerPoolGenerator,
    CalendarInitialPoolPlayer,
    CalendarInitialPoolResult,
    InitialPoolCalendarBasis,
)
from beta_engine.domain.players.initial_pool import InitialPoolGeneratedPlayer
from tests.domain.initial_player_pool_contract_suite import country

pytestmark = pytest.mark.pr_critical


def generator(clock, **kwargs):
    return CalendarInitialPlayerPoolGenerator(
        time_basis=InitialPoolCalendarBasis.from_run_calendar(clock), **kwargs,
    )


def countries():
    return [country("GER", population=20_000_000, system=4, popularity=4, tradition=4)]


@pytest.mark.parametrize("clock", [RunCalendar.earth_default(), RunCalendar(52, 35, 2030, 3),
    RunCalendar(61, 37, 2000, 50), RunCalendar(80, 80, 1955, 1), RunCalendar(7, 3, 2100, 1),
    RunCalendar(1, 1, 0, 1), RunCalendar(2_000_000_000, 1_000_000_000, 2030, 1)])
def test_generated_births_ages_and_serialized_calendar_are_consistent(clock):
    service = generator(clock)
    first = service.generate(countries=countries(), seed=802, target_pool_size=120,
                             naming_policy="country_serial.v1")
    assert first == service.generate(countries=countries(), seed=802, target_pool_size=120,
                                     naming_policy="country_serial.v1")
    assert CalendarInitialPoolResult.model_validate_json(first.model_dump_json()) == first
    for player in first.players:
        assert player.created_for_season == clock.label(0)
        assert 1 <= player.birth_year_week <= clock.weeks_per_year
        elapsed = completed_weeks_at_calendar_position(
            birth_year=player.birth_year, birth_year_week=player.birth_year_week,
            calendar_year=clock.start_year, year_week=clock.season_start_year_week,
            weeks_per_calendar_year=clock.weeks_per_year,
        )
        assert elapsed > 15 * clock.weeks_per_year
        assert elapsed // clock.weeks_per_year == player.age_at_generation == player.current_age_years
        assert player.time_basis == first.metadata.time_basis
        with pytest.raises(ValidationError):
            InitialPoolGeneratedPlayer.model_validate(player.model_dump())
    assert first.metadata.age_min == (16 if clock.weeks_per_year == 1 else 15)
    if clock.weeks_per_year == 80:
        assert any(p.birth_year_week > 61 for p in first.players)


@pytest.mark.parametrize("width,offset", [(2, 1), (2, 2), (52, 1), (52, 35), (61, 37), (80, 80)])
def test_age15_birth_year_weights_match_all_eligible_birth_weeks(width, offset):
    service = generator(RunCalendar(width, offset, 2030, 1), minimum_age=15, maximum_age=15)
    expected = Counter(2030 - 15 - (week > offset) for week in range(1, width + 1) if week != offset)
    actual = service._birth_year_weights(2030)
    assert actual == {year: count / (width - 1) for year, count in sorted(expected.items())}
    cohort = service.generate(countries=countries(), seed=80, target_pool_size=100)
    assert all(player.birth_year_week != offset and player.current_age_years == 15 for player in cohort.players)
    assert cohort.metadata.age_min == cohort.metadata.age_max == 15


def test_one_week_age15_condition_is_explained_and_existing_profiles_cannot_be_injected():
    with pytest.raises(ValueError, match="strictly before"):
        generator(RunCalendar(1, 1, 2000, 1), minimum_age=15, maximum_age=15)
    service = generator(RunCalendar.earth_default())
    with pytest.raises(ValueError, match="fresh generation"):
        service.generate(countries=countries(), seed=80, existing_locked_players=[])


def test_calendar_week_count_does_not_multiply_initial_ability_or_potential():
    a = generator(RunCalendar(52, 35, 2030, 1), minimum_age=18, maximum_age=18)
    b = generator(RunCalendar(61, 35, 2030, 1), minimum_age=18, maximum_age=18)
    left = a.generate(countries=countries(), seed=802, target_pool_size=80)
    right = b.generate(countries=countries(), seed=802, target_pool_size=80)
    for first, second in zip(left.players, right.players):
        assert first.attributes == second.attributes
        assert first.hidden_career_traits == second.hidden_career_traits
        assert first.current_ability == second.current_ability
        assert first.potential_ability == second.potential_ability
        assert first.generation_fingerprint != second.generation_fingerprint
    assert left.metadata.generation_fingerprint != right.metadata.generation_fingerprint


def test_v2_validation_refuses_misdated_or_mislabelled_profiles():
    service = generator(RunCalendar.earth_default(), minimum_age=18, maximum_age=18)
    player = service.generate(countries=countries(), seed=802, target_pool_size=1).players[0]
    for change in ({"birth_year_week": 53}, {"current_age_years": 19},
                   {"created_for_season": "2000/2001"}, {"time_basis": None}):
        with pytest.raises(ValidationError):
            CalendarInitialPoolPlayer.model_validate({**player.model_dump(), **change})


def test_population_weighting_uses_requested_age_cohorts_and_honest_fallbacks():
    service = generator(RunCalendar(52, 1, 1900, 1), minimum_age=20, maximum_age=20)
    source = countries()[0].model_copy(update={"population_by_year": {1955: 1_000_000, 2026: 2_000_000}})
    result = service.generate(countries=[source], seed=802, target_pool_size=4)
    diagnostic = result.metadata.population_weighting_diagnostics[0]
    assert diagnostic.population_year_min == 1879
    assert diagnostic.population_year_max == 1880
    assert diagnostic.age_min == diagnostic.age_max == 20
    assert diagnostic.source_year_min == diagnostic.source_year_max == 1955
    assert diagnostic.estimated_weight_share == 1
    assert diagnostic.effective_population_quantity == pytest.approx(1_000_000)
