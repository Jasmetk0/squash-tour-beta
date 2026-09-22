from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
)
from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
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
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.simulation_slots import WeekSimulationSchedule
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)

from test_authoritative_slot_matches import _driver_command, session_at
from test_season_entry_list_service import make_service


pytestmark = pytest.mark.smoke


def _resolve_players(plan, completed):
    players: list[str] = []
    assert plan.participant_sources is not None
    for source in plan.participant_sources:
        if source.startswith("player:"):
            players.append(source.removeprefix("player:"))
            continue
        assert source.startswith("winner:")
        feeder_id = source.removeprefix("winner:")
        players.append(completed[feeder_id].result.winner_player_id)
    assert len(players) == 2
    return players[0], players[1]


def test_real_qualification_lucky_loser_continues_to_canonical_tournament_close(
    tmp_path,
):
    """Real Q receipts feed frozen LL repair, then normal driver closes the event."""

    root = tmp_path / "lucky-loser-authoritative-close"
    entries = make_service(root, main_draw_size=4)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0].model_copy(
        update={
            "event_id": "event-ll-close",
            "season_week": 3,
            "start_season_week": 3,
            "end_season_week": 3,
            "qualification_draw_size": 4,
            "qualifier_spots": 1,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    calendar.events[0] = event
    entries.calendar_service._save_registry(calendars)

    player_ids = ("A", "B", "C", "D", "E", "F", "G")
    direct_main_ids = ("A", "B", "C")
    qualification_ids = ("D", "E", "F", "G")
    week = RankingWeek(season_index=0, week=3)
    ranking_week = RankingWeek(season_index=0, week=2)
    completed_week = RankingWeek(season_index=0, week=1)

    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Lucky Loser close",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="branch",
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
        policy=OfficialRankingPolicy(policy_id="ll-close-policy"),
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
        command_id="ll-close-ranking",
    )

    applications = tuple(
        TournamentEntryApplication(
            application_id=f"app-{player_id}",
            run_id="run",
            branch_id="branch",
            event_id=event.event_id,
            player_id=player_id,
            entry_window=(
                "main" if player_id in direct_main_ids else "qualification"
            ),
            decision_slot_ordinal=10,
            nr_tie_break_token=f"entry-{player_id}",
        )
        for player_id in player_ids
    )
    field = TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        applications=applications,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=4,
            qualifier_spots=1,
        ),
        command_id="ll-close-field",
    )
    assert field.direct_main_player_ids == direct_main_ids
    assert field.qualification_player_ids == qualification_ids

    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="ll-close-input",
        draw_seed=771122,
        main_seed_count=1,
        qualification_seed_count=1,
    )
    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="ll-close-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="ll-close-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )
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

    pre_ll_proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    pre_ll_schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(pre_ll_proposal["schedule"], sort_keys=True, separators=(",", ":"))
    )
    q_specs = tuple(
        slot
        for slot in pre_ll_schedule.slots
        if slot.draw_phase == "qualification"
    )
    main_specs = tuple(
        slot for slot in pre_ll_schedule.slots if slot.draw_phase == "main"
    )
    assert len(q_specs) == 3
    assert len(main_specs) == 3
    assert max(slot.ordinal for slot in q_specs) < min(
        slot.ordinal for slot in main_specs
    )

    completed = {}
    with factory.begin() as db:
        package = driver._packages(
            week,
            session=db,
            run_id="run",
            branch_id="branch",
        )[0]
        plans = driver._topology_for_session(
            db,
            "run",
            "branch",
            (package,),
            week=week,
        )
        executor = AuthoritativeSlotMatchExecutor(db)
        for index, spec in enumerate(q_specs, start=1):
            group_id = spec.group_ids[0]
            plan = plans[group_id]
            player_a, player_b = _resolve_players(plan, completed)
            slot_plan = executor.create_slot(
                run_id="run",
                branch_id="branch",
                week=week,
                slot_id=f"ll-q-slot-{spec.ordinal}",
                ordinal=spec.ordinal,
                group_ids=(group_id,),
                match_events=(plan,),
                dependency_ids=driver._plan_feeders(plan),
            )
            completed[group_id] = executor.execute_match_group(
                run_id="run",
                branch_id="branch",
                week=week,
                slot_id=slot_plan.slot_id,
                group_id=group_id,
                event_id=event.event_id,
                match_id=group_id,
                player_a_id=player_a,
                player_b_id=player_b,
                seed=881000 + index,
                expected_slot_start_fingerprint=slot_plan.slot_start_fingerprint,
            )

    q_terminal = max(
        draw.qualification_brackets[0].nodes,
        key=lambda node: (node.round_number, node.round_sequence),
    )
    q_winner_id = completed[q_terminal.node_id].result.winner_player_id
    q_final_loser_id = completed[q_terminal.node_id].result.loser_player_id

    with factory.begin() as db:
        revisions = TournamentDrawRevisionStore(db)
        withdrawn = draw_input.direct_main_player_ids[0]
        vacancy = revisions.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id=event.event_id,
            command_id="ll-close-vacancy",
            withdrawn_player_id=withdrawn,
            main_process_window_ordinal=3,
        )
        fill = revisions.fill_next_frozen_lucky_loser(
            run_id="run",
            branch_id="branch",
            event_id=event.event_id,
            command_id="ll-close-fill",
            main_process_window_ordinal=3,
        )
        assert vacancy.repair_kind == "lucky_loser_vacancy"
        assert fill.repair_kind == "lucky_loser_fill"
        assert fill.lucky_loser_fill_authority is not None
        selected_ll_id = (
            fill.lucky_loser_fill_authority.selected_candidate.player_id
        )
        assert selected_ll_id == q_final_loser_id
        assert selected_ll_id != q_winner_id
        repaired = fill.successor_draw
        assert all(
            slot.entrant_kind != "lucky_loser_placeholder"
            for slot in repaired.main.slots
        )
        assert selected_ll_id in {
            slot.player_id for slot in repaired.main.slots if slot.player_id
        }

    post_ll_proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    post_ll_schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(post_ll_proposal["schedule"], sort_keys=True, separators=(",", ":"))
    )
    assert tuple(
        (slot.ordinal, slot.group_ids, slot.draw_phase, slot.round_number)
        for slot in post_ll_schedule.slots
    ) == tuple(
        (slot.ordinal, slot.group_ids, slot.draw_phase, slot.round_number)
        for slot in pre_ll_schedule.slots
    )

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="ll-close-adopt-schedule",
        expected_week=week,
        expected_schedule_fingerprint=post_ll_proposal["schedule_fingerprint"],
        expected_position_fingerprint=post_ll_proposal["position_fingerprint"],
    )

    state = None
    for ordinal in range(len(q_specs) + 1, len(post_ll_schedule.slots) + 1):
        command, _ = _driver_command(
            driver,
            week,
            f"ll-close-main-slot-{ordinal}",
        )
        state = driver.simulate_next_slot(command)

    assert state is not None
    assert state["supported_tournament_complete"] is True

    with factory() as db:
        groups = db.scalars(
            select(SimulationEventGroupModel).order_by(
                SimulationEventGroupModel.group_id,
            )
        ).all()
        assert len(groups) == 6

        sources = OwnedTournamentRankingSourceStore(db).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        source = sources[0]
        result = source.canonical_result
        point_authority = source.canonical_awards
        assert result is not None
        assert point_authority is not None
        assert len(result.matches) == 6
        assert result.qualification_winner_ids == (q_winner_id,)

        ll_result = next(
            item for item in result.players if item.player_id == selected_ll_id
        )
        assert ll_result.draw_type == "both"
        assert ll_result.qualifier is False
        assert any(
            match.draw_type == "qualification"
            and match.loser_player_id == selected_ll_id
            for match in result.matches
        )
        assert any(
            match.draw_type == "main"
            and selected_ll_id in {
                match.winner_player_id,
                match.loser_player_id,
            }
            for match in result.matches
        )

        ll_award = next(
            item
            for item in point_authority.awards
            if item.player_id == selected_ll_id
        )
        assert ll_award.qualifier is False
        assert ll_award.qualification_point_stage == "qualification_final"
        assert ll_award.qualification_points_awarded is not None
        assert ll_award.ranking_points_awarded >= (
            ll_award.qualification_points_awarded
        )
