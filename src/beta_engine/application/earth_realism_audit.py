"""Deterministic review signals for Earth sport rating histories.

This module deliberately does not decide that a history is historically realistic.
It surfaces objective review signals so technical package integrity cannot be confused
with historical calibration/realism validation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping

from beta_engine.domain.countries.rating_history import (
    CountryRatingHistory,
    GAME_ATTRIBUTE_NAMES,
)


AUDIT_SCHEMA_VERSION = "earth_realism_audit.v1"
DEFAULT_LOW_CONFIDENCE_SHARE = 0.75
DEFAULT_LARGE_ANNUAL_JUMP = 1.5
DEFAULT_LONG_FLAT_RUN_YEARS = 12


def _numeric_signature(history: CountryRatingHistory) -> tuple:
    """Return the authored numeric trajectory only; evidence metadata is excluded."""

    return tuple(
        (
            year,
            tuple(history.years[year].ratings[name].value for name in GAME_ATTRIBUTE_NAMES),
        )
        for year in sorted(history.years)
    )


def _longest_flat_run(history: CountryRatingHistory, attribute: str) -> dict:
    """Return the longest consecutive-year run with an unchanged numeric rating."""

    years = sorted(history.years)
    if not years:
        return {"length": 0, "start_year": None, "end_year": None, "value": None}

    best_length = 1
    best_start = years[0]
    best_end = years[0]
    best_value = history.years[years[0]].ratings[attribute].value

    current_length = 1
    current_start = years[0]
    previous_year = years[0]
    previous_value = best_value

    for year in years[1:]:
        value = history.years[year].ratings[attribute].value
        if year == previous_year + 1 and value == previous_value:
            current_length += 1
        else:
            current_length = 1
            current_start = year

        if current_length > best_length:
            best_length = current_length
            best_start = current_start
            best_end = year
            best_value = value

        previous_year = year
        previous_value = value

    return {
        "length": best_length,
        "start_year": best_start,
        "end_year": best_end,
        "value": best_value,
    }


def audit_earth_world(
    *,
    world_id: str,
    countries: Mapping[str, CountryRatingHistory],
    low_confidence_share: float = DEFAULT_LOW_CONFIDENCE_SHARE,
    large_annual_jump: float = DEFAULT_LARGE_ANNUAL_JUMP,
    long_flat_run_years: int = DEFAULT_LONG_FLAT_RUN_YEARS,
) -> dict:
    """Audit one world's numeric trajectories and evidence-confidence shape.

    All findings are review signals, not validation failures. A package can be
    technically valid while still requiring historical calibration review.
    """

    confidence_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    country_reports: dict[str, dict] = {}
    large_jumps: list[dict] = []
    long_flat_runs: list[dict] = []
    signature_groups: dict[tuple, list[str]] = defaultdict(list)

    total_ratings = 0

    for code, history in sorted(countries.items()):
        signature_groups[_numeric_signature(history)].append(code)

        country_confidence: Counter[str] = Counter()
        sources: set[str] = set()
        observations: set[str] = set()
        calibration_models: set[str] = set()
        country_rating_count = 0
        country_jumps: list[dict] = []
        country_flats: list[dict] = []

        years = sorted(history.years)
        for year in years:
            entry = history.years[year]
            for attribute in GAME_ATTRIBUTE_NAMES:
                rating = entry.ratings[attribute]
                total_ratings += 1
                country_rating_count += 1
                confidence_counts[rating.confidence] += 1
                country_confidence[rating.confidence] += 1
                method_counts[rating.method] += 1
                sources.update(rating.source_ids)
                observations.update(rating.observation_ids)
                if rating.calibration_model_id:
                    calibration_models.add(rating.calibration_model_id)

        for attribute in GAME_ATTRIBUTE_NAMES:
            for previous_year, year in zip(years, years[1:]):
                if year != previous_year + 1:
                    continue
                previous_value = history.years[previous_year].ratings[attribute].value
                value = history.years[year].ratings[attribute].value
                delta = round(value - previous_value, 10)
                if abs(delta) >= large_annual_jump:
                    finding = {
                        "country": code,
                        "attribute": attribute,
                        "from_year": previous_year,
                        "to_year": year,
                        "from_value": previous_value,
                        "to_value": value,
                        "delta": delta,
                    }
                    large_jumps.append(finding)
                    country_jumps.append(finding)

            flat = _longest_flat_run(history, attribute)
            if flat["length"] >= long_flat_run_years:
                finding = {
                    "country": code,
                    "attribute": attribute,
                    **flat,
                }
                long_flat_runs.append(finding)
                country_flats.append(finding)

        low_count = country_confidence.get("low", 0)
        low_share = low_count / country_rating_count if country_rating_count else 0.0
        review_flags: list[str] = []
        if low_share >= low_confidence_share:
            review_flags.append("low_confidence_share")
        if country_jumps:
            review_flags.append("large_annual_jump")
        if country_flats:
            review_flags.append("long_flat_run")

        country_reports[code] = {
            "rating_count": country_rating_count,
            "confidence": dict(sorted(country_confidence.items())),
            "low_confidence_share": round(low_share, 6),
            "distinct_source_count": len(sources),
            "distinct_observation_count": len(observations),
            "calibration_models": sorted(calibration_models),
            "large_annual_jump_count": len(country_jumps),
            "long_flat_run_count": len(country_flats),
            "review_flags": review_flags,
        }

    duplicate_groups = sorted(
        (sorted(codes) for codes in signature_groups.values() if len(codes) > 1),
        key=lambda codes: (-len(codes), codes),
    )
    large_jumps.sort(
        key=lambda item: (
            -abs(item["delta"]),
            item["country"],
            item["attribute"],
            item["from_year"],
        )
    )
    long_flat_runs.sort(
        key=lambda item: (
            -item["length"],
            item["country"],
            item["attribute"],
            item["start_year"],
        )
    )
    countries_requiring_review = sorted(
        code for code, report in country_reports.items() if report["review_flags"]
    )

    return {
        "world_id": world_id,
        "country_count": len(countries),
        "rating_count": total_ratings,
        "confidence": dict(sorted(confidence_counts.items())),
        "methods": dict(sorted(method_counts.items())),
        "countries_requiring_review": countries_requiring_review,
        "countries_requiring_review_count": len(countries_requiring_review),
        "large_annual_jumps": large_jumps,
        "large_annual_jump_count": len(large_jumps),
        "long_flat_runs": long_flat_runs,
        "long_flat_run_count": len(long_flat_runs),
        "same_world_identical_numeric_history_groups": duplicate_groups,
        "same_world_identical_numeric_history_group_count": len(duplicate_groups),
        "countries": country_reports,
        "realism_validated": False,
    }


def audit_earth_realism(
    *,
    fifa_countries: Mapping[str, CountryRatingHistory],
    atp_countries: Mapping[str, CountryRatingHistory],
    low_confidence_share: float = DEFAULT_LOW_CONFIDENCE_SHARE,
    large_annual_jump: float = DEFAULT_LARGE_ANNUAL_JUMP,
    long_flat_run_years: int = DEFAULT_LONG_FLAT_RUN_YEARS,
) -> dict:
    """Return a deterministic two-world realism review report.

    Exact cross-world duplicates compare only authored numeric trajectories. This
    intentionally ignores provenance/evidence metadata: identical football and
    tennis numbers are a calibration-review signal even when their cited sources
    differ.
    """

    fifa = audit_earth_world(
        world_id="fifa_earth",
        countries=fifa_countries,
        low_confidence_share=low_confidence_share,
        large_annual_jump=large_annual_jump,
        long_flat_run_years=long_flat_run_years,
    )
    atp = audit_earth_world(
        world_id="atp_earth",
        countries=atp_countries,
        low_confidence_share=low_confidence_share,
        large_annual_jump=large_annual_jump,
        long_flat_run_years=long_flat_run_years,
    )

    common_codes = sorted(set(fifa_countries) & set(atp_countries))
    identical_cross_world = [
        code
        for code in common_codes
        if _numeric_signature(fifa_countries[code]) == _numeric_signature(atp_countries[code])
    ]

    review_required = any(
        (
            fifa["countries_requiring_review_count"],
            atp["countries_requiring_review_count"],
            fifa["same_world_identical_numeric_history_group_count"],
            atp["same_world_identical_numeric_history_group_count"],
            len(identical_cross_world),
        )
    )

    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "realism_validated": False,
        "review_required": bool(review_required),
        "validation_boundary": (
            "This report surfaces deterministic review signals only. "
            "It does not certify historical realism or calibration quality."
        ),
        "thresholds": {
            "low_confidence_share": low_confidence_share,
            "large_annual_jump": large_annual_jump,
            "long_flat_run_years": long_flat_run_years,
        },
        "worlds": {
            "fifa_earth": fifa,
            "atp_earth": atp,
        },
        "cross_world": {
            "shared_country_count": len(common_codes),
            "identical_numeric_histories": identical_cross_world,
            "identical_numeric_history_count": len(identical_cross_world),
        },
    }
