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
from beta_engine.application.authoritative_frozen_main_replacement import (
    AuthoritativeFrozenMainReplacement,
)
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    _AdoptedTournamentEvidence,
    AuthoritativeSimulationCommand,
    AuthoritativeMatchDayCommand,
    AuthoritativeRoundCommand,
    AuthoritativeTournamentCommand,
    AuthoritativeMatchReconstructionPreviewRequest,
    AuthoritativeMatchReconstructionCommitCommand,
    MatchReconstructionConstraints,
    MatchReconstructionGameScore,
)
from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_tournament_ranking_sources,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
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
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayedMatchCutoffEvidence,
    TournamentPlayerReplacementCutoffAuthorityBuilder,
)
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserAutoByeTerminalEvidence,
    TournamentLuckyLoserCandidate,
    TournamentLuckyLoserOrderAuthority,
)
from beta_engine.domain.tournaments.replacement_source_authority import (
    TournamentReplacementSourceAuthority,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
    TournamentEntryFieldResolver,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    fingerprint,
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
    PublishedOfficialRankingModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    WeekSimulationScheduleModel,
    RunBranchModel,
    RunContainerModel,
    RankingTransitionAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentDrawRevisionModel,
    TournamentEntryFieldVersionModel,
    TournamentWildCardAuthorityModel,
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
    capture_saved_sporting,
    put_sporting,
    get_sporting,
    resolve_completed_context_from_authoritative_matches,
    transition_sporting,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    _live_component_with_saved_shape,
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.player_slot_fork_remap import (
    _retarget_frozen_evidence,
    _retarget_lucky_loser_order_authority,
    _retarget_replacement_source_authority,
    remap_coupled_player_slot_history,
)
from beta_engine.infrastructure.db.simulation_slot_fork_remap import (
    SimulationSlotForkRemapUnsupportedError,
    remap_competitive_group_payload,
    remap_completed_simulation_slot_core,
    remap_slot_plan,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    _applications_fingerprint,
    _applications_json,
    _request_fingerprint as entry_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
    _request_fingerprint as draw_input_request_fingerprint,
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
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
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
    position = season_week_to_calendar_position(
        2000 + week.season_index,
        week.week,
    )
    lifecycle_age = age_at_calendar_position(
        birth_year=1975,
        birth_year_week=1,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
    )
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
                    age=lifecycle_age,
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
            completed_context_fingerprint="bootstrap:not-a-completed-week",
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


def _driver_fixture(path, *, season_week=None):
    from test_season_point_awards_service import make_points_service

    service, event_id = make_points_service(path / "source")
    match_service = service.result_service.match_service
    registry = match_service._load_registry()
    package = registry.matches_by_event_id[event_id]
    package.qualification_matches = []
    if season_week is not None:
        package.season_week = season_week
        calendars = service.calendar_service._load_registry()
        calendar = calendars.calendars_by_season[package.season]
        for index, event in enumerate(calendar.events):
            if event.event_id == event_id:
                calendar.events[index] = event.model_copy(
                    update={
                        "season_week": season_week,
                        "start_season_week": season_week,
                        "end_season_week": season_week,
                    }
                )
                break
        else:  # pragma: no cover
            raise AssertionError("driver fixture Calendar Event is missing")
        service.calendar_service._save_registry(calendars)
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



@pytest.mark.pr_critical
def test_match_reconstruction_preview_is_read_only_and_selected_candidate_commits(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "reconstruction")
    opening = driver.position(run_id="run", branch_id="branch")
    group_id = opening.eligible_match_ids[0]
    state = driver.inspect_match_reconstruction(
        run_id="run", branch_id="branch", group_id=group_id
    )
    assert state["player_a_id"] != state["player_b_id"]

    with factory() as session:
        before_groups = len(session.scalars(select(SimulationEventGroupModel)).all())
        before_slots = len(session.scalars(select(SimulationSlotModel)).all())
        before_adopted = len(session.scalars(select(AdoptedTournamentAuthorityModel)).all())

    winner_preview = driver.preview_match_reconstruction(
        AuthoritativeMatchReconstructionPreviewRequest(
            run_id="run",
            branch_id="branch",
            expected_week=week,
            expected_position_fingerprint=opening.position_fingerprint,
            expected_revision_id="revision",
            group_id=group_id,
            candidate_count=2,
            constraints=MatchReconstructionConstraints(
                winner_player_id=state["player_a_id"]
            ),
        )
    )
    assert winner_preview["candidate_count_found"] == 2
    assert all(
        candidate["winner_player_id"] == state["player_a_id"]
        for candidate in winner_preview["candidates"]
    )

    with factory() as session:
        assert len(session.scalars(select(SimulationEventGroupModel)).all()) == before_groups
        assert len(session.scalars(select(SimulationSlotModel)).all()) == before_slots
        assert (
            len(session.scalars(select(AdoptedTournamentAuthorityModel)).all())
            == before_adopted
        )

    source = winner_preview["candidates"][0]
    exact_scores = tuple(
        MatchReconstructionGameScore(**score) for score in source["game_scores"]
    )
    exact_preview = driver.preview_match_reconstruction(
        AuthoritativeMatchReconstructionPreviewRequest(
            run_id="run",
            branch_id="branch",
            expected_week=week,
            expected_position_fingerprint=opening.position_fingerprint,
            expected_revision_id="revision",
            group_id=group_id,
            candidate_count=1,
            constraints=MatchReconstructionConstraints(
                winner_player_id=source["winner_player_id"],
                player_a_sets_won=source["sets_won"][source["player_a_id"]],
                player_b_sets_won=source["sets_won"][source["player_b_id"]],
                exact_game_scores=exact_scores,
            ),
        )
    )
    assert exact_preview["candidate_count_found"] == 1
    selected = exact_preview["candidates"][0]
    assert selected["game_scores"] == source["game_scores"]

    command = AuthoritativeMatchReconstructionCommitCommand(
        command_id="reconstruct-sf",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=opening.position_fingerprint,
        expected_revision_id="revision",
        group_id=group_id,
        candidate_count=1,
        constraints=MatchReconstructionConstraints(
            winner_player_id=selected["winner_player_id"],
            player_a_sets_won=selected["sets_won"][selected["player_a_id"]],
            player_b_sets_won=selected["sets_won"][selected["player_b_id"]],
            exact_game_scores=tuple(
                MatchReconstructionGameScore(**score)
                for score in selected["game_scores"]
            ),
        ),
        expected_preview_fingerprint=exact_preview["preview_fingerprint"],
        selected_candidate_fingerprint=selected["candidate_fingerprint"],
        operator_label="Commissioner",
        audit_reason="Reconstruct reviewed historical score",
    )
    committed = driver.commit_match_reconstruction(command)
    assert committed["adoption"] == "committed"
    assert committed["candidate_fingerprint"] == selected["candidate_fingerprint"]
    assert committed["result_fingerprint"] == selected["result_fingerprint"]
    assert driver.commit_match_reconstruction(command) == committed

    with factory() as session:
        rows = session.scalars(select(SimulationEventGroupModel)).all()
        assert len(rows) == 1
        payload = json.loads(rows[0].payload_json)
        assert payload["match_reconstruction"]["candidate_fingerprint"] == selected[
            "candidate_fingerprint"
        ]
        assert payload["match_reconstruction"]["operator_label"] == "Commissioner"


@pytest.mark.pr_critical
def test_match_reconstruction_rejects_stale_preview_and_impossible_winner(tmp_path):
    driver, _, week = _driver_fixture(tmp_path / "reconstruction-conflicts")
    opening = driver.position(run_id="run", branch_id="branch")
    group_id = opening.eligible_match_ids[0]

    with pytest.raises(ValueError, match="not one of the frozen match participants"):
        driver.preview_match_reconstruction(
            AuthoritativeMatchReconstructionPreviewRequest(
                run_id="run",
                branch_id="branch",
                expected_week=week,
                expected_position_fingerprint=opening.position_fingerprint,
                expected_revision_id="revision",
                group_id=group_id,
                candidate_count=1,
                constraints=MatchReconstructionConstraints(
                    winner_player_id="not-a-participant"
                ),
            )
        )

    state = driver.inspect_match_reconstruction(
        run_id="run", branch_id="branch", group_id=group_id
    )
    preview = driver.preview_match_reconstruction(
        AuthoritativeMatchReconstructionPreviewRequest(
            run_id="run",
            branch_id="branch",
            expected_week=week,
            expected_position_fingerprint=opening.position_fingerprint,
            expected_revision_id="revision",
            group_id=group_id,
            candidate_count=1,
            constraints=MatchReconstructionConstraints(
                winner_player_id=state["player_a_id"]
            ),
        )
    )
    selected = preview["candidates"][0]
    stale = AuthoritativeMatchReconstructionCommitCommand(
        command_id="stale-reconstruction",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=opening.position_fingerprint,
        expected_revision_id="revision",
        group_id=group_id,
        candidate_count=1,
        constraints=MatchReconstructionConstraints(
            winner_player_id=state["player_a_id"]
        ),
        expected_preview_fingerprint="0" * 64,
        selected_candidate_fingerprint=selected["candidate_fingerprint"],
        operator_label="Commissioner",
        audit_reason="stale preview check",
    )
    with pytest.raises(ValueError, match="preview is stale"):
        driver.commit_match_reconstruction(stale)


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


@pytest.mark.smoke
def test_week61_closes_tournament_source_before_season_transition_boundary(tmp_path):
    driver, factory, week = _driver_fixture(
        tmp_path / "week61-close",
        season_week=61,
    )
    assert week == RankingWeek(season_index=0, week=61)

    first, _ = _driver_command(driver, week, "week61-semifinals")
    driver.simulate_next_slot(first)
    final, before_final = _driver_command(driver, week, "week61-final")
    assert "tournament_source_missing" in before_final.transition_blockers
    assert "season_transition_required" in before_final.transition_blockers

    boundary = driver.simulate_next_slot(final)
    assert boundary["current_week"] == {"season_index": 0, "week": 61}
    assert boundary["supported_tournament_complete"] is True
    assert boundary["week_ready_for_transition"] is False
    assert boundary["transition_blockers"] == ["season_transition_required"]

    with factory() as session:
        sources = OwnedTournamentRankingSourceStore(session).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        source = sources[0]
        assert source is not None
        assert source.binding.completed_week == week
        assert source.binding.first_publication_week == RankingWeek(
            season_index=1,
            week=1,
        )
        assert session.get(
            AuthoritativeWorldStateModel,
            ("run", "branch"),
        ) is None

    # A lost response / exact command retry returns the completed boundary state
    # without duplicating frozen tournament evidence.
    assert driver.simulate_next_slot(final) == boundary
    with factory() as session:
        assert len(
            OwnedTournamentRankingSourceStore(session).history(
                run_id="run",
                branch_id="branch",
            )
        ) == 1


def test_final_season_tournament_boundary_is_closing_only():
    completed = RankingWeek(season_index=49, week=61)
    publication, closing_ordinal = (
        AuthoritativeRunSimulationDriver._ranking_source_boundary(completed)
    )
    assert publication is None
    assert closing_ordinal == completed.ordinal + 1


@pytest.mark.pr_critical
def test_next_slot_receipt_preserves_private_request_evidence_without_changing_retry_shape(
    tmp_path,
):
    driver, factory, week = _driver_fixture(tmp_path / "receipt-request-evidence")
    command, _ = _driver_command(driver, week, "receipt-slot")

    first = driver.simulate_next_slot(command)
    assert "_request_evidence" not in first

    with factory() as session:
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", command.command_id),
        )
        assert receipt is not None
        stored = json.loads(receipt.result_json)
        evidence = stored["_request_evidence"]
        assert evidence["schema_version"] == (
            "authoritative_simulation_request_evidence.v3"
        )
        assert evidence["mode"] == "slot"
        assert evidence["command"] == command.model_dump(mode="json")
        assert fingerprint(evidence["opening_position_basis"]) == (
            command.expected_position_fingerprint
        )
        assert fingerprint(evidence["closing_position_basis"]) == (
            first["position_fingerprint"]
        )
        assert evidence["closing_position_basis"]["scope"][:2] == [
            "run",
            "branch",
        ]
        assert receipt.request_fingerprint == fingerprint(
            {"mode": "slot", "command": command.model_dump(mode="json")}
        )

        saved = {"content": {}}
        capture_saved_simulation_slots(
            session,
            saved,
            run_id="run",
            branch_id="branch",
        )
        command_rows = saved["content"]["simulation_slot_match_state"]["commands"]
        saved_receipt = next(
            row for row in command_rows if row["command_id"] == command.command_id
        )
        assert json.loads(saved_receipt["result_json"])["_request_evidence"] == evidence

    retry = driver.simulate_next_slot(command)
    assert retry == first
    assert "_request_evidence" not in retry

    visible_position = driver.position(run_id="run", branch_id="branch")
    assert "position_basis" not in visible_position.model_dump(mode="json")


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


@pytest.mark.pr_critical
def test_schedule_tiebreak_is_stable_and_scope_bound():
    week = RankingWeek(season_index=0, week=7)
    token = AuthoritativeRunSimulationDriver._deterministic_schedule_tiebreak(
        run_id="run",
        branch_id="branch",
        week=week,
        group_id="match-a",
    )
    assert token == AuthoritativeRunSimulationDriver._deterministic_schedule_tiebreak(
        run_id="run",
        branch_id="branch",
        week=week,
        group_id="match-a",
    )
    assert token != AuthoritativeRunSimulationDriver._deterministic_schedule_tiebreak(
        run_id="run",
        branch_id="branch",
        week=week,
        group_id="match-b",
    )
    assert token != AuthoritativeRunSimulationDriver._deterministic_schedule_tiebreak(
        run_id="run",
        branch_id="other-branch",
        week=week,
        group_id="match-a",
    )


@pytest.mark.pr_critical
def test_fair_rest_feeder_position_tracks_latest_prior_match():
    positions = {
        "early": (1, 1),
        "late": (1, 4),
        "previous-day": (2, 2),
    }

    assert AuthoritativeRunSimulationDriver._fair_rest_feeder_position(
        (), positions
    ) == (0, 0)
    assert AuthoritativeRunSimulationDriver._fair_rest_feeder_position(
        ("early", "late"), positions
    ) == (1, 4)
    assert AuthoritativeRunSimulationDriver._fair_rest_feeder_position(
        ("late", "previous-day"), positions
    ) == (2, 2)
    with pytest.raises(ValueError, match="requires every feeder position"):
        AuthoritativeRunSimulationDriver._fair_rest_feeder_position(
            ("missing",), positions
        )


@pytest.mark.pr_critical
def test_topological_schedule_proposal_parallelizes_independent_tournaments(tmp_path):
    driver, _, week, first, second = _multi_driver_fixture(
        tmp_path / "proposal-multi"
    )

    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )

    assert proposed["persisted"] is False
    assert "match_day_schedule_fair_rest.v2" in proposed["provenance"]
    assert schedule.schema_version == "week_simulation_schedule.v2"
    assert schedule.week == week
    assert len(schedule.slots) == 6
    assert all(len(slot.group_ids) == 1 for slot in schedule.slots)

    first_roots = {
        match.match_id
        for match in first.main_draw_matches
        if match.round_number == 1
    }
    second_roots = {
        match.match_id
        for match in second.main_draw_matches
        if match.round_number == 1
    }
    day_one = [slot for slot in schedule.slots if slot.match_day_ordinal == 1]
    day_two = [slot for slot in schedule.slots if slot.match_day_ordinal == 2]
    assert {slot.group_ids[0] for slot in day_one} == first_roots | second_roots
    expected_day_one = sorted(
        first_roots | second_roots,
        key=lambda group_id: (
            driver._deterministic_schedule_tiebreak(
                run_id="run",
                branch_id="branch",
                week=week,
                group_id=group_id,
            ),
            group_id,
        ),
    )
    assert [slot.group_ids[0] for slot in day_one] == expected_day_one
    assert [slot.match_order for slot in day_one] == [1, 2, 3, 4]
    assert {slot.group_ids[0] for slot in day_two} == {
        match.match_id
        for match in (*first.main_draw_matches, *second.main_draw_matches)
        if match.round_number == 2
    }
    assert [slot.match_order for slot in day_two] == [1, 2]

    preview = driver.preview_schedule(schedule)
    assert preview["schedule_fingerprint"] == proposed["schedule_fingerprint"]
    assert preview["position_fingerprint"] == proposed["position_fingerprint"]

    registry = driver.match_service._load_registry()
    registry.matches_by_event_id = dict(
        reversed(tuple(registry.matches_by_event_id.items()))
    )
    driver.match_service._save_registry(registry)
    repeated = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    assert repeated["schedule"] == proposed["schedule"]
    assert repeated["schedule_fingerprint"] == proposed["schedule_fingerprint"]
    assert repeated["position_fingerprint"] == proposed["position_fingerprint"]


