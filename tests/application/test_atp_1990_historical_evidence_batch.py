"""Verify the first historical ATP evidence batch against canonical source data."""
from collections import Counter
import json

import pytest

from beta_engine.application.atp_earth_week_mapping import SOURCE_FILE, build_projection
from beta_engine.application.atp_earth_run_calendar_preview import preview_atp_earth_weeks_on_run
from beta_engine.domain.calendar.run_calendar import RunCalendar

pytestmark = pytest.mark.pr_critical
ROOT = SOURCE_FILE.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def batch():
    return read(ROOT / "historical_evidence" / "1990_batch_01.json")


@pytest.fixture(scope="module")
def projection():
    return build_projection(read(SOURCE_FILE))


def test_complete_1990_queue_and_category_binding(batch, projection):
    rows = batch["occurrences"]
    source = read(SOURCE_FILE)["year_sources"]["1990"]
    year = next(row for row in read(ROOT / "seasons_1990_2026.json")["seasons"]
                if row["year"] == 1990)
    memberships = year["series_category_ids"]
    expected = sorted(source["events"], key=lambda e: (e["start_date"], e["series_id"]))
    assert len(rows) == len(expected) == len(memberships) == 75
    assert len({row["occurrence_id"] for row in rows}) == 75
    assert set(memberships) == {row["series_id"] for row in rows}
    assert Counter(row["category_id"] for row in rows) == {
        "atp_world_series": 53, "atp_championship_series": 12,
        "atp_championship_single_week": 9, "atp_finals": 1,
    }
    by_id = {row["source_identity"]: row for row in projection["mappings"]}
    for index, (row, event) in enumerate(zip(rows, expected), 1):
        assert row["queue_index"] == index
        assert row["series_id"] == event["series_id"]
        assert row["occurrence_id"] == "atp_1990_" + event["series_id"]
        assert row["category_id"] == memberships[event["series_id"]]
        assert row["original_start_date"] == event["start_date"]
        assert row["original_end_date"] == event["end_date"]
        assert row["calendar_source_url"] == event["source_url"]
        mapped = by_id[row["occurrence_id"]]
        assert row["mapped_year_weeks"] == mapped["mapped_year_weeks"]
        assert row["source_finish_iso_week"] == mapped["source_finish_iso_week"]
    assert batch["finals_alternate_window"] == source["finals_date_window_evidence"]
    assert batch["summary"]["all_dated_occurrences"] == projection["summary"]["source_event_count"]


@pytest.mark.parametrize("clock,field", [
    (RunCalendar(52, 1, 1990, 2), "run_positions_offset_1_start_1990"),
    (RunCalendar(52, 37, 1989, 2), "run_positions_offset_37_start_1989"),
])
def test_queue_positions_agree_with_real_run_calendar(batch, projection, clock, field):
    preview = preview_atp_earth_weeks_on_run(
        calendar=clock, mapping=projection, years=[1990])
    actual = {row["source_identity"]: row for row in preview["events"]}
    assert len(actual) == 75
    for row in batch["occurrences"]:
        positions = actual[row["occurrence_id"]]["run_weeks"]
        assert row[field] == [
            {k: pos[k] for k in ("season_index", "season_week")}
            for pos in positions
        ]


def test_first_january_evidence_is_not_playability(batch):
    rows = batch["occurrences"]
    assert [row["series_id"] for row in rows[:4]] == [
        "brisbane", "wellington_1992", "auckland", "sydney_2019",
    ]
    assert [row["historical_evidence"]["host_city"] for row in rows[:4]] == [
        "Adelaide", "Wellington", "Auckland", "Sydney",
    ]
    assert all(row["historical_evidence"]["main_draw_capacity"] == 32
               for row in rows[:4])
    assert all(row["historical_evidence"]["qualification_start_date"] is None
               for row in rows[:4])
    assert all(row["profile_status"] == "not_in_published_sporting_source"
               and row["plan_status"] == "not_tested"
               and row["played_and_reopened_status"] == "not_tested"
               for row in rows)
    assert sum("historical_evidence" in row for row in rows) == 4
    assert batch["summary"]["published_sporting_profiles"] == 0
    assert batch["historical_points_evidence"]["rank_dependent_bonus_awards"] is True
    assert batch["first_next_unreviewed_occurrence"] == rows[4]["occurrence_id"]
    assert rows[4]["series_id"] == "dallas"
