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
    assert sum(r["status"] == "played" for r in rows) == 143
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


DRAW_EVIDENCE = json.loads((ROOT / "draw_evidence_v1.json").read_text())


@pytest.mark.parametrize("edition", DRAW_EVIDENCE["editions"], ids=lambda e: e["occurrence_id"])
def test_reviewed_draw_positions_and_replacements(edition):
    main, q, nominal = edition["main"], edition["qualification"], edition["nominal"]
    positions = [p for values in main["slots"].values() for p in values]
    assert len(positions) == len(set(positions))
    assert all(1 <= p <= main["draw_capacity"] for p in positions)
    assert main["unmarked"] + len(positions) == main["entrants"] == 128
    assert len(main["slots"]["qualifier"]) == q["qualifier_spots"] == 16
    additional_wc = main.get("additional_verified_wild_card_slots", [])
    assert len(positions + additional_wc) == len(set(positions + additional_wc))
    assert all(1 <= p <= main["draw_capacity"] for p in additional_wc)
    assert len(main["slots"]["wild_card"]) + len(additional_wc) == nominal["main_wc"] == 8
    if additional_wc:
        assert main["additional_verified_wild_card_sources"]
    assert main["seeds"] == 32 and main["byes"] == 0
    assert nominal["main_other_places"] - (main["unmarked"] - len(additional_wc)) == len(main["slots"]["lucky_loser"])
    assert nominal["total_bracket_nodes"] == 239
    assert nominal["unique_field_without_replacements"] == 240
    assert main["sha256"] is None and q["sha256"] is None  # raw source bytes missing
    if "observed_slots" in q:
        q_positions = [p for values in q["observed_slots"].values() for p in values]
        assert len(q_positions) == len(set(q_positions))
        assert all(1 <= p <= q["draw_capacity"] for p in q_positions)
        assert q["observed_unmarked"] + len(q_positions) == 128
        assert q["seeds"] == 32 and q["byes"] == 0


@pytest.mark.parametrize("year", [2024, 2025])
def test_wimbledon_played_qualification_endpoints(year):
    e = next(e for e in DATA["editions"] if
             e["occurrence_id"] == f"atp_{year}_grand_slam_wimbledon")
    assert e["qualification_evidence"] == "observed_endpoints"
    assert len(e["qualification_sources"]) == 3
    assert e["qualification"]["iso_weeks"] == [{"year": year, "week": 26}]


def test_us_open_2024_wildcard_pdf_discrepancy_retained():
    e = next(e for e in DRAW_EVIDENCE["editions"] if e["occurrence_id"] == "atp_2024_grand_slam_us_open")
    assert len(e["main"]["slots"]["wild_card"]) == 7
    assert e["main"]["additional_verified_wild_card_slots"] == [114]
    assert len(e["main"]["additional_verified_wild_card_sources"]) == 2


def test_roland_garros_partial_snapshot_is_not_final():
    e = next(e for e in DRAW_EVIDENCE["editions"] if e["occurrence_id"] == "atp_2025_grand_slam_roland_garros")
    assert e["main"]["report_stage"] == "after_first_round_not_final"
    assert e["qualification"]["pages"] == [1]
    assert e["qualification"]["partial_slot_scope"] == [1, 64]
    assert "observed_slots" not in e["qualification"]


@pytest.mark.parametrize("year", range(1990, 2005))
def test_historical_batch_four_dated_events(year):
    rows = [r for r in DATA["inventory"] if r["year"] == year]
    assert len(rows) == 4
    assert all(r["status"] == "played" and r["source"].endswith(f"year={year}") for r in rows)
    assert all(len(r["main"]["iso_weeks"]) == 2 for r in rows)
    assert all(a["main"]["end"] < b["main"]["start"] for a, b in zip(rows, rows[1:]))


RULES = json.loads((ROOT / "modern_rules_evidence_v1.json").read_text())


@pytest.mark.parametrize("rule", RULES["years"], ids=lambda x: str(x["year"]))
def test_modern_ranking_points(rule):
    assert list(rule["main_points"].values()) == [2000,1300,800,400,200,100,50,10]
    assert list(rule["qualification_points"].values()) == [30,16,8,0]
    assert RULES["nominal"]["ranking_policy"]["main_wild_card_first_round_loss"] == 0
    assert RULES["nominal"]["ranking_policy"]["qualifier_points_additive"] is True
    assert rule["atp_ranking_rulebook"]["sha256"] is None


