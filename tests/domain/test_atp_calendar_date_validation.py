"""Fail-closed ATP source interval boundaries, without fabricated dates."""
from __future__ import annotations

import copy
import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def evidence():
    names = (
        "calendar_backfill_1997_candidates_v1.json",
        "seasons_1990_2026.json",
        "calendar_dates_v1.json",
    )
    return tuple(
        json.loads((SOURCE / name).read_text(encoding="utf-8"))
        for name in names
    )


@pytest.mark.parametrize(
    "start,end",
    [
        ("1997-02-28", "1997-02-27"),  # negative duration
        ("1997-01-01", "1997-03-10"),  # historically implausible Tour edition
        ("1996-12-25", "1997-02-01"),  # too long even across calendar years
    ],
)
def test_bad_historical_duration_is_rejected(start: str, end: str) -> None:
    candidate, seasons, dated = evidence()
    invalid = copy.deepcopy(candidate)
    invalid["events"][0]["start_date"] = start
    invalid["events"][0]["end_date"] = end
    with pytest.raises(ValueError, match="duration must be 1–35 days"):
        audit_candidates(invalid, seasons, dated)


def test_original_1997_cross_year_dates_and_two_week_archive_windows_survive() -> None:
    candidate, seasons, dated = evidence()
    report = audit_candidates(candidate, seasons, dated)
    events = {x["series_id"]: x for x in report["candidate_events"]}
    assert events["doha"]["iso_weeks_occupied"] == [
        {"iso_year": 1997, "iso_week": 1}
    ]
    assert events["st_petersburg"]["iso_weeks_occupied"] == [
        {"iso_year": 1997, "iso_week": 12},
        {"iso_year": 1997, "iso_week": 13},
    ]