@pytest.mark.pr_critical
def test_manual_match_day_schedule_can_split_round_without_breaking_feeders(tmp_path):
    driver, _, week, first, _ = _multi_driver_fixture(
        tmp_path / "manual-match-day-split"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    automatic = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    first_roots = sorted(
        (
            match
            for match in first.main_draw_matches
            if match.round_number == 1
        ),
        key=lambda match: match.bracket_position,
    )
    first_final = next(
        match
        for match in first.main_draw_matches
        if match.round_number == 2
    )
    moved_root_id = first_roots[-1].match_id

    def retime(day_overrides: dict[str, int]) -> WeekSimulationSchedule:
        rows = []
        for slot in automatic.slots:
            group_id = slot.group_ids[0]
            rows.append(
                (
                    day_overrides.get(
                        group_id,
                        slot.match_day_ordinal,
                    ),
                    slot.match_order,
                    slot.ordinal,
                    group_id,
                    slot,
                )
            )
        rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
        ordinal_pool = sorted(slot.ordinal for slot in automatic.slots)
        next_order: dict[int, int] = {}
        slots = []
        for index, (day, _, _, _, slot) in enumerate(rows):
            assert day is not None
            match_order = next_order.get(day, 0) + 1
            next_order[day] = match_order
            slots.append(
                slot.model_copy(
                    update={
                        "ordinal": ordinal_pool[index],
                        "match_day_ordinal": day,
                        "match_order": match_order,
                    }
                )
            )
        return automatic.model_copy(update={"slots": tuple(slots)})

    invalid = retime(
        {
            moved_root_id: 2,
            first_final.match_id: 2,
        }
    )
    with pytest.raises(
        ValueError,
        match="strictly later slot|later Match Day",
    ):
        driver.preview_schedule(invalid)

    manual = retime(
        {
            moved_root_id: 2,
            first_final.match_id: 3,
        }
    )
    preview = driver.preview_schedule(manual)
    assert preview["schedule_fingerprint"] == manual.fingerprint
    assert manual.fingerprint != automatic.fingerprint
    assert {
        slot.match_day_ordinal
        for slot in manual.slots
        if slot.group_ids[0] in {match.match_id for match in first_roots}
    } == {1, 2}
    assert next(
        slot.match_day_ordinal
        for slot in manual.slots
        if slot.group_ids[0] == first_final.match_id
    ) == 3

    adopted = driver.adopt_schedule(
        manual,
        request_id="manual-match-day-split",
        expected_position_fingerprint=preview["position_fingerprint"],
    )
    assert adopted["schedule_fingerprint"] == manual.fingerprint
    assert (
        driver.adopt_schedule(
            manual,
            request_id="manual-match-day-split",
            expected_position_fingerprint=preview["position_fingerprint"],
        )["adoption"]
        == "exact_retry"
    )


@pytest.mark.pr_critical
def test_match_day_v2_same_day_matches_use_sequential_sporting_snapshots(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "match-day-sequential-snapshots"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    day_one = [
        slot for slot in schedule.slots if slot.match_day_ordinal == 1
    ]
    assert len(day_one) >= 2
    assert day_one[0].match_order == 1
    assert day_one[1].match_order == 2

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="match-day-sequential-snapshots",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )

    first_command, first_position = _driver_command(
        driver, week, "match-day-first"
    )
    assert first_position.slot_ordinal == day_one[0].ordinal
    driver.simulate_next_slot(first_command)

    second_command, second_position = _driver_command(
        driver, week, "match-day-second"
    )
    assert second_position.slot_ordinal == day_one[1].ordinal
    driver.simulate_next_slot(second_command)

    with factory() as session:
        groups = session.scalars(
            select(SimulationEventGroupModel)
            .where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationEventGroupModel.slot_id)
        ).all()
        assert len(groups) == 2
        starts = [
            AuthoritativeSlotMatchExecutor._load_group(
                group
            ).authoritative_input.slot_start_fingerprint
            for group in groups
        ]
        assert starts[0] != starts[1]


@pytest.mark.pr_critical
def test_next_match_day_is_resumable_after_completed_child_response_loss(
    tmp_path,
    monkeypatch,
):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "next-match-day-resume"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    day_one = tuple(
        slot for slot in schedule.slots if slot.match_day_ordinal == 1
    )
    day_two = tuple(
        slot for slot in schedule.slots if slot.match_day_ordinal == 2
    )
    assert len(day_one) == 4
    assert len(day_two) == 2

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="next-match-day-schedule",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )
    preview = driver.preview_next_match_day(run_id="run", branch_id="branch")
    assert preview["match_day_ordinal"] == 1
    assert preview["target_slot_ordinals"] == [slot.ordinal for slot in day_one]
    assert preview["target_group_ids"] == [
        group_id for slot in day_one for group_id in slot.group_ids
    ]
    assert preview["expected_revision_id"] == "revision"

    command = AuthoritativeMatchDayCommand(
        command_id="next-match-day-1",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
    )

    original = AuthoritativeRunSimulationDriver.simulate_next_slot
    injected = {"raised": False}

    def lose_first_child_response(self, child, *, fault_at=None):
        result = original(self, child, fault_at=fault_at)
        if (
            child.command_id.startswith("match-day-slot:")
            and not injected["raised"]
        ):
            injected["raised"] = True
            raise RuntimeError("lost response after committed Match Day child")
        return result

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "simulate_next_slot",
        lose_first_child_response,
    )
    with pytest.raises(RuntimeError, match="lost response"):
        driver.simulate_next_match_day(command)

    with factory() as session:
        committed_after_fault = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        assert len(committed_after_fault) == 1

    result = driver.simulate_next_match_day(command)
    assert result["schema_version"] == "authoritative_match_day_result.v1"
    assert result["match_day_ordinal"] == 1
    assert result["completed_slot_count"] == len(day_one)
    assert result["target_slot_ordinals"] == [slot.ordinal for slot in day_one]
    assert len(result["child_command_ids"]) == len(day_one)
    assert len(set(result["child_command_ids"])) == len(day_one)
    assert result["position"]["current_slot_kind"] == "match"
    assert result["position"]["slot_ordinal"] == day_two[0].ordinal

    with factory() as session:
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        assert len(groups) == len(day_one)
        parent = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", "next-match-day-1"),
        )
        assert parent is not None
        assert parent.status == "complete"
        assert all(
            session.get(
                AuthoritativeSimulationCommandModel,
                ("run", "branch", child_id),
            ).status
            == "complete"
            for child_id in result["child_command_ids"]
        )

    assert driver.simulate_next_match_day(command) == result


@pytest.mark.pr_critical
def test_next_round_freezes_round_identity_executes_transit_and_resumes(
    tmp_path,
    monkeypatch,
):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "next-round-resume"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    automatic = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    by_group = {slot.group_ids[0]: slot for slot in automatic.slots}
    first_roots = sorted(
        (
            match
            for match in first.main_draw_matches
            if match.round_number == 1
        ),
        key=lambda match: match.bracket_position,
    )
    second_roots = sorted(
        (
            match
            for match in second.main_draw_matches
            if match.round_number == 1
        ),
        key=lambda match: match.bracket_position,
    )
    first_final = next(
        match for match in first.main_draw_matches if match.round_number == 2
    )
    second_final = next(
        match for match in second.main_draw_matches if match.round_number == 2
    )
    ordered_group_ids = [
        first_roots[0].match_id,
        second_roots[0].match_id,
        first_roots[1].match_id,
        second_roots[1].match_id,
        first_final.match_id,
        second_final.match_id,
    ]
    manual_slots = []
    for index, group_id in enumerate(ordered_group_ids):
        day = 1 if index < 4 else 2
        order = index + 1 if day == 1 else index - 3
        manual_slots.append(
            by_group[group_id].model_copy(
                update={
                    "ordinal": index + 1,
                    "match_day_ordinal": day,
                    "match_order": order,
                }
            )
        )
    manual = automatic.model_copy(update={"slots": tuple(manual_slots)})
    reviewed = driver.preview_schedule(manual)
    driver.adopt_schedule(
        manual,
        request_id="next-round-interleaved-schedule",
        expected_position_fingerprint=reviewed["position_fingerprint"],
    )

    preview = driver.preview_next_round(run_id="run", branch_id="branch")
    assert preview["round_identity"] == {
        "event_id": first.event_id,
        "draw_phase": "main",
        "round_number": 1,
    }
    assert preview["target_slot_ordinals"] == [1, 3]
    assert preview["target_group_ids"] == [
        first_roots[0].match_id,
        first_roots[1].match_id,
    ]
    assert preview["horizon_slot_ordinals"] == [1, 2, 3]
    assert preview["transit_slot_ordinals"] == [2]
    assert preview["transit_group_ids"] == [second_roots[0].match_id]
    assert preview["expected_revision_id"] == "revision"

    command = AuthoritativeRoundCommand(
        command_id="next-round-1",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
    )

    original = AuthoritativeRunSimulationDriver.simulate_next_slot
    injected = {"raised": False}

    def lose_first_child_response(self, child, *, fault_at=None):
        result = original(self, child, fault_at=fault_at)
        if child.command_id.startswith("round-slot:") and not injected["raised"]:
            injected["raised"] = True
            raise RuntimeError("lost response after committed Round child")
        return result

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "simulate_next_slot",
        lose_first_child_response,
    )
    with pytest.raises(RuntimeError, match="lost response"):
        driver.simulate_next_round(command)

    with factory() as session:
        committed_after_fault = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        assert len(committed_after_fault) == 1

    result = driver.simulate_next_round(command)
    assert result["schema_version"] == "authoritative_round_result.v1"
    assert result["round_identity"] == preview["round_identity"]
    assert result["target_slot_ordinals"] == [1, 3]
    assert result["horizon_slot_ordinals"] == [1, 2, 3]
    assert result["transit_slot_ordinals"] == [2]
    assert result["completed_slot_count"] == 3
    assert len(result["child_command_ids"]) == 3
    assert len(set(result["child_command_ids"])) == 3
    assert result["position"]["current_slot_kind"] == "match"
    assert result["position"]["slot_ordinal"] == 4

    with factory() as session:
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        assert len(groups) == 3
        assert {row.group_id for row in groups} == {
            first_roots[0].match_id,
            second_roots[0].match_id,
            first_roots[1].match_id,
        }
        parent = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", "next-round-1"),
        )
        assert parent is not None
        assert parent.status == "complete"

    assert driver.simulate_next_round(command) == result


@pytest.mark.pr_critical
def test_next_tournament_executes_interleaved_chronology_and_resumes(
    tmp_path,
    monkeypatch,
):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "next-tournament-resume"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    automatic = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    by_group = {slot.group_ids[0]: slot for slot in automatic.slots}
    first_roots = sorted(
        (
            match
            for match in first.main_draw_matches
            if match.round_number == 1
        ),
        key=lambda match: match.bracket_position,
    )
    second_roots = sorted(
        (
            match
            for match in second.main_draw_matches
            if match.round_number == 1
        ),
        key=lambda match: match.bracket_position,
    )
    first_final = next(
        match for match in first.main_draw_matches if match.round_number == 2
    )
    second_final = next(
        match for match in second.main_draw_matches if match.round_number == 2
    )
    ordered_group_ids = [
        first_roots[0].match_id,
        second_roots[0].match_id,
        first_roots[1].match_id,
        second_roots[1].match_id,
        first_final.match_id,
        second_final.match_id,
    ]
    manual_slots = []
    for index, group_id in enumerate(ordered_group_ids):
        day = 1 if index < 4 else 2
        order = index + 1 if day == 1 else index - 3
        manual_slots.append(
            by_group[group_id].model_copy(
                update={
                    "ordinal": index + 1,
                    "match_day_ordinal": day,
                    "match_order": order,
                }
            )
        )
    manual = automatic.model_copy(update={"slots": tuple(manual_slots)})
    reviewed = driver.preview_schedule(manual)
    driver.adopt_schedule(
        manual,
        request_id="next-tournament-interleaved-schedule",
        expected_position_fingerprint=reviewed["position_fingerprint"],
    )

    preview = driver.preview_next_tournament(run_id="run", branch_id="branch")
    assert preview["event_id"] == first.event_id
    assert preview["target_slot_ordinals"] == [1, 3, 5]
    assert preview["target_group_ids"] == [
        first_roots[0].match_id,
        first_roots[1].match_id,
        first_final.match_id,
    ]
    assert preview["horizon_slot_ordinals"] == [1, 2, 3, 4, 5]
    assert preview["transit_slot_ordinals"] == [2, 4]
    assert preview["transit_group_ids"] == [
        second_roots[0].match_id,
        second_roots[1].match_id,
    ]
    assert preview["expected_revision_id"] == "revision"

    command = AuthoritativeTournamentCommand(
        command_id="next-tournament-1",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
    )

    original = AuthoritativeRunSimulationDriver.simulate_next_slot
    injected = {"raised": False}

    def lose_first_child_response(self, child, *, fault_at=None):
        result = original(self, child, fault_at=fault_at)
        if (
            child.command_id.startswith("tournament-slot:")
            and not injected["raised"]
        ):
            injected["raised"] = True
            raise RuntimeError("lost response after committed Tournament child")
        return result

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "simulate_next_slot",
        lose_first_child_response,
    )
    with pytest.raises(RuntimeError, match="lost response"):
        driver.simulate_next_tournament(command)

    with factory() as session:
        committed_after_fault = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        assert len(committed_after_fault) == 1

    result = driver.simulate_next_tournament(command)
    assert result["schema_version"] == "authoritative_tournament_result.v1"
    assert result["event_id"] == first.event_id
    assert result["target_slot_ordinals"] == [1, 3, 5]
    assert result["horizon_slot_ordinals"] == [1, 2, 3, 4, 5]
    assert result["transit_slot_ordinals"] == [2, 4]
    assert result["completed_slot_count"] == 5
    assert len(result["child_command_ids"]) == 5
    assert len(set(result["child_command_ids"])) == 5
    assert len(result["owned_tournament_source_fingerprint"]) == 64
    assert result["position"]["current_slot_kind"] == "match"
    assert result["position"]["slot_ordinal"] == 6

    with factory() as session:
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        assert len(groups) == 5
        sources = OwnedTournamentRankingSourceStore(session).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        assert sources[0].binding.event_id == first.event_id
        assert sources[0].fingerprint == result[
            "owned_tournament_source_fingerprint"
        ]
        parent = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", "next-tournament-1"),
        )
        assert parent is not None
        assert parent.status == "complete"

    assert driver.simulate_next_tournament(command) == result


