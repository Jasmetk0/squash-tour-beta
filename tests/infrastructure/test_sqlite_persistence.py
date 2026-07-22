from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from beta_engine.application.persistence import SimulationPersistenceService
from beta_engine.application.finals_service import FinalsOrchestrationService
from beta_engine.application.rollover_service import SeasonRolloverOrchestrationService
from beta_engine.application.services import SeasonSimulationOrchestrator
from beta_engine.application.careers import SeasonRolloverService
from beta_engine.core import DeterministicRng
from beta_engine.domain.careers import CareerProgressionEngine
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.infrastructure.db import DatabaseSettings, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import PersistedSnapshotRecord, SimulationPersistenceRepository
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


def _repository(tmp_path) -> SimulationPersistenceRepository:
    db_file = tmp_path / "sim_state.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    return SimulationPersistenceRepository(engine=engine, session_factory=session_factory)


def _snapshot_summary(records: list[PersistedSnapshotRecord]) -> list[tuple[int, str, str | None, int, int]]:
    return [
        (record.snapshot_sequence, record.snapshot_kind, record.source_event_id, record.as_of_season, record.as_of_week)
        for record in records
    ]


def test_database_bootstrap_creates_required_tables(tmp_path) -> None:
    repository = _repository(tmp_path)

    repository.bootstrap_schema()

    assert repository.list_table_names() == [
        "admin_actions",
        "branch_checkpoints",
        "branch_fork_commands",
        "branch_states",
        "completed_event_metadata",
        "completed_events",
        "completed_tournament_inputs",
        "finals_qualification",
        "finals_results",
        "legacy_simulation_run_mappings",
        "next_season_players",
        "official_branch_selection_commands",
        "player_season_transitions",
        "race_snapshots",
        "ranking_snapshots",
        "run_branches",
        "run_generated_player_provenance",
        "run_prospects",
        "run_talent_country_allocations",
        "run_talent_plans",
        "runs",
        "season_rollovers",
        "season_state",
        "simulation_runs",
    ]




def test_database_bootstrap_ignores_benign_already_exists_operational_error_and_runs_compatibility(
    tmp_path, monkeypatch
) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()

    compatibility_called = {"value": False}

    def _raise_benign(*_args, **_kwargs) -> None:
        raise OperationalError(
            statement="CREATE TABLE season_state",
            params={},
            orig=RuntimeError("table season_state already exists"),
        )

    def _record_compatibility() -> None:
        compatibility_called["value"] = True

    monkeypatch.setattr("beta_engine.infrastructure.db.repositories.Base.metadata.create_all", _raise_benign)
    monkeypatch.setattr(repository, "_ensure_schema_compatibility", _record_compatibility)

    repository.bootstrap_schema()

    assert compatibility_called["value"] is True
    assert "season_state" in repository.list_table_names()


def test_database_bootstrap_reraises_non_benign_operational_error(tmp_path, monkeypatch) -> None:
    repository = _repository(tmp_path)

    def _raise_non_benign(*_args, **_kwargs) -> None:
        raise OperationalError(
            statement="CREATE TABLE season_state",
            params={},
            orig=RuntimeError("disk I/O error"),
        )

    monkeypatch.setattr("beta_engine.infrastructure.db.repositories.Base.metadata.create_all", _raise_non_benign)

    with pytest.raises(OperationalError):
        repository.bootstrap_schema()


def test_database_bootstrap_is_idempotent_for_existing_sqlite_schema(tmp_path) -> None:
    db_file = tmp_path / "sim_state.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))

    repository.bootstrap_schema()
    repository.bootstrap_schema()

    second_engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    second_repository = SimulationPersistenceRepository(
        engine=second_engine,
        session_factory=create_session_factory(second_engine),
    )
    second_repository.bootstrap_schema()

    assert "season_state" in repository.list_table_names()
    with second_engine.begin() as connection:
        columns = [row[1] for row in connection.execute(text("PRAGMA table_info('season_state')")).all()]
    assert "active_tournament_json" in columns


