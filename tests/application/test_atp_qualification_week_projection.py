"""Source dates constrain proposed weeks; legacy snapshots keep their bytes."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from beta_engine.application.atp_qualification_week_projection import project_qualification_window
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, parse_sporting_profile
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile

pytestmark = pytest.mark.pr_critical
LEGACY = Path(__file__).parents[1] / 'fixtures/atp/squash_sporting_profiles_source_v2.json'


def profile():
    return parse_sporting_profile(build_atp_sporting_package().entities[2].payload)


def test_old_profile_and_package_fingerprints_remain_exact(tmp_path):
    (tmp_path / 'squash_sporting_profiles_v1.json').write_bytes(LEGACY.read_bytes())
    old = build_atp_sporting_package(tmp_path)
    entity = old.entities[2]
    assert old.source_version == 2
    assert old.source_fingerprint == '3d83008f253510e329525b355ccb3da82e49218e4f5a7a8f5bbc8ae5bdf7a20f'
    assert entity.fingerprint == '284d527e3bddd3f03f0ca86a39aa18ff77ac814aaac7bd8c0cb6a9776035ff39'
    parsed = parse_sporting_profile(entity.payload)
    assert parsed.model_dump(mode='json') == entity.payload
    assert canonical_hash(entity.payload) == 'e779a0ac50c4fda917003751ec07f9ff9e4624246fade4845f7aa526ce21ac7f'
    assert parsed.qualification_date_status == 'not_verified'
    assert project_qualification_window(RunCalendar.earth_default(), parsed) is None
    # New server defaults cannot silently upgrade this old saved payload.
    assert build_atp_sporting_package().source_version == 3
    assert parsed.schema_version.endswith('.v1') and 'qualification_date_evidence' not in entity.payload


@pytest.mark.parametrize(('offset','start','season','week'), [(1,2025,0,5),(37,2024,0,21)])
def test_source_window_maps_to_w5_with_the_actual_run_offset(offset,start,season,week):
    projection = project_qualification_window(RunCalendar(52,offset,start,2),profile())
    assert projection['source_start_date'] == '2025-02-01'
    assert projection['source_end_date'] == '2025-02-02'
    assert projection['iso_year_weeks'] == [{'calendar_year':2025,'year_week':5}]
    assert projection['run_weeks'] == [{'season_index':season,'season_week':week}]
    assert projection['run_ordinals'] == [week-1]
    assert not projection['outside_year_weeks']
    assert projection['sporting_execution_ready'] is False


def test_outside_horizon_never_becomes_a_clipped_phase():
    projection = project_qualification_window(RunCalendar(52,6,2025,1),profile())
    assert projection['source_start_date'] == '2025-02-01'
    assert projection['outside_year_weeks'] == [{'calendar_year':2025,'year_week':5,'reason':'outside_run_horizon'}]
    assert 'run_weeks' not in projection and 'run_ordinals' not in projection


def test_partial_window_and_iso_week_53_remain_explicit_conflicts():
    # A generic sourced phase touching two ISO weeks cannot lose its first one.
    original = profile()
    evidence = original.qualification_date_evidence.model_copy(update={'start_date':'2025-01-31','end_date':'2025-02-03'})
    projection = project_qualification_window(RunCalendar(52,6,2025,1),original.model_copy(update={'qualification_date_evidence':evidence}))
    assert len(projection['iso_year_weeks']) == 2
    assert 'run_ordinals' not in projection
    week53 = SimpleNamespace(qualification_date_evidence=evidence.model_copy(update={'start_date':'2020-12-31','end_date':'2021-01-04'}))
    projection = project_qualification_window(RunCalendar(52,1,2020,2),week53)
    assert projection['outside_year_weeks'][0]['reason'] == 'iso_week_53_not_representable'
    assert projection['iso_year_weeks'] == [{'calendar_year':2020,'year_week':53},{'calendar_year':2021,'year_week':1}]
    assert 'run_weeks' not in projection


@pytest.mark.parametrize('weeks',[61,80])
def test_no_proportional_calendar_conversion(weeks):
    with pytest.raises(ValueError,match='W52'):
        project_qualification_window(RunCalendar(weeks,1,2025,2),profile())


@pytest.mark.parametrize('damage',[
    {'schema_version':'atp_squash_knockout_profile.v1'},
    {'qualification_date_status':'not_verified'},
    {'qualification_date_evidence':None},
])
def test_versions_cannot_claim_evidence_they_do_not_own(damage):
    with pytest.raises(ValueError):
        ATPKnockoutProfile.model_validate_json(json.dumps({**profile().model_dump(mode='json'),**damage}))


@pytest.mark.parametrize('damage',[
    {'start_date':'2025-02-03','end_date':'2025-02-01'},
    {'start_date':'2025-02-30'},
    {'start_date':'20250201'},
    {'end_date':'2025-02-10'},
    {'source_urls':[]},
    {'published_dates':['2025-02-03','2025-01-29']},
    {'published_dates':['2025-01-15']},
    {'published_dates':['20250115','2025-01-29']},
    {'source_urls':['http://example.invalid/source','https://example.invalid/other']},
])
def test_invalid_or_later_published_date_evidence_is_rejected(damage):
    raw = profile().model_dump(mode='json')
    raw['qualification_date_evidence'].update(damage)
    with pytest.raises(ValueError):
        ATPKnockoutProfile.model_validate_json(json.dumps(raw))
