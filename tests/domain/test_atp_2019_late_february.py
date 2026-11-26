"""Late February 2019 research evidence and explicit non-publication boundaries."""
import json
from types import SimpleNamespace

import pytest

from scripts.audit_atp_2019_research import ROOT, load
from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.atp_knockout_profile import ATPQualificationDateEvidence
from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

pytestmark = pytest.mark.pr_critical
ROWS = load(ROOT / "research_2019/late_february_evidence.json")["rows"]
BY_ID = {r["occurrence_id"]: r for r in ROWS}


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["occurrence_id"])
def test_observed_round_counts_and_calendar_projection(row):
    g = row["geometry"]
    assert g["main_capacity"] - g["main_byes"] == g["main_entrants"]
    assert g["main_entrants"] - 1 == row["main_expected_match_nodes"]
    assert sum(row["q_round_matches"]) == g["q_entrants"] - g["q_spots"] == 12
    assert row["qualifier_winners_in_main"] == 4
    assert row["gaps"] and all(s["sha256"] is None for s in row["sources"])
    evidence = SimpleNamespace(start_date=row["observed_q_dates"][0],
                               end_date=row["observed_q_dates"][1],
                               source_urls=(), published_dates=())
    weeks = {"atp_2019_rio": [7], "atp_2019_lyon": [7, 8],
             "atp_2019_dubai": [8], "atp_2019_sao_paulo": [8]}[row["occurrence_id"]]
    for offset, year, shift in [(1, 2019, 0), (37, 2018, 16)]:
        plan = project_qualification_window(RunCalendar(52, offset, year, 2),
                SimpleNamespace(qualification_date_evidence=evidence))
        assert plan["run_weeks"] == [
            {"season_index": 0, "season_week": w + shift} for w in weeks]
        assert not plan["sporting_execution_ready"]
    # Only use explicit final WC geometry where observed, not announced Sao Paulo.
    if g["main_wc"] is not None:
        main, sections = build_knockout_bracket_parts(
            event_id=row["occurrence_id"], main_entrants=g["main_entrants"],
            qualification_entrants=g["q_entrants"], qualifier_spots=g["q_spots"],
            wild_cards=g["main_wc"], byes=g["main_byes"])
        assert main.actual_match_count_if_fully_played == row["main_expected_match_nodes"]
        assert sum(s.actual_match_count_if_fully_played for s in sections) == 12


@pytest.mark.parametrize("key", ["atp_2019_rio", "atp_2019_sao_paulo"])
def test_dated_preplay_evidence_shape_passes_actual_validator(key):
    row = BY_ID[key]
    proof = ATPQualificationDateEvidence.model_validate_json(
        json.dumps(row["qualification_date_evidence"]))
    assert [proof.start_date, proof.end_date] == row["observed_q_dates"]
    assert row["gaps"]  # valid date evidence alone does not certify import


def test_marseille_overlap_and_walkover_distinction():
    m = BY_ID["atp_2019_lyon"]
    assert sum(r["q"] for r in m["daily_counts"]) == 12
    assert sum(r["main"] for r in m["daily_counts"]) == 27
    assert [r for r in m["daily_counts"] if r["q"] and r["main"]] == [
        {"date": "2019-02-18", "q": 4, "main": 3}]
    rio = BY_ID["atp_2019_rio"]
    assert rio["main_expected_match_nodes"] == 31 and rio["main_walkovers"] == 1
    assert rio["q_nominal_seed_count"] == 8 and rio["q_seed_markers"] == 7


def test_dubai_exact_event_point_tables_and_three_q_wildcards():
    d = BY_ID["atp_2019_dubai"]
    assert list(d["main_points"].values()) == [500, 300, 180, 90, 45, 0]
    assert d["qualification_points"] == {"qualifier": 20, "round_2_loss": 10, "round_1_loss": 0}
    assert d["q_wc"] == len(d["q_wc_slots"]) == 3
    assert d["main_ll_markers"] == len(d["main_ll_slots"]) == 2
    assert d["qualification_date_evidence"] is None


def test_announced_sao_paulo_wildcards_do_not_certify_final_draw():
    row = BY_ID["atp_2019_sao_paulo"]
    assert row["main_wc_announced"] == 3
    assert row["geometry"]["main_wc"] is None
    assert row["main_seed_markers"] is None
