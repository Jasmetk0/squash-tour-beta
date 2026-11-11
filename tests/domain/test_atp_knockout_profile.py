import json
import pytest
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, parse_sporting_profile
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile

pytestmark = pytest.mark.pr_critical


def profile():
    return parse_sporting_profile(build_atp_sporting_package().entities[2].payload)


def test_verified_rotterdam_keeps_full_main_and_four_independent_q_sections():
    p = profile()
    g = p.geometry()
    assert p.main_entrants == 32 and p.qualification_entrants == 16
    assert g['main']['direct_main_slots'] == 24
    assert g['main']['wild_card_slots'] == 4
    assert len(g['main']['nodes']) == 31
    assert len(g['qualification_sections']) == 4
    assert all(s['source_entrant_count'] == s['bracket_capacity'] == 4 and len(s['nodes']) == 3 for s in g['qualification_sections'])
    assert g['actual_match_count'] == 43
    ids=[n['node_id'] for n in g['main']['nodes']]+[n['node_id'] for s in g['qualification_sections'] for n in s['nodes']]
    assert len(ids) == len(set(ids)) == 43
    assert p.main_points['round_of_32'] == p.qualification_points['round_1_loss'] == 0
    assert p.main_points['champion'] == 500
    assert p.qualification_points['qualifier'] == 25
    assert p.qualification_points['round_2_loss'] == 13
    assert g['sporting_execution_ready'] is False
    assert p.qualification_date_status == 'not_verified'
    assert profile().geometry() == g


@pytest.mark.parametrize('patch', [
    {'qualification_entrants': 15}, {'qualifier_spots': 0}, {'wild_cards': 29},
    {'byes': 1}, {'seeds_count': 33}, {'main_entrants': True},
    {'main_points': {'champion':500}}, {'qualification_points': {'qualifier':25}},
    {'source_pdf_sha256': {}}, {'qualification_date_status':'verified'},
])
def test_invalid_knockout_configuration_cannot_become_a_ready_profile(patch):
    with pytest.raises(ValueError):
        ATPKnockoutProfile.model_validate_json(json.dumps({**profile().model_dump(mode='json'), **patch}))
