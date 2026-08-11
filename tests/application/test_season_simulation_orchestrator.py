from __future__ import annotations
from tests.support.world_packages import load_fax_reference_countries

from beta_engine.application import SeasonSimulationOrchestrator
from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.entries import AcceptanceStatus, EntryTarget
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.points_config import load_points_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_player_identity_config


def _players(seed: int, per_country: int = 24) -> tuple[list[Player], dict[str, Country]]:
    countries = load_fax_reference_countries().countries
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


def test_pre_draw_withdrawal_replacement_fold_updates_effective_main_draw_entries_deterministically() -> None:
    baseline_orchestrator = _orchestrator(seed=7801)
    state = baseline_orchestrator.initialize_state()
    event = state.ordered_events[0]
    template = baseline_orchestrator.templates_by_id[event.template_id]
    acceptance = baseline_orchestrator.entry_engine.build_acceptance_list(
        event=event,
        template=template,
        players=list(baseline_orchestrator.players_by_id.values()),
        countries_by_code=baseline_orchestrator.countries_by_code,
    )
    accepted_main = [
        entry
        for entry in acceptance.main_draw_entries
        if entry.status == AcceptanceStatus.DIRECT_ACCEPTANCE and entry.player_id is not None
    ]
    waitlist_candidate = next(
        entry for entry in acceptance.main_draw_applicants if entry.player_id not in {item.player_id for item in accepted_main}
    )
    placeholder = next(entry for entry in acceptance.main_draw_entries if entry.status == AcceptanceStatus.WITHDRAWAL_PLACEHOLDER)
    withdrawn_entry = accepted_main[0]

    replacement_payload = {
        "withdrawn_player_id": withdrawn_entry.player_id,
        "replacement_player_id": waitlist_candidate.player_id,
        "replacement_source": "main_draw_waitlist",
        "withdrawn_entry_id": withdrawn_entry.entry_id,
        "replacement_entry_id": placeholder.entry_id,
        "notes": None,
    }
    with_replacement = SeasonSimulationOrchestrator.build(
        calendar=baseline_orchestrator.calendar,
        templates=list(baseline_orchestrator.templates_by_id.values()),
        players=list(baseline_orchestrator.players_by_id.values()),
        countries_by_code=baseline_orchestrator.countries_by_code,
        points_by_ref=load_points_config(),
        entry_tuning=load_entry_tuning_config(),
        seed=7801,
        pre_draw_withdrawal_replacements_by_event={event.event_id: [replacement_payload]},
    )

    first = with_replacement.simulate_next_tournament(state=state)
    second = with_replacement.simulate_next_tournament(state=state)
    main_entries = first.tournament_result.acceptance_list.main_draw_entries
    replaced_entry = next(entry for entry in main_entries if entry.entry_id == placeholder.entry_id)
    removed_entry = next(entry for entry in main_entries if entry.entry_id == withdrawn_entry.entry_id)
    assert replaced_entry.player_id == waitlist_candidate.player_id
    assert removed_entry.player_id is None
    assert first.model_dump() == second.model_dump()


def test_late_replacement_fold_applies_after_pre_draw_withdrawal_with_destination_precedence() -> None:
    baseline_orchestrator = _orchestrator(seed=7802)
    state = baseline_orchestrator.initialize_state()
    event = state.ordered_events[0]
    template = baseline_orchestrator.templates_by_id[event.template_id]
    players = list(baseline_orchestrator.players_by_id.values())
    # Country V1's lossless decimal semantics legitimately alter this seeded
    # cohort's acceptance composition. Author one deterministic mid-level
    # candidate so this replacement-precedence test does not depend on a
    # coincidental qualification applicant in the generated reference pool.
    source_player = players[0]
    qualification_player = None
    for sequence in range(1, 101):
        candidate = source_player.model_copy(
            update={
                "player_id": f"qualification-fixture-{sequence}",
                "technique": 45,
                "movement": 45,
                "physical": 45,
                "mental": 45,
                "consistency": 45,
                "clutch": 45,
                "recovery": 45,
            }
        )
        decision = baseline_orchestrator.entry_engine.decide_entry(
            player=candidate,
            player_country=baseline_orchestrator.countries_by_code[candidate.nationality],
            event=event,
            template=template,
            event_rng=baseline_orchestrator.entry_engine.rng.branch(SeedScope.WEEK, event.season, event.week, event.event_id),
        )
        if decision.target == EntryTarget.QUALIFICATION:
            qualification_player = candidate
            break
    assert qualification_player is not None
    players.append(qualification_player)

    acceptance = baseline_orchestrator.entry_engine.build_acceptance_list(
        event=event,
        template=template,
        players=players,
        countries_by_code=baseline_orchestrator.countries_by_code,
    )
    accepted_main = [
        entry for entry in acceptance.main_draw_entries if entry.status == AcceptanceStatus.DIRECT_ACCEPTANCE and entry.player_id is not None
    ]
    pre_draw_candidate = next(entry for entry in acceptance.main_draw_applicants if entry.player_id not in {item.player_id for item in accepted_main})
    qualification_candidate = next(
        entry for entry in acceptance.qualification_applicants if entry.player_id not in {item.player_id for item in accepted_main}
    )
    pre_draw_withdrawn_entry = accepted_main[0]
    late_withdrawn_entry = accepted_main[1]
    withdrawal_placeholder = next(entry for entry in acceptance.main_draw_entries if entry.status == AcceptanceStatus.WITHDRAWAL_PLACEHOLDER)
    late_placeholder = next(entry for entry in acceptance.main_draw_entries if entry.status == AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER)

    with_actions = SeasonSimulationOrchestrator.build(
        calendar=baseline_orchestrator.calendar,
        templates=list(baseline_orchestrator.templates_by_id.values()),
        players=players,
        countries_by_code=baseline_orchestrator.countries_by_code,
        points_by_ref=load_points_config(),
        entry_tuning=load_entry_tuning_config(),
        seed=7802,
        pre_draw_withdrawal_replacements_by_event={
            event.event_id: [
                {
                    "withdrawn_player_id": pre_draw_withdrawn_entry.player_id,
                    "replacement_player_id": pre_draw_candidate.player_id,
                    "replacement_source": "main_draw_waitlist",
                    "withdrawn_entry_id": pre_draw_withdrawn_entry.entry_id,
                    "replacement_entry_id": withdrawal_placeholder.entry_id,
                    "notes": None,
                }
            ]
        },
        late_replacements_by_event={
            event.event_id: [
                {
                    "withdrawn_player_id": late_withdrawn_entry.player_id,
                    "replacement_player_id": qualification_candidate.player_id,
                    "replacement_source": "qualification_waitlist",
                    "withdrawn_entry_id": late_withdrawn_entry.entry_id,
                    "replacement_entry_id": late_placeholder.entry_id,
                    "candidate_slot_index": 1,
                    "notes": None,
                }
            ]
        },
    )
    first = with_actions.simulate_next_tournament(state=state)
    main_entries = first.tournament_result.acceptance_list.main_draw_entries
    assert next(entry for entry in main_entries if entry.entry_id == withdrawal_placeholder.entry_id).player_id == pre_draw_candidate.player_id
    assert next(entry for entry in main_entries if entry.entry_id == late_placeholder.entry_id).player_id == qualification_candidate.player_id
    assert next(entry for entry in main_entries if entry.entry_id == pre_draw_withdrawn_entry.entry_id).player_id is None
    assert next(entry for entry in main_entries if entry.entry_id == late_withdrawn_entry.entry_id).player_id is None
