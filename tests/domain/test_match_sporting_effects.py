"""Provisional match-effect calibration boundaries."""

from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    MatchSportingEffectsPolicy,
    provisional_form_delta,
    provisional_load_deltas,
    project_player,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.domain.players.sporting import PlayerSportingRecord


def test_close_underdog_loss_can_raise_form_and_weak_favorite_win_can_lower_it():
    policy = MatchSportingEffectsPolicy()
    # Point share is authoritative played performance. Win/loss is deliberately absent.
    assert (
        provisional_form_delta(
            expected_point_share=0.30,
            actual_point_share=0.48,
            played_rallies=100,
            policy=policy,
        )
        > 0
    )
    assert (
        provisional_form_delta(
            expected_point_share=0.75,
            actual_point_share=0.52,
            played_rallies=100,
            policy=policy,
        )
        < 0
    )


def test_played_data_weights_form_deterministically():
    policy = MatchSportingEffectsPolicy()
    short = provisional_form_delta(
        expected_point_share=0.3,
        actual_point_share=0.48,
        played_rallies=10,
        policy=policy,
    )
    long = provisional_form_delta(
        expected_point_share=0.3,
        actual_point_share=0.48,
        played_rallies=100,
        policy=policy,
    )
    assert 0 <= short < long
    assert long == provisional_form_delta(
        expected_point_share=0.3,
        actual_point_share=0.48,
        played_rallies=100,
        policy=policy,
    )


def test_sharpness_and_fatigue_respect_authoritative_duration_and_workload():
    policy = MatchSportingEffectsPolicy()
    short = provisional_load_deltas(
        duration_seconds=900, workload_units=30, policy=policy
    )
    long = provisional_load_deltas(
        duration_seconds=5400, workload_units=180, policy=policy
    )
    assert long[0] > short[0] >= 0
    assert long[1] > short[1] >= 0


def test_form_and_sharpness_are_distinct_projected_match_inputs():
    traits = HiddenCareerTraits(
        potential_ceiling=99,
        growth_curve="Standard",
        professionalism=0.5,
        ambition=0.5,
        travel_tolerance=0.5,
        schedule_aggression=0.5,
        injury_proneness=0.1,
        resilience=0.5,
    )
    base = PlayerSportingRecord(
        player_id="p",
        attributes=tuple((name, 100) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=150,
        potential_identity="potential",
        potential_provenance="test",
        development_timing="Standard",
        current_form=110,
        long_term_form_norm=100,
        match_sharpness=40,
        long_term_fatigue=20,
    )
    kwargs = dict(
        source_sporting_fingerprint="sport",
        policy=CanonicalMatchInputProjectionPolicy(),
        profile_source_fingerprint="profile",
        profile_provenance="owned",
        age=25,
        name="Player",
        nationality="CZE",
        play_style="attacking",
        archetype="power",
        hidden_career_traits=traits,
    )
    first = project_player(base, **kwargs)
    second = project_player(base.model_copy(update={"match_sharpness": 80}), **kwargs)
    assert first.form_modifier == second.form_modifier
    assert first.sharpness_modifier != second.sharpness_modifier
    assert first.fingerprint != second.fingerprint