@pytest.mark.pr_critical
def test_topological_schedule_proposal_adoption_is_atomic_and_idempotent(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "proposal-adoption"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )

    with pytest.raises(ValueError, match="proposal is stale"):
        driver.adopt_topological_schedule_proposal(
            run_id="run",
            branch_id="branch",
            request_id="adopt-proposal",
            expected_week=week,
            expected_schedule_fingerprint="0" * 64,
            expected_position_fingerprint=proposed["position_fingerprint"],
        )
    with factory() as session:
        assert session.scalars(select(WeekSimulationScheduleModel)).all() == []

    with pytest.raises(ValueError, match="simulation position is stale"):
        driver.adopt_topological_schedule_proposal(
            run_id="run",
            branch_id="branch",
            request_id="adopt-proposal",
            expected_week=week,
            expected_schedule_fingerprint=proposed["schedule_fingerprint"],
            expected_position_fingerprint="0" * 64,
        )
    with factory() as session:
        assert session.scalars(select(WeekSimulationScheduleModel)).all() == []

    adopted = driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="adopt-proposal",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )
    assert adopted["adoption"] == "adopted_topological_proposal"
    assert adopted["schedule_fingerprint"] == proposed["schedule_fingerprint"]

    retry = driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="adopt-proposal",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )
    assert retry["adoption"] == "exact_retry"
    assert retry["schedule_fingerprint"] == proposed["schedule_fingerprint"]

    with pytest.raises(ValueError, match="already adopted and immutable"):
        driver.adopt_topological_schedule_proposal(
            run_id="run",
            branch_id="branch",
            request_id="different-request",
            expected_week=week,
            expected_schedule_fingerprint=proposed["schedule_fingerprint"],
            expected_position_fingerprint=proposed["position_fingerprint"],
        )


