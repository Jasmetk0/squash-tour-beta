"""Research-only identity and phase checks; no promotion or invented PDF hashes."""
from types import SimpleNamespace

import pytest

from scripts.audit_atp_2019_research import ROOT, load
from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

pytestmark = pytest.mark.pr_critical
RESEARCH = ROOT / "research_2019"
ROWS = load(RESEARCH / "february_secondary_evidence.json")["rows"]


def test_lineage_followup_covers_all_seven_without_promoting_source():
    original = load(RESEARCH / "identity_crosswalk.json")
    candidates = {r["occurrence_id"]: r["atp_id"] for r in original["rows"]
                  if r["identity_state"] == "lineage_review_required"}
    followup = load(RESEARCH / "lineage_followup.json")["rows"]
    assert len(followup) == 7
    assert {r["occurrence_id"]: r["atp_id"] for r in followup} == candidates
    assert all(r["status"] == "lineage_supported_pending_full_source_review" for r in followup)
    assert all(r["profile_status"] == "not_installed" and len(r["sources"]) >= 2 for r in followup)
    assert all(s["sha256"] is None for r in followup for s in r["sources"])
    lyon = {r["occurrence_id"]: r for r in followup}
    assert lyon["atp_2019_lyon"]["atp_id"] == "496"
    assert lyon["atp_2019_lyon_old"]["atp_id"] == "7694"


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["occurrence_id"])
def test_february_observed_geometry_is_not_a_certified_profile(row):
    g = row["geometry"]
    main, sections = build_knockout_bracket_parts(
        event_id=row["occurrence_id"], main_entrants=g["main_entrants"],
        qualification_entrants=g["q_entrants"], qualifier_spots=g["q_spots"],
        wild_cards=g["main_wc"], byes=g["main_byes"])
    assert main.actual_match_count_if_fully_played == 27
    assert len(sections) == 4
    assert sum(s.actual_match_count_if_fully_played for s in sections) == sum(row["q_round_matches"]) == 12
    assert row["qualifier_winners_in_main"] == 4
    assert row["gaps"] and all(s["sha256"] is None for s in row["sources"])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["occurrence_id"])
def test_same_main_week_does_not_imply_same_q_week(row):
    evidence = SimpleNamespace(start_date=row["observed_q_dates"][0],
                               end_date=row["observed_q_dates"][-1],
                               source_urls=(), published_dates=())
    p = SimpleNamespace(qualification_date_evidence=evidence)
    weeks = [6, 7] if row["observed_overlap"] else [6]
    for offset, year, shift in [(1, 2019, 0), (37, 2018, 16)]:
        plan = project_qualification_window(RunCalendar(52, offset, year, 2), p)
        assert plan["run_weeks"] == [
            {"season_index": 0, "season_week": w + shift} for w in weeks]
        assert not plan["sporting_execution_ready"]


def test_new_york_q_overlap_and_lucky_loser_not_extra_entrant():
    ba, ny = ROWS
    assert ba["geometry"]["main_ll_markers"] == 0
    assert ny["geometry"]["main_ll_markers"] == 1
    assert ny["geometry"]["main_entrants"] == ba["geometry"]["main_entrants"] == 28
    assert ny["observed_q_dates"][-1] == ny["main_start"]
    assert ny["main_first_day_matches"] == 3
