"""Real SQLite acceptance tests for the first authoritative slot match slice."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import json
import hashlib
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
    build_authoritative_tournament_ranking_packages,
    execute_supported_four_player_tournament,
    execute_adopted_four_player_match_package,
)
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationCommand,
)
from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_tournament_ranking_sources,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.domain.players.sporting import (
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    SimulationMatchEventPlan,
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
)
from beta_engine.infrastructure.db.models import (
    Base,
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    AuthoritativeWorldStateModel,
    PlayerLifecycleWeekStateModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    RunBranchModel,
    RunContainerModel,
    RankingTransitionAuthorityModel,
)
from beta_engine.infrastructure.db.initial_world_state import (
    get_initial_world,
    put_initial_world,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    put_sporting,
    get_sporting,
    resolve_completed_context_from_authoritative_matches,
    transition_sporting,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionConflict,
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_walkover_authority import (
    TournamentWalkoverAuthorityStore,
)

WEEK = RankingWeek(season_index=0, week=1)


def player(player_id: str, value: int) -> PlayerSportingRecord:
    return PlayerSportingRecord(
        player_id=player_id,
        attributes=tuple((name, value) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=180,
        potential_identity=f"potential:{player_id}",
        potential_provenance="test",
        development_timing="Standard",
        current_form=100,
        long_term_form_norm=100,
        match_sharpness=50,
        long_term_fatigue=0,
    )


def session_at(
    path: Path,
    player_ids: tuple[str, str, str, str] = ("a", "b", "c", "d"),
    week: RankingWeek = WEEK,
) -> Session:
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    traits = HiddenCareerTraits(
        potential_ceiling=99,
        growth_curve="Standard",
        professionalism=0.5,
        ambition=0.5,
        travel_tolerance=0.5,
        schedule_aggression=0.5,
        injury_proneness=0.1,
        resilience=0.6,
    )
    profiles = tuple(
        SeasonActivePlayer(
            player_id=pid,
            name=pid.upper(),
            nationality="CZE",
            country_code="CZE",
            birth_year=1975,
            birth_year_week=1,
            age_years_at_season_start=25,
            age_weeks_at_season_start=25 * 61,
            current_ability=70,
            potential_ability=80,
            potential_tier="A",
            career_stage="prime",
            season="2000/2001",
            active_status="active",
            play_style=style,
            archetype=archetype,
            hidden_career_traits=traits,
            attributes=GeneratedPlayerAttributes(
                technique=70,
                movement=70,
                physical=70,
                mental=70,
                consistency=70,
                clutch=70,
                recovery=70,
            ),
            source_pool_player_id=pid,
            source_generation_fingerprint=f"profile:{pid}",
            source_generation="initial_pool",
            manual_override=False,
            locked_from_initial_pool=True,
            bootstrap_fingerprint="bootstrap",
            bootstrap_seed=1,
            bootstrap_id="bootstrap",
        )
        for index, pid in enumerate(player_ids)
        for style, archetype in (
            (
                ("attacking", "Power Attacker"),
                ("retrieving", "Retriever"),
                ("tempo-controller", "Control Player"),
                ("front-court", "Shot Maker"),
            )[index % 4],
        )
    )
    world = InitialWorldState(
        run_id="run",
        branch_id="branch",
        players=tuple(sorted(profiles, key=lambda player: player.player_id)),
        source_kind="production_initial_pool.v1",
        source_season="2000/2001",
        source_fingerprint="source",
        bootstrap_seed=1,
        bootstrap_fingerprint="bootstrap",
        adopted_by_command_id="adopt",
        audit_label="test",
        audit_reason="test",
        adoption_request_fingerprint="1" * 64,
    )
    put_initial_world(session, world)
    put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=week,
            source_initial_world_fingerprint=world.fingerprint,
            players=tuple(
                PlayerLifecycleIdentity(
                    player_id=pid,
                    birth_year=1975,
                    birth_year_week=1,
                    tie_break_token=f"token:{pid}",
                    tie_break_provenance="test",
                    tour_entry_week=week,
                    age=25,
                    status="active",
                    origin="test",
                )
                for pid in sorted(player_ids)
            ),
        ),
    )
    put_sporting(
        session,
        PlayerSportingWeekState(
            run_id="run",
            branch_id="branch",
            week=week,
            players=tuple(
                sorted(
                    (
                        player(pid, (130, 100, 125, 95)[index % 4])
                        for index, pid in enumerate(player_ids)
                    ),
                    key=lambda item: item.player_id,
                )
            ),
            effective_development_policy=PlayerDevelopmentPolicy(),
            completed_context_fingerprint="bootstrap",
            source_initial_world_fingerprint=world.fingerprint,
            stage_provenance="test",
        ),
    )
    session.commit()
    return session


def run_semifinals(path: Path, order: tuple[str, str]):
    session = session_at(path)
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-1",
        ordinal=1,
        group_ids=("sf-1", "sf-2"),
        match_events=(
            SimulationMatchEventPlan(
                group_id="sf-1",
                event_id="event",
                match_id="sf-1",
                direct_player_ids=("a", "b"),
            ),
            SimulationMatchEventPlan(
                group_id="sf-2",
                event_id="event",
                match_id="sf-2",
                direct_player_ids=("c", "d"),
            ),
        ),
    )
    participants = {"sf-1": ("a", "b", 101), "sf-2": ("c", "d", 202)}
    results = {}
    for group in order:
        a, b, seed = participants[group]
        results[group] = executor.execute_match_group(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot-1",
            group_id=group,
            event_id="event",
            match_id=group,
            player_a_id=a,
            player_b_id=b,
            seed=seed,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )
        session.commit()
    checkpoint = executor.terminal_checkpoint(
        run_id="run", branch_id="branch", week=WEEK
    )
    return session, executor, plan, results, checkpoint


def test_same_slot_frozen_snapshot_and_iteration_order_independence(tmp_path):
    one = run_semifinals(tmp_path / "one.sqlite", ("sf-1", "sf-2"))
    two = run_semifinals(tmp_path / "two.sqlite", ("sf-2", "sf-1"))
    assert one[2].slot_start_fingerprint == two[2].slot_start_fingerprint
    for group in ("sf-1", "sf-2"):
        assert one[3][group].authoritative_input == two[3][group].authoritative_input
        assert one[3][group].result == two[3][group].result
        assert one[3][group].effects == two[3][group].effects
        assert (
            one[3][group].authoritative_input.slot_start_fingerprint
            == one[2].slot_start_fingerprint
        )
    assert one[4] == two[4]


def test_production_four_player_application_path_derives_topology_and_result_refs(
    tmp_path,
):
    session = session_at(tmp_path / "production-four.sqlite")
    result = execute_supported_four_player_tournament(
        session,
        run_id="run",
        branch_id="branch",
        week=WEEK,
        event_id="owned-event",
        ordered_player_ids=("a", "b", "c", "d"),
        seed=500,
    )
    assert len(result.match_result_fingerprints) == 3
    assert result.match_result_fingerprints == tuple(
        item.result_fingerprint
        for item in (*result.semifinal_groups, result.final_group)
    )
    assert result.champion_player_id == result.final_group.result.winner_player_id
    final_ids = tuple(
        projection.player_id
        for projection in result.final_group.authoritative_input.player_projections
    )
    assert final_ids == tuple(
        item.result.winner_player_id for item in result.semifinal_groups
    )


def test_persisted_supported_main_draw_is_adopted_as_slot_truth(tmp_path):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(tmp_path / "legacy-source")
    package = service.result_service.match_service._load_registry().matches_by_event_id[
        event_id
    ]
    package.qualification_matches = []
    registry = service.result_service.match_service._load_registry()
    registry.matches_by_event_id[event_id] = package
    service.result_service.match_service._save_registry(registry)
    semifinal_matches = sorted(
        (match for match in package.main_draw_matches if match.round_number == 1),
        key=lambda match: match.bracket_position,
    )
    player_ids = tuple(
        player_id
        for match in semifinal_matches
        for player_id in (match.top_player_id, match.bottom_player_id)
    )
    tournament_week = RankingWeek(season_index=0, week=package.season_week)
    session = session_at(tmp_path / "adopted.sqlite", player_ids, tournament_week)
    result = execute_adopted_four_player_match_package(
        session,
        run_id="run",
        branch_id="branch",
        week=tournament_week,
        package=package,
        seed=700,
    )
    assert tuple(
        group.authoritative_input.match_id
        for group in (*result.semifinal_groups, result.final_group)
    ) == tuple(
        match.match_id
        for match in sorted(
            package.main_draw_matches,
            key=lambda match: (match.round_number, match.bracket_position),
        )
    )
    assert all(
        group.authoritative_input.slot_start_fingerprint
        for group in (*result.semifinal_groups, result.final_group)
    )
    registry_path = service.result_service.match_service.matches_path
    registry_before = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    _, completion, awards = build_authoritative_tournament_ranking_packages(
        service,
        package=package,
        authoritative=result,
        result_seed=701,
        award_seed=702,
    )
    assert hashlib.sha256(registry_path.read_bytes()).hexdigest() == registry_before
    assert tuple(
        ref.result_fingerprint for ref in completion.match_result_refs
    ) == tuple(
        group.result_fingerprint
        for group in (*result.semifinal_groups, result.final_group)
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="owned-edition",
        event_id=event_id,
        completed_week=tournament_week,
        first_publication_week=RankingWeek(
            season_index=0, week=tournament_week.week + 1
        ),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=completion.metadata.build_fingerprint,
        expected_award_fingerprint=awards.metadata.build_fingerprint,
    )
    assert prepare_tournament_ranking_sources(binding, completion, awards)
    owned = OwnedTournamentRankingSourceStore(session).append(
        OwnedTournamentRankingSource(
            binding=binding,
            result=completion,
            awards=awards,
            adopted_by_command_id="authoritative-slot-bridge",
        )
    )
    session.commit()
    reloaded = OwnedTournamentRankingSourceStore(session).get(
        run_id="run", branch_id="branch", edition_id="owned-edition"
    )
    assert reloaded.fingerprint == owned.fingerprint
    assert (
        tuple(ref.result_fingerprint for ref in reloaded.result.match_result_refs)
        == result.match_result_fingerprints
    )
    corrupt = completion.model_copy(deep=True)
    corrupt.match_result_refs[0].result_fingerprint = "0" * 64
    with pytest.raises(ValueError, match="result fingerprint mismatch"):
        prepare_tournament_ranking_sources(binding, corrupt, awards)


def test_driver_split_then_next_slot_closes_once_and_rejects_stale(tmp_path):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(tmp_path / "driver-source")
    package = service.result_service.match_service._load_registry().matches_by_event_id[
        event_id
    ]
    package.qualification_matches = []
    registry = service.result_service.match_service._load_registry()
    registry.matches_by_event_id[event_id] = package
    service.result_service.match_service._save_registry(registry)
    week = RankingWeek(season_index=0, week=package.season_week)
    ids = tuple(
        player_id
        for match in sorted(
            (m for m in package.main_draw_matches if m.round_number == 1),
            key=lambda m: m.bracket_position,
        )
        for player_id in (match.top_player_id, match.bottom_player_id)
    )
    session = session_at(tmp_path / "driver.sqlite", ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Driver test run",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
            saved_head_revision_id="revision",
        )
    )
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    session.close()
    driver = AuthoritativeRunSimulationDriver(
        factory, service.result_service.match_service, service
    )
    opening = driver.position(run_id="run", branch_id="branch")
    assert len(opening.eligible_match_ids) == 2
    assert len(opening.blocked_match_ids) == 1

    first = AuthoritativeSimulationCommand(
        command_id="sf-1",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=opening.position_fingerprint,
        expected_revision_id="revision",
        group_id=opening.eligible_match_ids[0],
    )
    after_first = driver.simulate_next_match(first)
    assert len(after_first["eligible_match_ids"]) == 1
    assert after_first["blocked_match_ids"]
    assert driver.simulate_next_match(first) == after_first
    with pytest.raises(ValueError, match="stale"):
        driver.simulate_next_match(
            first.model_copy(
                update={
                    "command_id": "stale",
                    "group_id": opening.eligible_match_ids[1],
                }
            )
        )

    current = driver.position(run_id="run", branch_id="branch")
    second = first.model_copy(
        update={
            "command_id": "sf-2",
            "expected_position_fingerprint": current.position_fingerprint,
            "group_id": current.eligible_match_ids[0],
        }
    )
    driver.simulate_next_match(second)
    final_position = driver.position(run_id="run", branch_id="branch")
    final = first.model_copy(
        update={
            "command_id": "final",
            "expected_position_fingerprint": final_position.position_fingerprint,
            "group_id": None,
        }
    )
    closed = driver.simulate_next_slot(final)
    assert closed["supported_tournament_complete"] is True
    assert closed["week_ready_for_transition"] is False
    assert closed["transition_blockers"] == ["run_branch_scope_missing"]
    with factory() as check:
        assert (
            len(
                OwnedTournamentRankingSourceStore(check).history(
                    run_id="run", branch_id="branch"
                )
            )
            == 1
        )
        assert len(check.scalars(select(SimulationEventGroupModel)).all()) == 3


def _driver_fixture(path):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(path / "source")
    match_service = service.result_service.match_service
    registry = match_service._load_registry()
    package = registry.matches_by_event_id[event_id]
    package.qualification_matches = []
    registry.matches_by_event_id[event_id] = package
    match_service._save_registry(registry)
    week = RankingWeek(season_index=0, week=package.season_week)
    ids = tuple(
        player_id
        for match in sorted(
            (m for m in package.main_draw_matches if m.round_number == 1),
            key=lambda m: m.bracket_position,
        )
        for player_id in (match.top_player_id, match.bottom_player_id)
    )
    session = session_at(path / "state.sqlite", ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Driver test run",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
            saved_head_revision_id="revision",
        )
    )
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    session.close()
    return (
        AuthoritativeRunSimulationDriver(factory, match_service, service),
        factory,
        week,
    )


def _multi_driver_fixture(path):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(path / "source")
    match_service = service.result_service.match_service
    registry = match_service._load_registry()
    first = registry.matches_by_event_id[event_id]
    first.qualification_matches = []
    first.season_week = 1
    second = first.model_copy(deep=True)
    second.event_id = f"{first.event_id}-SECOND"
    second.metadata.build_fingerprint = "b" * 64
    first_players = tuple(
        player_id
        for match in sorted(
            (m for m in first.main_draw_matches if m.round_number == 1),
            key=lambda match: match.bracket_position,
        )
        for player_id in (match.top_player_id, match.bottom_player_id)
    )
    second_players = tuple(
        player_id
        for player_id in (f"P{index}" for index in range(1, 9))
        if player_id not in first_players
    )
    semifinals = sorted(
        (match for match in second.main_draw_matches if match.round_number == 1),
        key=lambda match: match.bracket_position,
    )
    for match, players in zip(
        semifinals, (second_players[:2], second_players[2:]), strict=True
    ):
        match.top_player_id, match.bottom_player_id = players
    final = next(match for match in second.main_draw_matches if match.round_number == 2)
    final.top_player_id = None
    final.bottom_player_id = None
    for match in second.main_draw_matches:
        match.event_id = second.event_id
        match.match_id = f"B-{match.match_id}"
    registry.matches_by_event_id[event_id] = first
    registry.matches_by_event_id[second.event_id] = second
    match_service._save_registry(registry)
    calendar_registry = service.calendar_service._load_registry()
    calendar = calendar_registry.calendars_by_season[first.season]
    original_event = next(e for e in calendar.events if e.event_id == first.event_id)
    calendar.events.append(
        original_event.model_copy(update={"event_id": second.event_id})
    )
    service.calendar_service._save_registry(calendar_registry)
    week = RankingWeek(season_index=0, week=first.season_week)
    session = session_at(path / "state.sqlite", first_players + second_players, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Multi-event driver test run",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
            saved_head_revision_id="revision",
        )
    )
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    session.close()
    return (
        AuthoritativeRunSimulationDriver(factory, match_service, service),
        factory,
        week,
        first,
        second,
    )


def _driver_command(driver, week, command_id, group_id=None):
    position = driver.position(run_id="run", branch_id="branch")
    return AuthoritativeSimulationCommand(
        command_id=command_id,
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=position.position_fingerprint,
        expected_revision_id="revision",
        group_id=group_id,
    ), position


def test_next_slot_partial_commit_reopens_and_resumes(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "partial")
    command, _ = _driver_command(driver, week, "slot")
    with pytest.raises(RuntimeError, match="before second"):
        driver.simulate_next_slot(command, fault_at="before_second_group")
    with factory() as session:
        rows = session.scalars(select(SimulationEventGroupModel)).all()
        assert len(rows) == 1
        first_fingerprint = rows[0].result_fingerprint
    reopened = AuthoritativeRunSimulationDriver(
        factory, driver.match_service, driver.awards_service
    )
    resumed = reopened.simulate_next_slot(command)
    assert len(resumed["eligible_match_ids"]) == 1  # Final is now the next slot.
    with factory() as session:
        rows = session.scalars(
            select(SimulationEventGroupModel).order_by(
                SimulationEventGroupModel.group_id
            )
        ).all()
        assert len(rows) == 2
        assert first_fingerprint in {row.result_fingerprint for row in rows}


def test_pending_retry_uses_frozen_authority_after_legacy_source_changes(tmp_path):
    baseline, baseline_factory, week = _driver_fixture(tmp_path / "baseline")
    baseline_command, _ = _driver_command(baseline, week, "slot")
    baseline.simulate_next_slot(baseline_command)
    baseline_final, _ = _driver_command(baseline, week, "final")
    baseline.simulate_next_slot(baseline_final)
    with baseline_factory() as session:
        expected = tuple(
            row.result_fingerprint
            for row in session.scalars(
                select(SimulationEventGroupModel).order_by(
                    SimulationEventGroupModel.group_id
                )
            ).all()
        )
        expected_terminal = tuple(
            row.terminal_checkpoint_json
            for row in session.scalars(
                select(SimulationSlotModel).order_by(SimulationSlotModel.slot_ordinal)
            ).all()
        )
        expected_source = (
            OwnedTournamentRankingSourceStore(session)
            .history(run_id="run", branch_id="branch")[0]
            .fingerprint
        )

    driver, factory, week = _driver_fixture(tmp_path / "mutated")
    command, _ = _driver_command(driver, week, "slot")
    with pytest.raises(RuntimeError):
        driver.simulate_next_slot(command, fault_at="before_second_group")
    registry = driver.match_service._load_registry()
    event_id = next(iter(registry.matches_by_event_id))
    package = registry.matches_by_event_id[event_id]
    package.metadata.build_fingerprint = "f" * 64
    (
        package.main_draw_matches[1].top_player_id,
        package.main_draw_matches[1].bottom_player_id,
    ) = (
        package.main_draw_matches[1].bottom_player_id,
        package.main_draw_matches[1].top_player_id,
    )
    driver.match_service._save_registry(registry)
    driver.simulate_next_slot(command)
    final, _ = _driver_command(driver, week, "final")
    driver.simulate_next_slot(final)
    with factory() as session:
        actual = tuple(
            row.result_fingerprint
            for row in session.scalars(
                select(SimulationEventGroupModel).order_by(
                    SimulationEventGroupModel.group_id
                )
            ).all()
        )
        assert actual == expected
        assert (
            tuple(
                row.terminal_checkpoint_json
                for row in session.scalars(
                    select(SimulationSlotModel).order_by(
                        SimulationSlotModel.slot_ordinal
                    )
                ).all()
            )
            == expected_terminal
        )
        assert (
            OwnedTournamentRankingSourceStore(session)
            .history(run_id="run", branch_id="branch")[0]
            .fingerprint
            == expected_source
        )


def test_pre_adoption_full_package_change_makes_position_stale(tmp_path):
    driver, _, week = _driver_fixture(tmp_path / "pre-adoption-stale")
    command, opening = _driver_command(driver, week, "stale-source")
    registry = driver.match_service._load_registry()
    package = next(iter(registry.matches_by_event_id.values()))
    assert package.metadata.build_fingerprint
    (
        package.main_draw_matches[0].top_player_id,
        package.main_draw_matches[0].bottom_player_id,
    ) = (
        package.main_draw_matches[0].bottom_player_id,
        package.main_draw_matches[0].top_player_id,
    )
    driver.match_service._save_registry(registry)
    changed = driver.position(run_id="run", branch_id="branch")
    assert changed.position_fingerprint != opening.position_fingerprint
    with pytest.raises(ValueError, match="position is stale"):
        driver.simulate_next_slot(command)


def test_position_stales_when_world_or_transition_authority_changes(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "position-authorities")
    opening = driver.position(run_id="run", branch_id="branch")
    with factory.begin() as session:
        session.add(
            AuthoritativeWorldStateModel(
                run_id="run",
                branch_id="branch",
                current_ordinal=week.ordinal,
                ranking_fingerprint="1" * 64,
            )
        )
    with_world = driver.position(run_id="run", branch_id="branch")
    assert with_world.position_fingerprint != opening.position_fingerprint
    stale = AuthoritativeSimulationCommand(
        command_id="stale-world",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=opening.position_fingerprint,
        expected_revision_id="revision",
    )
    with pytest.raises(ValueError, match="position is stale"):
        driver.simulate_next_slot(stale)
    with factory.begin() as session:
        session.add(
            RankingTransitionAuthorityModel(
                run_id="run",
                branch_id="branch",
                target_ordinal=week.ordinal + 1,
                fingerprint="2" * 64,
                payload_json="{}",
            )
        )
    with_transition = driver.position(run_id="run", branch_id="branch")
    assert with_transition.position_fingerprint != with_world.position_fingerprint


def test_next_slot_and_both_split_orders_are_equivalent(tmp_path):
    snapshots = []
    for label, order in (("slot", None), ("forward", (0, 1)), ("reverse", (1, 0))):
        driver, factory, week = _driver_fixture(tmp_path / label)
        opening = driver.position(run_id="run", branch_id="branch")
        if order is None:
            command, _ = _driver_command(driver, week, "whole")
            driver.simulate_next_slot(command)
        else:
            ids = opening.eligible_match_ids
            for index in order:
                command, _ = _driver_command(driver, week, f"split-{index}", ids[index])
                driver.simulate_next_match(command)
        command, _ = _driver_command(driver, week, "final")
        driver.simulate_next_match(command)
        with factory() as session:
            slots = session.scalars(
                select(SimulationSlotModel).order_by(SimulationSlotModel.slot_ordinal)
            ).all()
            groups = session.scalars(
                select(SimulationEventGroupModel).order_by(
                    SimulationEventGroupModel.group_id
                )
            ).all()
            snapshots.append(
                (
                    tuple(
                        (
                            g.match_input_fingerprint,
                            g.result_fingerprint,
                            g.payload_json,
                        )
                        for g in groups
                    ),
                    tuple(slot.terminal_checkpoint_json for slot in slots),
                    AuthoritativeSlotMatchExecutor._load_group(
                        next(group for group in groups if group.slot_id.endswith(":2"))
                    ).authoritative_input.slot_start_fingerprint,
                )
            )
    assert snapshots[0] == snapshots[1] == snapshots[2]


def test_driver_rejects_qualification_and_insufficient_multi_event_chronology(
    tmp_path,
):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(tmp_path / "unsupported")
    package = service.result_service.match_service._load_registry().matches_by_event_id[
        event_id
    ]
    week = RankingWeek(season_index=0, week=package.season_week)
    driver = AuthoritativeRunSimulationDriver(
        None, service.result_service.match_service, service
    )
    with pytest.raises(ValueError, match="qualification final/placeholder mapping"):
        driver._package(week)
    registry = service.result_service.match_service._load_registry()
    clean = registry.matches_by_event_id[event_id].model_copy(deep=True)
    clean.qualification_matches = []
    registry.matches_by_event_id[event_id] = clean
    service.result_service.match_service._save_registry(registry)
    registry.matches_by_event_id["second-registry-entry"] = clean.model_copy(
        update={"event_id": clean.event_id + "-SECOND"}
    )
    service.result_service.match_service._save_registry(registry)
    with pytest.raises(ValueError, match="cross-event identity"):
        driver._package(week)


def test_multi_event_chronology_blocker_has_no_authoritative_mutation(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "multi-blocked")
    registry = driver.match_service._load_registry()
    package = next(iter(registry.matches_by_event_id.values()))
    registry.matches_by_event_id["second-registry-entry"] = package.model_copy(
        update={"event_id": package.event_id + "-SECOND"}
    )
    driver.match_service._save_registry(registry)

    with pytest.raises(ValueError, match="cross-event identity"):
        driver.position(run_id="run", branch_id="branch")

    with factory() as session:
        assert session.scalars(select(SimulationSlotModel)).all() == []
        assert session.scalars(select(SimulationEventGroupModel)).all() == []
        assert session.scalars(select(AdoptedTournamentAuthorityModel)).all() == []
        assert session.scalars(select(AuthoritativeSimulationCommandModel)).all() == []
        assert (
            OwnedTournamentRankingSourceStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )


def test_explicit_multi_event_schedule_adopts_and_executes_independent_sources(
    tmp_path,
):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "multi-scheduled"
    )

    with pytest.raises(ValueError, match="lack authoritative cross-event"):
        driver.position(run_id="run", branch_id="branch")

    first_matches = sorted(
        first.main_draw_matches, key=lambda m: (m.round_number, m.bracket_position)
    )
    second_matches = sorted(
        second.main_draw_matches, key=lambda m: (m.round_number, m.bracket_position)
    )
    valid = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=week,
        slots=(
            WeekSimulationScheduleSlot(
                ordinal=1,
                group_ids=tuple(
                    m.match_id for m in (*first_matches[:2], *second_matches[:2])
                ),
            ),
            WeekSimulationScheduleSlot(
                ordinal=2, group_ids=(first_matches[2].match_id,)
            ),
            WeekSimulationScheduleSlot(
                ordinal=3, group_ids=(second_matches[2].match_id,)
            ),
        ),
    )
    missing = valid.model_copy(update={"slots": valid.slots[:-1]})
    with pytest.raises(ValueError, match="cover every"):
        driver.preview_schedule(missing)
    same_slot_dependency = valid.model_copy(
        update={
            "slots": (
                WeekSimulationScheduleSlot(
                    ordinal=1,
                    group_ids=valid.slots[0].group_ids + valid.slots[1].group_ids,
                ),
                WeekSimulationScheduleSlot(
                    ordinal=2, group_ids=valid.slots[2].group_ids
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="strictly later"):
        driver.preview_schedule(same_slot_dependency)
    with pytest.raises(ValueError, match="duplicate group"):
        WeekSimulationSchedule(
            run_id="run",
            branch_id="branch",
            week=week,
            slots=(
                WeekSimulationScheduleSlot(
                    ordinal=1, group_ids=(first_matches[0].match_id,) * 2
                ),
            ),
        )

    preview = driver.preview_schedule(valid)
    changed = valid.model_copy(
        update={"slots": (valid.slots[0], valid.slots[2], valid.slots[1])}
    )
    assert (
        driver.preview_schedule(changed)["position_fingerprint"]
        != preview["position_fingerprint"]
    )
    adopted = driver.adopt_schedule(
        valid,
        request_id="schedule-1",
        expected_position_fingerprint=preview["position_fingerprint"],
    )
    assert adopted["schedule_fingerprint"] == valid.fingerprint
    assert (
        driver.adopt_schedule(
            valid,
            request_id="schedule-1",
            expected_position_fingerprint=preview["position_fingerprint"],
        )["adoption"]
        == "exact_retry"
    )
    with factory() as session:
        saved = {"content": {}}
        capture_saved_simulation_slots(session, saved, run_id="run", branch_id="branch")
        component = saved["content"]["simulation_slot_match_state"]
        assert component["schedules"][0]["schedule_fingerprint"] == valid.fingerprint
    reopened = AuthoritativeRunSimulationDriver(
        factory, driver.match_service, driver.awards_service
    )
    assert (
        reopened.inspect_schedule(run_id="run", branch_id="branch")[
            "schedule_fingerprint"
        ]
        == valid.fingerprint
    )
    driver = reopened

    with pytest.raises(RuntimeError, match="after first"):
        command, _ = _driver_command(driver, week, "slot-1")
        driver.simulate_next_slot(command, fault_at="after_first_group")
    result = driver.simulate_next_slot(command)
    with factory() as session:
        assert len(session.scalars(select(SimulationEventGroupModel)).all()) == 4
        bundle = session.get(
            AdoptedTournamentAuthorityModel, ("run", "branch", week.ordinal)
        )
        assert bundle.event_id == "__week_tournament_authority_bundle_v1__"
        assert [
            item.event_id
            for item in driver._decode_adopted_authority(bundle.package_json)
        ] == sorted((first.event_id, second.event_id))

    for index in range(2):
        command, before = _driver_command(driver, week, f"slot-{index + 2}")
        result = driver.simulate_next_slot(command)
        if index == 0:
            assert result["supported_tournament_complete"] is False
            with factory() as session:
                assert (
                    len(
                        OwnedTournamentRankingSourceStore(session).history(
                            run_id="run", branch_id="branch"
                        )
                    )
                    == 1
                )
    assert result["supported_tournament_complete"] is True
    with factory() as session:
        sources = OwnedTournamentRankingSourceStore(session).history(
            run_id="run", branch_id="branch"
        )
        assert len(sources) == 2
        slots = session.scalars(
            select(SimulationSlotModel).order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        assert len(slots) == 3
        assert (
            len(
                {
                    g.match_input_fingerprint
                    for g in session.scalars(
                        select(SimulationEventGroupModel).where(
                            SimulationEventGroupModel.slot_id == slots[0].slot_id
                        )
                    ).all()
                }
            )
            == 4
        )
        starts = {
            AuthoritativeSlotMatchExecutor._load_group(
                g
            ).authoritative_input.slot_start_fingerprint
            for g in session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.slot_id == slots[0].slot_id
                )
            ).all()
        }
        assert len(starts) == 1


def test_multi_event_same_slot_technical_order_is_authoritatively_irrelevant(tmp_path):
    snapshots = []
    for label, reverse in (("forward", False), ("reverse", True)):
        driver, factory, week, first, second = _multi_driver_fixture(tmp_path / label)
        matches_a = sorted(
            first.main_draw_matches,
            key=lambda match: (match.round_number, match.bracket_position),
        )
        matches_b = sorted(
            second.main_draw_matches,
            key=lambda match: (match.round_number, match.bracket_position),
        )
        schedule = WeekSimulationSchedule(
            run_id="run",
            branch_id="branch",
            week=week,
            slots=(
                WeekSimulationScheduleSlot(
                    ordinal=1,
                    group_ids=tuple(
                        match.match_id for match in (*matches_a[:2], *matches_b[:2])
                    ),
                ),
                WeekSimulationScheduleSlot(
                    ordinal=2, group_ids=(matches_a[2].match_id,)
                ),
                WeekSimulationScheduleSlot(
                    ordinal=3, group_ids=(matches_b[2].match_id,)
                ),
            ),
        )
        preview = driver.preview_schedule(schedule)
        driver.adopt_schedule(
            schedule,
            request_id="adopt",
            expected_position_fingerprint=preview["position_fingerprint"],
        )
        group_ids = list(schedule.slots[0].group_ids)
        if reverse:
            group_ids.reverse()
        for group_id in group_ids:
            command, _ = _driver_command(
                driver, week, f"group:{group_id}", group_id=group_id
            )
            driver.simulate_next_match(command)
        with factory() as session:
            groups = session.scalars(
                select(SimulationEventGroupModel).order_by(
                    SimulationEventGroupModel.group_id
                )
            ).all()
            slot = session.scalar(
                select(SimulationSlotModel).where(SimulationSlotModel.slot_ordinal == 1)
            )
            snapshots.append(
                (
                    tuple(
                        (
                            group.group_id,
                            group.result_fingerprint,
                            tuple(
                                effect.fingerprint
                                for effect in AuthoritativeSlotMatchExecutor._load_group(
                                    group
                                ).effects
                            ),
                        )
                        for group in groups
                    ),
                    slot.terminal_checkpoint_json,
                )
            )
    assert snapshots[0] == snapshots[1]


def test_multi_event_authority_is_canonical_across_registry_insertion_order(tmp_path):
    evidence = []
    for label, reverse in (("normal", False), ("reversed", True)):
        driver, _, week, first, second = _multi_driver_fixture(tmp_path / label)
        registry = driver.match_service._load_registry()
        if reverse:
            registry.matches_by_event_id = dict(
                reversed(tuple(registry.matches_by_event_id.items()))
            )
            driver.match_service._save_registry(registry)
        packages = driver._packages(week)
        items = tuple(
            (package, driver.awards_service.freeze_point_award_authority(package))
            for package in packages
        )
        inspected = driver.inspect_schedule(run_id="run", branch_id="branch")
        evidence.append(
            (
                tuple(package.event_id for package in packages),
                driver._tournament_authority_fingerprint("run", "branch", week, items),
                tuple(inspected["event_ids"]),
                tuple(inspected["group_ids"]),
            )
        )
    assert evidence[0] == evidence[1]


def test_general_eight_player_topology_uses_persisted_feeders_not_round_names(tmp_path):
    """The canonical graph accepts a complete seven-match persisted DAG."""
    driver, _, _ = _driver_fixture(tmp_path / "eight-topology")
    package = next(
        iter(driver.match_service._load_registry().matches_by_event_id.values())
    )
    base = package.main_draw_matches[0]

    def record(match_id, players=(None, None), winner_to=None, label="opaque"):
        return base.model_copy(
            update={
                "match_id": match_id,
                "round_number": 1,
                "round_name": label,
                "top_player_id": players[0],
                "bottom_player_id": players[1],
                "winner_to_match_id": winner_to,
                "status": "pending" if all(players) else "blocked_waiting_for_sources",
            }
        )

    matches = [
        record("q1", ("a", "b"), "s1"),
        record("q2", ("c", "d"), "s1"),
        record("q3", ("e", "f"), "s2"),
        record("q4", ("g", "h"), "s2"),
        record("s1", winner_to="final"),
        record("s2", winner_to="final"),
        record("final", label="not-a-final-name"),
    ]
    for target, top, bottom in (
        (matches[4], "q1", "q2"),
        (matches[5], "q3", "q4"),
        (matches[6], "s1", "s2"),
    ):
        target.top_source = top
        target.bottom_source = bottom
        target.top_slot_id = top
        target.bottom_slot_id = bottom
    frozen = package.model_copy(
        update={"qualification_matches": [], "main_draw_matches": matches}
    )
    plans = driver._topology((frozen,))
    assert set(plans) == {m.match_id for m in matches}
    assert plans["final"].participant_sources == ("winner:s1", "winner:s2")
    assert plans["q1"].participant_sources == ("player:a", "player:b")

    cyclic = frozen.model_copy(deep=True)
    cyclic.main_draw_matches[0].winner_to_match_id = "q2"
    cyclic.main_draw_matches[1].winner_to_match_id = "q1"
    with pytest.raises(ValueError, match="cycle"):
        driver._topology((cyclic,))


@pytest.mark.smoke
def test_real_persisted_eight_player_draw_executes_and_closes_once(tmp_path):
    """Production Entry -> Draw -> Match evidence drives all seven matches."""
    from test_season_entry_list_service import first_event_id, make_service
    from beta_engine.application.season_draw_service import (
        DrawGenerateRequest,
        SeasonDrawService,
    )
    from beta_engine.application.season_entry_list_service import (
        EntryListGenerateRequest,
    )
    from beta_engine.application.season_event_results_service import (
        SeasonEventResultsService,
    )
    from beta_engine.application.season_match_service import (
        MatchPackageGenerateRequest,
        SeasonMatchService,
    )
    from beta_engine.application.season_point_awards_service import (
        SeasonPointAwardsService,
    )

    root = tmp_path / "real-eight"
    entries = make_service(root, main_draw_size=8)
    event_id = first_event_id(entries)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0].model_copy(
        update={
            "qualification_draw_size": 0,
            "qualifier_spots": 0,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    calendar.events[0] = event
    entries.calendar_service._save_registry(calendars)
    entries.generate_entry_list(
        event_id=event_id,
        request=EntryListGenerateRequest(seed=1201, dry_run=False),
    )
    draws = SeasonDrawService(
        entry_list_service=entries,
        calendar_service=entries.calendar_service,
        draws_path=root / "draws.json",
    )
    draw = draws.generate_draw_package(
        event_id=event_id,
        request=DrawGenerateRequest(seed=1202, dry_run=False),
    ).draw_package
    assert draw is not None and draw.main_draw.draw_size == 8
    matches = SeasonMatchService(
        draw_service=draws,
        active_players_service=entries.active_players_service,
        matches_path=root / "matches.json",
    )
    package = matches.generate_match_package(
        event_id=event_id,
        request=MatchPackageGenerateRequest(seed=1203, dry_run=False),
    ).match_package
    assert package is not None and len(package.main_draw_matches) == 7
    results = SeasonEventResultsService(
        match_service=matches, results_path=root / "results.json"
    )
    awards = SeasonPointAwardsService(
        result_service=results,
        active_players_service=entries.active_players_service,
        calendar_service=entries.calendar_service,
        template_service=entries.calendar_service.template_service,
        awards_path=root / "awards.json",
        points_config_path=root / "points.json",
    )
    first_round = [m for m in package.main_draw_matches if m.status == "pending"]
    player_ids = tuple(
        player_id
        for match in first_round
        for player_id in (match.top_player_id, match.bottom_player_id)
    )
    week = RankingWeek(season_index=0, week=package.season_week)
    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Real eight",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
            saved_head_revision_id="revision",
        )
    )
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    session.close()
    driver = AuthoritativeRunSimulationDriver(factory, matches, awards)
    by_round = {}
    for match in package.main_draw_matches:
        by_round.setdefault(match.round_number, []).append(match.match_id)
    schedule = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=week,
        slots=tuple(
            WeekSimulationScheduleSlot(
                ordinal=index,
                group_ids=tuple(by_round[round_number]),
            )
            for index, round_number in enumerate(sorted(by_round), 1)
        ),
    )
    preview = driver.preview_schedule(schedule)
    driver.adopt_schedule(
        schedule,
        request_id="real-eight-schedule",
        expected_position_fingerprint=preview["position_fingerprint"],
    )
    first_command, _ = _driver_command(driver, week, "real-eight-1")
    first_state = driver.simulate_next_slot(first_command)
    assert driver.simulate_next_slot(first_command) == first_state
    # The first command adopts the v4 authority. All three producer files may
    # change after that without becoming execution truth again.
    entry_registry = entries._load_registry()
    entry_registry.entry_lists_by_event_id.clear()
    entries._save_registry(entry_registry)
    draw_registry = draws._load_registry()
    draw_registry.draws_by_event_id.clear()
    draws._save_registry(draw_registry)
    match_registry = matches._load_registry()
    match_registry.matches_by_event_id.clear()
    matches._save_registry(match_registry)
    assert (
        driver.position(run_id="run", branch_id="branch").position_fingerprint
        == first_state["position_fingerprint"]
    )
    with factory() as db:
        saved = {"content": {}}
        capture_saved_simulation_slots(db, saved, run_id="run", branch_id="branch")
        saved_component = saved["content"]["simulation_slot_match_state"]
        assert len(saved_component["groups"]) == 4
    reopened = AuthoritativeRunSimulationDriver(factory, matches, awards)
    assert (
        reopened.position(run_id="run", branch_id="branch").position_fingerprint
        == first_state["position_fingerprint"]
    )
    driver = reopened
    for ordinal in range(2, len(schedule.slots) + 1):
        command, _ = _driver_command(driver, week, f"real-eight-{ordinal}")
        state = driver.simulate_next_slot(command)
    assert state["supported_tournament_complete"] is True
    with factory() as db:
        groups = db.scalars(select(SimulationEventGroupModel)).all()
        assert len(groups) == 7
        assert len({g.group_id for g in groups}) == 7
        source = OwnedTournamentRankingSourceStore(db).history(
            run_id="run", branch_id="branch"
        )
        assert len(source) == 1
        assert len(source[0].result.match_result_refs) == 7
        slots = db.scalars(
            select(SimulationSlotModel).order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        opening_groups = [g for g in groups if g.slot_id == slots[0].slot_id]
        assert (
            len(
                {
                    AuthoritativeSlotMatchExecutor._load_group(
                        g
                    ).authoritative_input.slot_start_fingerprint
                    for g in opening_groups
                }
            )
            == 1
        )
        executor = AuthoritativeSlotMatchExecutor(db)
        for group in groups:
            stored = AuthoritativeSlotMatchExecutor._load_group(group)
            replayed = executor.replay(
                run_id="run",
                branch_id="branch",
                week=week,
                slot_id=group.slot_id,
                group_id=group.group_id,
            )
            assert replayed.result_fingerprint == stored.result_fingerprint
            assert (
                replayed.authoritative_input.fingerprint
                == stored.authoritative_input.fingerprint
            )


def test_real_eight_player_pre_adoption_entry_draw_match_mutation_fails_closed(
    tmp_path,
):
    """A proposal binds all current producer layers before any slot mutation."""
    from test_season_entry_list_service import first_event_id, make_service
    from beta_engine.application.season_draw_service import (
        DrawGenerateRequest,
        SeasonDrawService,
    )
    from beta_engine.application.season_entry_list_service import (
        EntryListGenerateRequest,
    )
    from beta_engine.application.season_match_service import (
        MatchPackageGenerateRequest,
        SeasonMatchService,
    )

    root = tmp_path / "stale-eight"
    entries = make_service(root, main_draw_size=8)
    event_id = first_event_id(entries)
    calendars = entries.calendar_service._load_registry()
    event = calendars.calendars_by_season["2000/2001"].events[0]
    calendars.calendars_by_season["2000/2001"].events[0] = event.model_copy(
        update={"qualification_draw_size": 0, "qualifier_spots": 0, "wild_cards": 0}
    )
    entries.calendar_service._save_registry(calendars)
    entries.generate_entry_list(
        event_id=event_id, request=EntryListGenerateRequest(seed=3101, dry_run=False)
    )
    draws = SeasonDrawService(entries, entries.calendar_service, root / "draws.json")
    draws.generate_draw_package(
        event_id=event_id, request=DrawGenerateRequest(seed=3102, dry_run=False)
    )
    matches = SeasonMatchService(
        draws, entries.active_players_service, root / "matches.json"
    )
    package = matches.generate_match_package(
        event_id=event_id, request=MatchPackageGenerateRequest(seed=3103, dry_run=False)
    ).match_package
    assert package
    week = RankingWeek(season_index=0, week=package.season_week)
    driver = AuthoritativeRunSimulationDriver(None, matches, SimpleNamespace())
    driver._packages(week)
    draw_registry = draws._load_registry()
    draw_registry.draws_by_event_id[event_id].metadata.entry_list_fingerprint = "0" * 64
    draws._save_registry(draw_registry)
    with pytest.raises(ValueError, match="EntryList fingerprint conflicts"):
        driver._packages(week)


def test_real_persisted_qualification_fails_only_when_bye_sources_are_ambiguous(
    tmp_path,
):
    from test_season_entry_list_service import first_event_id, make_service
    from beta_engine.application.season_draw_service import (
        DrawGenerateRequest,
        SeasonDrawService,
    )
    from beta_engine.application.season_entry_list_service import (
        EntryListGenerateRequest,
    )
    from beta_engine.application.season_event_results_service import (
        SeasonEventResultsService,
    )
    from beta_engine.application.season_match_service import (
        MatchPackageGenerateRequest,
        SeasonMatchService,
    )
    from beta_engine.application.season_point_awards_service import (
        SeasonPointAwardsService,
    )

    root = tmp_path / "real-qualification"
    entries = make_service(root, main_draw_size=8)
    event_id = first_event_id(entries)
    calendars = entries.calendar_service._load_registry()
    event = calendars.calendars_by_season["2000/2001"].events[0]
    calendars.calendars_by_season["2000/2001"].events[0] = event.model_copy(
        update={"wild_cards": 0, "byes": 0, "qualifier_spots": 1}
    )
    entries.calendar_service._save_registry(calendars)
    entries.generate_entry_list(
        event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=False)
    )
    draws = SeasonDrawService(entries, entries.calendar_service, root / "draws.json")
    draw = draws.generate_draw_package(
        event_id=event_id, request=DrawGenerateRequest(seed=2202, dry_run=False)
    ).draw_package
    matches = SeasonMatchService(
        draws, entries.active_players_service, root / "matches.json"
    )
    package = matches.generate_match_package(
        event_id=event_id, request=MatchPackageGenerateRequest(seed=2203, dry_run=False)
    ).match_package
    assert draw and package and len(draw.main_draw.qualifier_placeholders) == 1
    results = SeasonEventResultsService(
        match_service=matches, results_path=root / "results.json"
    )
    awards = SeasonPointAwardsService(
        result_service=results,
        active_players_service=entries.active_players_service,
        calendar_service=entries.calendar_service,
        template_service=entries.calendar_service.template_service,
        awards_path=root / "awards.json",
        points_config_path=root / "points.json",
    )
    player_ids = tuple(
        sorted(
            {
                p
                for m in package.qualification_matches + package.main_draw_matches
                for p in (m.top_player_id, m.bottom_player_id)
                if p
            }
        )
    )
    week = RankingWeek(season_index=0, week=package.season_week)
    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Qualification",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
            saved_head_revision_id="revision",
        )
    )
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    session.close()
    driver = AuthoritativeRunSimulationDriver(factory, matches, awards)
    ordered_rounds = []
    for draw_type in ("qualification", "main"):
        phase = [
            m
            for m in package.qualification_matches + package.main_draw_matches
            if m.draw_type == draw_type
        ]
        for round_number in sorted({m.round_number for m in phase}):
            ordered_rounds.append(
                tuple(m.match_id for m in phase if m.round_number == round_number)
            )
    schedule = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=week,
        slots=tuple(
            WeekSimulationScheduleSlot(ordinal=i, group_ids=groups)
            for i, groups in enumerate(ordered_rounds, 1)
        ),
    )
    assert package.qualification_matches
    assert all(
        match.status == "bye_auto_advance_pending"
        and match.top_player_id is None
        and match.bottom_player_id is None
        for match in package.qualification_matches
        if match.round_number == 1
    )
    with pytest.raises(ValueError, match="BYE advancement is ambiguous"):
        driver.preview_schedule(schedule)


def test_week_61_requires_season_transition(tmp_path):
    from beta_engine.infrastructure.db.authoritative_week_transition import (
        week_transition_readiness_blockers,
    )

    engine = create_engine(f"sqlite:///{tmp_path / 'week61.sqlite'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    assert week_transition_readiness_blockers(
        session,
        run_id="run",
        branch_id="branch",
        completed_week=RankingWeek(season_index=0, week=61),
    ) == ("season_transition_required",)


@pytest.mark.parametrize(
    "fault", ["after_final_before_source", "after_source_staging_before_receipt"]
)
def test_tournament_close_fault_retry_is_exactly_once(tmp_path, fault):
    driver, factory, week = _driver_fixture(tmp_path / fault)
    semifinal, _ = _driver_command(driver, week, "semifinals")
    driver.simulate_next_slot(semifinal)
    final, _ = _driver_command(driver, week, "final")
    with pytest.raises(RuntimeError, match="fault"):
        driver.simulate_next_slot(final, fault_at=fault)
    with factory() as session:
        final_row = session.scalars(
            select(SimulationEventGroupModel).order_by(
                SimulationEventGroupModel.slot_id.desc()
            )
        ).first()
        final_fingerprint = final_row.result_fingerprint
        assert (
            OwnedTournamentRankingSourceStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )
    closed = driver.simulate_next_slot(final)
    assert closed["week_ready_for_transition"] is False
    assert closed["transition_blockers"] == ["run_branch_scope_missing"]
    with factory() as session:
        final_row = session.scalars(
            select(SimulationEventGroupModel).order_by(
                SimulationEventGroupModel.slot_id.desc()
            )
        ).first()
        assert final_row.result_fingerprint == final_fingerprint
        assert (
            len(
                OwnedTournamentRankingSourceStore(session).history(
                    run_id="run", branch_id="branch"
                )
            )
            == 1
        )


def test_same_adopted_event_is_branch_safe_and_legacy_registry_is_read_only(tmp_path):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(tmp_path / "legacy-source-branches")
    match_service = service.result_service.match_service
    registry_path = match_service.matches_path
    registry_before = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    package = match_service._load_registry().matches_by_event_id[event_id]
    package.qualification_matches = []
    semifinal_matches = sorted(
        (match for match in package.main_draw_matches if match.round_number == 1),
        key=lambda match: match.bracket_position,
    )
    player_ids = tuple(
        player_id
        for match in semifinal_matches
        for player_id in (match.top_player_id, match.bottom_player_id)
    )
    week = RankingWeek(season_index=0, week=package.season_week)
    session = session_at(tmp_path / "branches.sqlite", player_ids, week)
    world_a = get_initial_world(session, run_id="run", branch_id="branch")
    lifecycle_a = get_lifecycle(session, run_id="run", branch_id="branch", week=week)
    sporting_a = get_sporting(session, run_id="run", branch_id="branch", week=week)
    world_b = world_a.model_copy(update={"branch_id": "branch-b"})
    put_initial_world(session, world_b)
    put_lifecycle(
        session,
        lifecycle_a.model_copy(
            update={
                "branch_id": "branch-b",
                "source_initial_world_fingerprint": world_b.fingerprint,
            }
        ),
    )
    put_sporting(
        session,
        sporting_a.model_copy(
            update={
                "branch_id": "branch-b",
                "source_initial_world_fingerprint": world_b.fingerprint,
            }
        ),
    )
    session.commit()

    owned_sources = []
    tournament_results = []
    for branch_id, seed in (("branch", 810), ("branch-b", 910)):
        tournament = execute_adopted_four_player_match_package(
            session,
            run_id="run",
            branch_id=branch_id,
            week=week,
            package=package,
            seed=seed,
        )
        _, completion, awards = build_authoritative_tournament_ranking_packages(
            service,
            package=package,
            authoritative=tournament,
            result_seed=seed + 1,
            award_seed=seed + 2,
        )
        binding = TournamentRankingBinding(
            run_id="run",
            branch_id=branch_id,
            edition_id="same-owned-edition",
            event_id=event_id,
            completed_week=week,
            first_publication_week=RankingWeek(season_index=0, week=week.week + 1),
            validity_weeks=61,
            ranking_status="ranked",
            expected_result_fingerprint=completion.metadata.build_fingerprint,
            expected_award_fingerprint=awards.metadata.build_fingerprint,
        )
        prepare_tournament_ranking_sources(binding, completion, awards)
        owned_sources.append(
            OwnedTournamentRankingSourceStore(session).append(
                OwnedTournamentRankingSource(
                    binding=binding,
                    result=completion,
                    awards=awards,
                    adopted_by_command_id=f"slot-bridge:{branch_id}",
                )
            )
        )
        tournament_results.append(tournament)
    session.commit()

    assert registry_before == hashlib.sha256(registry_path.read_bytes()).hexdigest()
    assert (
        tournament_results[0].match_result_fingerprints
        != tournament_results[1].match_result_fingerprints
    )
    assert owned_sources[0].fingerprint != owned_sources[1].fingerprint
    for branch_id, expected, tournament in zip(
        ("branch", "branch-b"), owned_sources, tournament_results, strict=True
    ):
        reloaded = OwnedTournamentRankingSourceStore(session).get(
            run_id="run", branch_id=branch_id, edition_id="same-owned-edition"
        )
        assert reloaded.fingerprint == expected.fingerprint
        assert (
            tuple(ref.result_fingerprint for ref in reloaded.result.match_result_refs)
            == tournament.match_result_fingerprints
        )


def test_semifinal_effects_feed_later_final_and_replay_is_historical(tmp_path):
    session, executor, first, semifinals, after = run_semifinals(
        tmp_path / "tournament.sqlite", ("sf-1", "sf-2")
    )
    finalists = tuple(result.result.winner_player_id for result in semifinals.values())
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        ordinal=2,
        group_ids=("final",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="final",
                event_id="event",
                match_id="final",
                feeder_group_ids=("sf-1", "sf-2"),
            ),
        ),
        dependency_ids=("sf-1", "sf-2"),
    )
    assert plan.slot_start_fingerprint != first.slot_start_fingerprint
    final = executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        group_id="final",
        event_id="event",
        match_id="final",
        player_a_id=finalists[0],
        player_b_id=finalists[1],
        seed=303,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    session.commit()
    after_players = {p.player_id: p for p in after.players}
    projected = {p.player_id: p for p in final.authoritative_input.player_projections}
    for finalist in finalists:
        assert projected[finalist].current_form == after_players[finalist].current_form
        assert (
            projected[finalist].match_sharpness
            == after_players[finalist].match_sharpness
        )
        assert (
            projected[finalist].long_term_fatigue
            == after_players[finalist].long_term_fatigue
        )
    stored_hash = final.authoritative_input.fingerprint
    session.close()
    reopened = Session(create_engine(f"sqlite:///{tmp_path / 'tournament.sqlite'}"))
    replay = AuthoritativeSlotMatchExecutor(reopened).replay(
        run_id="run", branch_id="branch", week=WEEK, slot_id="slot-2", group_id="final"
    )
    assert replay.authoritative_input.fingerprint == stored_hash
    assert replay.result == final.result


def test_owned_styles_reach_protected_gameplans_and_final_participants_are_enforced(
    tmp_path,
):
    session, executor, _, semifinals, _ = run_semifinals(
        tmp_path / "profiles.sqlite", ("sf-1", "sf-2")
    )
    first = semifinals["sf-1"].authoritative_input
    assert tuple(p.play_style for p in first.player_projections) == (
        "attacking",
        "retrieving",
    )
    natural = first.engine_input.effective_match_gameplans.natural_style_profiles
    assert natural[0].source_play_style == "attacking"
    assert natural[1].source_play_style == "retrieving"
    assert natural[0].axes != natural[1].axes
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        ordinal=2,
        group_ids=("final",),
        dependency_ids=("sf-1", "sf-2"),
        match_events=(
            SimulationMatchEventPlan(
                group_id="final",
                event_id="event",
                match_id="final",
                feeder_group_ids=("sf-1", "sf-2"),
            ),
        ),
    )
    winners = tuple(value.result.winner_player_id for value in semifinals.values())
    outsider = next(pid for pid in ("a", "b", "c", "d") if pid not in winners)
    with pytest.raises(ValueError, match="participants differ"):
        executor.execute_match_group(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot-2",
            group_id="final",
            event_id="event",
            match_id="final",
            player_a_id=outsider,
            player_b_id=winners[1],
            seed=9,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )


def test_replay_recomputes_result_fingerprint_and_rejects_corruption(tmp_path):
    session = session_at(tmp_path / "corrupt.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="g",
                event_id="event",
                match_id="match",
                direct_player_ids=("a", "b"),
            ),
        ),
    )
    executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=41,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    row = session.get(
        SimulationEventGroupModel, ("run", "branch", WEEK.ordinal, "slot", "g")
    )
    payload = json.loads(row.payload_json)
    payload["result"]["sets"][0]["was_close_endgame"] = not payload["result"]["sets"][
        0
    ]["was_close_endgame"]
    row.payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    session.flush()
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        executor.replay(
            run_id="run", branch_id="branch", week=WEEK, slot_id="slot", group_id="g"
        )


def test_pending_authoritative_slot_owns_week_and_blocks_context(tmp_path):
    session = session_at(tmp_path / "pending.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="g",
                event_id="event",
                match_id="match",
                direct_player_ids=("a", "b"),
            ),
        ),
    )
    with pytest.raises(ValueError, match="owns the week but is incomplete"):
        resolve_completed_context_from_authoritative_matches(
            session,
            run_id="run",
            branch_id="branch",
            completed_week=WEEK,
            player_ids=("a", "b", "c", "d"),
        )


def test_slot_creation_exact_retry_and_changed_request_conflict(tmp_path):
    session = session_at(tmp_path / "slot-retry.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    event = SimulationMatchEventPlan(
        group_id="g", event_id="event", match_id="match", direct_player_ids=("a", "b")
    )
    first = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(event,),
    )
    assert (
        executor.create_slot(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot",
            ordinal=1,
            group_ids=("g",),
            match_events=(event,),
        )
        == first
    )
    changed = event.model_copy(update={"match_id": "different"})
    with pytest.raises(ValueError, match="retry conflicts"):
        executor.create_slot(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot",
            ordinal=1,
            group_ids=("g",),
            match_events=(changed,),
        )


def test_retired_player_is_rejected_before_match_simulation(tmp_path):
    session = session_at(tmp_path / "retired.sqlite")
    lifecycle = get_lifecycle(session, run_id="run", branch_id="branch", week=WEEK)
    row = session.get(PlayerLifecycleWeekStateModel, ("run", "branch", WEEK.ordinal))
    retired = lifecycle.players[0].model_copy(
        update={"status": "retired", "retirement_effective_week": WEEK}
    )
    replacement = lifecycle.model_copy(
        update={"players": (retired, *lifecycle.players[1:])}
    )
    row.payload_json = replacement.model_dump_json()
    row.fingerprint = replacement.fingerprint
    session.flush()
    executor = AuthoritativeSlotMatchExecutor(session)
    event = SimulationMatchEventPlan(
        group_id="g", event_id="event", match_id="match", direct_player_ids=("a", "b")
    )
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(event,),
    )
    with pytest.raises(ValueError, match="requires active"):
        executor.execute_match_group(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot",
            group_id="g",
            event_id="event",
            match_id="match",
            player_a_id="a",
            player_b_id="b",
            seed=9,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )


def test_two_real_owned_branches_keep_independent_slot_histories(tmp_path):
    session = session_at(tmp_path / "branches.sqlite")
    world_a = get_initial_world(session, run_id="run", branch_id="branch")
    life_a = get_lifecycle(session, run_id="run", branch_id="branch", week=WEEK)
    sporting_a = get_sporting(session, run_id="run", branch_id="branch", week=WEEK)
    world_b = world_a.model_copy(update={"branch_id": "branch-b"})
    put_initial_world(session, world_b)
    put_lifecycle(
        session,
        life_a.model_copy(
            update={
                "branch_id": "branch-b",
                "source_initial_world_fingerprint": world_b.fingerprint,
            }
        ),
    )
    put_sporting(
        session,
        sporting_a.model_copy(
            update={
                "branch_id": "branch-b",
                "source_initial_world_fingerprint": world_b.fingerprint,
            }
        ),
    )
    session.commit()
    executor = AuthoritativeSlotMatchExecutor(session)
    event = SimulationMatchEventPlan(
        group_id="g", event_id="event", match_id="match", direct_player_ids=("a", "b")
    )
    plan_a = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(event,),
    )
    executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=1,
        expected_slot_start_fingerprint=plan_a.slot_start_fingerprint,
    )
    assert (
        executor.terminal_checkpoint(run_id="run", branch_id="branch-b", week=WEEK)
        is None
    )
    plan_b = executor.create_slot(
        run_id="run",
        branch_id="branch-b",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(event,),
    )
    result_b = executor.execute_match_group(
        run_id="run",
        branch_id="branch-b",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=2,
        expected_slot_start_fingerprint=plan_b.slot_start_fingerprint,
    )
    assert (
        result_b.result_fingerprint
        != executor.replay(
            run_id="run", branch_id="branch", week=WEEK, slot_id="slot", group_id="g"
        ).result_fingerprint
    )


def test_retry_conflict_exactly_once_branch_isolation_and_faults(tmp_path):
    session = session_at(tmp_path / "faults.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="g", event_id="e", match_id="m", direct_player_ids=("a", "b")
            ),
        ),
    )
    session.commit()
    with pytest.raises(ValueError, match="complete predecessor"):
        executor.create_slot(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="final-too-early",
            ordinal=2,
            group_ids=("final",),
            match_events=(
                SimulationMatchEventPlan(
                    group_id="final",
                    event_id="e",
                    match_id="final",
                    feeder_group_ids=("g", "other"),
                ),
            ),
            dependency_ids=("g",),
        )
    kwargs = dict(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="e",
        match_id="m",
        player_a_id="a",
        player_b_id="b",
        seed=1,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    for fault in ("after_match_staging", "after_effect_staging", "before_group_commit"):
        with pytest.raises(RuntimeError):
            executor.execute_match_group(**kwargs, fault_at=fault)
        session.rollback()
        assert (
            session.get(
                SimulationEventGroupModel, ("run", "branch", WEEK.ordinal, "slot", "g")
            )
            is None
        )
    result = executor.execute_match_group(**kwargs)
    session.commit()
    retry = executor.execute_match_group(**kwargs)
    assert retry.exact_retry and retry.effects == result.effects
    with pytest.raises(ValueError, match="conflicts"):
        executor.execute_match_group(**(kwargs | {"seed": 2}))
    with pytest.raises(ValueError, match="fingerprint changed"):
        executor.execute_match_group(
            **(kwargs | {"expected_slot_start_fingerprint": "0" * 64})
        )
    assert (
        session.query(SimulationEventGroupModel).filter_by(branch_id="other").count()
        == 0
    )


def test_projection_policy_is_versioned_and_changes_protected_input(tmp_path):
    session = session_at(tmp_path / "projection.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="g", event_id="e", match_id="m", direct_player_ids=("a", "b")
            ),
        ),
    )
    base = dict(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="e",
        match_id="m",
        player_a_id="a",
        player_b_id="b",
        seed=4,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    result = executor.execute_match_group(**base)
    projection = result.authoritative_input.player_projections[0]
    assert len(projection.canonical_attributes) == 57
    assert projection.current_form == 100
    assert projection.match_sharpness == 50
    assert projection.long_term_fatigue == 0
    assert (
        projection.projection_policy_id
        == "canonical-57-to-legacy-match-engine.provisional.v1"
    )
    changed = CanonicalMatchInputProjectionPolicy(
        policy_id="canonical-57-to-legacy-match-engine.provisional.v2"
    )
    with pytest.raises(ValueError, match="conflicts"):
        executor.execute_match_group(**base, projection_policy=changed)


def test_slot_history_saved_reopened_and_restored_backward_forward(tmp_path):
    path = tmp_path / "restore.sqlite"
    session = session_at(path)
    before = {"content": {}}
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="g",
                event_id="event",
                match_id="match",
                direct_player_ids=("a", "b"),
            ),
        ),
    )
    executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=77,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    after = {"content": {}}
    capture_saved_simulation_slots(session, after, run_id="run", branch_id="branch")
    legacy_after = json.loads(json.dumps(after))
    legacy_component = legacy_after["content"]["simulation_slot_match_state"]
    legacy_component.pop("commands", None)
    legacy_component.pop("authorities", None)
    legacy_component.pop("schedules", None)
    legacy_component.pop("entry_fields", None)
    legacy_body = {
        "slots": legacy_component["slots"],
        "groups": legacy_component["groups"],
    }
    legacy_component["fingerprint"] = hashlib.sha256(
        json.dumps(legacy_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    session.commit()
    session.close()

    reopened = Session(create_engine(f"sqlite:///{path}"))
    restore_saved_simulation_slots(
        reopened,
        current_payload=legacy_after,
        target_payload=before,
        run_id="run",
        branch_id="branch",
    )
    reopened.commit()
    assert reopened.query(SimulationEventGroupModel).count() == 0
    restore_saved_simulation_slots(
        reopened,
        current_payload=before,
        target_payload=legacy_after,
        run_id="run",
        branch_id="branch",
    )
    reopened.commit()
    replay = AuthoritativeSlotMatchExecutor(reopened).replay(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
    )
    assert replay.exact_retry is False


def test_restore_rejects_semantic_corruption_before_mutation(tmp_path):
    session, executor, _, _, terminal = run_semifinals(
        tmp_path / "semantic-restore.sqlite", ("sf-1", "sf-2")
    )
    current = {"content": {}}
    capture_saved_simulation_slots(session, current, run_id="run", branch_id="branch")
    corrupt = json.loads(json.dumps(current))
    component = corrupt["content"]["simulation_slot_match_state"]
    group_payload = json.loads(component["groups"][0]["payload_json"])
    group_payload["result"]["sets"][0]["was_close_endgame"] = not group_payload[
        "result"
    ]["sets"][0]["was_close_endgame"]
    component["groups"][0]["payload_json"] = json.dumps(
        group_payload, sort_keys=True, separators=(",", ":")
    )
    body = {"slots": component["slots"], "groups": component["groups"]}
    component["fingerprint"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    before = terminal.fingerprint
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        restore_saved_simulation_slots(
            session,
            current_payload=current,
            target_payload=corrupt,
            run_id="run",
            branch_id="branch",
        )
    assert (
        executor.terminal_checkpoint(
            run_id="run", branch_id="branch", week=WEEK
        ).fingerprint
        == before
    )


def test_week_transition_development_reads_terminal_post_match_form(tmp_path):
    session = session_at(tmp_path / "transition.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("match",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="match",
                event_id="event",
                match_id="match",
                direct_player_ids=("a", "b"),
            ),
        ),
    )
    played = executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="match",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=88,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    terminal = played.terminal_checkpoint
    resolve_completed_context_from_authoritative_matches(
        session,
        run_id="run",
        branch_id="branch",
        completed_week=WEEK,
        player_ids=("a", "b", "c", "d"),
    )
    target = transition_sporting(
        session,
        run_id="run",
        branch_id="branch",
        completed=WEEK,
        target=RankingWeek(season_index=0, week=2),
        lifecycle=SimpleNamespace(
            players=tuple(
                SimpleNamespace(player_id=pid, age=25) for pid in ("a", "b", "c", "d")
            )
        ),
    )
    terminal_players = {p.player_id: p for p in terminal.players}
    target_players = {p.player_id: p for p in target.players}
    policy = target.effective_development_policy
    for pid in ("a", "b"):
        difference = (
            terminal_players[pid].long_term_form_norm
            - terminal_players[pid].current_form
        )
        regression = int(difference / policy.form_regression_divisor)
        if regression == 0 and difference:
            regression = 1 if difference > 0 else -1
        expected_regressed = terminal_players[pid].current_form + regression
        assert target_players[pid].current_form == expected_regressed


def test_player_replacement_cutoff_uses_committed_real_match_receipts(tmp_path):
    session = session_at(tmp_path / "replacement-cutoff.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    cutoff_store = TournamentPlayerReplacementCutoffAuthorityStore(session)

    before = cutoff_store.resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id="a",
    )
    assert before.status == "replacement_open"
    assert before.played_matches == ()

    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-1",
        ordinal=1,
        group_ids=("match-1",),
        match_events=(
            SimulationMatchEventPlan(
                group_id="match-1",
                event_id="event",
                match_id="match-1",
                direct_player_ids=("a", "b"),
            ),
        ),
    )
    played = executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-1",
        group_id="match-1",
        event_id="event",
        match_id="match-1",
        player_a_id="a",
        player_b_id="b",
        seed=123,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )

    winner = played.result.winner_player_id
    loser = played.result.loser_player_id
    winner_cutoff = cutoff_store.resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=winner,
    )
    loser_cutoff = cutoff_store.resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=loser,
    )
    untouched = cutoff_store.resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id="c",
    )

    assert winner_cutoff.status == "walkover_required"
    assert winner_cutoff.first_real_match is not None
    assert winner_cutoff.first_real_match.match_id == "match-1"
    assert winner_cutoff.first_real_match.result_fingerprint == (
        played.result_fingerprint
    )
    assert loser_cutoff.status == "already_eliminated"
    assert untouched.status == "replacement_open"

    draw_revision_store = TournamentDrawRevisionStore(session)
    with pytest.raises(
        TournamentDrawRevisionConflict,
        match="W/O authority is required",
    ):
        draw_revision_store._replacement_cutoff_authorities(
            run_id="run",
            branch_id="branch",
            event_id="event",
            withdrawn_player_ids=(winner,),
        )
    with pytest.raises(
        TournamentDrawRevisionConflict,
        match="already eliminated",
    ):
        draw_revision_store._replacement_cutoff_authorities(
            run_id="run",
            branch_id="branch",
            event_id="event",
            withdrawn_player_ids=(loser,),
        )


def test_post_cutoff_walkover_commits_group_without_sporting_effects(
    tmp_path, monkeypatch
):
    session, executor, _, semifinals, _ = run_semifinals(
        tmp_path / "walkover.sqlite", ("sf-1", "sf-2")
    )
    withdrawn = semifinals["sf-1"].result.winner_player_id
    expected_winner = semifinals["sf-2"].result.winner_player_id
    final_plan = SimulationMatchEventPlan(
        group_id="final",
        event_id="event",
        match_id="final",
        participant_sources=("winner:sf-1", "winner:sf-2"),
    )
    slot_plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        ordinal=2,
        group_ids=("final",),
        match_events=(final_plan,),
        dependency_ids=("sf-1", "sf-2"),
    )
    slot = session.get(
        SimulationSlotModel, ("run", "branch", WEEK.ordinal, "slot-2")
    )
    start = executor._load_slot_start(slot)

    monkeypatch.setattr(
        TournamentDrawAuthorityStore,
        "get",
        lambda self, **kwargs: SimpleNamespace(fingerprint="d" * 64),
    )
    store = TournamentWalkoverAuthorityStore(session)
    walkover = store.commit(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        event_id="event",
        command_id="walkover-final",
        withdrawn_player_id=withdrawn,
        slot_id="slot-2",
        group_id="final",
    )

    assert walkover.result.scoreline == "W/O"
    assert walkover.result.winner_player_id == expected_winner
    assert walkover.result.loser_player_id == withdrawn
    assert walkover.effects == ()
    assert walkover.authoritative_input.replacement_cutoff_authority.status == (
        "walkover_required"
    )
    assert walkover.authoritative_input.source_real_match_id == "sf-1"
    assert slot.status == "complete"

    terminal = executor._load_checkpoint(slot)
    assert terminal.players == start.players
    assert terminal.applied_effect_fingerprints == start.applied_effect_fingerprints
    replay = executor.replay(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        group_id="final",
    )
    assert replay.result == walkover.result
    assert replay.effects == ()

    cutoff_after = TournamentPlayerReplacementCutoffAuthorityStore(
        session
    ).resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=withdrawn,
    )
    assert cutoff_after.status == "walkover_required"
    assert tuple(item.match_id for item in cutoff_after.played_matches) == ("sf-1",)

    context = resolve_completed_context_from_authoritative_matches(
        session,
        run_id="run",
        branch_id="branch",
        completed_week=WEEK,
        player_ids=("a", "b", "c", "d"),
    )
    assert {
        item.player_id: item.count for item in context.competitive_match_counts
    } == {"a": 1, "b": 1, "c": 1, "d": 1}

    retry = store.commit(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        event_id="event",
        command_id="walkover-final",
        withdrawn_player_id=withdrawn,
        slot_id="slot-2",
        group_id="final",
    )
    assert retry.exact_retry is True
    assert retry.result_fingerprint == walkover.result_fingerprint

    with pytest.raises(ValueError, match="conflicts"):
        executor.execute_match_group(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot-2",
            group_id="final",
            event_id="event",
            match_id="final",
            player_a_id=withdrawn,
            player_b_id=expected_winner,
            seed=999,
            expected_slot_start_fingerprint=slot_plan.slot_start_fingerprint,
        )


def test_walkover_group_saved_revision_round_trips(tmp_path, monkeypatch):
    session, executor, _, semifinals, _ = run_semifinals(
        tmp_path / "walkover-restore.sqlite", ("sf-1", "sf-2")
    )
    withdrawn = semifinals["sf-1"].result.winner_player_id
    final_plan = SimulationMatchEventPlan(
        group_id="final",
        event_id="event",
        match_id="final",
        participant_sources=("winner:sf-1", "winner:sf-2"),
    )
    executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        ordinal=2,
        group_ids=("final",),
        match_events=(final_plan,),
        dependency_ids=("sf-1", "sf-2"),
    )
    before = {"content": {}}
    capture_saved_simulation_slots(
        session, before, run_id="run", branch_id="branch"
    )

    monkeypatch.setattr(
        TournamentDrawAuthorityStore,
        "get",
        lambda self, **kwargs: SimpleNamespace(fingerprint="e" * 64),
    )
    committed = TournamentWalkoverAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        event_id="event",
        command_id="walkover-restore",
        withdrawn_player_id=withdrawn,
        slot_id="slot-2",
        group_id="final",
    )
    after = {"content": {}}
    capture_saved_simulation_slots(
        session, after, run_id="run", branch_id="branch"
    )

    restore_saved_simulation_slots(
        session,
        current_payload=after,
        target_payload=before,
        run_id="run",
        branch_id="branch",
    )
    assert (
        session.get(
            SimulationEventGroupModel,
            ("run", "branch", WEEK.ordinal, "slot-2", "final"),
        )
        is None
    )

    restore_saved_simulation_slots(
        session,
        current_payload=before,
        target_payload=after,
        run_id="run",
        branch_id="branch",
    )
    replay = executor.replay(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        group_id="final",
    )
    assert replay.result_fingerprint == committed.result_fingerprint
    assert replay.result.scoreline == "W/O"
    assert replay.effects == ()
