"""Adversarial ATP source-week mapping checks (no sporting Run writes)."""
from __future__ import annotations

import json
from datetime import date

import pytest

from scripts.audit_atp_earth_week_mapping_v1 import (
    SOURCE_FILE, MAPPING_POLICY, build_projection, map_one,
)

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def source() -> dict:
    return json.loads(SOURCE_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report(source: dict) -> dict:
    return build_projection(source)


def _one(report: dict, year: int, series_id: str) -> dict:
    return next(
        item for item in report["mappings"]
        if item["atp_season_year"] == year and item["series_id"] == series_id
    )


def _weeks(item: dict) -> list[tuple[int, int]]:
    return [
        (row["calendar_year"], row["year_week"])
        for row in item["mapped_year_weeks"]
    ]


def test_all_original_atp_years_have_stable_source_only_projection(report: dict) -> None:
    summary = report["summary"]
    assert report["schema_version"] == MAPPING_POLICY
    assert report["intended_run_weeks_per_year"] == 52
    assert report["requires_explicit_sporting_import_design"] is True
    assert summary["source_event_count"] == 2407
    assert summary["source_years"] == 37
    assert summary["provisional_years"] == [2026]
    assert summary["simulated_week_count_distribution"] == {
        "1": 2325, "2": 79, "3": 3
    }
    assert summary["source_iso_week_count_distribution"] == {
        "1": 2075, "2": 329, "3": 3
    }
    assert summary["source_non_weekend_finishes"] == 29
    assert summary["review_flag_counts"]["single_week_majority_precedes_finish_week"] == 26
    assert summary["distinct_mapped_year_weeks"] == 1284
    assert summary["mapped_week_concurrency_distribution"] == {
        "1": 448, "2": 474, "3": 353, "4": 8, "5": 1
    }
    assert summary["max_parallel_source_tournaments_in_week"] == 5
    assert summary["weekly_occupancy_is_not_player_conflict_evidence"] is True
    assert summary["sporting_schedule_installed"] is False
    assert len({row["source_identity"] for row in report["mappings"]}) == 2407
    assert all(
        1 <= week["year_week"] <= 52
        for row in report["mappings"] for week in row["mapped_year_weeks"]
    )
    assert all(
        row["sporting_schedule_installed"] is False
        for row in report["mappings"]
    )
    assert summary["review_flag_counts"]["cross_iso_year"] == 10
    assert summary["review_flag_counts"]["reviewed_source_iso_week_53_not_projected"] == 1
    assert summary["review_flag_counts"]["three_week_interval_manual_sporting_review"] == 3


def test_rebuild_replay_is_identical_and_input_is_unchanged(source: dict) -> None:
    before = json.dumps(source, sort_keys=True)
    a = build_projection(source)
    b = build_projection(source)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert json.dumps(source, sort_keys=True) == before


def test_brief_sunday_to_sunday_span_uses_only_closing_week(report: dict) -> None:
    brisbane = _one(report, 2013, "brisbane")
    assert brisbane["original_start_date"] == "2012-12-30"
    assert brisbane["original_end_date"] == "2013-01-06"
    assert _weeks(brisbane) == [(2013, 1)]
    assert brisbane["mapping_rule"] == "single_majority_week"
    assert "cross_iso_year" in brisbane["review_flags"]
    assert "compressed_boundary_iso_week" in brisbane["review_flags"]


def test_iso_week_53_is_explicitly_source_only_not_silently_clamped(report: dict) -> None:
    item = _one(report, 2010, "brisbane")
    assert item["original_start_date"] == "2010-01-03"
    assert (2009, 53) in [
        (r["calendar_year"], r["year_week"]) for r in item["source_iso_weeks"]
    ]
    assert _weeks(item) == [(2010, 1)]
    assert "reviewed_source_iso_week_53_not_projected" in item["review_flags"]


def test_nonreviewed_iso_week_53_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unreviewed source ISO W53"):
        map_one(
            season_year=2021, series_id="fictional",
            start_date="2021-01-03", end_date="2021-01-10",
            year_source_status="verified_results_archive",
        )


def test_large_week_crossings_preserve_three_distinct_weeks(report: dict) -> None:
    assert _weeks(_one(report, 2025, "canadian_open")) == [
        (2025, 30), (2025, 31), (2025, 32)
    ]
    assert _weeks(_one(report, 2025, "cincinnati")) == [
        (2025, 32), (2025, 33), (2025, 34)
    ]
    assert _weeks(_one(report, 2026, "canadian_open")) == [
        (2026, 31), (2026, 32), (2026, 33)
    ]
    assert "three_week_interval_manual_sporting_review" in (
        _one(report, 2025, "canadian_open")["review_flags"]
    )
    assert "provisional_2026" in (
        _one(report, 2026, "canadian_open")["review_flags"]
    )


def test_short_midweek_and_monday_endings_are_explicit_flags(report: dict) -> None:
    midweek = _one(report, 2025, "chengdu")
    assert midweek["original_start_date"] == "2025-09-17"
    assert midweek["original_end_date"] == "2025-09-23"
    assert _weeks(midweek) == [(2025, 38)]
    assert midweek["source_finish_iso_week"] == {"calendar_year": 2025, "year_week": 39}
    assert "single_week_majority_precedes_finish_week" in midweek["review_flags"]
    assert "non_weekend_finish" in midweek["review_flags"]

    monday = _one(report, 2016, "stuttgart")
    assert monday["original_start_date"] == "2016-06-06"
    assert monday["original_end_date"] == "2016-06-13"
    assert _weeks(monday) == [(2016, 23)]
    assert monday["source_finish_iso_week"] == {"calendar_year": 2016, "year_week": 24}
    assert [row["source_days_in_week"] for row in monday["source_iso_week_day_counts"]] == [7, 1]
    assert "single_week_majority_precedes_finish_week" in monday["review_flags"]
    assert "monday_finish_majority_in_prior_iso_week" in monday["review_flags"]

    canadian_2024 = _one(report, 2024, "canadian_open")
    assert _weeks(canadian_2024) == [(2024, 32)]
    assert canadian_2024["source_finish_iso_week"] == {
        "calendar_year": 2024, "year_week": 33
    }


@pytest.mark.parametrize(
    "start,end",
    [
        ("2025-01-01", "2025-01-04"),    # under 5 days, unreviewed
        ("2025-01-01", "2025-01-30"),    # overly long
        ("2025-01-10", "2025-01-05"),    # backwards
        ("2025-02-29", "2025-03-07"),    # non-leap day
    ],
)
def test_unknown_duration_or_invalid_dates_fail_closed(start: str, end: str) -> None:
    with pytest.raises(ValueError):
        map_one(
            season_year=2025, series_id="sample",
            start_date=start, end_date=end,
            year_source_status="verified_results_archive",
        )


def test_source_removal_or_duplicate_identity_is_rejected(source: dict) -> None:
    modified = json.loads(json.dumps(source))
    modified["year_sources"]["2000"]["events"].append(
        dict(modified["year_sources"]["2000"]["events"][0])
    )
    with pytest.raises(ValueError, match="Duplicate source occurrence"):
        build_projection(modified)
    modified = json.loads(json.dumps(source))
    modified["year_sources"].pop("1990")
    with pytest.raises(ValueError, match="all 37"):
        build_projection(modified)


def test_2026_source_not_mistaken_for_completed_history(source: dict) -> None:
    modified = json.loads(json.dumps(source))
    modified["year_sources"]["2026"]["status"] = "verified_results_archive"
    with pytest.raises(ValueError, match="provenance status"):
        build_projection(modified)


def test_majority_week_keeps_2023_chinese_tour_stages_in_natural_order(report: dict) -> None:
    """Finishes on Tuesday/Wednesday must not shift most play a week late."""
    assert _weeks(_one(report, 2023, "chengdu")) == [(2023, 38)]
    assert _weeks(_one(report, 2023, "hangzhou")) == [(2023, 38)]
    assert _weeks(_one(report, 2023, "beijing")) == [(2023, 39)]
    assert _weeks(_one(report, 2023, "almaty")) == [(2023, 39)]
    assert _one(report, 2023, "beijing")["source_finish_iso_week"] == {
        "calendar_year": 2023, "year_week": 40,
    }


def test_majority_week_nonmutation_of_source_dates(report: dict) -> None:
    """Even moved mapped weeks must keep original dates and all ISO weeks."""
    example = _one(report, 2012, "atp_finals")
    assert _weeks(example) == [(2012, 45)]
    assert example["source_finish_iso_week"] == {
        "calendar_year": 2012, "year_week": 46,
    }
    assert example["original_start_date"] == "2012-11-05"
    assert example["original_end_date"] == "2012-11-12"
    assert len(example["source_iso_weeks"]) == 2
    assert sum(r["source_days_in_week"] for r in example["source_iso_week_day_counts"]) == 8