@pytest.mark.pr_critical
def test_topological_schedule_proposal_fails_on_parallel_known_player_conflict(
    tmp_path,
    monkeypatch,
):
    driver, _, _, first, _ = _multi_driver_fixture(
        tmp_path / "proposal-conflict"
    )
    roots = sorted(
        (
            match
            for match in first.main_draw_matches
            if match.round_number == 1
        ),
        key=lambda match: match.bracket_position,
    )
    plans = {
        roots[0].match_id: SimulationMatchEventPlan(
            group_id=roots[0].match_id,
            event_id=first.event_id,
            match_id=roots[0].match_id,
            participant_sources=("player:shared", "player:left"),
        ),
        roots[1].match_id: SimulationMatchEventPlan(
            group_id=roots[1].match_id,
            event_id=first.event_id,
            match_id=roots[1].match_id,
            participant_sources=("player:shared", "player:right"),
        ),
    }
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_topology_for_session",
        lambda self, *args, **kwargs: plans,
    )

    with pytest.raises(
        ValueError,
        match="multiple matches on the same day",
    ):
        driver.propose_topological_schedule(
            run_id="run",
            branch_id="branch",
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
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    assert schedule.schema_version == "week_simulation_schedule.v2"
    assert len(schedule.slots) == 7
    assert all(len(slot.group_ids) == 1 for slot in schedule.slots)
    assert [
        sum(slot.match_day_ordinal == day for slot in schedule.slots)
        for day in (1, 2, 3)
    ] == [4, 2, 1]
    preview = driver.preview_schedule(schedule)
    assert preview["position_fingerprint"] == proposed["position_fingerprint"]
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
        assert len(saved_component["groups"]) == 1
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
        assert len(slots) == 7
        first_day_ordinals = {
            slot.ordinal
            for slot in schedule.slots
            if slot.match_day_ordinal == 1
        }
        first_day_slot_ids = {
            slot.slot_id
            for slot in slots
            if slot.slot_ordinal in first_day_ordinals
        }
        first_day_groups = [
            group for group in groups if group.slot_id in first_day_slot_ids
        ]
        assert len(first_day_groups) == 4
        assert len(
            {
                AuthoritativeSlotMatchExecutor._load_group(
                    group
                ).authoritative_input.slot_start_fingerprint
                for group in first_day_groups
            }
        ) == 4
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


@pytest.mark.smoke
def test_real_persisted_sixteen_player_draw_executes_and_closes_once(tmp_path):
    """Run-owned Ranking -> Field -> Draw drives all fifteen canonical matches."""
    from test_season_entry_list_service import make_service
    from beta_engine.application.season_draw_service import SeasonDrawService
    from beta_engine.application.season_event_results_service import (
        SeasonEventResultsService,
    )
    from beta_engine.application.season_match_service import SeasonMatchService
    from beta_engine.application.season_point_awards_service import (
        SeasonPointAwardsService,
    )
    from beta_engine.domain.rankings.official import (
        OfficialRankingPlayer,
        OfficialRankingPolicy,
        OfficialRankingResult,
        calculate_official_ranking,
    )
    from beta_engine.domain.tournaments.entry_field import (
        TournamentEntryApplication,
        TournamentEntryFieldCapacity,
    )
    from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
    from beta_engine.infrastructure.db.tournament_draw_authority import (
        TournamentDrawAuthorityStore,
    )
    from beta_engine.infrastructure.db.tournament_draw_input_authority import (
        TournamentDrawInputAuthorityStore,
    )
    from beta_engine.infrastructure.db.tournament_entry_field import (
        TournamentEntryFieldStore,
    )
    from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
        TournamentRankingSnapshotAuthorityStore,
    )

    root = tmp_path / "real-sixteen-canonical"
    entries = make_service(root, main_draw_size=16)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0].model_copy(
        update={
            "event_id": "event",
            "season_week": 3,
            "start_season_week": 3,
            "end_season_week": 3,
            "qualification_draw_size": 0,
            "qualifier_spots": 0,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    calendar.events[0] = event
    entries.calendar_service._save_registry(calendars)

    player_ids = tuple(chr(ord("A") + index) for index in range(16))
    week = RankingWeek(season_index=0, week=3)
    ranking_week = RankingWeek(season_index=0, week=2)
    completed_week = RankingWeek(season_index=0, week=1)

    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Canonical sixteen",
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
    ranking_players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"rank-{player_id}",
            tour_entry_week=completed_week,
        )
        for player_id in player_ids
    )
    ranking_results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed_week,
            first_publication_week=ranking_week,
            main_points=(len(player_ids) - index) * 10,
        )
        for index, player_id in enumerate(player_ids)
    )
    ranking = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=ranking_week,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=ranking_players,
        results=ranking_results,
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=ranking.week.ordinal,
            snapshot_fingerprint=ranking.fingerprint,
            payload_json=ranking.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).adopt(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        ranking_week=ranking.week,
        command_id="adopt-ranking",
    )

    applications = tuple(
        TournamentEntryApplication(
            application_id=f"app-{player_id}",
            run_id="run",
            branch_id="branch",
            event_id=event.event_id,
            player_id=player_id,
            entry_window="main",
            decision_slot_ordinal=10,
            nr_tie_break_token=f"entry-{player_id}",
        )
        for player_id in player_ids
    )
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        applications=applications,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=16,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        command_id="initial-field",
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="commit-draw-input",
        draw_seed=1802,
        main_seed_count=4,
        qualification_seed_count=0,
    )
    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="generate-draw",
    )
    assert draw.draw_input_fingerprint == draw_input.fingerprint
    assert draw.main.bracket_size == 16
    assert len(draw.main.nodes) == 15
    session.commit()

    factory = sessionmaker(bind=session.get_bind())
    session.close()

    draws = SeasonDrawService(
        entry_list_service=entries,
        calendar_service=entries.calendar_service,
        draws_path=root / "legacy-draws-unused.json",
    )
    matches = SeasonMatchService(
        draw_service=draws,
        active_players_service=entries.active_players_service,
        matches_path=root / "legacy-matches-unused.json",
    )
    results = SeasonEventResultsService(
        match_service=matches,
        results_path=root / "legacy-results-unused.json",
    )
    awards = SeasonPointAwardsService(
        result_service=results,
        active_players_service=entries.active_players_service,
        calendar_service=entries.calendar_service,
        template_service=entries.calendar_service.template_service,
        awards_path=root / "legacy-awards-unused.json",
        points_config_path=root / "legacy-points-unused.json",
    )

    driver = AuthoritativeRunSimulationDriver(factory, matches, awards)
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    assert schedule.schema_version == "week_simulation_schedule.v2"
    assert len(schedule.slots) == 15
    assert all(len(slot.group_ids) == 1 for slot in schedule.slots)
    assert [
        sum(slot.match_day_ordinal == day for slot in schedule.slots)
        for day in (1, 2, 3, 4)
    ] == [8, 4, 2, 1]

    adopted = driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="real-sixteen-schedule",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )
    assert adopted["adoption"] == "adopted_topological_proposal"

    for ordinal in range(1, len(schedule.slots) + 1):
        command, _ = _driver_command(
            driver,
            week,
            f"real-sixteen-{ordinal}",
        )
        state = driver.simulate_next_slot(command)

    assert state["supported_tournament_complete"] is True

    with factory() as db:
        groups = db.scalars(select(SimulationEventGroupModel)).all()
        assert len(groups) == 15
        assert len({group.group_id for group in groups}) == 15

        sources = OwnedTournamentRankingSourceStore(db).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        source = sources[0]
        assert source.schema_version == "owned_tournament_ranking_source.v5"
        assert source.canonical_result is not None
        assert len(source.canonical_result.matches) == 15
        assert len(source.canonical_result.players) == 16

        stages = [
            player.reached_stage for player in source.canonical_result.players
        ]
        assert stages.count("round_of_16") == 8
        assert stages.count("quarterfinal") == 4
        assert stages.count("semifinal") == 2
        assert stages.count("finalist") == 1
        assert stages.count("champion") == 1

        slots = db.scalars(
            select(SimulationSlotModel).order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        assert len(slots) == 15
        assert all(
            len(
                [
                    group
                    for group in groups
                    if group.slot_id == slot.slot_id
                ]
            )
            == 1
            for slot in slots
        )
        first_day_ordinals = {
            slot.ordinal
            for slot in schedule.slots
            if slot.match_day_ordinal == 1
        }
        first_day_slot_ids = {
            slot.slot_id
            for slot in slots
            if slot.slot_ordinal in first_day_ordinals
        }
        opening_groups = [
            group for group in groups if group.slot_id in first_day_slot_ids
        ]
        assert len(opening_groups) == 8
        assert len(
            {
                AuthoritativeSlotMatchExecutor._load_group(
                    group
                ).authoritative_input.slot_start_fingerprint
                for group in opening_groups
            }
        ) == 8


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


@pytest.mark.smoke
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

    canonical_draw = SimpleNamespace(
        fingerprint="d" * 64,
        main=SimpleNamespace(
            nodes=(
                SimpleNamespace(node_id="sf-1"),
                SimpleNamespace(node_id="sf-2"),
                SimpleNamespace(node_id="final"),
            )
        ),
        qualification_brackets=(),
    )
    monkeypatch.setattr(
        TournamentDrawAuthorityStore,
        "get",
        lambda self, **kwargs: canonical_draw,
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
    assert walkover.authoritative_input.replacement_cutoff_authority.schema_version == (
        "tournament_player_replacement_cutoff.v2"
    )
    assert walkover.authoritative_input.replacement_cutoff_authority.draw_type == "main"
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


@pytest.mark.smoke
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

    restore_draw = SimpleNamespace(
        fingerprint="e" * 64,
        main=SimpleNamespace(
            nodes=(
                SimpleNamespace(node_id="sf-1"),
                SimpleNamespace(node_id="sf-2"),
                SimpleNamespace(node_id="final"),
            )
        ),
        qualification_brackets=(),
    )
    monkeypatch.setattr(
        TournamentDrawAuthorityStore,
        "get",
        lambda self, **kwargs: restore_draw,
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


@pytest.mark.pr_critical
def test_branch_fork_adapter_rebuilds_real_slot_plan_and_competitive_group(tmp_path):
    session, _, plan, results, _ = run_semifinals(
        tmp_path / "fork-remap-source.sqlite",
        ("sf-1", "sf-2"),
    )
    row = session.get(
        SimulationEventGroupModel,
        ("run", "branch", WEEK.ordinal, "slot-1", "sf-1"),
    )
    assert row is not None

    target_start = "target-slot-start-fingerprint"
    target_plan = remap_slot_plan(
        plan,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        slot_start_fingerprint_map={
            plan.slot_start_fingerprint: target_start,
        },
    )
    remapped = remap_competitive_group_payload(
        row.payload_json,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        slot_start_fingerprint_map={
            plan.slot_start_fingerprint: target_start,
        },
    )

    payload = json.loads(remapped.payload_json)
    target_input = payload["authoritative_input"]
    assert target_plan.branch_id == "target"
    assert target_plan.slot_start_fingerprint == target_start
    assert target_input["branch_id"] == "target"
    assert target_input["slot_start_fingerprint"] == target_start
    assert all(
        projection["source_sporting_fingerprint"] == target_start
        for projection in target_input["player_projections"]
    )
    assert remapped.match_input_fingerprint != row.match_input_fingerprint
    assert remapped.result_fingerprint != row.result_fingerprint
    assert len(remapped.effect_fingerprint_map) == len(results["sf-1"].effects)
    assert set(remapped.effect_fingerprint_map) == {
        effect.fingerprint for effect in results["sf-1"].effects
    }
    assert all(
        value not in remapped.effect_fingerprint_map
        for value in remapped.effect_fingerprint_map.values()
    )


@pytest.mark.pr_critical
def test_completed_slot_core_saved_revision_remaps_and_emits_sporting_v2_maps(tmp_path):
    session, executor, plan, results, checkpoint = run_semifinals(
        tmp_path / "fork-remap-core.sqlite",
        ("sf-1", "sf-2"),
    )
    payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    opening = get_sporting(
        session,
        run_id="run",
        branch_id="branch",
        week=WEEK,
    )
    assert opening is not None
    assert checkpoint is not None

    remapped = remap_completed_simulation_slot_core(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        opening_sporting_fingerprint_map={
            opening.fingerprint: "target-opening-sporting-fingerprint",
        },
    )

    assert remapped is not None
    component = remapped.component
    assert component["fingerprint"] != payload["content"]["simulation_slot_match_state"]["fingerprint"]
    assert all(value["branch_id"] == "target" for value in component["slots"])
    assert all(value["branch_id"] == "target" for value in component["groups"])
    assert remapped.slot_starts[plan.slot_start_fingerprint] != plan.slot_start_fingerprint
    assert remapped.terminal_checkpoints[checkpoint.fingerprint] != checkpoint.fingerprint
    source_result_fingerprints = {
        result.result_fingerprint for result in results.values()
    }
    assert set(remapped.results) == source_result_fingerprints
    source_effect_fingerprints = {
        effect.fingerprint
        for result in results.values()
        for effect in result.effects
    }
    assert set(remapped.match_effects) == source_effect_fingerprints

    from beta_engine.infrastructure.db.simulation_slot_state import _load

    target_payload = {
        "content": {
            "simulation_slot_match_state": component,
        }
    }
    loaded = _load(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert loaded is not None
    assert loaded["fingerprint"] == component["fingerprint"]


@pytest.mark.pr_critical
def test_simulation_command_receipt_fork_is_read_only_historical_audit():
    source_command = {
        "command_id": "slot-command-1",
        "run_id": "run",
        "branch_id": "branch",
        "expected_week": WEEK.model_dump(mode="json"),
        "expected_position_fingerprint": "1" * 64,
        "expected_revision_id": "source-revision",
        "group_id": None,
    }
    source_fp = fingerprint({"mode": "slot", "command": source_command})
    source_row = AuthoritativeSimulationCommandModel(
        run_id="run",
        branch_id="branch",
        command_id="slot-command-1",
        request_fingerprint=source_fp,
        status="complete",
        result_json=json.dumps(
            {
                "run_id": "run",
                "branch_id": "branch",
                "position_fingerprint": "2" * 64,
                "_request_evidence": {
                    "schema_version": "authoritative_simulation_request_evidence.v1",
                    "mode": "slot",
                    "command": source_command,
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )

    from beta_engine.infrastructure.db.player_slot_fork_remap import (
        _retarget_simulation_command_receipt_as_historical,
    )

    target_row = _retarget_simulation_command_receipt_as_historical(
        source_row,
        target_branch_id="target",
        target_base_revision_id="fork-revision",
    )
    payload = json.loads(target_row.result_json)

    assert target_row.run_id == "run"
    assert target_row.branch_id == "target"
    assert target_row.command_id == source_row.command_id
    assert target_row.status == "historical_fork"
    assert target_row.request_fingerprint != source_row.request_fingerprint
    assert payload["schema_version"] == (
        "authoritative_simulation_historical_fork_receipt.v2"
    )
    assert payload["target_base_revision_id"] == "fork-revision"
    assert payload["retryable"] is False
    assert payload["source_branch_id"] == "branch"
    assert payload["source_request_fingerprint"] == source_fp
    assert payload["source_status"] == "complete"
    assert payload["source_result"]["_request_evidence"]["command"] == source_command
    assert payload["source_request_evidence_fingerprint"] == fingerprint(
        payload["source_result"]["_request_evidence"]
    )

    from beta_engine.infrastructure.db.simulation_slot_state import (
        _validate_command_rows_shape,
    )

    _validate_command_rows_shape([target_row])
    tampered = json.loads(target_row.result_json)
    tampered["source_result"]["_request_evidence"]["mode"] = "match"
    target_row.result_json = json.dumps(
        tampered,
        sort_keys=True,
        separators=(",", ":"),
    )
    with pytest.raises(
        ValueError,
        match="historical simulation fork receipt request evidence is corrupt",
    ):
        _validate_command_rows_shape([target_row])

    target_row = _retarget_simulation_command_receipt_as_historical(
        source_row,
        target_branch_id="target",
        target_base_revision_id="fork-revision",
    )
    tampered_revision = json.loads(target_row.result_json)
    tampered_revision["target_base_revision_id"] = "different-fork-revision"
    target_row.result_json = json.dumps(
        tampered_revision,
        sort_keys=True,
        separators=(",", ":"),
    )
    with pytest.raises(
        ValueError,
        match="historical simulation fork receipt fingerprint is corrupt",
    ):
        _validate_command_rows_shape([target_row])


@pytest.mark.pr_critical
def test_simulation_command_receipt_fork_reconstructs_target_position_identity():
    from beta_engine.infrastructure.db.player_slot_fork_remap import (
        SimulationPositionForkIdentityGraph,
        _retarget_simulation_command_receipt_as_historical,
    )
    from beta_engine.infrastructure.db.simulation_slot_state import (
        _validate_command_rows_shape,
    )

    source_basis = {
        "scope": ["run", "branch", 0],
        "schedule": "source-schedule",
        "entry_slot_ordinals": [],
        "wc_slot_ordinals": [],
        "week_tournament_lock": "source-lock",
        "week_tournament_lock_conflicts": [],
        "entry_validation_slots": [],
        "current_slot_kind": "match",
        "current_slot_ordinal": 2,
        "proposed_schedule_requirement": ["event-one"],
        "slots": [
            ["slot-one", "complete", "source-plan-one", "source-terminal-json"],
            ["slot-two", "pending", "source-plan-two", None],
        ],
        "groups": [["group-one", "source-command-fp", "source-result-fp"]],
        "owned": [["event-one", "source-owned-fp"]],
        "tournament_authority": "source-tournament-authority",
        "sporting": "source-sporting",
        "lifecycle": "source-lifecycle",
        "branch_head": "source-revision",
        "draft": ["source-revision", "clean", 0],
        "transition_authority": "source-transition",
        "world": [0, "source-ranking"],
        "terminal": "source-terminal-fp",
        "empty_week_context": "source-empty-context",
    }
    source_command = {
        "command_id": "slot-command-v2",
        "run_id": "run",
        "branch_id": "branch",
        "expected_week": {"season_index": 0, "week": 1},
        "expected_position_fingerprint": fingerprint(source_basis),
        "expected_revision_id": "source-revision",
        "group_id": None,
    }
    source_evidence = {
        "schema_version": "authoritative_simulation_request_evidence.v2",
        "mode": "slot",
        "command": source_command,
        "opening_position_basis": source_basis,
    }
    source_row = AuthoritativeSimulationCommandModel(
        run_id="run",
        branch_id="branch",
        command_id="slot-command-v2",
        request_fingerprint=fingerprint(
            {"mode": "slot", "command": source_command}
        ),
        status="complete",
        result_json=json.dumps(
            {
                "position_fingerprint": "f" * 64,
                "_request_evidence": source_evidence,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    graph = SimulationPositionForkIdentityGraph(
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        target_base_revision_id="target-revision",
        schedule_fingerprints={"source-schedule": "target-schedule"},
        slot_plan_fingerprints={
            "source-plan-one": "target-plan-one",
            "source-plan-two": "target-plan-two",
        },
        group_command_fingerprints={
            "source-command-fp": "target-command-fp",
        },
        result_fingerprints={"source-result-fp": "target-result-fp"},
        terminal_checkpoint_payloads={
            "source-terminal-json": "target-terminal-json",
        },
        owned_tournament_fingerprints={
            "source-owned-fp": "target-owned-fp",
        },
        week_tournament_lock_fingerprints={
            "source-lock": "target-lock",
        },
        tournament_authority_fingerprints={
            "source-tournament-authority": "target-tournament-authority",
        },
        sporting_fingerprints={"source-sporting": "target-sporting"},
        lifecycle_fingerprints={"source-lifecycle": "target-lifecycle"},
        transition_authority_fingerprints={
            "source-transition": "target-transition",
        },
        ranking_snapshot_fingerprints={"source-ranking": "target-ranking"},
        terminal_checkpoint_fingerprints={
            "source-terminal-fp": "target-terminal-fp",
        },
        sporting_context_fingerprints={
            "source-empty-context": "target-empty-context",
        },
    )

    target_row = _retarget_simulation_command_receipt_as_historical(
        source_row,
        target_branch_id="target",
        target_base_revision_id="target-revision",
        position_identity_graph=graph,
    )
    payload = json.loads(target_row.result_json)
    target_evidence = payload["target_request_evidence"]
    target_command = target_evidence["command"]
    target_basis = target_evidence["opening_position_basis"]

    assert payload["schema_version"] == (
        "authoritative_simulation_historical_fork_receipt.v3"
    )
    assert payload["retryable"] is False
    assert target_command["branch_id"] == "target"
    assert target_command["expected_revision_id"] == "target-revision"
    assert target_basis["scope"] == ["run", "target", 0]
    assert target_basis["branch_head"] == "target-revision"
    assert target_basis["draft"] == ["target-revision", "clean", 0]
    assert target_basis["schedule"] == "target-schedule"
    assert target_basis["slots"][0][2:] == [
        "target-plan-one",
        "target-terminal-json",
    ]
    assert target_basis["groups"][0][1:] == [
        "target-command-fp",
        "target-result-fp",
    ]
    assert target_basis["owned"] == [["event-one", "target-owned-fp"]]
    assert target_basis["tournament_authority"] == "target-tournament-authority"
    assert target_basis["sporting"] == "target-sporting"
    assert target_basis["lifecycle"] == "target-lifecycle"
    assert target_basis["transition_authority"] == "target-transition"
    assert target_basis["world"] == [0, "target-ranking"]
    assert target_basis["terminal"] == "target-terminal-fp"
    assert target_basis["empty_week_context"] == "target-empty-context"
    assert target_command["expected_position_fingerprint"] == fingerprint(
        target_basis
    )
    assert payload["target_request_fingerprint"] == fingerprint(
        {"mode": "slot", "command": target_command}
    )

    _validate_command_rows_shape([target_row])

    tampered = json.loads(target_row.result_json)
    tampered["target_request_evidence"]["opening_position_basis"]["scope"][1] = (
        "tampered-target"
    )
    target_row.result_json = json.dumps(
        tampered,
        sort_keys=True,
        separators=(",", ":"),
    )
    with pytest.raises(
        ValueError,
        match="historical simulation fork target request evidence is corrupt",
    ):
        _validate_command_rows_shape([target_row])


@pytest.mark.pr_critical
def test_simulation_command_receipt_fork_reconstructs_target_public_result():
    from beta_engine.infrastructure.db.player_slot_fork_remap import (
        SimulationPositionForkIdentityGraph,
        _retarget_simulation_command_receipt_as_historical,
    )
    from beta_engine.infrastructure.db.simulation_slot_state import (
        _validate_command_rows_shape,
    )

    opening_basis = {
        "scope": ["run", "branch", 0],
        "schedule": None,
        "entry_slot_ordinals": [],
        "wc_slot_ordinals": [],
        "week_tournament_lock": None,
        "week_tournament_lock_conflicts": [],
        "entry_validation_slots": [],
        "current_slot_kind": "match",
        "current_slot_ordinal": 1,
        "proposed_schedule_requirement": [],
        "slots": [],
        "groups": [],
        "owned": [],
        "tournament_authority": None,
        "sporting": None,
        "lifecycle": None,
        "branch_head": "source-revision",
        "draft": ["source-revision", "clean", 0],
        "transition_authority": None,
        "world": None,
        "terminal": None,
        "empty_week_context": None,
    }
    closing_basis = {
        **opening_basis,
        "current_slot_kind": None,
        "current_slot_ordinal": None,
    }
    source_command = {
        "command_id": "result-contract-command",
        "run_id": "run",
        "branch_id": "branch",
        "expected_week": {"season_index": 0, "week": 1},
        "expected_position_fingerprint": fingerprint(opening_basis),
        "expected_revision_id": "source-revision",
        "group_id": None,
    }
    source_evidence = {
        "schema_version": "authoritative_simulation_request_evidence.v3",
        "mode": "slot",
        "command": source_command,
        "opening_position_basis": opening_basis,
        "closing_position_basis": closing_basis,
    }
    source_result = {
        "run_id": "run",
        "branch_id": "branch",
        "current_week": {"season_index": 0, "week": 1},
        "current_slot_kind": None,
        "current_slot_id": None,
        "slot_ordinal": None,
        "unresolved_group_ids": [],
        "eligible_match_ids": [],
        "blocked_match_ids": [],
        "current_slot_complete": True,
        "supported_tournament_complete": False,
        "week_ready_for_transition": False,
        "transition_blockers": ["tournament_source_missing"],
        "terminal_sporting_fingerprint": None,
        "position_fingerprint": fingerprint(closing_basis),
        "_request_evidence": source_evidence,
    }
    source_row = AuthoritativeSimulationCommandModel(
        run_id="run",
        branch_id="branch",
        command_id=source_command["command_id"],
        request_fingerprint=fingerprint(
            {"mode": "slot", "command": source_command}
        ),
        status="complete",
        result_json=json.dumps(
            source_result,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    graph = SimulationPositionForkIdentityGraph(
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        target_base_revision_id="target-revision",
        schedule_fingerprints={},
        slot_plan_fingerprints={},
        group_command_fingerprints={},
        result_fingerprints={},
        terminal_checkpoint_payloads={},
        owned_tournament_fingerprints={},
        week_tournament_lock_fingerprints={},
        tournament_authority_fingerprints={},
        sporting_fingerprints={},
        lifecycle_fingerprints={},
        transition_authority_fingerprints={},
        ranking_snapshot_fingerprints={},
        terminal_checkpoint_fingerprints={},
        sporting_context_fingerprints={},
    )

    target_row = _retarget_simulation_command_receipt_as_historical(
        source_row,
        target_branch_id="target",
        target_base_revision_id="target-revision",
        position_identity_graph=graph,
    )
    payload = json.loads(target_row.result_json)
    target_evidence = payload["target_request_evidence"]
    target_result = payload["target_result"]
    target_closing_basis = target_evidence["closing_position_basis"]

    assert payload["schema_version"] == (
        "authoritative_simulation_historical_fork_receipt.v5"
    )
    assert payload["retryable"] is True
    assert target_evidence["schema_version"] == (
        "authoritative_simulation_request_evidence.v3"
    )
    assert target_closing_basis["scope"] == ["run", "target", 0]
    assert target_closing_basis["branch_head"] == "target-revision"
    assert target_result["branch_id"] == "target"
    assert target_result["position_fingerprint"] == fingerprint(
        target_closing_basis
    )
    assert payload["target_result_fingerprint"] == fingerprint(target_result)
    assert {
        key: value
        for key, value in target_result.items()
        if key not in {"branch_id", "position_fingerprint"}
    } == {
        key: value
        for key, value in source_result.items()
        if key not in {
            "branch_id",
            "position_fingerprint",
            "_request_evidence",
        }
    }

    _validate_command_rows_shape([target_row])

    tampered = json.loads(target_row.result_json)
    tampered["target_result"]["branch_id"] = "wrong-target"
    target_row.result_json = json.dumps(
        tampered,
        sort_keys=True,
        separators=(",", ":"),
    )
    with pytest.raises(
        ValueError,
        match="historical simulation fork target result identity is corrupt",
    ):
        _validate_command_rows_shape([target_row])


@pytest.mark.pr_critical
def test_historical_v5_exact_retry_returns_target_result_without_execution(tmp_path):
    from beta_engine.infrastructure.db.player_slot_fork_remap import (
        SimulationPositionForkIdentityGraph,
        _retarget_simulation_command_receipt_as_historical,
    )

    driver, factory, week = _driver_fixture(tmp_path / "historical-v5-retry")
    opening_basis = {
        "scope": ["run", "branch", week.ordinal],
        "schedule": None,
        "entry_slot_ordinals": [],
        "wc_slot_ordinals": [],
        "week_tournament_lock": None,
        "week_tournament_lock_conflicts": [],
        "entry_validation_slots": [],
        "current_slot_kind": "match",
        "current_slot_ordinal": 1,
        "proposed_schedule_requirement": [],
        "slots": [],
        "groups": [],
        "owned": [],
        "tournament_authority": None,
        "sporting": None,
        "lifecycle": None,
        "branch_head": "source-revision",
        "draft": ["source-revision", "clean", 0],
        "transition_authority": None,
        "world": None,
        "terminal": None,
        "empty_week_context": None,
    }
    closing_basis = {
        **opening_basis,
        "current_slot_kind": None,
        "current_slot_ordinal": None,
    }
    source_command = AuthoritativeSimulationCommand(
        command_id="historical-retry-command",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=fingerprint(opening_basis),
        expected_revision_id="source-revision",
        group_id=None,
    )
    source_evidence = {
        "schema_version": "authoritative_simulation_request_evidence.v3",
        "mode": "slot",
        "command": source_command.model_dump(mode="json"),
        "opening_position_basis": opening_basis,
        "closing_position_basis": closing_basis,
    }
    source_result = {
        "run_id": "run",
        "branch_id": "branch",
        "current_week": week.model_dump(mode="json"),
        "current_slot_kind": None,
        "current_slot_id": None,
        "slot_ordinal": None,
        "unresolved_group_ids": [],
        "eligible_match_ids": [],
        "blocked_match_ids": [],
        "current_slot_complete": True,
        "supported_tournament_complete": False,
        "week_ready_for_transition": False,
        "transition_blockers": ["tournament_source_missing"],
        "terminal_sporting_fingerprint": None,
        "position_fingerprint": fingerprint(closing_basis),
        "_request_evidence": source_evidence,
    }
    source_row = AuthoritativeSimulationCommandModel(
        run_id="run",
        branch_id="branch",
        command_id=source_command.command_id,
        request_fingerprint=fingerprint(
            {"mode": "slot", "command": source_command.model_dump(mode="json")}
        ),
        status="complete",
        result_json=json.dumps(
            source_result,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    target_revision = "target-revision"
    graph = SimulationPositionForkIdentityGraph(
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        target_base_revision_id=target_revision,
        schedule_fingerprints={},
        slot_plan_fingerprints={},
        group_command_fingerprints={},
        result_fingerprints={},
        terminal_checkpoint_payloads={},
        owned_tournament_fingerprints={},
        week_tournament_lock_fingerprints={},
        tournament_authority_fingerprints={},
        sporting_fingerprints={},
        lifecycle_fingerprints={},
        transition_authority_fingerprints={},
        ranking_snapshot_fingerprints={},
        terminal_checkpoint_fingerprints={},
        sporting_context_fingerprints={},
    )
    target_row = _retarget_simulation_command_receipt_as_historical(
        source_row,
        target_branch_id="target",
        target_base_revision_id=target_revision,
        position_identity_graph=graph,
    )
    target_payload = json.loads(target_row.result_json)
    assert target_payload["schema_version"] == (
        "authoritative_simulation_historical_fork_receipt.v5"
    )
    assert target_payload["retryable"] is True
    target_command = AuthoritativeSimulationCommand.model_validate(
        target_payload["target_request_evidence"]["command"]
    )

    with factory.begin() as session:
        session.add(
            RunBranchModel(
                branch_id="target",
                run_id="run",
                display_name="Target fork",
                saved_head_revision_id=target_revision,
            )
        )
        session.add(target_row)

    with factory() as session:
        before_slots = len(session.scalars(select(SimulationSlotModel)).all())
        before_groups = len(session.scalars(select(SimulationEventGroupModel)).all())

    replayed = driver.simulate_next_slot(target_command)
    assert replayed == target_payload["target_result"]

    with factory() as session:
        assert len(session.scalars(select(SimulationSlotModel)).all()) == before_slots
        assert len(session.scalars(select(SimulationEventGroupModel)).all()) == before_groups
        stored = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "target", target_command.command_id),
        )
        assert stored is not None
        assert stored.status == "historical_fork"
        assert json.loads(stored.result_json) == target_payload

    changed = target_command.model_copy(
        update={"expected_position_fingerprint": "0" * 64}
    )
    with pytest.raises(
        ValueError,
        match="simulation command ID already has a different request",
    ):
        driver.simulate_next_slot(changed)


@pytest.mark.pr_critical
def test_simulation_command_receipt_fork_keeps_v2_when_target_position_is_unsupported():
    from beta_engine.infrastructure.db.player_slot_fork_remap import (
        SimulationPositionForkIdentityGraph,
        _retarget_simulation_command_receipt_as_historical,
    )

    source_basis = {
        "scope": ["run", "branch", 0],
        "schedule": None,
        "entry_slot_ordinals": [1],
        "wc_slot_ordinals": [],
        "week_tournament_lock": None,
        "week_tournament_lock_conflicts": [],
        "entry_validation_slots": [[1, "source-entry-validation-fp"]],
        "current_slot_kind": "match",
        "current_slot_ordinal": 2,
        "proposed_schedule_requirement": [],
        "slots": [],
        "groups": [],
        "owned": [],
        "tournament_authority": None,
        "sporting": None,
        "lifecycle": None,
        "branch_head": "source-revision",
        "draft": ["source-revision", "clean", 0],
        "transition_authority": None,
        "world": None,
        "terminal": None,
        "empty_week_context": None,
    }
    source_command = {
        "command_id": "unsupported-v2-command",
        "run_id": "run",
        "branch_id": "branch",
        "expected_week": {"season_index": 0, "week": 1},
        "expected_position_fingerprint": fingerprint(source_basis),
        "expected_revision_id": "source-revision",
        "group_id": None,
    }
    source_row = AuthoritativeSimulationCommandModel(
        run_id="run",
        branch_id="branch",
        command_id="unsupported-v2-command",
        request_fingerprint=fingerprint(
            {"mode": "slot", "command": source_command}
        ),
        status="complete",
        result_json=json.dumps(
            {
                "_request_evidence": {
                    "schema_version": "authoritative_simulation_request_evidence.v2",
                    "mode": "slot",
                    "command": source_command,
                    "opening_position_basis": source_basis,
                }
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    graph = SimulationPositionForkIdentityGraph(
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        target_base_revision_id="target-revision",
        schedule_fingerprints={},
        slot_plan_fingerprints={},
        group_command_fingerprints={},
        result_fingerprints={},
        terminal_checkpoint_payloads={},
        owned_tournament_fingerprints={},
        week_tournament_lock_fingerprints={},
        tournament_authority_fingerprints={},
        sporting_fingerprints={},
        lifecycle_fingerprints={},
        transition_authority_fingerprints={},
        ranking_snapshot_fingerprints={},
        terminal_checkpoint_fingerprints={},
        sporting_context_fingerprints={},
    )

    target_row = _retarget_simulation_command_receipt_as_historical(
        source_row,
        target_branch_id="target",
        target_base_revision_id="target-revision",
        position_identity_graph=graph,
    )
    payload = json.loads(target_row.result_json)

    assert payload["schema_version"] == (
        "authoritative_simulation_historical_fork_receipt.v2"
    )
    assert "target_request_evidence" not in payload
    assert payload["retryable"] is False

    from beta_engine.infrastructure.db.simulation_slot_state import (
        _validate_command_rows_shape,
    )

    _validate_command_rows_shape([target_row])


@pytest.mark.pr_critical
def test_coupled_sporting_v2_and_slot_history_remap_real_week(tmp_path):
    session, _, plan, results, checkpoint = run_semifinals(
        tmp_path / "coupled-fork-remap.sqlite",
        ("sf-1", "sf-2"),
    )
    opening = get_sporting(
        session,
        run_id="run",
        branch_id="branch",
        week=WEEK,
    )
    assert opening is not None
    context = resolve_completed_context_from_authoritative_matches(
        session,
        run_id="run",
        branch_id="branch",
        completed_week=WEEK,
        player_ids=tuple(player.player_id for player in opening.players),
    )
    assert context.schema_version == "completed_week_sporting_context.v2"
    assert checkpoint is not None
    assert context.terminal_sporting_fingerprint == checkpoint.fingerprint

    payload = {"content": {}}
    capture_saved_sporting(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    capture_saved_simulation_slots(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    source_sporting = payload["content"]["player_sporting_state"]
    source_simulation = payload["content"]["simulation_slot_match_state"]

    remapped = remap_coupled_player_slot_history(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
    )

    assert remapped is not None
    target_sporting = remapped.sporting_component
    target_simulation = remapped.simulation_component
    assert target_sporting["fingerprint"] != payload["content"]["player_sporting_state"]["fingerprint"]
    assert target_simulation["fingerprint"] != payload["content"]["simulation_slot_match_state"]["fingerprint"]
    assert target_sporting["states"][0]["branch_id"] == "target"
    assert target_sporting["contexts"][0]["branch_id"] == "target"
    assert all(value["branch_id"] == "target" for value in target_simulation["slots"])
    assert all(value["branch_id"] == "target" for value in target_simulation["groups"])
    assert target_sporting["contexts"][0]["terminal_sporting_fingerprint"] == remapped.terminal_checkpoint_fingerprints[checkpoint.fingerprint]
    assert set(target_sporting["contexts"][0]["source_fingerprints"]) == {
        remapped.result_fingerprints[result.result_fingerprint]
        for result in results.values()
    }
    assert set(target_sporting["contexts"][0]["match_effect_fingerprints"]) == {
        remapped.match_effect_fingerprints[effect.fingerprint]
        for result in results.values()
        for effect in result.effects
    }
    assert target_simulation["slots"][0]["slot_start_fingerprint"] != plan.slot_start_fingerprint
    source_state_fp = fingerprint(source_sporting["states"][0])
    target_state_fp = fingerprint(target_sporting["states"][0])
    assert remapped.sporting_fingerprints[source_state_fp] == target_state_fp
    for source_slot, target_slot in zip(
        source_simulation["slots"],
        target_simulation["slots"],
        strict=True,
    ):
        assert (
            remapped.slot_plan_fingerprints[source_slot["plan_fingerprint"]]
            == target_slot["plan_fingerprint"]
        )
        assert (
            remapped.terminal_checkpoint_payloads[
                source_slot["terminal_checkpoint_json"]
            ]
            == target_slot["terminal_checkpoint_json"]
        )
    for source_group, target_group in zip(
        source_simulation["groups"],
        target_simulation["groups"],
        strict=True,
    ):
        assert (
            remapped.group_command_fingerprints[
                source_group["command_fingerprint"]
            ]
            == target_group["command_fingerprint"]
        )


@pytest.mark.pr_critical
def test_coupled_fork_remaps_week_schedule_and_legacy_adopted_authority(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "fork-schedule-authority"
    )
    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="fork-schedule",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )

    with factory.begin() as session:
        _, source_authority_fp = driver._authority_package(
            session,
            "run",
            "branch",
            week,
            adopt=True,
        )

    with factory() as session:
        payload = {"content": {}}
        capture_saved_sporting(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        capture_saved_simulation_slots(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        source_component = payload["content"]["simulation_slot_match_state"]
        assert source_component["schedules"]
        assert source_component["authorities"]
        assert not source_component.get("commands")

    remapped = remap_coupled_player_slot_history(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
    )

    assert remapped is not None
    target_component = remapped.simulation_component
    target_schedule_row = target_component["schedules"][0]
    target_authority_row = target_component["authorities"][0]

    assert target_schedule_row["branch_id"] == "target"
    assert (
        target_schedule_row["schedule_fingerprint"]
        != source_component["schedules"][0]["schedule_fingerprint"]
    )
    assert (
        target_schedule_row["request_fingerprint"]
        != source_component["schedules"][0]["request_fingerprint"]
    )
    target_schedule = WeekSimulationSchedule.model_validate_json(
        target_schedule_row["payload_json"]
    )
    assert target_schedule.branch_id == "target"
    assert target_schedule.slots == WeekSimulationSchedule.model_validate_json(
        source_component["schedules"][0]["payload_json"]
    ).slots

    assert target_authority_row["branch_id"] == "target"
    assert target_authority_row["authority_fingerprint"] != source_authority_fp
    assert (
        target_authority_row["package_json"]
        == source_component["authorities"][0]["package_json"]
    )
    assert (
        remapped.schedule_fingerprints[
            source_component["schedules"][0]["schedule_fingerprint"]
        ]
        == target_schedule_row["schedule_fingerprint"]
    )
    assert (
        remapped.adopted_tournament_authority_fingerprints[source_authority_fp]
        == target_authority_row["authority_fingerprint"]
    )


@pytest.mark.pr_critical
def test_coupled_fork_remaps_entry_wc_and_draw_input_chain(tmp_path):
    session, _, _, _, _ = run_semifinals(
        tmp_path / "pre-draw-chain-fork.sqlite",
        ("sf-1", "sf-2"),
    )
    if session.get(RunContainerModel, "run") is None:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
    if session.get(RunBranchModel, "branch") is None:
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Source",
            )
        )
    session.flush()
    snapshot = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="ranking-policy"),
        players=(),
        results=(),
        previous=None,
    )
    source_ranking_authority = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-draw",
        ranking_week=WEEK,
        ranking_snapshot=snapshot,
        adopted_by_command_id="adopt-ranking",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(
        source_ranking_authority
    )
    target_snapshot = snapshot.model_copy(update={"branch_id": "target"})
    target_ranking_authority = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="target",
        event_id="event-draw",
        ranking_week=WEEK,
        ranking_snapshot=target_snapshot,
        adopted_by_command_id="adopt-ranking",
    )
    apps = (
        TournamentEntryApplication(
            application_id="a1",
            run_id="run",
            branch_id="branch",
            event_id="event-draw",
            player_id="p1",
            entry_window="main",
            decision_slot_ordinal=1,
            nr_tie_break_token="1",
        ),
        TournamentEntryApplication(
            application_id="a2",
            run_id="run",
            branch_id="branch",
            event_id="event-draw",
            player_id="p2",
            entry_window="main",
            decision_slot_ordinal=1,
            nr_tie_break_token="2",
        ),
    )
    capacity = TournamentEntryFieldCapacity(
        main_draw_size=4,
        wild_card_slots=1,
        bye_slots=1,
    )
    source_field = TournamentEntryFieldResolver.build_initial(
        authority=source_ranking_authority,
        applications=apps,
        capacity=capacity,
    )
    apps_fp = _applications_fingerprint(apps)
    source_field_request = entry_request_fingerprint(
        {
            "mode": "initial",
            "run_id": "run",
            "branch_id": "branch",
            "event_id": "event-draw",
            "authority_fingerprint": source_ranking_authority.fingerprint,
            "applications_fingerprint": apps_fp,
            "capacity": capacity.model_dump(mode="json"),
        }
    )
    source_wc = TournamentWildCardAuthorityBuilder.build(
        field=source_field,
        field_sequence=1,
        command_id="resolve-wc",
        original_wild_card_player_ids=("wc-1",),
    )
    wc_request = {
        "entry_field_fingerprint": source_field.fingerprint,
        "field_sequence": 1,
        "original_wild_card_player_ids": ["wc-1"],
        "reserve_wild_card_player_ids": [],
        "unavailable_player_ids": [],
    }
    source_draw_input = TournamentDrawInputAuthorityBuilder.build(
        authority=source_ranking_authority,
        field=source_field,
        field_sequence=1,
        command_id="commit-draw",
        draw_seed=17,
        main_seed_count=None,
        qualification_seed_count=None,
        schema_version="tournament_draw_input_authority.v3",
        wild_card_authority=source_wc,
    )
    draw_request = TournamentDrawInputAuthorityStore._request(
        ranking_authority_fingerprint=source_ranking_authority.fingerprint,
        entry_field_fingerprint=source_field.fingerprint,
        field_sequence=1,
        draw_seed=17,
        main_seed_count=source_draw_input.main_seed_count,
        qualification_seed_count=source_draw_input.qualification_seed_count,
        wild_card_authority_fingerprint=source_wc.fingerprint,
    )
    session.add(
        TournamentEntryFieldVersionModel(
            run_id="run",
            branch_id="branch",
            event_id="event-draw",
            sequence=1,
            command_id="field-cut",
            request_fingerprint=source_field_request,
            field_fingerprint=source_field.fingerprint,
            predecessor_fingerprint=None,
            ranking_authority_fingerprint=source_ranking_authority.fingerprint,
            applications_fingerprint=apps_fp,
            applications_json=_applications_json(apps),
            payload_json=source_field.model_dump_json(),
        )
    )
    session.add(
        TournamentWildCardAuthorityModel(
            run_id="run",
            branch_id="branch",
            event_id="event-draw",
            command_id="resolve-wc",
            request_fingerprint=fingerprint(wc_request),
            authority_fingerprint=source_wc.fingerprint,
            entry_field_fingerprint=source_field.fingerprint,
            field_sequence=1,
            payload_json=source_wc.model_dump_json(),
        )
    )
    session.add(
        TournamentDrawInputAuthorityModel(
            run_id="run",
            branch_id="branch",
            event_id="event-draw",
            command_id="commit-draw",
            request_fingerprint=draw_input_request_fingerprint(draw_request),
            authority_fingerprint=source_draw_input.fingerprint,
            ranking_authority_fingerprint=source_ranking_authority.fingerprint,
            entry_field_fingerprint=source_field.fingerprint,
            field_sequence=1,
            payload_json=source_draw_input.model_dump_json(),
        )
    )
    session.flush()
    source_draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event-draw",
        command_id="generate-draw",
    )
    source_process = TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event-draw",
        command_id="configure-process",
        main_process_window_count=3,
    )
    adopted_event = CalendarEvent(
        event_id="event-draw",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="fork-draw-template",
        event_name="Fork Draw Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=0,
        seeds_count=2,
        qualifier_spots=0,
        ranking_points_table={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
        },
        ranking_configuration_legacy=False,
        calendar_fingerprint="c" * 64,
    )
    adopted_points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )
    source_adopted_items = (
        _AdoptedTournamentEvidence(
            event_id="event-draw",
            calendar_event=adopted_event,
            point_award_authority=adopted_points,
            draw_authority_fingerprint=source_draw.fingerprint,
        ),
    )
    source_adopted_fingerprint = (
        AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
            "run",
            "branch",
            WEEK,
            source_adopted_items,
        )
    )
    session.add(
        AdoptedTournamentAuthorityModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            event_id="event-draw",
            authority_fingerprint=source_adopted_fingerprint,
            package_json=AuthoritativeRunSimulationDriver._encode_adopted_authority(
                source_adopted_items
            ),
        )
    )
    session.flush()

    payload = {"content": {}}
    capture_saved_sporting(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    capture_saved_simulation_slots(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    remapped = remap_coupled_player_slot_history(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
        tournament_ranking_authority_map={
            source_ranking_authority.fingerprint: target_ranking_authority
        },
    )

    assert remapped is not None
    component = remapped.simulation_component
    target_field_row = component["entry_fields"][0]
    target_wc_row = component["wild_card_authorities"][0]
    target_draw_input_row = component["draw_inputs"][0]
    target_draw_row = component["draw_authorities"][0]
    target_process_row = component["draw_process_authorities"][0]
    target_adopted_row = component["authorities"][0]
    target_adopted_items = AuthoritativeRunSimulationDriver._decode_adopted_authority(
        target_adopted_row["package_json"]
    )
    assert target_field_row["branch_id"] == "target"
    assert target_wc_row["branch_id"] == "target"
    assert target_draw_input_row["branch_id"] == "target"
    assert target_draw_row["branch_id"] == "target"
    assert target_process_row["branch_id"] == "target"
    assert target_field_row["field_fingerprint"] != source_field.fingerprint
    assert target_wc_row["authority_fingerprint"] != source_wc.fingerprint
    assert (
        target_draw_input_row["authority_fingerprint"]
        != source_draw_input.fingerprint
    )
    assert target_draw_row["authority_fingerprint"] != source_draw.fingerprint
    assert target_process_row["authority_fingerprint"] != source_process.fingerprint
    assert (
        target_draw_input_row["ranking_authority_fingerprint"]
        == target_ranking_authority.fingerprint
    )
    assert (
        target_draw_input_row["entry_field_fingerprint"]
        == target_field_row["field_fingerprint"]
    )
    assert (
        target_draw_row["draw_input_fingerprint"]
        == target_draw_input_row["authority_fingerprint"]
    )
    assert (
        target_process_row["draw_authority_fingerprint"]
        == target_draw_row["authority_fingerprint"]
    )
    assert target_adopted_row["branch_id"] == "target"
    assert (
        target_adopted_row["authority_fingerprint"]
        != source_adopted_fingerprint
    )
    assert (
        target_adopted_items[0].draw_authority_fingerprint
        == target_draw_row["authority_fingerprint"]
    )
    assert (
        target_adopted_items[0].draw_authority_fingerprint
        != source_draw.fingerprint
    )


@pytest.mark.pr_critical
def test_special_revision_frozen_evidence_retargets_nested_match_identity():
    source_result = "1" * 64
    target_result = "2" * 64
    source = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id="withdrawn",
        played_matches=(
            TournamentPlayedMatchCutoffEvidence(
                match_id="m1",
                week_ordinal=0,
                slot_id="slot-1",
                slot_ordinal=1,
                group_id="group-1",
                result_fingerprint=source_result,
                opponent_player_id="opponent",
                outcome="win",
            ),
        ),
    )

    target = _retarget_frozen_evidence(
        source,
        target_branch_id="target",
        fingerprint_map={source_result: target_result},
    )

    assert target.branch_id == "target"
    assert target.played_matches[0].result_fingerprint == target_result
    assert target.status == source.status
    assert target.fingerprint != source.fingerprint


@pytest.mark.pr_critical
def test_lucky_loser_auto_bye_order_retargets_derived_terminal_identity():
    source_bracket = "a" * 64
    target_bracket = "b" * 64
    source_elimination = "c" * 64
    target_elimination = "d" * 64
    source_draw = "e" * 64
    target_draw = "f" * 64
    source_ranking = "1" * 64
    target_ranking = "2" * 64

    source_auto = TournamentLuckyLoserAutoByeTerminalEvidence(
        match_id="q-terminal",
        section_id="Q1",
        winner_player_id="q-winner",
        qualification_bracket_fingerprint=source_bracket,
    )
    source_candidate = TournamentLuckyLoserCandidate(
        player_id="q-loser",
        priority_ordinal=1,
        qualification_round_reached=1,
        tournament_ranking=7,
        elimination_match_id="q-semi",
        elimination_result_fingerprint=source_elimination,
    )
    source = TournamentLuckyLoserOrderAuthority(
        schema_version="tournament_lucky_loser_order.v2",
        run_id="run",
        branch_id="branch",
        event_id="event",
        draw_authority_fingerprint=source_draw,
        tournament_ranking_authority_fingerprint=source_ranking,
        qualification_terminal_match_ids=("q-terminal",),
        qualification_terminal_result_fingerprints=(source_auto.fingerprint,),
        qualification_auto_bye_terminals=(source_auto,),
        candidates=(source_candidate,),
    )

    target = _retarget_lucky_loser_order_authority(
        source,
        target_branch_id="target",
        fingerprint_map={
            source_bracket: target_bracket,
            source_elimination: target_elimination,
            source_draw: target_draw,
            source_ranking: target_ranking,
        },
    )

    target_auto = target.qualification_auto_bye_terminals[0]
    assert target.branch_id == "target"
    assert target.draw_authority_fingerprint == target_draw
    assert target.tournament_ranking_authority_fingerprint == target_ranking
    assert target_auto.qualification_bracket_fingerprint == target_bracket
    assert target_auto.fingerprint != source_auto.fingerprint
    assert target.qualification_terminal_result_fingerprints == (
        target_auto.fingerprint,
    )
    assert target.candidates[0].elimination_result_fingerprint == target_elimination
    assert target.fingerprint != source.fingerprint


@pytest.mark.pr_critical
def test_lucky_loser_v2_rejects_detached_auto_bye_terminal_fingerprint():
    source_auto = TournamentLuckyLoserAutoByeTerminalEvidence(
        match_id="q-terminal",
        section_id="Q1",
        winner_player_id="q-winner",
        qualification_bracket_fingerprint="a" * 64,
    )

    with pytest.raises(
        ValueError,
        match="auto-BYE terminal fingerprint differs from embedded evidence",
    ):
        TournamentLuckyLoserOrderAuthority(
            schema_version="tournament_lucky_loser_order.v2",
            run_id="run",
            branch_id="branch",
            event_id="event",
            draw_authority_fingerprint="b" * 64,
            tournament_ranking_authority_fingerprint="c" * 64,
            qualification_terminal_match_ids=("q-terminal",),
            qualification_terminal_result_fingerprints=("d" * 64,),
            qualification_auto_bye_terminals=(source_auto,),
            candidates=(),
        )


@pytest.mark.pr_critical
def test_lucky_loser_order_fails_closed_when_nested_result_mapping_is_missing():
    source_auto = TournamentLuckyLoserAutoByeTerminalEvidence(
        match_id="q-terminal",
        section_id="Q1",
        winner_player_id="q-winner",
        qualification_bracket_fingerprint="a" * 64,
    )
    source = TournamentLuckyLoserOrderAuthority(
        schema_version="tournament_lucky_loser_order.v2",
        run_id="run",
        branch_id="branch",
        event_id="event",
        draw_authority_fingerprint="b" * 64,
        tournament_ranking_authority_fingerprint="c" * 64,
        qualification_terminal_match_ids=("q-terminal",),
        qualification_terminal_result_fingerprints=(source_auto.fingerprint,),
        qualification_auto_bye_terminals=(source_auto,),
        candidates=(
            TournamentLuckyLoserCandidate(
                player_id="q-loser",
                priority_ordinal=1,
                qualification_round_reached=1,
                tournament_ranking=9,
                elimination_match_id="q-semi",
                elimination_result_fingerprint="d" * 64,
            ),
        ),
    )

    with pytest.raises(
        SimulationSlotForkRemapUnsupportedError,
        match="candidate elimination.*without a target mapping",
    ):
        _retarget_lucky_loser_order_authority(
            source,
            target_branch_id="target",
            fingerprint_map={
                "a" * 64: "1" * 64,
                "b" * 64: "2" * 64,
                "c" * 64: "3" * 64,
            },
        )


@pytest.mark.pr_critical
def test_pre_q_replacement_source_retargets_every_branch_owned_binding():
    source_cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id="main-player",
        played_matches=(),
        draw_type="main",
    )
    source = TournamentReplacementSourceAuthority(
        schema_version="tournament_replacement_source.v1",
        run_id="run",
        branch_id="branch",
        event_id="event",
        withdrawn_player_id="main-player",
        predecessor_draw_fingerprint="4" * 64,
        predecessor_draw_input_fingerprint="5" * 64,
        physical_slot_index=2,
        source="qualification_promotion",
        selected_player_id="q-player",
        source_ordinal=1,
        replacement_cutoff_authority=source_cutoff,
        unavailable_player_ids=(),
        prior_lucky_loser_player_ids=(),
        external_reserve_player_ids=("reserve",),
        base_wild_card_authority_fingerprint="6" * 64,
    )

    target = _retarget_replacement_source_authority(
        source,
        target_branch_id="target",
        fingerprint_map={
            "4" * 64: "7" * 64,
            "5" * 64: "8" * 64,
            "6" * 64: "9" * 64,
        },
    )

    assert target.branch_id == "target"
    assert target.predecessor_draw_fingerprint == "7" * 64
    assert target.predecessor_draw_input_fingerprint == "8" * 64
    assert target.base_wild_card_authority_fingerprint == "9" * 64
    assert target.replacement_cutoff_authority.branch_id == "target"
    assert target.replacement_cutoff_authority.status == "replacement_open"
    assert target.selected_player_id == source.selected_player_id
    assert target.fingerprint != source.fingerprint


@pytest.mark.pr_critical
def test_real_q_receipts_ll_vacancy_fill_survive_fork_restore_retry(tmp_path):
    player_ids = ("A", "B", "C", "D", "E", "F", "G")
    session = session_at(
        tmp_path / "real-q-ll-fork-restore.sqlite",
        player_ids,
        WEEK,
    )
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Real Q LL fork restore",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="branch",
            display_name="Source",
        )
    )
    session.flush()

    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    ranking_week = RankingWeek(season_index=0, week=3)
    ranking_players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"rank-{player_id}",
            tour_entry_week=completed,
        )
        for player_id in player_ids
    )
    ranking_results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=(len(player_ids) - index) * 10,
        )
        for index, player_id in enumerate(player_ids)
    )
    source_snapshot = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=ranking_week,
        policy=OfficialRankingPolicy(policy_id="real-q-ll-ranking"),
        players=ranking_players,
        results=ranking_results,
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=ranking_week.ordinal,
            snapshot_fingerprint=source_snapshot.fingerprint,
            payload_json=source_snapshot.model_dump_json(),
        )
    )
    session.flush()
    source_ranking = TournamentRankingSnapshotAuthorityStore(session).adopt(
        run_id="run",
        branch_id="branch",
        event_id="event-real-q-ll",
        ranking_week=ranking_week,
        command_id="real-q-ll-adopt-ranking",
    )

    applications = tuple(
        TournamentEntryApplication(
            application_id=f"real-q-ll-{player_id}",
            run_id="run",
            branch_id="branch",
            event_id="event-real-q-ll",
            player_id=player_id,
            entry_window=(
                "main" if player_id in {"A", "C", "D"} else "qualification"
            ),
            decision_slot_ordinal=10,
            nr_tie_break_token=f"entry-{player_id}",
        )
        for player_id in player_ids
    )
    field = TournamentEntryFieldResolver.build_initial(
        authority=source_ranking,
        applications=applications,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=4,
            qualifier_spots=1,
        ),
    )
    apps_fp = _applications_fingerprint(applications)
    session.add(
        TournamentEntryFieldVersionModel(
            run_id="run",
            branch_id="branch",
            event_id="event-real-q-ll",
            sequence=1,
            command_id="real-q-ll-field",
            request_fingerprint=entry_request_fingerprint(
                {
                    "mode": "initial",
                    "run_id": "run",
                    "branch_id": "branch",
                    "event_id": "event-real-q-ll",
                    "authority_fingerprint": source_ranking.fingerprint,
                    "applications_fingerprint": apps_fp,
                    "capacity": field.capacity.model_dump(mode="json"),
                }
            ),
            field_fingerprint=field.fingerprint,
            predecessor_fingerprint=None,
            ranking_authority_fingerprint=source_ranking.fingerprint,
            applications_fingerprint=apps_fp,
            applications_json=_applications_json(applications),
            payload_json=field.model_dump_json(),
        )
    )
    session.flush()

    source_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event-real-q-ll",
        command_id="real-q-ll-input",
        draw_seed=771122,
        main_seed_count=1,
        qualification_seed_count=1,
    )
    assert len(source_input.direct_main_player_ids) == 3
    assert len(source_input.qualification_player_ids) == 4

    source_draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event-real-q-ll",
        command_id="real-q-ll-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event-real-q-ll",
        command_id="real-q-ll-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )

    q = source_draw.qualification_brackets[0]
    q_slots = {slot.slot_index: slot.player_id for slot in q.slots}
    q_round_one = tuple(
        sorted(
            (node for node in q.nodes if node.round_number == 1),
            key=lambda node: node.round_sequence,
        )
    )
    assert len(q_round_one) == 2
    q_final = max(q.nodes, key=lambda node: (node.round_number, node.round_sequence))

    executor = AuthoritativeSlotMatchExecutor(session)
    round_one_events = []
    round_one_players = {}
    for node in q_round_one:
        top = q_slots[int(node.source_top.removeprefix("slot:"))]
        bottom = q_slots[int(node.source_bottom.removeprefix("slot:"))]
        assert top is not None and bottom is not None
        round_one_players[node.node_id] = (top, bottom)
        round_one_events.append(
            SimulationMatchEventPlan(
                group_id=node.node_id,
                event_id="event-real-q-ll",
                match_id=node.node_id,
                direct_player_ids=(top, bottom),
            )
        )
    q_r1_plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="real-q-r1",
        ordinal=1,
        group_ids=tuple(node.node_id for node in q_round_one),
        match_events=tuple(round_one_events),
    )
    q_semis = {}
    for index, node in enumerate(q_round_one, start=1):
        top, bottom = round_one_players[node.node_id]
        q_semis[node.node_id] = executor.execute_match_group(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="real-q-r1",
            group_id=node.node_id,
            event_id="event-real-q-ll",
            match_id=node.node_id,
            player_a_id=top,
            player_b_id=bottom,
            seed=772000 + index,
            expected_slot_start_fingerprint=q_r1_plan.slot_start_fingerprint,
        )
    session.commit()

    semi_winners = tuple(
        q_semis[node.node_id].result.winner_player_id
        for node in q_round_one
    )
    q_final_plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="real-q-final",
        ordinal=2,
        group_ids=(q_final.node_id,),
        dependency_ids=tuple(node.node_id for node in q_round_one),
        match_events=(
            SimulationMatchEventPlan(
                group_id=q_final.node_id,
                event_id="event-real-q-ll",
                match_id=q_final.node_id,
                feeder_group_ids=tuple(node.node_id for node in q_round_one),
            ),
        ),
    )
    q_final_result = executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="real-q-final",
        group_id=q_final.node_id,
        event_id="event-real-q-ll",
        match_id=q_final.node_id,
        player_a_id=semi_winners[0],
        player_b_id=semi_winners[1],
        seed=773000,
        expected_slot_start_fingerprint=q_final_plan.slot_start_fingerprint,
    )
    session.commit()

    q_match_ids = {node.node_id for node in q.nodes}
    source_q_rows = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == "run",
            SimulationEventGroupModel.branch_id == "branch",
            SimulationEventGroupModel.match_id.in_(q_match_ids),
        )
        .order_by(SimulationEventGroupModel.match_id)
    ).all()
    assert len(source_q_rows) == 3
    source_q_result_fingerprints = {
        row.match_id: row.result_fingerprint for row in source_q_rows
    }
    assert source_q_result_fingerprints[q_final.node_id] == (
        q_final_result.result_fingerprint
    )

    source_store = TournamentDrawRevisionStore(session)
    first_direct = source_input.direct_main_player_ids[0]
    second_direct = source_input.direct_main_player_ids[1]
    source_vacancy = source_store.draw_frozen_lucky_loser_vacancy(
        run_id="run",
        branch_id="branch",
        event_id="event-real-q-ll",
        command_id="real-q-ll-vacancy-1",
        withdrawn_player_id=first_direct,
        main_process_window_ordinal=3,
    )
    source_fill = source_store.fill_next_frozen_lucky_loser(
        run_id="run",
        branch_id="branch",
        event_id="event-real-q-ll",
        command_id="real-q-ll-fill-1",
        main_process_window_ordinal=3,
    )
    assert source_vacancy.repair_kind == "lucky_loser_vacancy"
    assert source_fill.repair_kind == "lucky_loser_fill"
    source_fill_authority = source_fill.lucky_loser_fill_authority
    assert source_fill_authority is not None
    assert source_fill_authority.order_authority.candidates
    assert (
        source_fill_authority.order_authority.qualification_terminal_result_fingerprints
        == (source_q_result_fingerprints[q_final.node_id],)
    )

    source_payload = {"content": {}}
    capture_saved_sporting(
        session,
        source_payload,
        run_id="run",
        branch_id="branch",
    )
    capture_saved_simulation_slots(
        session,
        source_payload,
        run_id="run",
        branch_id="branch",
    )

    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="target",
            display_name="Target",
            forked_from_branch_id="branch",
        )
    )
    target_snapshot = source_snapshot.model_copy(update={"branch_id": "target"})
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="target",
            week_ordinal=ranking_week.ordinal,
            snapshot_fingerprint=target_snapshot.fingerprint,
            payload_json=target_snapshot.model_dump_json(),
        )
    )
    session.flush()
    target_ranking = TournamentRankingSnapshotAuthorityStore(session).adopt(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
        ranking_week=ranking_week,
        command_id="real-q-ll-adopt-ranking",
    )

    remapped = remap_coupled_player_slot_history(
        source_payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
        tournament_ranking_authority_map={
            source_ranking.fingerprint: target_ranking,
        },
    )
    assert remapped is not None
    assert len(remapped.simulation_component["draw_revisions"]) == 2

    target_q_result_fingerprints = {
        source_match_id: remapped.result_fingerprints[source_result]
        for source_match_id, source_result in source_q_result_fingerprints.items()
    }
    assert all(
        target_q_result_fingerprints[match_id]
        != source_q_result_fingerprints[match_id]
        for match_id in source_q_result_fingerprints
    )

    fork_root_payload = {
        "content": {
            "simulation_slot_match_state": remapped.simulation_component,
        }
    }
    restore_saved_simulation_slots(
        session,
        current_payload={"content": {}},
        target_payload=fork_root_payload,
        run_id="run",
        branch_id="target",
    )

    target_store = TournamentDrawRevisionStore(session)
    fork_history = target_store.history(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
    )
    assert tuple(item.repair_kind for item in fork_history) == (
        "lucky_loser_vacancy",
        "lucky_loser_fill",
    )
    target_fill = fork_history[1]
    target_fill_authority = target_fill.lucky_loser_fill_authority
    assert target_fill_authority is not None
    assert (
        target_fill_authority.order_authority.qualification_terminal_result_fingerprints
        == (target_q_result_fingerprints[q_final.node_id],)
    )
    assert {
        candidate.elimination_result_fingerprint
        for candidate in target_fill_authority.order_authority.candidates
    } <= set(target_q_result_fingerprints.values())
    assert (
        target_fill_authority.order_authority.fingerprint
        != source_fill_authority.order_authority.fingerprint
    )

    installed_fork_root = {
        "content": {
            "simulation_slot_match_state": _live_component_with_saved_shape(
                session,
                run_id="run",
                branch_id="target",
                shape_hint=remapped.simulation_component,
            )
        }
    }
    assert installed_fork_root["content"]["simulation_slot_match_state"] is not None
    assert (
        installed_fork_root["content"]["simulation_slot_match_state"]["fingerprint"]
        == remapped.simulation_component["fingerprint"]
    )

    target_vacancy_2 = target_store.draw_frozen_lucky_loser_vacancy(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
        command_id="real-q-ll-vacancy-2",
        withdrawn_player_id=second_direct,
        main_process_window_ordinal=3,
    )
    target_fill_2 = target_store.fill_next_frozen_lucky_loser(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
        command_id="real-q-ll-fill-2",
        main_process_window_ordinal=3,
    )
    assert target_vacancy_2.sequence == 3
    assert target_fill_2.sequence == 4
    assert target_fill_2.lucky_loser_fill_authority is not None
    assert (
        target_fill_2.lucky_loser_fill_authority.selected_candidate.player_id
        != target_fill_authority.selected_candidate.player_id
    )

    live_payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        live_payload,
        run_id="run",
        branch_id="target",
    )
    restore_saved_simulation_slots(
        session,
        current_payload=live_payload,
        target_payload=installed_fork_root,
        run_id="run",
        branch_id="target",
    )

    restored_history = target_store.history(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
    )
    assert tuple(item.fingerprint for item in restored_history) == tuple(
        item.fingerprint for item in fork_history
    )
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
    ).count() == 2

    retry_fill = target_store.fill_next_frozen_lucky_loser(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
        command_id="real-q-ll-fill-1",
        main_process_window_ordinal=3,
    )
    assert retry_fill.fingerprint == target_fill.fingerprint
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="target",
        event_id="event-real-q-ll",
    ).count() == 2

    recaptured = _live_component_with_saved_shape(
        session,
        run_id="run",
        branch_id="target",
        shape_hint=installed_fork_root["content"]["simulation_slot_match_state"],
    )
    assert recaptured is not None
    assert (
        recaptured["fingerprint"]
        == installed_fork_root["content"]["simulation_slot_match_state"]["fingerprint"]
    )


