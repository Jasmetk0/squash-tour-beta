import json
import pytest
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, parse_sporting_profile
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile

pytestmark = pytest.mark.pr_critical


def profile(series_id="rotterdam"):
    occurrence_id = series_id if series_id.startswith("atp_") else f"atp_2025_{series_id}"
    entity = next(item for item in build_atp_sporting_package().entities
                  if item.source_entity_id == occurrence_id)
    return parse_sporting_profile(entity.payload)


@pytest.mark.parametrize(("series_id", "wild_cards", "q_start", "q_end"), [
    ("rotterdam", 4, "2025-02-01", "2025-02-02"),
    ("dallas", 3, "2025-02-01", "2025-02-02"),
    ("munich", 3, "2025-04-12", "2025-04-13"),
    ("vienna", 3, "2025-10-18", "2025-10-19"),
    ("atp_2025_doha", 3, "2025-02-15", "2025-02-16"),
    ("atp_2025_dubai", 3, "2025-02-22", "2025-02-23"),
    ("atp_2025_halle", 3, "2025-06-14", "2025-06-15"),
    ("atp_2024_dubai", 3, "2024-02-24", "2024-02-25"),
    ("atp_2024_halle", 3, "2024-06-15", "2024-06-16"),
    ("atp_2025_queens_club", 3, "2025-06-14", "2025-06-15"),
])
def test_verified_atp_500_keeps_full_main_and_four_independent_q_sections(series_id, wild_cards, q_start, q_end):
    p = profile(series_id)
    g = p.geometry()
    assert p.main_entrants == 32 and p.qualification_entrants == 16
    assert p.qualifier_spots == 4 and p.seeds_count == 8 and p.byes == 0
    assert p.main_points == {'champion': 500, 'finalist': 330, 'semifinal': 200,
                             'quarterfinal': 100, 'round_of_16': 50, 'round_of_32': 0}
    assert p.qualification_points == {'qualifier': 25, 'round_2_loss': 13, 'round_1_loss': 0}
    assert g['main']['direct_main_slots'] == 28 - wild_cards
    assert g['main']['wild_card_slots'] == wild_cards
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
    assert p.qualification_date_status == 'verified'
    assert p.qualification_date_evidence.start_date == q_start
    assert p.qualification_date_evidence.end_date == q_end
    assert profile(series_id).geometry() == g


@pytest.mark.parametrize('patch', [
    {'qualification_entrants': 15}, {'qualifier_spots': 0}, {'wild_cards': 29},
    {'byes': 1}, {'seeds_count': 33}, {'main_entrants': True},
    {'main_points': {'champion':500}}, {'qualification_points': {'qualifier':25}},
    {'source_pdf_sha256': {}}, {'qualification_date_status':'not_verified'},
    {'qualification_date_evidence': None},
])
def test_invalid_knockout_configuration_cannot_become_a_ready_profile(patch):
    with pytest.raises(ValueError):
        ATPKnockoutProfile.model_validate_json(json.dumps({**profile().model_dump(mode='json'), **patch}))


@pytest.mark.parametrize(("year", "q_start", "q_end"), [
    (2024, "2024-06-08", "2024-06-09"),
    (2025, "2025-06-07", "2025-06-08"),
])
def test_atp_250_28_player_geometry_counts_byes_not_matches(year, q_start, q_end):
    p = profile(f"atp_{year}_stuttgart")
    g = p.geometry()
    assert p.category_id == "atp_250"
    assert (p.main_entrants, p.qualification_entrants, p.qualifier_spots) == (28, 16, 4)
    assert (p.seeds_count, p.wild_cards, p.byes) == (8, 3, 4)
    assert g["main"]["bracket_capacity"] == 32
    assert g["main"]["unplaced_byes"] == 4
    assert g["main"]["direct_main_slots"] == 21
    assert len(g["main"]["nodes"]) == 31
    assert len(g["qualification_sections"]) == 4
    assert all(len(s["nodes"]) == 3 and s["unplaced_byes"] == 0
               for s in g["qualification_sections"])
    assert g["actual_match_count"] == 39
    assert p.main_points == {"champion": 250, "finalist": 165, "semifinal": 100,
                             "quarterfinal": 50, "round_of_16": 25, "round_of_32": 0}
    assert p.qualification_points == {"qualifier": 13, "round_2_loss": 7, "round_1_loss": 0}
    assert (p.qualification_date_evidence.start_date, p.qualification_date_evidence.end_date) == (q_start, q_end)
    assert not g["sporting_execution_ready"]
    with pytest.raises(ValueError):
        ATPKnockoutProfile.model_validate_json(json.dumps({**p.model_dump(mode="json"), "byes": 0}))
