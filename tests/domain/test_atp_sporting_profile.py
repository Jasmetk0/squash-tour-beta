"""Sporting source contracts, exact capacities and independent Run snapshots."""
import json

import pytest

from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package
from beta_engine.domain.tournaments.atp_sporting_profile import ATPSportingProfile

pytestmark = pytest.mark.pr_critical


def source_profile():
    return build_atp_sporting_package().entities[0].payload


def test_finals_points_are_additive_once_and_keep_real_eight_person_structure():
    p = ATPSportingProfile.model_validate_json(json.dumps(source_profile()))
    assert p.group_count * p.group_size == 8
    # Three round-robin wins + semifinal win + final win, not a flat 1500 award.
    assert 3 * p.played_group_win_points + p.knockout_stage_points["champion"] == 1500
    assert p.knockout_stage_points["finalist"] == 400
    assert p.knockout_stage_points["semifinal"] == 0
    assert p.match_best_of == p.knockout_best_of == 5


@pytest.mark.parametrize("patch", [
    {"advancing_per_group": 5},
    {"knockout_crossings": []},
    {"ranked": False},
    {"played_group_win_points": True},
    {"knockout_stage_points": {"champion": 900}},
    {"source_end_date": "2025-11-01"},
    {"source_start_date": "2024-11-09"},
    {"match_best_of": 3, "scoring_policy_id": "tennis_sets"},
])
def test_invalid_source_profile_is_rejected(patch):
    payload = {**source_profile(), **patch}
    with pytest.raises(ValueError):
        ATPSportingProfile.model_validate_json(json.dumps(payload))


def test_source_order_and_fingerprints_are_reproducible():
    assert build_atp_sporting_package() == build_atp_sporting_package()
    assert len(build_atp_sporting_package().entities) == 16


@pytest.mark.parametrize(("occurrence", "start", "end", "ranked", "points"), [
    ("atp_2024_atp_finals", "2024-11-10", "2024-11-17", True, 1500),
    ("atp_2024_next_gen_atp_finals", "2024-12-18", "2024-12-22", False, 0),
])
def test_2024_finals_profile_is_independently_sourced(occurrence, start, end, ranked, points):
    entity = next(e for e in build_atp_sporting_package().entities if e.source_entity_id == occurrence)
    p = ATPSportingProfile.model_validate_json(json.dumps(entity.payload))
    assert (p.source_start_date, p.source_end_date, p.ranked) == (start, end, ranked)
    assert (p.group_count, p.group_size, p.advancing_per_group) == (2, 4, 2)
    assert 3 * p.played_group_win_points + p.knockout_stage_points.get("champion", 0) == points
    assert p.match_best_of == p.knockout_best_of == 5
    assert p.entrant_selection == "admin_selected_no_automatic_race_or_age"
    assert len(p.source_urls) >= 2