def test_admin_wildcard_actions_are_append_only_and_replayable(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()

    repository.append_admin_action(
        run_id="run-admin",
        event_id="EVENT-1",
        action_kind="assign_wildcards",
        payload={"assignments": [{"slot_index": 1, "player_id": "P-A"}]},
    )
    repository.append_admin_action(
        run_id="run-admin",
        event_id="EVENT-1",
        action_kind="assign_wildcards",
        payload={"assignments": [{"slot_index": 1, "player_id": "P-B"}, {"slot_index": 2, "player_id": "P-C"}]},
    )

    actions = repository.list_admin_actions(run_id="run-admin", event_id="EVENT-1", action_kind="assign_wildcards")
    assert [action.action_sequence for action in actions] == [1, 2]
    assert repository.get_wildcard_assignments_for_event(run_id="run-admin", event_id="EVENT-1") == {1: "P-B", 2: "P-C"}


def test_admin_pre_draw_withdrawal_actions_are_append_only_and_replayable(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()

    repository.append_admin_action(
        run_id="run-admin",
        event_id="EVENT-2",
        action_kind="pre_draw_withdrawal_replacement",
        payload={
            "withdrawn_player_id": "P-A",
            "replacement_player_id": "P-B",
            "replacement_source": "main_draw_waitlist",
            "withdrawn_entry_id": "EVENT-2:P-A:MAIN",
            "replacement_entry_id": "EVENT-2:WITHDRAWAL_PLACEHOLDER:1",
            "notes": None,
        },
    )
    repository.append_admin_action(
        run_id="run-admin",
        event_id="EVENT-2",
        action_kind="pre_draw_withdrawal_replacement",
        payload={
            "withdrawn_player_id": "P-C",
            "replacement_player_id": "P-D",
            "replacement_source": "qualification_waitlist",
            "withdrawn_entry_id": "EVENT-2:P-C:MAIN",
            "replacement_entry_id": "EVENT-2:P-C:MAIN",
            "notes": None,
        },
    )

    actions = repository.list_admin_actions(
        run_id="run-admin",
        event_id="EVENT-2",
        action_kind="pre_draw_withdrawal_replacement",
    )
    assert [action.action_sequence for action in actions] == [1, 2]
    assert repository.get_pre_draw_withdrawal_replacements_for_event(run_id="run-admin", event_id="EVENT-2") == [
        {
            "withdrawn_player_id": "P-A",
            "replacement_player_id": "P-B",
            "replacement_source": "main_draw_waitlist",
            "withdrawn_entry_id": "EVENT-2:P-A:MAIN",
            "replacement_entry_id": "EVENT-2:WITHDRAWAL_PLACEHOLDER:1",
            "notes": None,
        },
        {
            "withdrawn_player_id": "P-C",
            "replacement_player_id": "P-D",
            "replacement_source": "qualification_waitlist",
            "withdrawn_entry_id": "EVENT-2:P-C:MAIN",
            "replacement_entry_id": "EVENT-2:P-C:MAIN",
            "notes": None,
        },
    ]


def test_admin_late_replacement_actions_are_append_only_and_replayable(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()

    repository.append_admin_action(
        run_id="run-admin",
        event_id="EVENT-3",
        action_kind="late_replacement_lucky_loser",
        payload={
            "withdrawn_player_id": "P-A",
            "replacement_player_id": "P-B",
            "replacement_source": "qualification_waitlist",
            "withdrawn_entry_id": "EVENT-3:P-A:MAIN",
            "replacement_entry_id": "EVENT-3:LATE_REPLACEMENT_PLACEHOLDER:1",
            "candidate_slot_index": 1,
            "notes": None,
        },
    )
    repository.append_admin_action(
        run_id="run-admin",
        event_id="EVENT-3",
        action_kind="late_replacement_lucky_loser",
        payload={
            "withdrawn_player_id": "P-C",
            "replacement_player_id": "P-D",
            "replacement_source": "main_draw_waitlist",
            "withdrawn_entry_id": "EVENT-3:P-C:MAIN",
            "replacement_entry_id": "EVENT-3:WITHDRAWAL_PLACEHOLDER:1",
            "candidate_slot_index": 2,
            "notes": None,
        },
    )

    actions = repository.list_admin_actions(
        run_id="run-admin",
        event_id="EVENT-3",
        action_kind="late_replacement_lucky_loser",
    )
    assert [action.action_sequence for action in actions] == [1, 2]
    assert repository.get_late_replacements_for_event(run_id="run-admin", event_id="EVENT-3") == [
        {
            "withdrawn_player_id": "P-A",
            "replacement_player_id": "P-B",
            "replacement_source": "qualification_waitlist",
            "withdrawn_entry_id": "EVENT-3:P-A:MAIN",
            "replacement_entry_id": "EVENT-3:LATE_REPLACEMENT_PLACEHOLDER:1",
            "candidate_slot_index": 1,
            "notes": None,
        },
        {
            "withdrawn_player_id": "P-C",
            "replacement_player_id": "P-D",
            "replacement_source": "main_draw_waitlist",
            "withdrawn_entry_id": "EVENT-3:P-C:MAIN",
            "replacement_entry_id": "EVENT-3:WITHDRAWAL_PLACEHOLDER:1",
            "candidate_slot_index": 2,
            "notes": None,
        },
    ]


def test_simulation_step_state_can_be_saved_and_reloaded(tmp_path) -> None:
    orchestrator = _orchestrator(seed=8801)
    first_step = orchestrator.simulate_next_week(state=orchestrator.initialize_state())

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-001", season=first_step.season_state.season, seed=8801)

    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=first_step)

    loaded = repository.load_season_state(run_id=run.run_id)

    assert loaded is not None
    assert loaded.model_dump() == first_step.season_state.model_dump()


def test_simulate_next_tournament_persists_same_week_event_snapshots_without_overwrite(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9001)
    initial = orchestrator.initialize_state()

    first = orchestrator.simulate_next_tournament(state=initial)
    second = orchestrator.simulate_next_tournament(state=first.season_state)

    assert first.tournament_result is not None
    assert second.tournament_result is not None
    assert first.tournament_result.event.week == second.tournament_result.event.week

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-tournament", season=initial.season, seed=9001)

    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=first)
    persistence.persist_step(run_id=run.run_id, step=second)

    ranking_records = repository.list_ranking_snapshot_records(run_id=run.run_id)
    race_records = repository.list_race_snapshot_records(run_id=run.run_id)

    assert _snapshot_summary(ranking_records) == [
        (1, "tournament", first.tournament_result.event.event_id, first.tournament_result.event.season, first.tournament_result.event.week),
        (11, "tournament", second.tournament_result.event.event_id, second.tournament_result.event.season, second.tournament_result.event.week),
    ]
    assert _snapshot_summary(race_records) == [
        (1, "tournament", first.tournament_result.event.event_id, first.tournament_result.event.season, first.tournament_result.event.week),
        (11, "tournament", second.tournament_result.event.event_id, second.tournament_result.event.season, second.tournament_result.event.week),
    ]


def test_simulate_next_week_persists_tournament_and_week_snapshots_deterministically(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9101)
    state = orchestrator.initialize_state()
    week_one = orchestrator.simulate_next_week(state=state)
    assert week_one.weekly_result is not None

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-week", season=state.season, seed=9101)

    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=week_one)

    ranking_records = repository.list_ranking_snapshot_records(run_id=run.run_id)
    race_records = repository.list_race_snapshot_records(run_id=run.run_id)

    expected_tournament_records = [
        (index * 10 + 1, "tournament", tournament.event.event_id, tournament.event.season, tournament.event.week)
        for index, tournament in enumerate(week_one.weekly_result.tournaments)
    ]
    expected_week_record = (
        (len(week_one.weekly_result.tournaments) - 1) * 10 + 9,
        "week",
        week_one.weekly_result.tournaments[-1].event.event_id,
        week_one.weekly_result.season,
        week_one.weekly_result.week,
    )

    assert _snapshot_summary(ranking_records) == [*expected_tournament_records, expected_week_record]
    assert _snapshot_summary(race_records) == [*expected_tournament_records, expected_week_record]


