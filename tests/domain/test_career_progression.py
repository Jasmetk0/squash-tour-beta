from __future__ import annotations

from beta_engine.core import DeterministicRng
from beta_engine.domain.careers import CareerProgressionEngine, SeasonHealthInput
from beta_engine.domain.players import HiddenCareerTraits, Player


def _player(*, player_id: str, age: int, ceiling: int, growth_curve: str, professionalism: float, ambition: float, proneness: float, resilience: float, base: int = 70) -> Player:
    return Player(
        player_id=player_id,
        name=f"Player {player_id}",
        age=age,
        nationality="EGY",
        technique=base,
        movement=base,
        physical=base,
        mental=base,
        consistency=base,
        clutch=base,
        recovery=base,
        play_style="attacking",
        archetype="balanced",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=ceiling,
            growth_curve=growth_curve,
            professionalism=professionalism,
            ambition=ambition,
            travel_tolerance=0.5,
            schedule_aggression=0.5,
            injury_proneness=proneness,
            resilience=resilience,
        ),
    )


def _total_delta(progression: dict) -> int:
    return sum(delta["delta"] for delta in progression["transition"]["development_deltas"])


def test_same_seed_inputs_and_context_produce_same_progression() -> None:
    player = _player(
        player_id="P-001",
        age=22,
        ceiling=95,
        growth_curve="early",
        professionalism=0.82,
        ambition=0.84,
        proneness=0.22,
        resilience=0.78,
    )
    health = SeasonHealthInput(fatigue_load=0.25, wear_load=0.2, injury_events=0)

    engine_a = CareerProgressionEngine(rng=DeterministicRng(1001))
    engine_b = CareerProgressionEngine(rng=DeterministicRng(1001))

    result_a = engine_a.progress_player(from_season=2027, to_season=2028, player=player, health_input=health)
    result_b = engine_b.progress_player(from_season=2027, to_season=2028, player=player, health_input=health)

    assert result_a.model_dump() == result_b.model_dump()


def test_younger_high_potential_players_improve_more_than_older_low_ceiling_group() -> None:
    engine = CareerProgressionEngine(rng=DeterministicRng(2029))

    young_group = [
        _player(
            player_id=f"Y-{index:03d}",
            age=20,
            ceiling=96,
            growth_curve="early",
            professionalism=0.78,
            ambition=0.79,
            proneness=0.2,
            resilience=0.76,
        )
        for index in range(40)
    ]
    old_group = [
        _player(
            player_id=f"O-{index:03d}",
            age=34,
            ceiling=74,
            growth_curve="steady",
            professionalism=0.48,
            ambition=0.44,
            proneness=0.6,
            resilience=0.42,
        )
        for index in range(40)
    ]

    health = SeasonHealthInput(fatigue_load=0.2, wear_load=0.2, injury_events=0)
    young_delta = sum(
        _total_delta(
            engine.progress_player(from_season=2027, to_season=2028, player=player, health_input=health).model_dump()
        )
        for player in young_group
    ) / len(young_group)
    old_delta = sum(
        _total_delta(
            engine.progress_player(from_season=2027, to_season=2028, player=player, health_input=health).model_dump()
        )
        for player in old_group
    ) / len(old_group)

    assert young_delta > old_delta + 3.0


def test_age_curve_and_traits_meaningfully_change_progression_and_readiness() -> None:
    engine = CareerProgressionEngine(rng=DeterministicRng(3030))

    growth_player = _player(
        player_id="P-GROW",
        age=21,
        ceiling=97,
        growth_curve="early",
        professionalism=0.9,
        ambition=0.9,
        proneness=0.15,
        resilience=0.86,
    )
    decline_player = _player(
        player_id="P-DECLINE",
        age=35,
        ceiling=76,
        growth_curve="steady",
        professionalism=0.42,
        ambition=0.4,
        proneness=0.72,
        resilience=0.34,
    )

    low_wear = SeasonHealthInput(fatigue_load=0.1, wear_load=0.1, injury_events=0)
    high_wear = SeasonHealthInput(fatigue_load=0.6, wear_load=0.55, injury_events=1)

    growth = engine.progress_player(from_season=2027, to_season=2028, player=growth_player, health_input=low_wear)
    decline = engine.progress_player(from_season=2027, to_season=2028, player=decline_player, health_input=high_wear)

    assert _total_delta(growth.model_dump()) > 0
    assert _total_delta(decline.model_dump()) < 0
    assert growth.next_state.readiness > decline.next_state.readiness
    assert growth.next_state.carryover_fatigue < decline.next_state.carryover_fatigue


def test_rollover_preserves_player_identity_and_returns_structured_deltas() -> None:
    players = [
        _player(
            player_id="ID-001",
            age=26,
            ceiling=88,
            growth_curve="balanced",
            professionalism=0.67,
            ambition=0.65,
            proneness=0.35,
            resilience=0.62,
        ),
        _player(
            player_id="ID-002",
            age=31,
            ceiling=82,
            growth_curve="steady",
            professionalism=0.61,
            ambition=0.59,
            proneness=0.44,
            resilience=0.57,
        ),
    ]

    engine = CareerProgressionEngine(rng=DeterministicRng(4040))
    rollover = engine.rollover_season(season=2027, players=players)

    assert [p.player_id for p in rollover.next_players] == ["ID-001", "ID-002"]
    assert set(rollover.next_states_by_player_id.keys()) == {"ID-001", "ID-002"}
    assert len(rollover.transitions) == 2

    first_transition = rollover.transitions[0]
    assert first_transition.age_after == first_transition.age_before + 1
    assert len(first_transition.development_deltas) == 7
    assert {delta.attribute for delta in first_transition.development_deltas} == {
        "technique",
        "movement",
        "physical",
        "mental",
        "consistency",
        "clutch",
        "recovery",
    }
