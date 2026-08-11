from __future__ import annotations

from beta_engine.domain.countries import Country
from beta_engine.domain.players import (
    AnnualTalentClassPlanner,
    NeutralRecentGreatnessDampener,
    RecentGreatnessSignal,
    TalentQualityBand,
    WeightedRecentGreatnessDampener,
)


def _country(
    *,
    code: str,
    population: int,
    squash_popularity: int = 3,
    squash_access: int = 3,
    development_quality: int = 3,
    competition_quality: int = 3,
    elite_support: int = 3,
    squash_tradition: int = 3,
) -> Country:
    return Country(
        code=code,
        name=code,
        flag_asset=None,
        region="TEST",
        population=population,
        squash_popularity=squash_popularity,
        squash_access=squash_access,
        development_quality=development_quality,
        competition_quality=competition_quality,
        elite_support=elite_support,
        squash_tradition=squash_tradition,
    )


def test_country_validation_rejects_factor_out_of_range() -> None:
    try:
        _country(code="BAD", population=10_000_000, squash_access=0)
    except Exception as exc:  # noqa: BLE001 - assert validation boundary only.
        assert "squash_access" in str(exc)
    else:
        raise AssertionError("country factor outside 1..5 should be rejected")


def test_planner_is_deterministic_for_same_seed_and_year() -> None:
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=90_000_000, squash_popularity=4, squash_access=4, development_quality=4),
        _country(code="BBB", population=220_000_000, squash_popularity=2, squash_access=2, development_quality=2),
    ]

    left = planner.plan(year=2032, seed=10101, countries=countries)
    right = planner.plan(year=2032, seed=10101, countries=countries)

    assert left.model_dump() == right.model_dump()


def test_different_years_produce_different_total_cohort_sizes() -> None:
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=90_000_000, squash_popularity=4, squash_access=4),
        _country(code="BBB", population=220_000_000, squash_popularity=2, squash_access=2),
    ]

    plan_2031 = planner.plan(year=2031, seed=2027, countries=countries)
    plan_2032 = planner.plan(year=2032, seed=2027, countries=countries)

    assert plan_2031.total_talents != plan_2032.total_talents


def test_country_development_strength_does_not_change_innate_quality_band_odds() -> None:
    planner = AnnualTalentClassPlanner()
    strong = _country(
        code="STR",
        population=40_000_000,
        squash_popularity=3,
        squash_access=3,
        development_quality=5,
        competition_quality=5,
        elite_support=5,
        squash_tradition=5,
    )
    weak = _country(
        code="WEK",
        population=40_000_000,
        squash_popularity=3,
        squash_access=3,
        development_quality=1,
        competition_quality=1,
        elite_support=1,
        squash_tradition=1,
    )

    plan = planner.plan(year=2030, seed=444, countries=[strong, weak])
    by_code = {allocation.country_code: allocation for allocation in plan.allocations}

    assert by_code["STR"].quality_weights == by_code["WEK"].quality_weights
    assert abs(by_code["STR"].planned_count - by_code["WEK"].planned_count) <= 1
    assert by_code["STR"].bias_profile.professionalism_tendency == 0.0
    assert by_code["STR"].bias_profile.technical_vs_physical_lean == 0.0
    assert by_code["STR"].bias_profile.mental_sharpness_tendency == 0.0


def test_popularity_and_access_increase_prospect_volume_at_same_population() -> None:
    planner = AnnualTalentClassPlanner()
    strong_pool = _country(code="BIG", population=50_000_000, squash_popularity=5, squash_access=5)
    weak_pool = _country(code="SML", population=50_000_000, squash_popularity=1, squash_access=1)

    plan = planner.plan(year=2035, seed=1515, countries=[strong_pool, weak_pool])
    by_code = {allocation.country_code: allocation for allocation in plan.allocations}

    assert by_code["BIG"].planned_count > by_code["SML"].planned_count


def test_population_helps_volume_but_does_not_dominate_absurdly() -> None:
    planner = AnnualTalentClassPlanner()
    huge_mid = _country(code="HUG", population=1_300_000_000)
    smaller_mid = _country(code="SML", population=65_000_000)

    plan = planner.plan(year=2035, seed=1515, countries=[huge_mid, smaller_mid])
    by_code = {allocation.country_code: allocation for allocation in plan.allocations}

    assert by_code["HUG"].planned_count > by_code["SML"].planned_count
    assert by_code["HUG"].planned_count / by_code["SML"].planned_count < 3.5


def test_generational_band_is_very_rare() -> None:
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=120_000_000, squash_popularity=4, squash_access=4),
        _country(code="BBB", population=95_000_000),
        _country(code="CCC", population=180_000_000, squash_popularity=2, squash_access=2),
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
    country = _country(code="DMP", population=80_000_000, squash_popularity=4, squash_access=4)

    plan = planner.plan(year=2040, seed=999, countries=[country])

    assert dampener.quality_multiplier(country_code="DMP", year=2040, band=TalentQualityBand.GENERATIONAL) == 1.0
    assert plan.total_talents > 0
    assert plan.allocations[0].country_code == "DMP"
    assert plan.allocations[0].dampener.active is False
    assert set(plan.allocations[0].dampener.multipliers.values()) == {1.0}


def test_weighted_dampener_is_audit_only_and_cannot_change_v1_innate_odds() -> None:
    country_a = _country(code="AAA", population=80_000_000, squash_popularity=4, squash_access=4)
    country_b = _country(code="BBB", population=80_000_000, squash_popularity=4, squash_access=4)
    baseline = AnnualTalentClassPlanner()
    dampened = AnnualTalentClassPlanner(
        dampener=WeightedRecentGreatnessDampener(
            signals=(
                RecentGreatnessSignal(
                    country_code="AAA",
                    season=2035,
                    source="manual_override",
                    quality_band=TalentQualityBand.GENERATIONAL,
                    raw_weight=2.6,
                    reference_id="aaa-legend",
                ),
            )
        )
    )

    base = baseline.plan(year=2037, seed=123, countries=[country_a, country_b])
    mod = dampened.plan(year=2037, seed=123, countries=[country_a, country_b])
    base_by = {item.country_code: item for item in base.allocations}
    mod_by = {item.country_code: item for item in mod.allocations}

    assert mod_by["AAA"].quality_weights == base_by["AAA"].quality_weights
    assert mod_by["BBB"].quality_weights == base_by["BBB"].quality_weights
    assert mod_by["AAA"].dampener.active is True
    assert mod_by["AAA"].dampener.signal_count == 1
    assert len(mod_by["AAA"].dampener.contributions) == 1
    assert set(mod_by["AAA"].dampener.multipliers.values()) == {1.0}


def test_weighted_dampener_decays_and_has_floor_as_legacy_diagnostic_math() -> None:
    dampener = WeightedRecentGreatnessDampener(
        signals=(
            RecentGreatnessSignal(
                country_code="AAA",
                season=2030,
                source="manual_override",
                quality_band=TalentQualityBand.GENERATIONAL,
                raw_weight=3.2,
                reference_id="aaa-goat",
            ),
        )
    )

    early = dampener.quality_multiplier(country_code="AAA", year=2031, band=TalentQualityBand.GENERATIONAL)
    late = dampener.quality_multiplier(country_code="AAA", year=2037, band=TalentQualityBand.GENERATIONAL)
    beyond = dampener.quality_multiplier(country_code="AAA", year=2045, band=TalentQualityBand.GENERATIONAL)

    assert early < late < 1.0
    assert early >= 0.28
    assert beyond == 1.0
