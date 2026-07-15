from __future__ import annotations

import json
from pathlib import Path

import pytest

from beta_engine.domain.countries.models import CountriesConfig, Country
from beta_engine.domain.countries.population_resolver import resolve_effective_population


def _country(**overrides: object) -> Country:
    payload: dict[str, object] = {
        "code": "AAA",
        "name": "Alpha",
        "flag_asset": None,
        "region": "EUROPE",
        "population": 169_702_055,
        "wealth_support": 3,
        "squash_popularity": 4,
        "squash_tradition": 2,
        "system_quality": 5,
    }
    payload.update(overrides)
    return Country.model_validate(payload)


def test_exact_population_year_returns_authored_value() -> None:
    result = resolve_effective_population(_country(population_by_year={"1987": 123_000_000}), 1987)

    assert result.requested_year == 1987
    assert result.effective_population == 123_000_000
    assert result.source_type == "exact_population_year"
    assert result.source_year == 1987
    assert result.is_estimated is False


def test_nearest_later_population_year_is_used() -> None:
    result = resolve_effective_population(
        _country(population_by_year={"1980": 100_000_000, "1990": 120_000_000}), 1987
    )

    assert result.effective_population == 120_000_000
    assert result.source_type == "nearest_population_year"
    assert result.source_year == 1990
    assert result.is_estimated is True


def test_nearest_earlier_population_year_is_used() -> None:
    result = resolve_effective_population(
        _country(population_by_year={"1980": 100_000_000, "1990": 120_000_000}), 1982
    )

    assert result.effective_population == 100_000_000
    assert result.source_type == "nearest_population_year"
    assert result.source_year == 1980
    assert result.is_estimated is True


def test_tied_nearest_population_year_prefers_earlier_year() -> None:
    result = resolve_effective_population(
        _country(population_by_year={"1980": 100_000_000, "1990": 120_000_000}), 1985
    )

    assert result.effective_population == 100_000_000
    assert result.source_type == "nearest_population_year"
    assert result.source_year == 1980
    assert result.is_estimated is True


def test_null_exact_population_year_is_ignored() -> None:
    result = resolve_effective_population(_country(population_by_year={"1987": None, "1985": 110_000_000}), 1987)

    assert result.effective_population == 110_000_000
    assert result.source_type == "nearest_population_year"
    assert result.source_year == 1985
    assert result.is_estimated is True


def test_null_population_year_values_are_ignored_entirely() -> None:
    result = resolve_effective_population(_country(population_by_year={"1980": None, "1990": 120_000_000}), 1982)

    assert result.effective_population == 120_000_000
    assert result.source_type == "nearest_population_year"
    assert result.source_year == 1990
    assert result.is_estimated is True


@pytest.mark.parametrize("population_by_year", [None, {}])
def test_falls_back_to_default_population_when_no_usable_population_years(
    population_by_year: dict[str, int | None] | None,
) -> None:
    result = resolve_effective_population(
        _country(
            population_by_year=population_by_year,
            default_population_year=2020,
            default_population=169_702_055,
        ),
        1987,
    )

    assert result.effective_population == 169_702_055
    assert result.source_type == "default_population"
    assert result.source_year == 2020
    assert result.is_estimated is True


def test_falls_back_to_default_population_when_all_population_years_are_null() -> None:
    result = resolve_effective_population(
        _country(
            population_by_year={"1980": None, "1990": None},
            default_population_year=2020,
            default_population=169_702_055,
        ),
        1987,
    )

    assert result.effective_population == 169_702_055
    assert result.source_type == "default_population"
    assert result.source_year == 2020
    assert result.is_estimated is True


def test_default_population_is_not_estimated_for_2020_request() -> None:
    result = resolve_effective_population(_country(default_population_year=2020, default_population=169_702_055), 2020)

    assert result.effective_population == 169_702_055
    assert result.source_type == "default_population"
    assert result.source_year == 2020
    assert result.is_estimated is False


def test_falls_back_to_legacy_population_when_default_population_missing() -> None:
    result = resolve_effective_population(_country(), 1987)

    assert result.effective_population == 169_702_055
    assert result.source_type == "legacy_population"
    assert result.source_year is None
    assert result.is_estimated is True


@pytest.mark.parametrize("requested_year", [1955, 2035])
def test_boundary_years_are_accepted(requested_year: int) -> None:
    result = resolve_effective_population(_country(population_by_year={str(requested_year): 1_000_000}), requested_year)

    assert result.effective_population == 1_000_000
    assert result.source_type == "exact_population_year"


@pytest.mark.parametrize("requested_year", [1954, 2036])
def test_out_of_range_requested_years_are_rejected(requested_year: int) -> None:
    with pytest.raises(ValueError, match="requested population year must be between 1955 and 2035"):
        resolve_effective_population(_country(), requested_year)


def test_resolver_does_not_mutate_population_by_year_or_fill_missing_years() -> None:
    country = _country(population_by_year={"1980": 100_000_000, "1990": None})
    before = country.population_by_year.copy() if country.population_by_year is not None else None

    resolve_effective_population(country, 1987)

    assert country.population_by_year == before
    assert 1987 not in country.population_by_year


def test_official_fax_world_ger_uses_authored_2020_population_year_as_nearest() -> None:
    payload = json.loads(Path("config/worlds/official_fax_world/countries.json").read_text())
    config = CountriesConfig.model_validate(payload)
    germany = next(country for country in config.countries if country.code == "GER")

    result = resolve_effective_population(germany, 1987)

    assert result.effective_population == 169_702_055
    assert result.source_type == "nearest_population_year"
    assert result.source_year == 2020
    assert result.is_estimated is True