@pytest.mark.pr_critical
def test_source_bound_pre_q_revision_materializes_on_target_branch(tmp_path):
    session, _, _, _, _ = run_semifinals(
        tmp_path / "pre-q-fork-materialize.sqlite",
        ("sf-1", "sf-2"),
    )
    if session.get(RunContainerModel, "run") is None:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
    if session.get(RunBranchModel, "branch") is None:
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Source",
            )
        )
    session.flush()

    source_snapshot = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="pre-q-fork-ranking"),
        players=(),
        results=(),
        previous=None,
    )
    source_ranking = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-pre-q-fork",
        ranking_week=WEEK,
        ranking_snapshot=source_snapshot,
        adopted_by_command_id="pre-q-fork-adopt-ranking",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=source_snapshot.fingerprint,
            payload_json=source_snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(source_ranking)

    apps = tuple(
        TournamentEntryApplication(
            application_id=f"pre-q-a{index}",
            run_id="run",
            branch_id="branch",
            event_id="event-pre-q-fork",
            player_id=f"pre-q-p{index}",
            entry_window="main",
            decision_slot_ordinal=1,
            nr_tie_break_token=str(index),
        )
        for index in range(1, 8)
    )
    capacity = TournamentEntryFieldCapacity(
        main_draw_size=4,
        qualification_draw_size=2,
        qualifier_spots=1,
    )
    field = TournamentEntryFieldResolver.build_initial(
        authority=source_ranking,
        applications=apps,
        capacity=capacity,
    )
    apps_fp = _applications_fingerprint(apps)
    session.add(
        TournamentEntryFieldVersionModel(
            run_id="run",
            branch_id="branch",
            event_id="event-pre-q-fork",
            sequence=1,
            command_id="pre-q-field",
            request_fingerprint=entry_request_fingerprint(
                {
                    "mode": "initial",
                    "run_id": "run",
                    "branch_id": "branch",
                    "event_id": "event-pre-q-fork",
                    "authority_fingerprint": source_ranking.fingerprint,
                    "applications_fingerprint": apps_fp,
                    "capacity": capacity.model_dump(mode="json"),
                }
            ),
            field_fingerprint=field.fingerprint,
            predecessor_fingerprint=None,
            ranking_authority_fingerprint=source_ranking.fingerprint,
            applications_fingerprint=apps_fp,
            applications_json=_applications_json(apps),
            payload_json=field.model_dump_json(),
        )
    )
    session.flush()

    source_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event-pre-q-fork",
        command_id="pre-q-input",
        draw_seed=991122,
    )
    assert source_input.qualification_player_ids
    assert source_input.direct_main_player_ids
    withdrawn = source_input.direct_main_player_ids[0]

    TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event-pre-q-fork",
        command_id="pre-q-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event-pre-q-fork",
        command_id="pre-q-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )
    source_result = AuthoritativeFrozenMainReplacement(session).execute(
        run_id="run",
        branch_id="branch",
        event_id="event-pre-q-fork",
        command_id="pre-q-promote",
        withdrawn_player_id=withdrawn,
        main_process_window_ordinal=3,
        qualification_process_window_ordinal=3,
        repair_draw_seed=None,
    )
    assert source_result.source == "qualification_promotion"
    assert len(source_result.draw_revisions) == 1
    source_revision = source_result.draw_revisions[0]
    assert source_revision.repair_kind == "source_bound_pre_q_promotion"
    assert source_revision.replacement_source_authority is not None

    source_payload = {"content": {}}
    capture_saved_sporting(
        session,
        source_payload,
        run_id="run",
        branch_id="branch",
    )
    capture_saved_simulation_slots(
        session,
        source_payload,
        run_id="run",
        branch_id="branch",
    )

    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="target",
            display_name="Target",
            forked_from_branch_id="branch",
        )
    )
    target_snapshot = source_snapshot.model_copy(update={"branch_id": "target"})
    target_ranking = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="target",
        event_id="event-pre-q-fork",
        ranking_week=WEEK,
        ranking_snapshot=target_snapshot,
        adopted_by_command_id="pre-q-fork-adopt-ranking",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="target",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=target_snapshot.fingerprint,
            payload_json=target_snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(target_ranking)

    remapped = remap_coupled_player_slot_history(
        source_payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
        tournament_ranking_authority_map={
            source_ranking.fingerprint: target_ranking,
        },
    )
    assert remapped is not None
    assert len(remapped.simulation_component["draw_revisions"]) == 1

    fork_root = {
        "content": {
            "simulation_slot_match_state": remapped.simulation_component,
        }
    }
    restore_saved_simulation_slots(
        session,
        current_payload={"content": {}},
        target_payload=fork_root,
        run_id="run",
        branch_id="target",
    )

    target_history = TournamentDrawRevisionStore(session).history(
        run_id="run",
        branch_id="target",
        event_id="event-pre-q-fork",
    )
    assert len(target_history) == 1
    target_revision = target_history[0]
    assert target_revision.repair_kind == "source_bound_pre_q_promotion"
    assert target_revision.branch_id == "target"
    assert target_revision.fingerprint != source_revision.fingerprint
    target_source = target_revision.replacement_source_authority
    assert target_source is not None
    assert target_source.branch_id == "target"
    assert (
        target_source.predecessor_draw_fingerprint
        == target_revision.predecessor_draw_fingerprint
    )
    assert (
        target_source.predecessor_draw_input_fingerprint
        != source_revision.replacement_source_authority.predecessor_draw_input_fingerprint
    )

    retry = TournamentDrawRevisionStore(session).apply_source_bound_pre_q_promotion(
        run_id="run",
        branch_id="target",
        event_id="event-pre-q-fork",
        command_id=target_revision.command_id,
        main_process_window_ordinal=target_revision.main_process_window_ordinal,
        qualification_process_window_ordinal=(
            target_revision.qualification_process_window_ordinal
        ),
        repair_draw_seed=target_revision.repair_draw_seed,
        replacement_source_authority=target_source,
    )
    assert retry.fingerprint == target_revision.fingerprint
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="target",
        event_id="event-pre-q-fork",
    ).count() == 1


