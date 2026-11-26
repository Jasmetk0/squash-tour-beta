import json
from types import SimpleNamespace

import pytest

from scripts.audit_atp_2019_research import ROOT, load
from scripts.audit_atp_2019_match_crosscheck import compare_match_groups
from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.domain.calendar.run_calendar import RunCalendar

pytestmark = pytest.mark.pr_critical
RESEARCH = ROOT / "research_2019"


def test_guide_63_and_preserve_four_primary_date_conflicts():
    g = load(RESEARCH / "official_finals_guide.json")
    c = load(RESEARCH / "identity_crosswalk.json")
    assert len(g["start_by_occurrence"]) == len(c["rows"]) == 63
    assert g["scope"]["table_rows"] - g["scope"]["excluded_majors"] == 63
    differences = {r["occurrence_id"] for r in c["rows"]
                   if g["start_by_occurrence"][r["occurrence_id"]] != r["external_start"]}
    assert differences == {r["occurrence_id"] for r in g["conflicts"]} == {
        "atp_2019_newport", "atp_2019_washington", "atp_2019_metz", "atp_2019_st_petersburg"}
    assert g["start_by_occurrence"]["atp_2019_tokyo"] == "2019-09-30"
    assert g["source"]["sha256"] is None


def test_montpellier_actual_overlap_counts():
    rows = load(RESEARCH / "edition_evidence.json")["rows"]
    row = next(r for r in rows if r["occurrence_id"] == "atp_2019_montpellier")
    counts = row["daily_match_counts"]
    assert sum(r["qualification"] for r in counts) == 12
    assert sum(r["main"] for r in counts) == 27
    overlap = [r for r in counts if r["qualification"] and r["main"]]
    assert overlap == [{"date": "2019-02-04", "qualification": 4, "main": 3}]
    assert row["profile_status"] == "blocked"


@pytest.mark.parametrize("row", load(RESEARCH / "january_secondary_evidence.json")["rows"],
                         ids=lambda r: r["occurrence_id"])
def test_january_candidate_geometry_and_observed_q_projection(row):
    g = row["geometry"]
    assert g["main_capacity"] - g["main_byes"] == g["main_entrants"] == 28
    assert g["q_entrants"] - g["q_spots"] == sum(row["q_round_matches"]) == 12
    assert row["qualifier_winners_in_main"] == 4
    e = SimpleNamespace(start_date=row["observed_q_dates"][0], end_date=row["observed_q_dates"][-1],
                        source_urls=(), published_dates=())
    p = SimpleNamespace(qualification_date_evidence=e)
    for offset, year, week in [(1, 2019, 1), (37, 2018, 17)]:
        projected = project_qualification_window(RunCalendar(52, offset, year, 2), p)
        assert projected["run_weeks"] == [{"season_index": 0, "season_week": week}]
        assert not projected["sporting_execution_ready"]


def test_sydney_and_auckland_do_not_normalize_seed_and_date_conflicts():
    s, a = load(RESEARCH / "january_secondary_evidence.json")["rows"]
    assert s["geometry"]["main_actual_seed_markers"] == 7
    assert s["geometry"]["main_nominal_seed_count"] == 8
    assert s["main_start"] == "2019-01-06"
    assert a["geometry"]["q_seed_markers"] is None


def test_match_crosscheck_distinguishes_local_id_and_group_rounds():
    header = "tourney_id,tourney_name,tourney_level,tourney_date,draw_size,match_num,round,winner_rank_points,loser_rank_points\n"
    body = "2019-M001,Test,A,20190107,2,1,F,100,50\n"
    body += "".join(f"2019-0605,Finals,F,20191111,8,{i},{round_},100,50\n"
                    for i, round_ in enumerate(["RR"]*12 + ["SF"]*2 + ["F"], 1))
    cross = {"rows": [{"atp_id": "338", "occurrence_id": "sydney", "external_type": "ATP 250",
                       "external_start": "2019-01-06", "advertised_main": 2},
                      {"atp_id": "605", "occurrence_id": "finals", "external_type": "ATP Finals",
                       "external_start": "2019-11-11", "advertised_main": 8}]}
    expected = dict(paired=2, direct_numeric=1, local_id_candidates=1, archive_date_equal=1,
                    archive_date_diff=1, knockout_group_count_matches=1, knockout_group_count_diff=0,
                    group_finals_count_matches=1)
    m = {"crosscheck": {"candidate_local_id_overrides": {"338": "M001"}, "expected": expected}}
    result = compare_match_groups((header + body).encode(), cross, m)
    assert result["counts"] == expected
    assert result["date_differences"] == [{"occurrence_id": "sydney", "archive_start": "2019-01-06",
                                           "match_week_anchor": "2019-01-07"}]
    assert result["production_profiles_certified"] == 0
    with pytest.raises(ValueError, match="Unexpected Finals group structure"):
        compare_match_groups((header + body.replace(",15,F,", ",15,RR,")).encode(), cross, m)
