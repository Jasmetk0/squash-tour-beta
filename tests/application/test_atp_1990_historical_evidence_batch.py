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
    assert sum("historical_evidence" in row for row in rows) == 13
    assert batch["summary"]["published_sporting_profiles"] == 0
    assert batch["historical_points_evidence"]["rank_dependent_bonus_awards"] is True
    assert batch["first_next_unreviewed_occurrence"] == rows[13]["occurrence_id"]
    assert rows[13]["series_id"] == "indian_wells"


def test_february_geometry_and_evidence_boundaries(batch):
    rows = {row["series_id"]: row["historical_evidence"]
            for row in batch["occurrences"] if "historical_evidence" in row}
    assert len(rows) == batch["summary"]["individual_detail_reviewed"] == 13
    assert batch["summary"]["queued_for_individual_review"] == 62
    assert rows["dallas"]["host_city"] == "San Francisco"
    assert rows["maceio_1992"]["host_city"] == "Guarujá"
    assert rows["sofia"]["host_city"] == "Milan"
    assert rows["rio"]["host_city"] == "Memphis"
    assert rows["maceio_1992"]["observed_lucky_losers"] == 1
    assert rows["maceio_1992"]["qualifier_spots"] == 4
    for name, entrants, seeds, byes, q in (
        ("toronto_indoor_1990", 56, 16, 8, 28),
        ("philadelphia_1998", 48, 16, 16, 24),
        ("rio", 48, 16, 16, 24),
    ):
        evidence = rows[name]
        assert evidence["main_draw_capacity"] == entrants
        assert evidence["main_bracket_slots"] == 64
        assert evidence["main_seeds"] == seeds
        assert evidence["main_byes"] == byes
        assert evidence["qualification_size_secondary"] == q
    for evidence in rows.values():
        assert evidence["main_draw_capacity"] + evidence["main_byes"] == evidence["main_bracket_slots"]
        assert evidence["qualification_entrants"] is None
        assert evidence["qualification_start_date"] is None
        assert evidence["qualification_end_date"] is None
        assert evidence["point_table_status"] == "unresolved_exact_prize_band_and_full_historical_awards"
    assert sum(row.get("qualification_size_secondary") is not None
               for row in rows.values()) == batch["summary"]["reported_qualification_size_rows"]
    assert sum("candidate_point_row" in row for row in rows.values()) == batch["summary"]["candidate_point_row_links"]
    for evidence in rows.values():
        if "candidate_point_row" in evidence:
            candidate = evidence["candidate_point_row"]
            assert candidate["status"] == "secondary_candidate_not_verified_for_occurrence"
            assert candidate["iteration"] == 1990
            assert candidate["band_usd"] == evidence["reported_financial_commitment_usd"]
    points = batch["historical_points_evidence"]
    assert points["qualifying_loss_points"] is None
    assert points["base_points_150k_32_candidate"]["round_of_32"] == 1
    assert points["base_points_250k_32_candidate"]["champion"] == 103
    bands = points["bonus_bands_secondary"]
    assert bands[0] == {"from_rank": 1, "to_rank": 1, "points": 50}
    assert bands[-1]["to_rank"] == 200
    assert all(left["to_rank"] + 1 == right["from_rank"]
               for left, right in zip(bands, bands[1:]))
