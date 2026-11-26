"""2019 source evidence and minimal production geometry/date reproductions."""
import json
from types import SimpleNamespace

import pytest

from scripts.audit_atp_2019_research import ROOT, audit
from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.atp_knockout_profile import ATPQualificationDateEvidence
from beta_engine.domain.tournaments.fax_reference_bracket_topology import build_knockout_bracket_parts

pytestmark = pytest.mark.pr_critical
ROWS = {r["occurrence_id"]: r for r in json.loads(
    (ROOT / "research_2019/edition_evidence.json").read_text(encoding="utf-8"))["rows"]}


def geometry(key):
    g = ROWS[key]["geometry"]
    return build_knockout_bracket_parts(
        event_id=key, main_entrants=g["main_entrants"],
        qualification_entrants=g["q_entrants"], qualifier_spots=g["q_spots"],
        wild_cards=g["main_wc"], byes=g["main_byes"])


def test_inventory_pinned_and_not_production():
    report = audit()
    assert report["totals"] == {"dated": 2407, "not_held": 24, "profiled": 23}
    assert report["reviewed"] == 4
    assert report["production_profiles_added"] == 0
    assert all(v == "missing_local_bytes" for v in report["external_inputs"].values())


def test_rotterdam_actual_q_bye_rejected_by_production_geometry():
    with pytest.raises(ValueError, match="not divisible into equal Q sections"):
        geometry("atp_2019_rotterdam")


@pytest.mark.parametrize("key", ["atp_2019_cordoba", "atp_2019_montpellier", "atp_2019_sofia"])
def test_compatible_capacity_only(key):
    main, sections = geometry(key)
    assert main.bracket_capacity == 32
    assert main.source_main_entrants == 28
    assert main.unplaced_byes == 4
    assert len(sections) == 4
    assert all(s.source_entrant_count == 4 for s in sections)
    assert main.actual_match_count_if_fully_played + sum(
        s.actual_match_count_if_fully_played for s in sections) == 39


@pytest.mark.parametrize(("key", "iso_weeks"), [
    ("atp_2019_rotterdam", [6]), ("atp_2019_cordoba", [5]),
    ("atp_2019_montpellier", [5, 6]), ("atp_2019_sofia", [5, 6]),
])
@pytest.mark.parametrize(("offset", "year", "shift"), [(1, 2019, 0), (37, 2018, 16)])
def test_actual_q_window_projection_without_claiming_source_validation(key, iso_weeks, offset, year, shift):
    row = ROWS[key]
    # The production projection accepts an evidence-shaped object; this is
    # deliberately NOT an ATPKnockoutProfile nor validated publication evidence.
    evidence = SimpleNamespace(start_date=row["q_start"], end_date=row["q_end"],
                               source_urls=(), published_dates=())
    result = project_qualification_window(RunCalendar(52, offset, year, 2),
                                         SimpleNamespace(qualification_date_evidence=evidence))
    assert [x["year_week"] for x in result["iso_year_weeks"]] == iso_weeks
    assert [x["season_week"] for x in result["run_weeks"]] == [w + shift for w in iso_weeks]
    assert not result["outside_year_weeks"]
    assert result["sporting_execution_ready"] is False


def test_contemporary_post_start_results_not_preplay_publication():
    row = ROWS["atp_2019_sofia"]
    with pytest.raises(ValueError, match="published before play"):
        ATPQualificationDateEvidence.model_validate_json(json.dumps({
            "start_date": row["q_start"], "end_date": row["q_end"],
            "source_urls": ["https://topsport.bg/tennis/vsichki-rezultati-ot-sofia-open-2019.html"],
            "published_dates": ["2019-02-04"],
        }))