def test_materialized_fork_mixed_revision_restore_equivalence(tmp_path):
    session, _, _, _, _ = run_semifinals(
        tmp_path / "materialized-fork-mixed-restore.sqlite",
        ("sf-1", "sf-2"),
    )
    if session.get(RunContainerModel, "run") is None:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
    if session.get(RunBranchModel, "branch") is None:
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Source",
            )
        )
    session.flush()

    source_snapshot = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="fork-mixed-ranking"),
        players=(),
        results=(),
        previous=None,
    )
    source_ranking = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-fork-mixed",
        ranking_week=WEEK,
        ranking_snapshot=source_snapshot,
        adopted_by_command_id="fork-mixed-adopt-ranking",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=source_snapshot.fingerprint,
            payload_json=source_snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(source_ranking)

    apps = tuple(
        TournamentEntryApplication(
            application_id=f"fork-mixed-a{index}",
            run_id="run",
            branch_id="branch",
            event_id="event-fork-mixed",
            player_id=f"fork-mixed-p{index}",
            entry_window="main",
            decision_slot_ordinal=1,
            nr_tie_break_token=str(index),
        )
        for index in range(1, 7)
    )
    field = TournamentEntryFieldResolver.build_initial(
        authority=source_ranking,
        applications=apps,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            wild_card_slots=1,
        ),
    )
    apps_fp = _applications_fingerprint(apps)
    session.add(
        TournamentEntryFieldVersionModel(
            run_id="run",
            branch_id="branch",
            event_id="event-fork-mixed",
            sequence=1,
            command_id="fork-mixed-field",
            request_fingerprint=entry_request_fingerprint(
                {
                    "mode": "initial",
                    "run_id": "run",
                    "branch_id": "branch",
                    "event_id": "event-fork-mixed",
                    "authority_fingerprint": source_ranking.fingerprint,
                    "applications_fingerprint": apps_fp,
                    "capacity": field.capacity.model_dump(mode="json"),
                }
            ),
            field_fingerprint=field.fingerprint,
            predecessor_fingerprint=None,
            ranking_authority_fingerprint=source_ranking.fingerprint,
            applications_fingerprint=apps_fp,
            applications_json=_applications_json(apps),
            payload_json=field.model_dump_json(),
        )
    )
    session.flush()

    source_wc = TournamentWildCardAuthorityStore(session).resolve(
        run_id="run",
        branch_id="branch",
        event_id="event-fork-mixed",
        command_id="fork-mixed-wc",
        original_wild_card_player_ids=("fork-mixed-p4",),
        reserve_wild_card_player_ids=("fork-mixed-p5", "fork-mixed-p6"),
    )
    assert source_wc.active_wild_card_player_ids == ("fork-mixed-p4",)

    source_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event-fork-mixed",
        command_id="fork-mixed-input",
        draw_seed=441122,
    )
    source_draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event-fork-mixed",
        command_id="fork-mixed-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event-fork-mixed",
        command_id="fork-mixed-process",
        main_process_window_count=3,
    )

    source_store = TournamentDrawRevisionStore(session)
    source_rwc = source_store.draw_frozen_wild_card_withdrawal(
        run_id="run",
        branch_id="branch",
        event_id="event-fork-mixed",
        command_id="fork-mixed-rwc",
        withdrawn_player_id="fork-mixed-p4",
        main_process_window_ordinal=3,
    )
    assert tuple(
        revision.repair_kind
        for revision in source_store.history(
            run_id="run",
            branch_id="branch",
            event_id="event-fork-mixed",
        )
    ) == ("frozen_wild_card_repair",)
    assert source_rwc.wild_card_repair_authority is not None
    assert (
        source_rwc.wild_card_repair_authority.replacement_player_id
        == "fork-mixed-p5"
    )

    source_payload = {"content": {}}
    capture_saved_sporting(
        session,
        source_payload,
        run_id="run",
        branch_id="branch",
    )
    capture_saved_simulation_slots(
        session,
        source_payload,
        run_id="run",
        branch_id="branch",
    )

    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="target",
            display_name="Target",
            forked_from_branch_id="branch",
        )
    )
    target_snapshot = source_snapshot.model_copy(update={"branch_id": "target"})
    target_ranking = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
        ranking_week=WEEK,
        ranking_snapshot=target_snapshot,
        adopted_by_command_id="fork-mixed-adopt-ranking",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="target",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=target_snapshot.fingerprint,
            payload_json=target_snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(target_ranking)

    remapped = remap_coupled_player_slot_history(
        source_payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
        tournament_ranking_authority_map={
            source_ranking.fingerprint: target_ranking,
        },
    )
    assert remapped is not None

    fork_root_payload = {
        "content": {
            "simulation_slot_match_state": remapped.simulation_component,
        }
    }
    restore_saved_simulation_slots(
        session,
        current_payload={"content": {}},
        target_payload=fork_root_payload,
        run_id="run",
        branch_id="target",
    )

    fork_component = _live_component_with_saved_shape(
        session,
        run_id="run",
        branch_id="target",
        shape_hint=remapped.simulation_component,
    )
    assert fork_component is not None
    assert fork_component["fingerprint"] == remapped.simulation_component["fingerprint"]
    installed_fork_root = {
        "content": {
            "simulation_slot_match_state": fork_component,
        }
    }
    target_history = TournamentDrawRevisionStore(session).history(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
    )
    assert tuple(item.repair_kind for item in target_history) == (
        "frozen_wild_card_repair",
    )
    assert target_history[0].fingerprint != source_rwc.fingerprint
    assert target_history[0].branch_id == "target"

    target_store = TournamentDrawRevisionStore(session)
    live_second = target_store.draw_frozen_wild_card_withdrawal(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
        command_id="target-live-rwc",
        withdrawn_player_id="fork-mixed-p5",
        main_process_window_ordinal=3,
    )
    assert live_second.sequence == 2
    assert live_second.wild_card_repair_authority is not None
    assert (
        live_second.wild_card_repair_authority.replacement_player_id
        == "fork-mixed-p6"
    )
    live_history = target_store.history(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
    )
    assert len(live_history) == 2
    assert (
        live_history[0].successor_draw.fingerprint
        == live_history[1].predecessor_draw_fingerprint
    )

    current_payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        current_payload,
        run_id="run",
        branch_id="target",
    )
    restore_saved_simulation_slots(
        session,
        current_payload=current_payload,
        target_payload=installed_fork_root,
        run_id="run",
        branch_id="target",
    )

    restored_history = target_store.history(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
    )
    assert tuple(item.fingerprint for item in restored_history) == tuple(
        item.fingerprint for item in target_history
    )
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
    ).count() == 1

    retry = target_store.draw_frozen_wild_card_withdrawal(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
        command_id="fork-mixed-rwc",
        withdrawn_player_id="fork-mixed-p4",
        main_process_window_ordinal=3,
    )
    assert retry.fingerprint == target_history[0].fingerprint
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="target",
        event_id="event-fork-mixed",
    ).count() == 1

    recaptured = _live_component_with_saved_shape(
        session,
        run_id="run",
        branch_id="target",
        shape_hint=fork_component,
    )
    assert recaptured is not None
    assert recaptured["fingerprint"] == fork_component["fingerprint"]
    assert (
        json.loads(
            recaptured["draw_revisions"][0]["payload_json"]
        )["branch_id"]
        == "target"
    )