def test_completed_event_order_and_reloaded_state_remain_deterministic_across_weeks(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9201)
    state = orchestrator.initialize_state()
    week_one = orchestrator.simulate_next_week(state=state)
    week_two = orchestrator.simulate_next_week(state=week_one.season_state)
    assert week_one.weekly_result is not None
    assert week_two.weekly_result is not None

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-ordered", season=state.season, seed=9201)

    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=week_one)
    persistence.persist_step(run_id=run.run_id, step=week_two)

    loaded = repository.load_season_state(run_id=run.run_id)
    assert loaded is not None
    assert loaded.model_dump() == week_two.season_state.model_dump()

    assert repository.list_completed_event_ids(run_id=run.run_id) == week_two.season_state.completed_event_ids


def test_finals_qualification_and_result_can_be_persisted_and_reloaded(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9301)
    full_season = orchestrator.simulate_full_season(state=orchestrator.initialize_state())
    assert full_season.season_state.race_snapshot is not None

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-finals-persist", season=full_season.season_state.season, seed=9301)
    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=full_season)

    players, _ = _players(seed=99)
    finals_service = FinalsOrchestrationService(repository=repository)
    simulation = finals_service.simulate_world_tour_finals(
        run=run,
        state=full_season.season_state,
        players_by_id={player.player_id: player for player in players},
    )
    assert simulation.already_simulated is False

    persisted_qualification = repository.get_finals_qualification(run_id=run.run_id, season=run.season)
    persisted_result = repository.get_finals_result(run_id=run.run_id, season=run.season)
    assert persisted_qualification is not None
    assert persisted_result is not None
    assert persisted_qualification.qualification.model_dump() == simulation.qualification.qualification.model_dump()
    assert persisted_result.result.model_dump() == simulation.result.result.model_dump()


