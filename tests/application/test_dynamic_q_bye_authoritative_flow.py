from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
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
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityBuilder,
)
from beta_engine.domain.tournaments.replacement_source_authority import (
    TournamentReplacementSourceAuthority,
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


pytestmark = [pytest.mark.smoke, pytest.mark.pr_critical]


def test_dynamic_qualifier_vs_bye_closes_through_authoritative_run_flow(tmp_path):
    """A Q feeder facing a repaired Main BYE auto-advances without a fake match."""

    root = tmp_path / "dynamic-q-vs-bye"
    entries = make_service(root, main_draw_size=4)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0].model_copy(
        update={
            "event_id": "event",
            "season_week": 3,
            "start_season_week": 3,
            "end_season_week": 3,
            "qualification_draw_size": 2,
            "qualifier_spots": 1,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    calendar.events[0] = event
    entries.calendar_service._save_registry(calendars)

    player_ids = ("A", "B", "C", "D", "E")
    direct_main_ids = ("A", "B", "C")
    qualification_ids = ("D", "E")
    week = RankingWeek(season_index=0, week=3)
    ranking_week = RankingWeek(season_index=0, week=2)
    completed_week = RankingWeek(season_index=0, week=1)

    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Dynamic Q vs BYE",
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
            qualification_draw_size=2,
            qualifier_spots=1,
        ),
        command_id="initial-field",
    )
    assert field.direct_main_player_ids == direct_main_ids
    assert field.qualification_player_ids == qualification_ids

    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="commit-draw-input",
        draw_seed=44123,
        main_seed_count=1,
        qualification_seed_count=1,
    )
    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="generate-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="configure-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )

    qualifier_slot = next(
        slot
        for slot in draw.main.slots
        if slot.entrant_kind == "qualifier_placeholder"
    )
    qualifier_source = f"slot:{qualifier_slot.slot_index}"
    target_node = next(
        node
        for node in draw.main.nodes
        if node.round_number == 1
        and qualifier_source in (node.source_top, node.source_bottom)
    )
    sibling_source = (
        target_node.source_bottom
        if target_node.source_top == qualifier_source
        else target_node.source_top
    )
    assert sibling_source.startswith("slot:")
    sibling_slot_index = int(sibling_source.removeprefix("slot:"))
    sibling_slot = next(
        slot for slot in draw.main.slots if slot.slot_index == sibling_slot_index
    )
    assert sibling_slot.player_id in direct_main_ids
    withdrawn_player_id = sibling_slot.player_id
    assert withdrawn_player_id is not None

    cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        player_id=withdrawn_player_id,
        played_matches=(),
        draw_type="main",
    )
    bye_source = TournamentReplacementSourceAuthority(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        withdrawn_player_id=withdrawn_player_id,
        predecessor_draw_fingerprint=draw.fingerprint,
        predecessor_draw_input_fingerprint=draw_input.fingerprint,
        physical_slot_index=sibling_slot.slot_index,
        source="bye",
        replacement_cutoff_authority=cutoff,
    )
    revision = TournamentDrawRevisionStore(session).apply_frozen_ordinary_fallback(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="repair-to-bye",
        main_process_window_ordinal=1,
        replacement_source_authority=bye_source,
    )
    repaired = revision.successor_draw
    repaired_sibling = next(
        slot
        for slot in repaired.main.slots
        if slot.slot_index == sibling_slot.slot_index
    )
    assert repaired_sibling.entrant_kind == "bye"
    assert repaired_sibling.player_id is None
    assert next(
        slot
        for slot in repaired.main.slots
        if slot.slot_index == qualifier_slot.slot_index
    ).entrant_kind == "qualifier_placeholder"
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
    with factory() as db:
        package = driver._packages(
            week,
            session=db,
            run_id="run",
            branch_id="branch",
        )[0]

    assert len(package.qualification_matches) == 1
    assert len(package.main_draw_matches) == 3
    assert len(package.frozen_qualifier_promotions) == 1
    assert len(package.frozen_bye_match_ids) == 1

    dynamic_bye_id = package.frozen_bye_match_ids[0]
    dynamic_bye = next(
        match
        for match in package.main_draw_matches
        if match.match_id == dynamic_bye_id
    )
    assert dynamic_bye.status == "bye_auto_advance_pending"
    assert dynamic_bye.winner_player_id is None

    promotion = package.frozen_qualifier_promotions[0]
    assert promotion.target_match_id == dynamic_bye_id

    proposed = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposed["schedule"], sort_keys=True, separators=(",", ":"))
    )
    scheduled_group_ids = {
        group_id
        for slot in schedule.slots
        for group_id in slot.group_ids
    }
    assert dynamic_bye_id not in scheduled_group_ids
    assert promotion.source_match_id in scheduled_group_ids
    assert len(scheduled_group_ids) == 3

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="dynamic-q-bye-schedule",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )

    state = None
    for ordinal in range(1, len(schedule.slots) + 1):
        command, _ = _driver_command(
            driver,
            week,
            f"dynamic-q-bye-slot-{ordinal}",
        )
        state = driver.simulate_next_slot(command)

    assert state is not None
    assert state["supported_tournament_complete"] is True

    with factory() as db:
        groups = db.scalars(select(SimulationEventGroupModel)).all()
        assert {group.group_id for group in groups} == scheduled_group_ids
        assert dynamic_bye_id not in {group.group_id for group in groups}

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

        assert len(result.matches) == 4
        bye_results = [
            match
            for match in result.matches
            if match.match_id == dynamic_bye_id
        ]
        assert len(bye_results) == 1
        bye_result = bye_results[0]
        assert bye_result.draw_type == "main"
        assert bye_result.scoreline == "BYE"
        assert bye_result.loser_player_id is None

        assert len(result.qualification_winner_ids) == 1
        qualifier_winner_id = result.qualification_winner_ids[0]
        assert bye_result.winner_player_id == qualifier_winner_id

        qualifier_player_result = next(
            item for item in result.players if item.player_id == qualifier_winner_id
        )
        assert qualifier_player_result.draw_type == "both"
        assert qualifier_player_result.byes_received == 1

        qualifier_award = next(
            item
            for item in point_authority.awards
            if item.player_id == qualifier_winner_id
        )
        assert qualifier_award.qualification_point_stage == "qualification_winner"
