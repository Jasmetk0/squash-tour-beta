"""Real SQLite acceptance tests for the first authoritative slot match slice."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
    build_authoritative_tournament_ranking_packages,
    execute_supported_four_player_tournament,
    execute_adopted_four_player_match_package,
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
)
from beta_engine.infrastructure.db.models import (
    Base,
    PlayerLifecycleWeekStateModel,
    SimulationEventGroupModel,
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
        for pid, (style, archetype) in zip(
            player_ids,
            (
                ("attacking", "Power Attacker"),
                ("retrieving", "Retriever"),
                ("tempo-controller", "Control Player"),
                ("front-court", "Shot Maker"),
            ),
            strict=True,
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
                        player(pid, value)
                        for pid, value in zip(
                            player_ids, (130, 100, 125, 95), strict=True
                        )
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
    session.commit()
    session.close()

    reopened = Session(create_engine(f"sqlite:///{path}"))
    restore_saved_simulation_slots(
        reopened,
        current_payload=after,
        target_payload=before,
        run_id="run",
        branch_id="branch",
    )
    reopened.commit()
    assert reopened.query(SimulationEventGroupModel).count() == 0
    restore_saved_simulation_slots(
        reopened,
        current_payload=before,
        target_payload=after,
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