def test_draw_revision_restore_round_trip_and_retry_are_identity_stable(tmp_path):
    session, _, _, _, _ = run_semifinals(
        tmp_path / "draw-revision-restore-retry.sqlite",
        ("sf-1", "sf-2"),
    )
    if session.get(RunContainerModel, "run") is None:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
    if session.get(RunBranchModel, "branch") is None:
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Source",
            )
        )
    session.flush()

    snapshot = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="ranking-policy"),
        players=(),
        results=(),
        previous=None,
    )
    ranking = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        ranking_week=WEEK,
        ranking_snapshot=snapshot,
        adopted_by_command_id="adopt-ranking-restore-retry",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(ranking)

    apps = tuple(
        TournamentEntryApplication(
            application_id=f"restore-a{index}",
            run_id="run",
            branch_id="branch",
            event_id="event-restore-retry",
            player_id=f"restore-p{index}",
            entry_window="main",
            decision_slot_ordinal=1,
            nr_tie_break_token=str(index),
        )
        for index in range(1, 8)
    )
    capacity = TournamentEntryFieldCapacity(main_draw_size=4)
    field = TournamentEntryFieldResolver.build_initial(
        authority=ranking,
        applications=apps,
        capacity=capacity,
    )
    apps_fp = _applications_fingerprint(apps)
    session.add(
        TournamentEntryFieldVersionModel(
            run_id="run",
            branch_id="branch",
            event_id="event-restore-retry",
            sequence=1,
            command_id="restore-field-cut",
            request_fingerprint=entry_request_fingerprint(
                {
                    "mode": "initial",
                    "run_id": "run",
                    "branch_id": "branch",
                    "event_id": "event-restore-retry",
                    "authority_fingerprint": ranking.fingerprint,
                    "applications_fingerprint": apps_fp,
                    "capacity": capacity.model_dump(mode="json"),
                }
            ),
            field_fingerprint=field.fingerprint,
            predecessor_fingerprint=None,
            ranking_authority_fingerprint=ranking.fingerprint,
            applications_fingerprint=apps_fp,
            applications_json=_applications_json(apps),
            payload_json=field.model_dump_json(),
        )
    )
    draw_input = TournamentDrawInputAuthorityBuilder.build(
        authority=ranking,
        field=field,
        field_sequence=1,
        command_id="restore-commit-draw",
        draw_seed=17,
        main_seed_count=None,
        qualification_seed_count=None,
        schema_version="tournament_draw_input_authority.v2",
    )
    draw_request = TournamentDrawInputAuthorityStore._request(
        ranking_authority_fingerprint=ranking.fingerprint,
        entry_field_fingerprint=field.fingerprint,
        field_sequence=1,
        draw_seed=17,
        main_seed_count=draw_input.main_seed_count,
        qualification_seed_count=draw_input.qualification_seed_count,
        wild_card_authority_fingerprint=None,
    )
    session.add(
        TournamentDrawInputAuthorityModel(
            run_id="run",
            branch_id="branch",
            event_id="event-restore-retry",
            command_id="restore-commit-draw",
            request_fingerprint=draw_input_request_fingerprint(draw_request),
            authority_fingerprint=draw_input.fingerprint,
            ranking_authority_fingerprint=ranking.fingerprint,
            entry_field_fingerprint=field.fingerprint,
            field_sequence=1,
            payload_json=draw_input.model_dump_json(),
        )
    )
    session.flush()
    TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        command_id="restore-generate-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        command_id="restore-configure-process",
        main_process_window_count=3,
    )
    store = TournamentDrawRevisionStore(session)
    first = store.full_redraw_withdrawal(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        command_id="restore-withdraw-p1",
        withdrawn_player_ids=("restore-p1",),
        repair_draw_seed=29,
        main_process_window_ordinal=1,
    )
    second = store.draw_frozen_phase_withdrawal(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        command_id="restore-withdraw-p2",
        withdrawn_player_ids=("restore-p2",),
        main_process_window_ordinal=3,
    )

    target_payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        target_payload,
        run_id="run",
        branch_id="branch",
    )
    target_component_fingerprint = target_payload["content"][
        "simulation_slot_match_state"
    ]["fingerprint"]

    third = store.draw_frozen_phase_withdrawal(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        command_id="restore-withdraw-p3",
        withdrawn_player_ids=("restore-p3",),
        main_process_window_ordinal=3,
    )
    assert third.sequence == 3

    current_payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        current_payload,
        run_id="run",
        branch_id="branch",
    )

    corrupt_target = json.loads(json.dumps(target_payload))
    corrupt_row = corrupt_target["content"]["simulation_slot_match_state"][
        "draw_revisions"
    ][1]
    corrupt_revision = json.loads(corrupt_row["payload_json"])
    corrupt_revision["branch_id"] = "wrong-branch"
    corrupt_row["payload_json"] = json.dumps(
        corrupt_revision,
        sort_keys=True,
        separators=(",", ":"),
    )
    with pytest.raises(
        ValueError,
        match="scope mismatch|Draw revision row is corrupt",
    ):
        restore_saved_simulation_slots(
            session,
            current_payload=current_payload,
            target_payload=corrupt_target,
            run_id="run",
            branch_id="branch",
        )
    assert len(
        store.history(
            run_id="run",
            branch_id="branch",
            event_id="event-restore-retry",
        )
    ) == 3

    restore_saved_simulation_slots(
        session,
        current_payload=current_payload,
        target_payload=target_payload,
        run_id="run",
        branch_id="branch",
    )
    restored_history = store.history(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
    )
    assert tuple(item.fingerprint for item in restored_history) == (
        first.fingerprint,
        second.fingerprint,
    )
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
    ).count() == 2

    retry = store.draw_frozen_phase_withdrawal(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
        command_id="restore-withdraw-p2",
        withdrawn_player_ids=("restore-p2",),
        main_process_window_ordinal=3,
    )
    assert retry.fingerprint == second.fingerprint
    assert session.query(TournamentDrawRevisionModel).filter_by(
        run_id="run",
        branch_id="branch",
        event_id="event-restore-retry",
    ).count() == 2

    second_row = session.scalar(
        select(TournamentDrawRevisionModel).where(
            TournamentDrawRevisionModel.run_id == "run",
            TournamentDrawRevisionModel.branch_id == "branch",
            TournamentDrawRevisionModel.event_id == "event-restore-retry",
            TournamentDrawRevisionModel.sequence == 2,
        )
    )
    assert second_row is not None
    valid_request_fingerprint = second_row.request_fingerprint
    second_row.request_fingerprint = "f" * 64
    session.flush()
    with pytest.raises(ValueError, match="request identity is corrupt"):
        store.history(
            run_id="run",
            branch_id="branch",
            event_id="event-restore-retry",
        )
    second_row.request_fingerprint = valid_request_fingerprint
    session.flush()

    restored_payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        restored_payload,
        run_id="run",
        branch_id="branch",
    )
    assert restored_payload["content"]["simulation_slot_match_state"][
        "fingerprint"
    ] == target_component_fingerprint


