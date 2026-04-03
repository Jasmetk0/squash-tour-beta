from __future__ import annotations

from beta_engine.domain.countries import Country
from beta_engine.domain.players import (
    AnnualTalentClassPlanner,
    NeutralRecentGreatnessDampener,
    TalentQualityBand,
)


def _country(
    *,
    code: str,
    population: int,
    wealth_support: int,
    squash_popularity: int,
    squash_tradition: int,
    system_quality: int,
) -> Country:
    return Country(
        code=code,
        name=code,
        flag_asset=None,
        region="TEST",
        population=population,
        wealth_support=wealth_support,
        squash_popularity=squash_popularity,
        squash_tradition=squash_tradition,
        system_quality=system_quality,
    )


def test_country_validation_rejects_factor_out_of_range() -> None:
    try:
        _country(
            code="BAD",
            population=10_000_000,
            wealth_support=0,
            squash_popularity=3,
            squash_tradition=3,
            system_quality=3,
        )
    except Exception as exc:  # noqa: BLE001 - assert validation boundary only.
        assert "wealth_support" in str(exc)
    else:
        raise AssertionError("country factor outside 1..5 should be rejected")


def test_planner_is_deterministic_for_same_seed_and_year() -> None:
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=90_000_000, wealth_support=4, squash_popularity=4, squash_tradition=4, system_quality=4),
        _country(code="BBB", population=220_000_000, wealth_support=2, squash_popularity=2, squash_tradition=2, system_quality=2),
    ]

    left = planner.plan(year=2032, seed=10101, countries=countries)
    right = planner.plan(year=2032, seed=10101, countries=countries)

    assert left.model_dump() == right.model_dump()


def test_different_years_produce_different_total_cohort_sizes() -> None:
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=90_000_000, wealth_support=4, squash_popularity=4, squash_tradition=4, system_quality=4),
        _country(code="BBB", population=220_000_000, wealth_support=2, squash_popularity=2, squash_tradition=2, system_quality=2),
    ]

    plan_2031 = planner.plan(year=2031, seed=2027, countries=countries)
    plan_2032 = planner.plan(year=2032, seed=2027, countries=countries)

    assert plan_2031.total_talents != plan_2032.total_talents


def test_stronger_country_has_better_top_band_odds() -> None:
    planner = AnnualTalentClassPlanner()
    strong = _country(code="STR", population=40_000_000, wealth_support=5, squash_popularity=5, squash_tradition=5, system_quality=5)
    weak = _country(code="WEK", population=40_000_000, wealth_support=1, squash_popularity=1, squash_tradition=1, system_quality=1)

    plan = planner.plan(year=2030, seed=444, countries=[strong, weak])
    by_code = {allocation.country_code: allocation for allocation in plan.allocations}

    strong_top = (
        by_code["STR"].quality_weights[TalentQualityBand.ELITE]
        + by_code["STR"].quality_weights[TalentQualityBand.SPECIAL]
        + by_code["STR"].quality_weights[TalentQualityBand.GENERATIONAL]
    )
    weak_top = (
        by_code["WEK"].quality_weights[TalentQualityBand.ELITE]
        + by_code["WEK"].quality_weights[TalentQualityBand.SPECIAL]
        + by_code["WEK"].quality_weights[TalentQualityBand.GENERATIONAL]
    )

    assert strong_top > weak_top


def test_population_helps_volume_but_does_not_dominate_absurdly() -> None:
    planner = AnnualTalentClassPlanner()
    huge_mid = _country(code="HUG", population=1_300_000_000, wealth_support=3, squash_popularity=3, squash_tradition=3, system_quality=3)
    smaller_mid = _country(code="SML", population=65_000_000, wealth_support=3, squash_popularity=3, squash_tradition=3, system_quality=3)

    plan = planner.plan(year=2035, seed=1515, countries=[huge_mid, smaller_mid])
    by_code = {allocation.country_code: allocation for allocation in plan.allocations}

    assert by_code["HUG"].planned_count > by_code["SML"].planned_count
    assert by_code["HUG"].planned_count / by_code["SML"].planned_count < 3.5


def test_generational_band_is_very_rare() -> None:
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=120_000_000, wealth_support=4, squash_popularity=4, squash_tradition=5, system_quality=4),
        _country(code="BBB", population=95_000_000, wealth_support=3, squash_popularity=3, squash_tradition=3, system_quality=3),
        _country(code="CCC", population=180_000_000, wealth_support=2, squash_popularity=2, squash_tradition=2, system_quality=2),
    ]

    total = 0
    generational = 0
    for year in range(2030, 2140):
        plan = planner.plan(year=year, seed=8877, countries=countries)
        for allocation in plan.allocations:
            for talent in allocation.talents:
                total += 1
                if talent.quality_band == TalentQualityBand.GENERATIONAL:
                    generational += 1

    assert generational > 0
    assert generational / total < 0.004


def test_neutral_dampener_is_default_safe_and_neutral() -> None:
    dampener = NeutralRecentGreatnessDampener()
    planner = AnnualTalentClassPlanner(dampener=dampener)
    country = _country(code="DMP", population=80_000_000, wealth_support=4, squash_popularity=4, squash_tradition=4, system_quality=4)

    plan = planner.plan(year=2040, seed=999, countries=[country])

    assert dampener.quality_multiplier(country_code="DMP", year=2040, band=TalentQualityBand.GENERATIONAL) == 1.0
    assert plan.total_talents > 0
    assert plan.allocations[0].country_code == "DMP"
