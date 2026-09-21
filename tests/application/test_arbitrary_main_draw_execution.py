from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
)
from beta_engine.application.season_draw_service import SeasonDrawService
from beta_engine.application.season_event_results_service import SeasonEventResultsService
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
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
    SimulationSlotModel,
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
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)

from test_authoritative_slot_matches import _driver_command, session_at
from test_season_entry_list_service import make_service


@pytest.mark.smoke
def test_thirteen_player_canonical_main_draw_closes_with_three_byes(tmp_path):
    """13 entrants use a 16-slot binary DAG, three BYEs and 12 played matches."""
    root = tmp_path / "canonical-thirteen"
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
            "byes": 3,
        }
    )
    calendar.events[0] = event
    entries.calendar_service._save_registry(calendars)

    player_ids = tuple(f"P{index:02d}" for index in range(1, 14))
    week = RankingWeek(season_index=0, week=3)
    ranking_week = RankingWeek(season_index=0, week=2)
    completed_week = RankingWeek(season_index=0, week=1)

    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Canonical thirteen",
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

    ranking = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=ranking_week,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=tuple(
            OfficialRankingPlayer(
                player_id=player_id,
                tie_break_token=f"rank-{player_id}",
                tour_entry_week=completed_week,
            )
            for player_id in player_ids
        ),
        results=tuple(
            OfficialRankingResult(
                edition_id=f"prior-{player_id}",
                player_id=player_id,
                source_fingerprint=f"source-{player_id}",
                completed_week=completed_week,
                first_publication_week=ranking_week,
                main_points=(len(player_ids) - index) * 10,
            )
            for index, player_id in enumerate(player_ids)
        ),
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

    capacity = TournamentEntryFieldCapacity.for_main_entrant_count(
        main_entrant_count=len(player_ids),
    )
    assert capacity.main_draw_size == 16
    assert capacity.bye_slots == 3

    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        applications=tuple(
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
        ),
        capacity=capacity,
        command_id="initial-field",
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="commit-draw-input",
        draw_seed=1316,
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
    assert len(draw.main.bye_slot_indexes) == 3
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
    assert len(schedule.slots) == 12
    assert all(len(slot.group_ids) == 1 for slot in schedule.slots)
    assert [
        sum(slot.match_day_ordinal == day for slot in schedule.slots)
        for day in (1, 2, 3, 4)
    ] == [5, 4, 2, 1]

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="thirteen-player-schedule",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )

    state = None
    for ordinal in range(1, len(schedule.slots) + 1):
        command, _ = _driver_command(
            driver,
            week,
            f"thirteen-player-slot-{ordinal}",
        )
        state = driver.simulate_next_slot(command)

    assert state is not None
    assert state["supported_tournament_complete"] is True

    with factory() as db:
        groups = db.scalars(select(SimulationEventGroupModel)).all()
        assert len(groups) == 12
        assert len({group.group_id for group in groups}) == 12

        slots = db.scalars(
            select(SimulationSlotModel).order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        assert len(slots) == 12

        sources = OwnedTournamentRankingSourceStore(db).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        source = sources[0]
        assert source.schema_version == "owned_tournament_ranking_source.v5"
        assert source.canonical_result is not None
        assert source.canonical_awards is not None
        assert len(source.canonical_result.players) == 13
        assert len(source.canonical_result.matches) == 15

        bye_matches = [
            match
            for match in source.canonical_result.matches
            if match.scoreline == "BYE"
        ]
        assert len(bye_matches) == 3
        assert sum(
            match.scoreline != "BYE"
            for match in source.canonical_result.matches
        ) == 12
        assert sum(
            player.byes_received
            for player in source.canonical_result.players
        ) == 3

        stages = [
            player.reached_stage
            for player in source.canonical_result.players
        ]
        assert stages.count("round_of_16") == 5
        assert stages.count("quarterfinal") == 4
        assert stages.count("semifinal") == 2
        assert stages.count("finalist") == 1
        assert stages.count("champion") == 1

        results_by_player = {
            player.player_id: player
            for player in source.canonical_result.players
        }
        awards_by_player = {
            award.player_id: award
            for award in source.canonical_awards.awards
        }
        for player_id, player in results_by_player.items():
            award = awards_by_player[player_id]
            if (
                player.byes_received > 0
                and player.wins == 0
                and player.losses == 1
                and player.walkovers_received == 0
            ):
                assert award.point_stage == "round_of_16"
            else:
                assert award.point_stage is None
