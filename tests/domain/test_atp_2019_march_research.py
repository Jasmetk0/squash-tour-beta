"""Research-only March geometry, weather exception and historical point semantics."""
import json
from types import SimpleNamespace
import pytest

from scripts.audit_atp_2019_research import ROOT, load
from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.atp_knockout_profile import ATPQualificationDateEvidence
from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

pytestmark = pytest.mark.pr_critical
RESEARCH = ROOT / "research_2019"
ROWS = load(RESEARCH / "march_research.json")["rows"]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["occurrence_id"])
def test_large_draw_geometry_without_padding_entrants(row):
    g = row["geometry"]
    main, sections = build_knockout_bracket_parts(
        event_id=row["occurrence_id"], main_entrants=g["main_entrants"],
        qualification_entrants=g["q_entrants"], qualifier_spots=g["q_spots"],
        wild_cards=g["main_wc"], byes=g["main_byes"])
    assert main.bracket_capacity == g["main_capacity"]
    assert main.unplaced_byes == g["main_byes"]
    assert len(sections) == g["q_spots"]
    assert all(s.source_entrant_count == 4 and s.unplaced_byes == 0 for s in sections)
    assert main.actual_match_count_if_fully_played == g["main_entrants"] - 1
    assert sum(s.actual_match_count_if_fully_played for s in sections) == sum(row["q_round_nodes"])
    assert row["qualifier_winners_in_main"] == g["q_spots"]
    assert row["gaps"] and all(s["sha256"] is None for s in row["sources"])


def test_acapulco_walkover_and_retirement_are_not_byes():
    a = ROWS[0]
    assert a["q_walkovers"] == a["q_retirements"] == 1
    assert a["geometry"]["q_byes"] == 0
    assert sum(a["q_round_nodes"]) == 12
    assert a["q_nominal_seeds"] == 8 and a["q_seed_markers"] == 7


def test_miami_planned_and_actual_qualification_differ_even_in_same_week():
    m = ROWS[2]
    planned = ATPQualificationDateEvidence.model_validate_json(json.dumps(m["planned_q_window"]))
    assert planned.end_date == m["cancelled_q_day"] == "2019-03-19"
    assert m["actual_q_window"]["end_date"] == m["main_start"] == "2019-03-20"
    assert m["cancelled_q_day"] not in m["observed_q_days"]
    # A valid preplay publication is not proof of actual weather-delayed dates.
    with pytest.raises(ValueError, match="published before play"):
        ATPQualificationDateEvidence.model_validate_json(json.dumps({
            **m["actual_q_window"],
            "source_urls": ["https://www.miamiopen.com/announcements/session-2-cancelled/"],
            "published_dates": ["2019-03-19"]}))
    actual = SimpleNamespace(**m["actual_q_window"], source_urls=(), published_dates=())
    for offset, year, expected in [(1, 2019, 12), (37, 2018, 28)]:
        for evidence in (planned, actual):
            result = project_qualification_window(RunCalendar(52, offset, year, 2),
                        SimpleNamespace(qualification_date_evidence=evidence))
            assert result["run_weeks"] == [{"season_index": 0, "season_week": expected}]
            assert result["sporting_execution_ready"] is False
    assert m["day1_media_notes_ll_estimate"] == 1 and m["main_ll"] == 3


def test_historical_points_exceptions_not_encoded_as_generic_round_award():
    p = load(RESEARCH / "points_source_evidence.json")
    rule = p["rulebook_followup"]
    assert p["rows"]["atp_masters_1000_draw_96"] == [
        1000, 600, 360, 180, 90, 45, 25, 10, 16, None, 8]
    assert rule["rules"]["masters_wildcard_first_round_loss"] == 0
    cases = rule["examples"]
    assert [x["total"] for x in cases] == [10, 10, 0, 26, 20]
    assert all(x["total"] == x["main"] + x["q"] for x in cases)
    assert rule["raw_sha256"] is None
