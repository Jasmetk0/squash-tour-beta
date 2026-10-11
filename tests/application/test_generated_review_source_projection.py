"""Regression: the Generator review uses actual saved-cohort player facts, not invented UI values."""
import pytest

from beta_engine.application.run_world_initial_world_service import RunWorldInitialWorldService
from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator
from tests.domain.initial_player_pool_contract_suite import country


pytestmark = pytest.mark.pr_critical


def test_reviewed_initial_world_players_retain_real_opening_age_tier_and_source_ability():
    generated = InitialPlayerPoolGenerator().generate(
        countries=[
            country("BOG", population=9_000_000, system=3, popularity=3, tradition=3),
            country("GER", population=16_000_000, system=4, popularity=4, tradition=4),
        ],
        season="2000/2001", seed=4201, target_pool_size=16,
        min_age=18, max_age=25, dry_run=True,
    )
    assert len(generated.players) == 16
    saved_players = [
        RunWorldInitialWorldService._convert_player(
            player, season="2000/2001", bootstrap_seed=4201,
            source_fingerprint="a" * 64,
        )
        for player in generated.players
    ]
    assert len(saved_players) == len(generated.players)
    assert len({p.player_id for p in saved_players}) == 16
    for original, canonical in zip(generated.players, saved_players):
        # Browser inspector is allowed to show only these actual first-week fields.
        assert canonical.player_id == original.player_id
        assert canonical.country_code == original.country_code
        assert canonical.age_years_at_season_start == original.age_at_generation
        assert canonical.current_ability == original.current_ability
        assert canonical.potential_ability == original.potential_ability
        assert canonical.potential_tier == original.potential_tier
        assert canonical.career_stage == original.career_stage
        assert canonical.ranking_points == 0
        assert canonical.race_points == 0
        assert 18 <= canonical.age_years_at_season_start <= 25
        assert 1 <= canonical.current_ability <= 99
        assert 1 <= canonical.potential_ability <= 99
    replay = InitialPlayerPoolGenerator().generate(
        countries=[
            country("BOG", population=9_000_000, system=3, popularity=3, tradition=3),
            country("GER", population=16_000_000, system=4, popularity=4, tradition=4),
        ],
        season="2000/2001", seed=4201, target_pool_size=16,
        min_age=18, max_age=25, dry_run=True,
    )
    assert replay.players == generated.players
