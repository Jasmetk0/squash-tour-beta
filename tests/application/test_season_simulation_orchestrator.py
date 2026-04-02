from __future__ import annotations

from beta_engine.application import SeasonSimulationOrchestrator
from beta_engine.core import DeterministicRng
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.points_config import load_points_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config


def _players(seed: int, per_country: int = 24) -> tuple[list[Player], dict[str, Country]]:
    countries = load_countries_config().countries
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=load_player_identity_config(),
        country_talent_model=CountryTalentModel(),
    )
    players: list[Player] = []
    for country in countries:
        players.extend(generator.generate(country=country, sequence=i + 1) for i in range(per_country))
    return players, {country.code: country for country in countries}


def _orchestrator(seed: int = 6060) -> SeasonSimulationOrchestrator:
    calendar = load_season_calendar()
    templates = load_tournament_templates_config().templates
    players, countries_by_code = _players(seed=99)
    return SeasonSimulationOrchestrator.build(
        calendar=calendar,
        templates=templates,
        players=players,
        countries_by_code=countries_by_code,
        points_by_ref=load_points_config(),
        entry_tuning=load_entry_tuning_config(),
        seed=seed,
    )


def test_same_seed_and_inputs_produce_same_full_season_output() -> None:
    orchestrator_a = _orchestrator(seed=7001)
    orchestrator_b = _orchestrator(seed=7001)

    state_a = orchestrator_a.initialize_state()
    state_b = orchestrator_b.initialize_state()

    result_a = orchestrator_a.simulate_full_season(state=state_a)
    result_b = orchestrator_b.simulate_full_season(state=state_b)

    assert result_a.model_dump() == result_b.model_dump()


def test_simulate_next_tournament_advances_exactly_one_event() -> None:
    orchestrator = _orchestrator(seed=7101)
    state = orchestrator.initialize_state()

    result = orchestrator.simulate_next_tournament(state=state)

    assert result.tournament_result is not None
    assert result.season_state.next_event_index == 1
    assert len(result.season_state.completed_event_ids) == 1
    assert result.season_state.completed_event_ids[0] == result.tournament_result.event.event_id


def test_simulate_next_week_advances_all_events_in_one_week() -> None:
    orchestrator = _orchestrator(seed=7201)
    state = orchestrator.initialize_state()

    expected_first_week = state.ordered_events[0].week
    expected_event_ids = [
        event.event_id
        for event in state.ordered_events
        if event.week == expected_first_week
    ]

    result = orchestrator.simulate_next_week(state=state)

    assert result.weekly_result is not None
    observed_event_ids = [t.event.event_id for t in result.weekly_result.tournaments]
    assert observed_event_ids == expected_event_ids
    assert result.season_state.next_event_index == len(expected_event_ids)


def test_simulate_full_season_processes_remaining_events_in_calendar_order() -> None:
    orchestrator = _orchestrator(seed=7301)
    state = orchestrator.initialize_state()

    first_step = orchestrator.simulate_next_tournament(state=state)
    second_state = first_step.season_state

    full_result = orchestrator.simulate_full_season(state=second_state)

    assert full_result.season_result is not None
    ordered_event_ids = [event.event_id for event in state.ordered_events]
    expected_remaining = ordered_event_ids[1:]
    assert full_result.season_state.completed_event_ids == ordered_event_ids
    observed_remaining = [
        tournament.event.event_id
        for week_result in full_result.season_result.weekly_results
        for tournament in week_result.tournaments
    ]
    assert observed_remaining == expected_remaining


def test_ranking_and_race_snapshots_update_after_processed_events() -> None:
    orchestrator = _orchestrator(seed=7401)
    state = orchestrator.initialize_state()

    first = orchestrator.simulate_next_tournament(state=state)
    second = orchestrator.simulate_next_tournament(state=first.season_state)

    first_ranking = first.season_state.ranking_snapshot
    second_ranking = second.season_state.ranking_snapshot
    first_race = first.season_state.race_snapshot
    second_race = second.season_state.race_snapshot

    assert first_ranking is not None
    assert second_ranking is not None
    assert first_race is not None
    assert second_race is not None

    assert len(second.season_state.completed_tournament_inputs) == 2
    assert second_ranking.report.model_dump() != first_ranking.report.model_dump()
    assert second_race.report.model_dump() != first_race.report.model_dump()


def test_simulate_next_match_progresses_active_tournament_before_completing_event() -> None:
    orchestrator = _orchestrator(seed=7501)
    state = orchestrator.initialize_state()

    first_step = orchestrator.simulate_next_match(state=state)

    assert first_step.tournament_result is not None
    assert first_step.season_state.next_event_index == 0
    assert first_step.season_state.active_tournament is not None
    assert first_step.season_state.active_tournament.revealed_match_count == 1
    assert first_step.season_state.completed_event_ids == []
    assert first_step.tournament_result.ranking_snapshot is None
    assert first_step.tournament_result.race_snapshot is None
    assert first_step.tournament_result.completed_tournament_input is None

    current = first_step.season_state
    while current.active_tournament is not None:
        step = orchestrator.simulate_next_match(state=current)
        current = step.season_state

    assert current.next_event_index == 1
    assert len(current.completed_event_ids) == 1


def test_simulate_next_round_advances_one_round_at_a_time() -> None:
    orchestrator = _orchestrator(seed=7601)
    state = orchestrator.initialize_state()

    first_step = orchestrator.simulate_next_round(state=state)
    assert first_step.season_state.active_tournament is not None
    revealed_after_first = first_step.season_state.active_tournament.revealed_match_count
    assert first_step.tournament_result.ranking_snapshot is None
    assert first_step.tournament_result.race_snapshot is None
    assert first_step.tournament_result.completed_tournament_input is None

    second_step = orchestrator.simulate_next_round(state=first_step.season_state)
    assert second_step.season_state.active_tournament is not None
    revealed_after_second = second_step.season_state.active_tournament.revealed_match_count
    assert revealed_after_second > revealed_after_first


def test_partial_simulation_hides_post_event_artifacts_until_completion() -> None:
    orchestrator = _orchestrator(seed=7650)
    state = orchestrator.initialize_state()

    partial = orchestrator.simulate_next_match(state=state)
    assert partial.tournament_result is not None
    assert partial.tournament_result.ranking_snapshot is None
    assert partial.tournament_result.race_snapshot is None
    assert partial.tournament_result.completed_tournament_input is None

    current = partial.season_state
    final_step = partial
    while current.active_tournament is not None:
        final_step = orchestrator.simulate_next_match(state=current)
        current = final_step.season_state

    assert final_step.tournament_result is not None
    assert final_step.tournament_result.ranking_snapshot is not None
    assert final_step.tournament_result.race_snapshot is not None
    assert final_step.tournament_result.completed_tournament_input is not None


def test_match_and_round_progression_are_deterministic_for_same_seed() -> None:
    orchestrator_a = _orchestrator(seed=7701)
    orchestrator_b = _orchestrator(seed=7701)
    state_a = orchestrator_a.initialize_state()
    state_b = orchestrator_b.initialize_state()

    steps_a = [orchestrator_a.simulate_next_match(state=state_a)]
    steps_b = [orchestrator_b.simulate_next_match(state=state_b)]
    assert steps_a[0].model_dump() == steps_b[0].model_dump()

    step_a_round = orchestrator_a.simulate_next_round(state=steps_a[0].season_state)
    step_b_round = orchestrator_b.simulate_next_round(state=steps_b[0].season_state)
    assert step_a_round.model_dump() == step_b_round.model_dump()
