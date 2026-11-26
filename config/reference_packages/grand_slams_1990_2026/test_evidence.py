"""Run explicitly: python -m pytest config/reference_packages/grand_slams_1990_2026/test_evidence.py

Source-only checks plus expected blockers on buuk 712f0b3c. A passing blocker
test is NOT a successful sporting import or schedule preview.
"""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "calendar_evidence_v1.json").read_text())
FIXTURE = json.loads((ROOT / "australian_open_2025_import_candidate.json").read_text())


def check_phase(phase):
    first, last = map(date.fromisoformat, (phase["start"], phase["end"]))
    assert first <= last
    weeks = list(dict.fromkeys(
        (day.isocalendar().year, day.isocalendar().week)
        for day in (first + timedelta(days=i) for i in range((last-first).days+1))
    ))
    assert phase["iso_weeks"] == [{"year": y, "week": w} for y, w in weeks]
    for offset in (1, 37):
        assert all(w <= 52 for _, w in weeks)
        assert phase["run_offsets"][str(offset)] == [
            {"season_start_year": y - (w < offset), "season_week": (w-offset)%52+1}
            for y, w in weeks
        ]


def test_inventory_and_cancellation():
    assert len(DATA["series"]) == 4
    rows = DATA["inventory"]
    assert len(rows) == len({r["occurrence_id"] for r in rows}) == 148
    assert {r["year"] for r in rows} == set(range(1990, 2027))
    assert all(sum(r["year"] == y for r in rows) == 4 for y in range(1990, 2027))
    assert sum(r["status"] == "played" for r in rows) == 12
    cancelled = [r for r in rows if r["status"] == "cancelled"]
    assert len(cancelled) == 1
    assert cancelled[0]["occurrence_id"] == "atp_2020_grand_slam_wimbledon"
    assert "main" not in cancelled[0]
    for row in rows:
        if row["status"] == "played":
            check_phase(row["main"])
        else:
            assert "main" not in row


@pytest.mark.parametrize("edition", DATA["editions"], ids=lambda e:e["occurrence_id"])
def test_modern_phase_source_windows(edition):
    check_phase(edition["qualification"])
    check_phase(edition["main"])
    assert edition["qualification"]["end"] < edition["main"]["start"]
    assert edition["main"] == next(r["main"] for r in DATA["inventory"]
                                  if r["occurrence_id"] == edition["occurrence_id"])
    assert edition["schedule_status"] == "not_previewed"
    assert edition["sporting_profile_status"] == "not_imported"


def test_ao_geometry_and_proposed_round_chronology():
    p = FIXTURE["profile"]
    assert p["main_entrants"] - p["qualifier_spots"] - p["wild_cards"] == 104
    assert p["qualification_entrants"] // p["qualifier_spots"] == 8
    assert p["main_entrants"] - 1 + p["qualification_entrants"] - p["qualifier_spots"] == 239
    s = FIXTURE["proposed_schedule"]
    assert len(s["qualification"]) == 3 and len(s["main"]) == 7
    rounds = [(r["week"], r["slot"]) for r in s["qualification"] + s["main"]]
    assert rounds == sorted(set(rounds))
    assert s["status"] == "manual_proposal_not_native_preview"


def test_current_pdf_provenance_guard_rejects_candidate():
    from beta_engine.application.atp_sporting_package_adapter import parse_sporting_profile
    with pytest.raises(ValueError, match="Knockout sources require exact PDF evidence hashes"):
        parse_sporting_profile(FIXTURE["profile"])


def test_current_mapping_rejects_15_day_main():
    from beta_engine.application.atp_earth_week_mapping import map_one
    with pytest.raises(ValueError, match="Source event duration requires individual review"):
        map_one(season_year=2025, series_id="grand_slam_australian_open",
                start_date="2025-01-12", end_date="2025-01-26",
                year_source_status="verified_results_archive")