def test_modern_nominal_geometry_and_bindings():
    n = RULES["nominal"]
    main, q = n["main"], n["qualification"]
    assert main["direct_acceptances"] + main["qualifiers"] + main["wild_cards"] == main["capacity"] == 128
    assert q["direct_acceptances"] + q["wild_cards"] == q["capacity"] == 128
    assert q["sections"] * q["section_size"] == q["capacity"]
    assert q["sections"] == main["qualifiers"]
    assert q["seeds_per_section"] * q["sections"] == 32
    assert RULES["status"] == "source_only_not_runtime_import"
    draws = {e["occurrence_id"]: e for e in DRAW_EVIDENCE["editions"]}
    assert len(draws) == len(RULES["edition_bindings"]) == 8
    assert set(draws) == {e["occurrence_id"] for e in DATA["editions"]}
    for b in RULES["edition_bindings"]:
        draw = draws[b["draw_evidence_id"]]
        assert b["occurrence_id"] == draw["occurrence_id"]
        assert b["rule_year"] == int(b["occurrence_id"].split("_")[1])
        assert b["observed_main_lucky_losers"] == len(draw["main"]["slots"]["lucky_loser"])
        assert b["qualification_marker_audit"] == ("complete" if "observed_slots" in draw["qualification"] else "incomplete")
        assert b["profile_status"] == "source_evidence_only_not_imported"


def test_no_fixed_qualifying_feeder_claim():
    assert "after qualifying concludes" in RULES["nominal"]["qualification_winner_assignment"]
    assert any("fixed feeder" in s for s in RULES["unresolved_runtime"])


@pytest.mark.parametrize("year", [y for y in range(2005, 2026) if y != 2020])
def test_completed_historical_year_coverage(year):
    rows = [r for r in DATA["inventory"] if r["year"] == year]
    assert len(rows) == 4
    assert all(r["status"] == "played" for r in rows)
    ordered = sorted(rows, key=lambda r: r["main"]["start"])
    assert all(a["main"]["end"] < b["main"]["start"] for a, b in zip(ordered, ordered[1:]))


def test_2020_actual_archive_order_and_cancellation():
    rows = [r for r in DATA["inventory"] if r["year"] == 2020]
    played = sorted((r for r in rows if r["status"] == "played"), key=lambda r: r["main"]["start"])
    assert [r["series_id"] for r in played] == [
        "grand_slam_australian_open", "grand_slam_us_open", "grand_slam_roland_garros"]
    assert len([r for r in rows if r["status"] == "cancelled"]) == 1
    assert played[-1]["main"]["start"] == "2020-09-27"


@pytest.mark.parametrize("year", range(2008, 2013))
def test_us_open_monday_final_distinct_from_archive(year):
    r = next(r for r in DATA["inventory"] if r["occurrence_id"] == f"atp_{year}_grand_slam_us_open")
    e = r["actual_mens_final_evidence"]
    p = e["actual_window_projection"]
    check_phase(p)
    assert date.fromisoformat(e["date"]) - date.fromisoformat(r["main"]["end"]) == timedelta(days=1)
    assert p["start"] == r["main"]["start"] and p["end"] == e["date"]
    assert len(r["main"]["iso_weeks"]) == 2 and len(p["iso_weeks"]) == 3


def test_ao_2020_archive_extra_day():
    r = next(r for r in DATA["inventory"] if r["occurrence_id"] == "atp_2020_grand_slam_australian_open")
    p = r["actual_mens_final_evidence"]["actual_window_projection"]
    check_phase(p)
    assert r["main"]["end"] == "2020-02-03" and p["end"] == "2020-02-02"
    assert len(r["main"]["iso_weeks"]) == 3 and len(p["iso_weeks"]) == 2


@pytest.mark.parametrize("year", [2024, 2025])
def test_roland_garros_indexed_marker_audit_separate_from_final_visual(year):
    q = next(e["qualification"] for e in DRAW_EVIDENCE["editions"]
             if e["occurrence_id"] == f"atp_{year}_grand_slam_roland_garros")
    a = q["indexed_marker_audit"]
    assert a["scope"] == [1, 128]
    assert len(set(a["wild_card_slots"])) == 9
    assert a["seed_positions"] == [p for i in range(16) for p in (8*i+1, 8*i+8)]
    assert not set(a["wild_card_slots"]) & set(a["seed_positions"])
    assert a["seed_count"] == 32 and a["alternate_labels_observed"] == 0
    assert a["report_stage"] == "early_first_round_snapshot_not_final"
    assert "observed_slots" not in q and q["sha256"] is None
