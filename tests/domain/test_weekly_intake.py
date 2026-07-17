from __future__ import annotations

import pytest

from beta_engine.domain.countries import Country
from beta_engine.domain.players.weekly_intake import WeeklyIntakePlanner


def _country(code: str, **overrides: object) -> Country:
    payload: dict[str, object] = {
        "code": code,
        "name": f"Country {code}",
        "region": "TEST",
        "population": 1_000_000,
        "wealth_support": 3,
        "squash_popularity": 3,
        "squash_tradition": 3,
        "system_quality": 3,
    }
    payload.update(overrides)
    return Country.model_validate(payload)


def _allocations_by_code(plan):
    return {row.country_code: row for row in plan.allocations}


@pytest.mark.parametrize(
    ("season_week", "calendar_year", "year_week", "birth_year", "birth_year_week"),
    [
        (1, 2000, 37, 1985, 37),
        (25, 2000, 61, 1985, 61),
        (26, 2001, 1, 1986, 1),
        (61, 2001, 36, 1986, 36),
    ],
)
def test_weekly_intake_maps_season_week_to_fifteenth_birthday_cohort(
    season_week: int,
    calendar_year: int,
    year_week: int,
    birth_year: int,
    birth_year_week: int,
) -> None:
    plan = WeeklyIntakePlanner().plan_weekly_intake(
        countries=[_country("AAA")],
        season="2000/2001",
        season_week=season_week,
        target_intake_count=1,
    )

    assert plan.season == "2000/2001"
    assert plan.season_start_year == 2000
    assert plan.calendar_year == calendar_year
    assert plan.year_week == year_week
    assert plan.birth_year == birth_year
    assert plan.birth_year_week == birth_year_week
    assert plan.intake_age == 15


@pytest.mark.parametrize("season_week", [0, 62])
def test_weekly_intake_rejects_invalid_season_week(season_week: int) -> None:
    with pytest.raises(ValueError, match="season_week must be between 1 and 61"):
        WeeklyIntakePlanner().plan_weekly_intake(
            countries=[_country("AAA")],
            season="2000/2001",
            season_week=season_week,
            target_intake_count=1,
        )


def test_weekly_intake_uses_birth_year_as_population_year() -> None:
    countries = [
        _country("AAA", population_by_year={1985: 9_000_000, 1986: 1_000_000}),
        _country("BBB", population_by_year={1985: 1_000_000, 1986: 9_000_000}),
    ]
    planner = WeeklyIntakePlanner()

    week_1 = _allocations_by_code(
        planner.plan_weekly_intake(
            countries=countries,
            season="2000/2001",
            season_week=1,
            target_intake_count=10,
        )
    )
    week_26 = _allocations_by_code(
        planner.plan_weekly_intake(
            countries=countries,
            season="2000/2001",
            season_week=26,
            target_intake_count=10,
        )
    )

    assert week_1["AAA"].allocated_count > week_1["BBB"].allocated_count
    assert week_1["AAA"].effective_population == 9_000_000
    assert week_26["BBB"].allocated_count > week_26["AAA"].allocated_count
    assert week_26["BBB"].effective_population == 9_000_000


def test_weekly_intake_exposes_population_source_diagnostics() -> None:
    countries = [
        _country("AAA", population_by_year={1985: 2_000_000}),
        _country("BBB", population_by_year={1984: 2_000_000}),
        _country("CCC", default_population_year=2020, default_population=2_000_000),
        _country("DDD", population=2_000_000),
    ]

    rows = _allocations_by_code(
        WeeklyIntakePlanner().plan_weekly_intake(
            countries=countries,
            season="2000/2001",
            season_week=1,
            target_intake_count=8,
        )
    )

    assert rows["AAA"].population_source_type == "exact_population_year"
    assert rows["AAA"].population_source_year == 1985
    assert rows["AAA"].is_population_estimated is False
    assert rows["BBB"].population_source_type == "nearest_population_year"
    assert rows["BBB"].population_source_year == 1984
    assert rows["BBB"].is_population_estimated is True
    assert rows["CCC"].population_source_type == "default_population"
    assert rows["CCC"].population_source_year == 2020
    assert rows["CCC"].is_population_estimated is True
    assert rows["DDD"].population_source_type == "legacy_population"
    assert rows["DDD"].population_source_year is None
    assert rows["DDD"].is_population_estimated is True


def test_weekly_intake_allocation_is_deterministic_and_ties_by_country_code() -> None:
    countries = [_country("BBB", population_by_year={1985: 1_000}), _country("AAA", population_by_year={1985: 1_000})]
    planner = WeeklyIntakePlanner()

    first = planner.plan_weekly_intake(countries=countries, season=2000, season_week=1, target_intake_count=1)
    second = planner.plan_weekly_intake(countries=countries, season=2000, season_week=1, target_intake_count=1)
    rows = _allocations_by_code(first)

    assert first == second
    assert first.total_allocated == 1
    assert sum(row.allocation_share for row in first.allocations) == pytest.approx(1.0)
    assert rows["AAA"].allocated_count == 1
    assert rows["BBB"].allocated_count == 0


def test_weekly_intake_zero_target_returns_empty_allocations() -> None:
    plan = WeeklyIntakePlanner().plan_weekly_intake(
        countries=[_country("AAA")],
        season="2000/2001",
        season_week=1,
        target_intake_count=0,
    )

    assert plan.allocations == []
    assert plan.total_allocated == 0


def test_weekly_intake_rejects_negative_target() -> None:
    with pytest.raises(ValueError, match="target_intake_count"):
        WeeklyIntakePlanner().plan_weekly_intake(
            countries=[_country("AAA")],
            season="2000/2001",
            season_week=1,
            target_intake_count=-1,
        )


def test_weekly_intake_does_not_mutate_countries() -> None:
    countries = [_country("AAA", population_by_year={1985: 1_000_000})]
    before = [country.model_dump(mode="python") for country in countries]

    WeeklyIntakePlanner().plan_weekly_intake(
        countries=countries,
        season="2000/2001",
        season_week=1,
        target_intake_count=3,
    )

    assert [country.model_dump(mode="python") for country in countries] == before
