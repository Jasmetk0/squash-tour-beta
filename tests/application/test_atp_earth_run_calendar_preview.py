"""ATP reference-to-native RunCalendar planning; no Run writes or match authority."""
from __future__ import annotations

import json

import pytest

from beta_engine.application.atp_earth_run_calendar_preview import (
    ATP_EARTH_RUN_WEEK_PREVIEW_SCHEMA,
    preview_atp_earth_weeks_on_run,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def mapping():
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    return build_projection(source)


@pytest.fixture(scope="module")
def full(mapping):
    return preview_atp_earth_weeks_on_run(
        calendar=RunCalendar.earth_default(start_year=1990, season_count=37),
        mapping=mapping,
    )


def _event(report, year, series):
    return next(
        row for row in report["events"]
        if row["atp_season_year"] == year and row["source_series_id"] == series
    )


def test_all_2407_mapped_to_real_run_clock_with_no_sporting_install(full):
    assert full["schema_version"] == ATP_EARTH_RUN_WEEK_PREVIEW_SCHEMA
    assert full["calendar"]["weeks_per_year"] == 52
    assert len(full["selected_atp_years"]) == 37
    assert full["summary"]["mapped_occurrences"] == 2407
    assert full["summary"]["distinct_run_weeks"] == 1284
    assert full["summary"]["max_parallel_source_tournaments_in_week"] == 5
    assert full["summary"]["concurrent_run_week_distribution"] == {
        "1": 448, "2": 474, "3": 353, "4": 8, "5": 1
    }
    assert full["summary"]["sporting_ready"] is False
    assert full["no_sporting_install"] is True
    assert full["no_simulation_slot_or_match_generation"] is True
    assert full["requires_explicit_confirmation_and_save_for_future_import"] is True
    assert len(full["summary"]["three_week_sporting_review_required"]) == 3
    assert len(full["summary"]["short_majority_before_finish_review_required"]) == 26
    assert full["summary"]["native_finish_week_is_reference_only"] is True
    assert sum(r["source_finish_after_mapped_occupancy"] for r in full["events"]) == 26
    assert all(
        r["source_finish_run_week"]["calendar_year"]
        == r["source_finish_iso_week"]["calendar_year"]
        and r["source_finish_run_week"]["year_week"]
        == r["source_finish_iso_week"]["year_week"]
        and r["source_finish_is_not_sporting_result_closure"] is True
        for r in full["events"]
    )
    assert len({r["source_identity"] for r in full["events"]}) == 2407
    assert all(
        r["requires_sporting_round_and_slot_design"] is True
        for r in full["events"]
    )
    assert all(
        all(1 <= v["season_week"] <= 52 for v in r["run_weeks"])
        for r in full["events"]
    )


def test_week_53_provenance_does_not_turn_into_run_w53(full):
    brisbane = _event(full, 2010, "brisbane")
    assert brisbane["run_weeks"] == [{
        "season_index": 20,
        "season_week": 1,
        "calendar_year": 2010,
        "year_week": 1,
    }]
    assert brisbane["source_start_date"] == "2010-01-03"
    assert brisbane["source_end_date"] == "2010-01-10"
    assert "reviewed_source_iso_week_53_not_projected" in brisbane["review_flags"]


def test_three_iso_week_cases_become_contiguous_run_positions(full):
    canadian = _event(full, 2025, "canadian_open")
    assert [w["year_week"] for w in canadian["run_weeks"]] == [30, 31, 32]
    assert [w["season_week"] for w in canadian["run_weeks"]] == [30, 31, 32]
    assert canadian["run_ordinals"] == [1849, 1850, 1851]
    assert "three_week_interval_manual_sporting_review" in canadian["review_flags"]
    cincinnati = _event(full, 2025, "cincinnati")
    assert [w["year_week"] for w in cincinnati["run_weeks"]] == [32, 33, 34]
    assert canadian["run_ordinals"][-1] == cincinnati["run_ordinals"][0]


def test_majority_week_and_recorded_finish_remain_distinct(full):
    stuttgart = _event(full, 2016, "stuttgart")
    assert stuttgart["run_weeks"][0]["year_week"] == 23
    assert stuttgart["source_finish_iso_week"] == {
        "calendar_year": 2016, "year_week": 24
    }
    assert "single_week_majority_precedes_finish_week" in stuttgart["review_flags"]
    assert stuttgart["source_finish_run_week"]["year_week"] == 24
    assert stuttgart["source_finish_run_ordinal"] == stuttgart["run_ordinals"][-1] + 1
    assert stuttgart["source_finish_after_mapped_occupancy"] is True
    ordinary = _event(full, 2013, "brisbane")
    assert ordinary["source_finish_after_mapped_occupancy"] is False
    assert ordinary["source_finish_run_ordinal"] == ordinary["run_ordinals"][-1]


def test_year_slice_is_deterministic_and_cannot_look_outside_run(mapping):
    cal = RunCalendar.earth_default(start_year=2025, season_count=2)
    one = preview_atp_earth_weeks_on_run(
        calendar=cal, mapping=mapping, years=[2025, 2026]
    )
    two = preview_atp_earth_weeks_on_run(
        calendar=cal, mapping=mapping, years=[2026, 2025]
    )
    assert one == two
    assert len(one["events"]) > 80
    assert one["selected_atp_years"] == [2025, 2026]
    assert any(r["source_status"] == "provisional_published_schedule"
               for r in one["events"])
    assert all(r["atp_season_year"] in (2025, 2026) for r in one["events"])
    with pytest.raises(ValueError, match="outside Run horizon"):
        preview_atp_earth_weeks_on_run(
            calendar=cal, mapping=mapping, years=[2024, 2025]
        )


def test_offset_run_calendar_uses_season_to_year_projection_without_clamping(mapping):
    clock = RunCalendar(
        weeks_per_year=52, season_start_year_week=37,
        start_year=1989, season_count=40
    )
    result = preview_atp_earth_weeks_on_run(
        calendar=clock, mapping=mapping, years=[1990]
    )
    earliest = min((w for r in result["events"] for w in r["run_weeks"]),
                   key=lambda w: (w["calendar_year"], w["year_week"]))
    assert earliest["calendar_year"] == 1990
    assert earliest["season_index"] == 0
    assert earliest["season_week"] >= 17
    with pytest.raises(ValueError, match="outside Run horizon"):
        preview_atp_earth_weeks_on_run(
            calendar=RunCalendar(52, 37, 1990, 37), mapping=mapping, years=[1990]
        )


def test_partial_horizon_reports_all_occurrences_without_clamping(mapping):
    # This Run ends at 2025/W38, the projected Chengdu occupancy.
    clock = RunCalendar(52, 39, 2024, 1)
    result = preview_atp_earth_weeks_on_run(
        calendar=clock, mapping=mapping, years=[2025], report_outside_horizon=True,
    )
    inside = {row["source_identity"] for row in result["events"]}
    outside = {row["source_identity"]: row for row in result["outside_horizon"]}
    expected = {
        row["source_identity"] for row in mapping["mappings"]
        if row["atp_season_year"] == 2025
    }
    assert inside and outside
    assert inside.isdisjoint(outside)
    assert inside | outside.keys() == expected
    assert all(0 <= ordinal < 52 for row in result["events"] for ordinal in row["run_ordinals"])
    chengdu = outside["atp_2025_chengdu"]
    assert chengdu["mapped_year_weeks"] == [{"calendar_year": 2025, "year_week": 38}]
    assert chengdu["outside_year_weeks"] == [{"calendar_year": 2025, "year_week": 39}]
    assert chengdu["source_finish_iso_week"] == chengdu["outside_year_weeks"][0]


def test_wrong_calendar_or_mapping_fails_closed(mapping):
    with pytest.raises(ValueError, match="W=52"):
        preview_atp_earth_weeks_on_run(
            calendar=RunCalendar.fax_default(), mapping=mapping, years=[2000]
        )
    with pytest.raises(ValueError, match="Legacy"):
        preview_atp_earth_weeks_on_run(
            calendar=RunCalendar.legacy_fax(), mapping=mapping, years=[2000]
        )
    with pytest.raises(ValueError, match="explicit RunCalendar"):
        preview_atp_earth_weeks_on_run(
            calendar=None, mapping=mapping, years=[2000]
        )
    broken = dict(mapping, schema_version="other")
    with pytest.raises(ValueError, match="schema mismatch"):
        preview_atp_earth_weeks_on_run(
            calendar=RunCalendar.earth_default(), mapping=broken, years=[2000]
        )


@pytest.mark.parametrize("years", [
    [], [2025, 2025], [1989], [2027], [True], [2025, "2026"],
])
def test_invalid_requested_year_set_fails_closed(mapping, years):
    with pytest.raises(ValueError):
        preview_atp_earth_weeks_on_run(
            calendar=RunCalendar.earth_default(start_year=2025, season_count=2),
            mapping=mapping, years=years
        )


def test_missing_or_forged_source_mapping_fails_closed(mapping):
    cal = RunCalendar.earth_default(start_year=2025, season_count=2)
    incomplete = dict(mapping, mappings=mapping["mappings"][:-1])
    with pytest.raises(ValueError, match="2407"):
        preview_atp_earth_weeks_on_run(
            calendar=cal, mapping=incomplete, years=[2025]
        )
    rows = list(mapping["mappings"])
    modified = dict(rows[-1])
    modified["sporting_schedule_installed"] = True
    rows[-1] = modified
    forged = dict(mapping, mappings=rows)
    with pytest.raises(ValueError, match="sporting authority"):
        preview_atp_earth_weeks_on_run(
            calendar=cal, mapping=forged, years=[2026]
        )


def test_forged_source_finish_cannot_authorize_a_different_closure_week(mapping):
    cal = RunCalendar.earth_default(start_year=2025, season_count=2)
    rows = list(mapping["mappings"])
    idx = next(i for i, row in enumerate(rows)
               if row["source_identity"] == "atp_2025_chengdu")
    row = dict(rows[idx], source_finish_iso_week={
        "calendar_year": 2025, "year_week": 40
    })
    rows[idx] = row
    with pytest.raises(ValueError, match="finish/occupancy mismatch"):
        preview_atp_earth_weeks_on_run(
            calendar=cal, mapping=dict(mapping, mappings=rows), years=[2025]
        )


def test_native_finish_week_respects_nondefault_run_offset(mapping):
    clock = RunCalendar(
        weeks_per_year=52, season_start_year_week=37,
        start_year=2024, season_count=3
    )
    preview = preview_atp_earth_weeks_on_run(
        calendar=clock, mapping=mapping, years=[2025]
    )
    chengdu = _event(preview, 2025, "chengdu")
    assert chengdu["run_weeks"][0]["year_week"] == 38
    assert chengdu["source_finish_run_week"]["year_week"] == 39
    assert chengdu["source_finish_run_week"]["season_week"] == (
        chengdu["run_weeks"][-1]["season_week"] + 1
    )
    assert chengdu["source_finish_run_ordinal"] == chengdu["run_ordinals"][-1] + 1
