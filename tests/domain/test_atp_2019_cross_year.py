"""Preserve ATP season identity across civil-year rollover; no production fixes."""
import json
from types import SimpleNamespace

import pytest

from scripts.audit_atp_2019_research import ROOT, load
from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile

pytestmark = pytest.mark.pr_critical
RESEARCH = ROOT / "research_2019"
CASES = load(RESEARCH / "cross_year_evidence.json")["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["occurrence_id"])
def test_current_profile_validator_rejects_prior_civil_year_start(case):
    # Shape-only negative regression: not a historical profile, no fabricated
    # source hashes, no transplanted Q evidence. Exercise the identity guard first.
    source = load(RESEARCH / "profile_candidates.json")["candidates"][0]["profile"]
    p = {**source, "schema_version": "atp_squash_knockout_profile.v1",
         "occurrence_id": case["occurrence_id"],
         "source_start_date": case["canonical_main_start"],
         "source_end_date": case["canonical_main_end"],
         "qualification_date_status": "not_verified", "source_pdf_sha256": {}}
    p.pop("qualification_date_evidence", None)
    with pytest.raises(ValueError, match="Invalid ATP knockout dates or identity"):
        ATPKnockoutProfile.model_validate_json(json.dumps(p))


def test_observed_brisbane_q_days_not_clamped_to_new_year():
    # Projection of observed days only, not a validated full Q window.
    q = CASES[0]["qualification_observations"]
    evidence = SimpleNamespace(start_date=q["observed_mens_q1_date"],
                               end_date=q["observed_mens_q2_date"],
                               source_urls=q["sources"], published_dates=())
    profile = SimpleNamespace(qualification_date_evidence=evidence)
    first = project_qualification_window(RunCalendar(52, 1, 2019, 1), profile)
    assert first["iso_year_weeks"] == [{"calendar_year": 2018, "year_week": 52}]
    assert first["outside_year_weeks"] == [
        {"calendar_year": 2018, "year_week": 52, "reason": "outside_run_horizon"}]
    assert "run_weeks" not in first
    shifted = project_qualification_window(RunCalendar(52, 37, 2018, 2), profile)
    assert shifted["run_weeks"] == [{"season_index": 0, "season_week": 16}]
    assert shifted["sporting_execution_ready"] is False


def test_final_main_draw_preserves_nominal_and_actual_seed_distinction():
    draw = CASES[0]["main_pdf"]
    assert draw["main_capacity"] - len(draw["bye_slots"]) == draw["main_entrants"] == 28
    assert draw["nominal_seeds"] == 8 and draw["actual_seed_markers"] == 7
    assert draw["ll"] == 1 and draw["q_markers"] == 4
    assert draw["sha256"] is None
