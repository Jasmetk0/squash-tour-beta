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
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)

from test_authoritative_slot_matches import _driver_command, session_at
from test_season_entry_list_service import make_service


pytestmark = pytest.mark.smoke


def test_multi_q_byes_promote_into_main_with_per_draw_point_unlocks(tmp_path):
    """Two real Q finals plus two auto-BYE Q sections feed one eight-player Main."""

    root = tmp_path / "canonical-four-q-with-byes"
    entries = make_service(root, main_draw_size=8)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0].model_copy(
        update={
            "event_id": "event",
            "season_week": 3,
            "start_season_week": 3,
            "end_season_week": 3,
            "qualification_draw_size": 8,
            "qualifier_spots": 4,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    calendar.events[0] = event
    entries.calendar_service._save_registry(calendars)

    player_ids = tuple(chr(ord("A") + index) for index in range(10))
    direct_main_ids = player_ids[:4]
    qualification_ids = player_ids[4:]
    week = RankingWeek(season_index=0, week=3)
    ranking_week = RankingWeek(season_index=0, week=2)
    completed_week = RankingWeek(season_index=0, week=1)

    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Canonical four Q with BYEs",
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
            main_draw_size=8,
            qualification_draw_size=8,
            qualifier_spots=4,
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
        draw_seed=9814,
    )
    assert draw_input.main_seed_count == 2
    assert draw_input.qualification_seed_count == 4
    assert draw_input.qualifier_placeholder_ids == ("Q1", "Q2", "Q3", "Q4")

    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        command_id="generate-draw",
    )
    assert tuple(
        bracket.section_id for bracket in draw.qualification_brackets
    ) == ("Q1", "Q2", "Q3", "Q4")
    assert all(bracket.bracket_size == 2 for bracket in draw.qualification_brackets)
    live_counts = tuple(
        sum(slot.player_id is not None for slot in bracket.slots)
        for bracket in draw.qualification_brackets
    )
    assert sorted(live_counts) == [1, 1, 2, 2]
    assert sum(len(bracket.bye_slot_indexes) for bracket in draw.qualification_brackets) == 2
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

    assert len(package.frozen_qualifier_promotions) == 4
    assert len(package.frozen_bye_match_ids) == 2

    bye_matches = {
        match.match_id: match
        for match in package.qualification_matches
        if match.match_id in package.frozen_bye_match_ids
    }
    assert len(bye_matches) == 2
    assert all(match.scoreline == "BYE" for match in bye_matches.values())
    bye_q_winner_ids = {
        match.winner_player_id for match in bye_matches.values()
    }
    assert None not in bye_q_winner_ids
    assert len(bye_q_winner_ids) == 2

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
    assert len(scheduled_group_ids) == 9
    assert not (set(package.frozen_bye_match_ids) & scheduled_group_ids)

    slot_by_group = {
        group_id: slot.ordinal
        for slot in schedule.slots
        for group_id in slot.group_ids
    }
    for promotion in package.frozen_qualifier_promotions:
        if promotion.source_match_id in package.frozen_bye_match_ids:
            assert promotion.source_match_id not in slot_by_group
        else:
            assert slot_by_group[promotion.source_match_id] < slot_by_group[
                promotion.target_match_id
            ]

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="four-q-bye-schedule",
        expected_week=week,
        expected_schedule_fingerprint=proposed["schedule_fingerprint"],
        expected_position_fingerprint=proposed["position_fingerprint"],
    )

    state = None
    for ordinal in range(1, len(schedule.slots) + 1):
        command, _ = _driver_command(
            driver,
            week,
            f"four-q-bye-slot-{ordinal}",
        )
        state = driver.simulate_next_slot(command)

    assert state is not None
    assert state["supported_tournament_complete"] is True

    with factory() as db:
        groups = db.scalars(select(SimulationEventGroupModel)).all()
        assert len(groups) == 9
        assert {group.group_id for group in groups} == scheduled_group_ids

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
        assert len(result.matches) == 11
        assert len([match for match in result.matches if match.scoreline == "BYE"]) == 2
        assert len(result.players) == 10
        assert len(result.qualification_winner_ids) == 4
        assert point_authority.schema_version == "tournament_point_award_authority.v3"

        awards_by_player = {
            award.player_id: award for award in point_authority.awards
        }
        distribution = dict(point_authority.point_distribution)
        real_q_winner_ids = set(result.qualification_winner_ids) - bye_q_winner_ids
        assert len(real_q_winner_ids) == 2

        for player_id in real_q_winner_ids:
            award = awards_by_player[player_id]
            assert award.qualification_point_stage == "qualification_winner"
            assert award.qualification_points_awarded == distribution[
                "qualification_winner"
            ]

        for player_id in bye_q_winner_ids:
            award = awards_by_player[player_id]
            assert award.qualification_point_stage == "qualification_final"
            assert award.qualification_points_awarded == distribution[
                "qualification_final"
            ]
            main_stage = award.point_stage or award.reached_stage
            assert award.ranking_points_awarded == (
                distribution[main_stage]
                + distribution["qualification_final"]
            )

        q_losers = set(qualification_ids) - set(result.qualification_winner_ids)
        assert len(q_losers) == 2
        for player_id in q_losers:
            award = awards_by_player[player_id]
            assert award.qualification_point_stage is None
            assert award.ranking_points_awarded == distribution[
                "qualification_final"
            ]
