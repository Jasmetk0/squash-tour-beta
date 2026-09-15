"""Provisional match-effect calibration boundaries."""

from beta_engine.domain.simulation_slots import (
    MatchSportingEffectsPolicy,
    provisional_form_delta,
    provisional_load_deltas,
)


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
