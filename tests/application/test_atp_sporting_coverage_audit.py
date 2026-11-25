"""Coverage audits cannot silently claim dates, profiles or execution."""
from copy import deepcopy
import json

import pytest

from scripts.audit_atp_sporting_coverage import ROOT, audit

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def sources():
    return (json.loads((ROOT / "calendar.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "squash_sporting_profiles_v1.json").read_text(encoding="utf-8")))


def test_real_source_coverage_is_deterministic_and_not_execution(sources):
    calendar, sporting = sources
    report = audit(calendar, sporting, [2025, 2024, 2025])
    assert report == audit(calendar, sporting, [2024, 2025])
    assert not report["execution_readiness_assessed"]
    assert [(row["year"], row["dated"], row["profiled"], row["missing"])
            for row in report["years"]] == [(2024, 62, 2, 60), (2025, 57, 6, 51)]
    for row in report["years"]:
        assert sum(v["missing"] for v in row["categories"].values()) == row["missing"]
        assert len(row["occurrences"]) == row["dated"]
        assert all(e["profile_schema"] is None for e in row["occurrences"]
                   if e["profile_status"] == "missing")
    full = audit(calendar, sporting)
    assert len(full["years"]) == 37
    assert sum(row["dated"] for row in full["years"]) == 2407


@pytest.mark.parametrize(("damage", "message"), [
    ("duplicate", "Duplicate profile"), ("orphan", "Orphan profile"),
    ("date", "mismatch"), ("category", "mismatch"),
])
def test_profile_binding_fail_closed_even_outside_requested_year(sources, damage, message):
    calendar, original = sources
    sporting = deepcopy(original)
    p = sporting["profiles"][0]
    if damage == "duplicate":
        sporting["profiles"].append(deepcopy(p))
    elif damage == "orphan":
        p["occurrence_id"] = "atp_2025_nonexistent"
    elif damage == "date":
        p["source_start_date"] = "2025-01-01"
    else:
        p["category_id"] = "atp_250"
    with pytest.raises(ValueError, match=message):
        audit(calendar, sporting, [2024])


def test_unknown_year_rejected(sources):
    with pytest.raises(ValueError, match="Requested year"):
        audit(*sources, [2027])



def test_category_backlog_and_multiweek_source_flags(sources):
    report = audit(*sources, [2024, 2025])
    first, second = report["years"]
    assert first["categories"]["atp_250"] == {"dated": 38, "profiled": 0, "missing": 38}
    assert first["categories"]["atp_500"] == {"dated": 13, "profiled": 0, "missing": 13}
    assert second["categories"]["atp_500"] == {"dated": 16, "profiled": 4, "missing": 12}
    assert second["missing_three_or_more_iso_weeks"] == [
        "atp_2025_canadian_open", "atp_2025_cincinnati",
    ]
    event = next(e for e in second["occurrences"] if e["occurrence_id"] == "atp_2025_doha")
    assert event["profile_status"] == "missing"
    assert event["year_source_state"] == "verified_results_archive"
    assert event["duration_days_inclusive"] == 6
    assert event["iso_weeks_occupied"] == [{"iso_week": 8, "iso_year": 2025}]


@pytest.mark.parametrize("damage", ["dated_count", "overlap", "duplicate", "roster"])
def test_invalid_calendar_membership_outside_requested_year(sources, damage):
    original, sporting = sources
    calendar = deepcopy(original)
    coverage = next(e["payload"] for e in calendar["entities"]
                    if e["source_entity_id"] == "season_2025_date_coverage")
    if damage == "dated_count":
        coverage["dated_series_count"] += 1
    elif damage == "overlap":
        coverage["undated_series_ids"].append("doha")
        coverage["roster_series_count"] += 1
    elif damage == "duplicate":
        coverage["known_not_held_series_ids"].extend(["not_held", "not_held"])
        coverage["roster_series_count"] += 1
    else:
        coverage["roster_series_count"] += 1
    with pytest.raises(ValueError, match="Calendar .* mismatch: 2025"):
        audit(calendar, sporting, [2024])
