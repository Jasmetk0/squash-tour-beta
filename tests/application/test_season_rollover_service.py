from __future__ import annotations

from beta_engine.application.careers import SeasonRolloverService
from beta_engine.core import DeterministicRng
from beta_engine.domain.careers import CareerProgressionEngine, SeasonHealthInput
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.domain.rankings import CompletedTournamentPointsInput


def _player(player_id: str, recovery: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="ENG",
        technique=72,
        movement=72,
        physical=72,
        mental=72,
        consistency=72,
        clutch=72,
        recovery=recovery,
        play_style="counterpuncher",
        archetype="balanced",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.6,
            schedule_aggression=0.55,
            injury_proneness=0.3,
            resilience=0.68,
        ),
    )


def _completed_tournament(player_a: str, player_b: str) -> CompletedTournamentPointsInput:
    return CompletedTournamentPointsInput(
        event_id="EVT-01",
        season=2027,
        week=10,
        template_id="WORLD_1000",
        point_distribution_ref="WORLD_1000",
        placements=[],
        rounds=[
            {
                "draw_type": "MAIN",
                "round_number": 1,
                "matches": [
                    {
                        "disposition": "PLAYED",
                        "top_player_id": player_a,
                        "bottom_player_id": player_b,
                        "loser_player_id": player_b,
                        "match_result": {"termination_reason": "RETIREMENT"},
                    }
                ],
            }
        ],
    )


def test_rollover_service_is_deterministic_for_same_seed_and_inputs() -> None:
    players = [_player("P-A", 78), _player("P-B", 65)]
    completed = [_completed_tournament("P-A", "P-B")]

    service_a = SeasonRolloverService(progression_engine=CareerProgressionEngine(rng=DeterministicRng(8080)))
    service_b = SeasonRolloverService(progression_engine=CareerProgressionEngine(rng=DeterministicRng(8080)))

    rollover_a = service_a.rollover(season=2027, players=players, completed_tournaments=completed)
    rollover_b = service_b.rollover(season=2027, players=players, completed_tournaments=completed)

    assert rollover_a.model_dump() == rollover_b.model_dump()


def test_rollover_service_derives_health_carryover_from_completed_tournament_workload() -> None:
    players = [_player("P-A", 82), _player("P-B", 60), _player("P-C", 73)]
    completed = [_completed_tournament("P-A", "P-B")]

    service = SeasonRolloverService(progression_engine=CareerProgressionEngine(rng=DeterministicRng(9090)))
    rollover = service.rollover(season=2027, players=players, completed_tournaments=completed)

    transition_by_id = {transition.player_id: transition for transition in rollover.transitions}
    p_b_health = transition_by_id["P-B"].season_health_input
    p_c_health = transition_by_id["P-C"].season_health_input

    assert p_b_health.injury_events == 1
    assert p_b_health.fatigue_load > p_c_health.fatigue_load
    assert p_b_health.wear_load > p_c_health.wear_load


def test_explicit_health_inputs_override_derived_values() -> None:
    players = [_player("P-A", 80)]
    completed = [_completed_tournament("P-A", "P-A")]
    explicit = {"P-A": SeasonHealthInput(fatigue_load=0.0, wear_load=0.0, injury_events=0)}

    service = SeasonRolloverService(progression_engine=CareerProgressionEngine(rng=DeterministicRng(10090)))
    rollover = service.rollover(
        season=2027,
        players=players,
        completed_tournaments=completed,
        health_inputs_by_player_id=explicit,
    )

    assert rollover.transitions[0].season_health_input == explicit["P-A"]
