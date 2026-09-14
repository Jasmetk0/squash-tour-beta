"""Canonical sporting-state and deterministic development contract tests."""

import pytest
from pydantic import ValidationError

from beta_engine.domain.players.attribute_catalog import (
    ATTRIBUTE_GROUPS,
    CANONICAL_PLAYER_ATTRIBUTES,
)
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    DevelopmentTiming,
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
    PlayerSportingWeekState,
    between_week_state_update,
    weekly_player_development_update,
)
from beta_engine.domain.rankings.official import RankingWeek


def record(
    player_id="p1",
    *,
    timing: DevelopmentTiming = "Standard",
    value=100,
    potential=90,
):
    return PlayerSportingRecord(
        player_id=player_id,
        attributes={name: value for name in CANONICAL_PLAYER_ATTRIBUTES},
        potential_ovr=potential,
        potential_identity=f"potential:{player_id}",
        potential_provenance="test creation provenance",
        development_timing=timing,
        current_form=120,
        long_term_form_norm=100,
        match_sharpness=80,
        long_term_fatigue=30,
    )


def state(players, *, policy=None):
    return PlayerSportingWeekState(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        players=tuple(sorted(players, key=lambda p: p.player_id)),
        policy=policy or PlayerDevelopmentPolicy(),
        completed_context_fingerprint="bootstrap",
        source_initial_world_fingerprint="world-fingerprint",
        stage_provenance="test bootstrap",
    )


def develop(value, ages):
    context = CompletedWeekSportingContext()
    return weekly_player_development_update(
        value,
        target=RankingWeek(season_index=0, week=2),
        player_ages=ages,
        context=context,
    )


def test_catalog_is_exactly_master_57_and_validation_is_closed():
    assert len(ATTRIBUTE_GROUPS) == 6
    assert len(CANONICAL_PLAYER_ATTRIBUTES) == 57
    with pytest.raises(ValidationError, match="canonical 57"):
        record().model_copy(update={"attributes": {"Forehand": 100}}).model_validate(
            record().model_dump() | {"attributes": {"Forehand": 100}}
        )
    with pytest.raises(ValidationError, match="0 through 200"):
        PlayerSportingRecord.model_validate(
            record().model_dump()
            | {"attributes": dict(record().attributes) | {"Forehand": 201}}
        )


def test_development_timing_changes_calculation_age_not_potential():
    policy = PlayerDevelopmentPolicy(
        weekly_change_basis_points=10000,
        form_influence_basis_points=0,
        growth_end_age=27,
        physical_decline_age=30,
        other_decline_age=34,
    )
    players = [
        record("early", timing="Early Bloomer"),
        record("standard"),
        record("late", timing="Late Bloomer"),
    ]
    result = develop(state(players, policy=policy), {p.player_id: 29 for p in players})
    by_id = {player.player_id: player for player in result.players}
    # shifted ages are 32/29/26: early physical declines; late still grows.
    assert by_id["early"].attributes["Speed"] == 99
    assert by_id["standard"].attributes["Speed"] == 100
    assert by_id["late"].attributes["Speed"] == 101
    assert {player.potential_ovr for player in result.players} == {90}


def test_potential_is_soft_not_attribute_cap_and_absolute_cap_is_200():
    policy = PlayerDevelopmentPolicy(
        weekly_change_basis_points=10000, form_influence_basis_points=0
    )
    result = develop(
        state([record(value=199, potential=80)], policy=policy), {"p1": 20}
    )
    player = result.players[0]
    assert player.ovr == 200 > player.potential_ovr
    assert max(player.attributes.values()) == 200
    assert player.potential_ovr == 80


def test_order_independence_and_completed_context_provenance():
    policy = PlayerDevelopmentPolicy(weekly_change_basis_points=5000)
    a, b = record("a"), record("b")
    first = develop(state([a, b], policy=policy), {"a": 20, "b": 35})
    # Construction canonicalizes input; calculations and fingerprint cannot depend on iteration.
    second = develop(state([b, a], policy=policy), {"b": 35, "a": 20})
    assert first == second
    assert first.fingerprint == second.fingerprint


def test_development_reads_pre_regression_form_then_between_week_updates_state():
    policy = PlayerDevelopmentPolicy(
        weekly_change_basis_points=0,
        form_influence_basis_points=1000,
        form_regression_divisor=4,
        inactive_sharpness_decay=3,
        fatigue_recovery=7,
    )
    predecessor = state([record()], policy=policy)
    developed = develop(predecessor, {"p1": 20})
    # High completed-week Form makes the deterministic threshold certain.
    assert developed.players[0].attributes["Forehand"] == 101
    assert developed.players[0].current_form == 120
    final = between_week_state_update(developed, context=CompletedWeekSportingContext())
    assert final.players[0].current_form == 115
    assert final.players[0].match_sharpness == 77
    assert final.players[0].long_term_fatigue == 23


def test_policy_boundary_is_historical_and_completed_week_owned():
    policy_a = PlayerDevelopmentPolicy(
        policy_id="A", weekly_change_basis_points=10000, form_influence_basis_points=0
    )
    week1 = state([record()], policy=policy_a)
    week2 = between_week_state_update(
        develop(week1, {"p1": 20}), context=CompletedWeekSportingContext()
    )
    fingerprint_a = week2.fingerprint
    policy_b = policy_a.model_copy(
        update={"policy_id": "B", "weekly_change_basis_points": 0}
    )
    week2_with_b = week2.model_copy(update={"policy": policy_b})
    week3 = weekly_player_development_update(
        week2_with_b,
        target=RankingWeek(season_index=0, week=3),
        player_ages={"p1": 20},
        context=CompletedWeekSportingContext(),
    )
    assert week2.policy.policy_id == "A"
    assert week2.fingerprint == fingerprint_a
    assert week3.policy.policy_id == "B"
    assert week3.players[0].attributes == week2.players[0].attributes