def test_rollover_records_are_persisted_and_reloadable(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9402)
    full_season = orchestrator.simulate_full_season(state=orchestrator.initialize_state())

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-rollover-persist", season=full_season.season_state.season, seed=9402)
    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=full_season)

    players, _ = _players(seed=99)
    rollover_service = SeasonRolloverOrchestrationService(
        repository=repository,
        rollover_service=SeasonRolloverService(
            progression_engine=CareerProgressionEngine(rng=DeterministicRng(run.seed))
        ),
    )
    rollover = rollover_service.rollover_to_next_season(
        run=run,
        state=full_season.season_state,
        players_by_id={player.player_id: player for player in players},
    )

    summary = repository.get_season_rollover(run_id=run.run_id, to_season=run.season + 1)
    transitions = repository.list_player_transitions(run_id=run.run_id, to_season=run.season + 1)
    next_players = repository.list_next_season_players(run_id=run.run_id, to_season=run.season + 1)

    assert summary is not None
    assert summary.transitioned_players == rollover.transitioned_players
    assert len(transitions) == rollover.transitioned_players
    assert len(next_players) == rollover.transitioned_players


def test_bootstrap_schema_backfills_active_tournament_column_for_existing_db(tmp_path) -> None:
    db_file = tmp_path / "legacy-schema.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE season_state (
                  run_id VARCHAR(128) PRIMARY KEY,
                  season INTEGER NOT NULL,
                  next_event_index INTEGER NOT NULL,
                  ordered_events_json TEXT NOT NULL,
                  completed_event_ids_json TEXT NOT NULL,
                  ranking_snapshot_json TEXT NULL,
                  race_snapshot_json TEXT NULL
                )
                """
            )
        )

    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    repository.bootstrap_schema()

    with engine.connect() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(season_state)"))
        }
    assert "active_tournament_json" in columns


def test_partial_tournament_steps_do_not_persist_completed_event_artifacts_until_completion(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9501)
    initial_state = orchestrator.initialize_state()
    partial = orchestrator.simulate_next_match(state=initial_state)

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-partial-persist", season=initial_state.season, seed=9501)
    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=partial)

    assert repository.list_completed_events(run_id=run.run_id) == []
    assert repository.list_ranking_snapshot_records(run_id=run.run_id) == []
    assert repository.list_race_snapshot_records(run_id=run.run_id) == []

    current_state = partial.season_state
    final_step = partial
    while current_state.active_tournament is not None:
        final_step = orchestrator.simulate_next_match(state=current_state)
        current_state = final_step.season_state

    persistence.persist_step(run_id=run.run_id, step=final_step)
    completed_events = repository.list_completed_events(run_id=run.run_id)
    assert len(completed_events) == 1
    assert completed_events[0].event_id == final_step.tournament_result.event.event_id
    assert len(repository.list_ranking_snapshot_records(run_id=run.run_id)) == 1
    assert len(repository.list_race_snapshot_records(run_id=run.run_id)) == 1