def test_coupled_fork_remaps_basic_draw_revision_chain(tmp_path):
    session, _, _, _, _ = run_semifinals(
        tmp_path / "basic-draw-revision-fork.sqlite",
        ("sf-1", "sf-2"),
    )
    if session.get(RunContainerModel, "run") is None:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
    if session.get(RunBranchModel, "branch") is None:
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Source",
            )
        )
    session.flush()

    snapshot = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="ranking-policy"),
        players=(),
        results=(),
        previous=None,
    )
    source_ranking_authority = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-revision",
        ranking_week=WEEK,
        ranking_snapshot=snapshot,
        adopted_by_command_id="adopt-ranking-revision",
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=WEEK.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()
    TournamentRankingSnapshotAuthorityStore(session).append(
        source_ranking_authority
    )
    target_snapshot = snapshot.model_copy(update={"branch_id": "target"})
    target_ranking_authority = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="target",
        event_id="event-revision",
        ranking_week=WEEK,
        ranking_snapshot=target_snapshot,
        adopted_by_command_id="adopt-ranking-revision",
    )

    apps = tuple(
        TournamentEntryApplication(
            application_id=f"revision-a{index}",
            run_id="run",
            branch_id="branch",
            event_id="event-revision",
            player_id=f"revision-p{index}",
            entry_window="main",
            decision_slot_ordinal=1,
            nr_tie_break_token=str(index),
        )
        for index in range(1, 6)
    )
    capacity = TournamentEntryFieldCapacity(main_draw_size=4)
    source_field = TournamentEntryFieldResolver.build_initial(
        authority=source_ranking_authority,
        applications=apps,
        capacity=capacity,
    )
    apps_fp = _applications_fingerprint(apps)
    source_field_request = entry_request_fingerprint(
        {
            "mode": "initial",
            "run_id": "run",
            "branch_id": "branch",
            "event_id": "event-revision",
            "authority_fingerprint": source_ranking_authority.fingerprint,
            "applications_fingerprint": apps_fp,
            "capacity": capacity.model_dump(mode="json"),
        }
    )
    session.add(
        TournamentEntryFieldVersionModel(
            run_id="run",
            branch_id="branch",
            event_id="event-revision",
            sequence=1,
            command_id="revision-field-cut",
            request_fingerprint=source_field_request,
            field_fingerprint=source_field.fingerprint,
            predecessor_fingerprint=None,
            ranking_authority_fingerprint=source_ranking_authority.fingerprint,
            applications_fingerprint=apps_fp,
            applications_json=_applications_json(apps),
            payload_json=source_field.model_dump_json(),
        )
    )

    source_draw_input = TournamentDrawInputAuthorityBuilder.build(
        authority=source_ranking_authority,
        field=source_field,
        field_sequence=1,
        command_id="revision-commit-draw",
        draw_seed=17,
        main_seed_count=None,
        qualification_seed_count=None,
        schema_version="tournament_draw_input_authority.v2",
    )
    draw_request = TournamentDrawInputAuthorityStore._request(
        ranking_authority_fingerprint=source_ranking_authority.fingerprint,
        entry_field_fingerprint=source_field.fingerprint,
        field_sequence=1,
        draw_seed=17,
        main_seed_count=source_draw_input.main_seed_count,
        qualification_seed_count=source_draw_input.qualification_seed_count,
        wild_card_authority_fingerprint=None,
    )
    session.add(
        TournamentDrawInputAuthorityModel(
            run_id="run",
            branch_id="branch",
            event_id="event-revision",
            command_id="revision-commit-draw",
            request_fingerprint=draw_input_request_fingerprint(draw_request),
            authority_fingerprint=source_draw_input.fingerprint,
            ranking_authority_fingerprint=source_ranking_authority.fingerprint,
            entry_field_fingerprint=source_field.fingerprint,
            field_sequence=1,
            payload_json=source_draw_input.model_dump_json(),
        )
    )
    session.flush()

    source_draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event-revision",
        command_id="revision-generate-draw",
    )
    source_process = TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event-revision",
        command_id="revision-configure-process",
        main_process_window_count=3,
    )
    source_revision = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
        run_id="run",
        branch_id="branch",
        event_id="event-revision",
        command_id="revision-withdraw-p1",
        withdrawn_player_ids=("revision-p1",),
        repair_draw_seed=29,
        main_process_window_ordinal=1,
    )

    payload = {"content": {}}
    capture_saved_sporting(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    capture_saved_simulation_slots(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    remapped = remap_coupled_player_slot_history(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        v1_source_fingerprint_map={},
        tournament_ranking_authority_map={
            source_ranking_authority.fingerprint: target_ranking_authority
        },
    )

    assert remapped is not None
    component = remapped.simulation_component
    target_draw_row = component["draw_authorities"][0]
    target_process_row = component["draw_process_authorities"][0]
    target_revision_row = component["draw_revisions"][0]
    target_revision = json.loads(target_revision_row["payload_json"])

    assert target_revision_row["branch_id"] == "target"
    assert target_revision_row["revision_fingerprint"] != source_revision.fingerprint
    assert (
        target_revision_row["predecessor_draw_fingerprint"]
        == target_draw_row["authority_fingerprint"]
    )
    assert (
        target_revision["process_authority_fingerprint"]
        == target_process_row["authority_fingerprint"]
    )
    assert target_revision["repair_kind"] == "full_redraw"
    assert target_revision["withdrawn_player_ids"] == ["revision-p1"]
    assert (
        target_revision_row["successor_draw_fingerprint"]
        != source_revision.successor_draw.fingerprint
    )
    assert target_revision["branch_id"] == "target"
    assert target_revision["successor_draw"]["branch_id"] == "target"
