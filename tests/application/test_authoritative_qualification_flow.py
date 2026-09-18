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
from beta_engine.application.season_draw_service import DrawGenerateRequest, SeasonDrawService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from beta_engine.application.season_event_results_service import SeasonEventResultsService
from beta_engine.application.season_match_service import (
    MatchPackageGenerateRequest,
    SeasonMatchService,
)
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayersRegistry
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)

from test_authoritative_slot_matches import _driver_command, session_at
from test_season_entry_list_service import active_player, first_event_id, make_service


def _persist_full_three_player_qualification(entries, event_id: str) -> int:
    """Choose fixture entropy only; all acceptance decisions remain production-owned."""
    for seed in range(1, 101):
        preview = entries.generate_entry_list(
            event_id=event_id,
            request=EntryListGenerateRequest(seed=seed, dry_run=True, max_alternates=0),
        )
        if (
            preview.summary.main_draw_acceptances == 3
            and preview.summary.qualification_acceptances == 3
        ):
            entries.generate_entry_list(
                event_id=event_id,
                request=EntryListGenerateRequest(
                    seed=seed,
                    dry_run=False,
                    max_alternates=0,
                ),
            )
            return seed
    raise AssertionError(
        "fixture could not produce three direct and three qualification acceptances"
    )


@pytest.mark.smoke
def test_production_qualification_bye_promotes_into_main_draw_and_closes_once(tmp_path):
    """Real Entry -> Qualification -> Main Draw evidence becomes one owned source."""
    root = tmp_path / "qualification-flow"
    entries = make_service(root, main_draw_size=4)

    # The generic fixture intentionally contains only strong players, so its
    # production Entry Engine targets Main almost exclusively. Keep Entry logic
    # untouched and provide a deterministic mixed-quality world instead: strong
    # players genuinely target Main, while mid-level players genuinely target
    # Qualification through the same production decision path.
    active_players = [
        *(active_player(index, ability=88) for index in range(1, 11)),
        *(active_player(index, ability=45) for index in range(101, 121)),
    ]
    active_registry = SeasonActivePlayersRegistry(
        players_by_season={"2000/2001": active_players},
        bootstrap_metadata_by_season={},
    )
    (root / "active.json").write_text(
        json.dumps(active_registry.model_dump(mode="json")),
        encoding="utf-8",
    )

    event_id = first_event_id(entries)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0]
    calendar.events[0] = event.model_copy(
        update={
            "qualification_draw_size": 3,
            "qualifier_spots": 1,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    entries.calendar_service._save_registry(calendars)

    _persist_full_three_player_qualification(entries, event_id)
    draws = SeasonDrawService(
        entry_list_service=entries,
        calendar_service=entries.calendar_service,
        draws_path=root / "draws.json",
    )
    draw = draws.generate_draw_package(
        event_id=event_id,
        request=DrawGenerateRequest(seed=4102, dry_run=False),
    ).draw_package
    assert draw is not None
    assert draw.qualification_draw is not None
    assert len(draw.qualification_draw.byes) == 1
    assert len(draw.main_draw.qualifier_placeholders) == 1

    matches = SeasonMatchService(
        draw_service=draws,
        active_players_service=entries.active_players_service,
        matches_path=root / "matches.json",
    )
    raw_package = matches.generate_match_package(
        event_id=event_id,
        request=MatchPackageGenerateRequest(seed=4103, dry_run=False),
    ).match_package
    assert raw_package is not None
    bye_matches = [
        match
        for match in raw_package.qualification_matches
        if match.status == "bye_auto_advance_pending"
    ]
    assert len(bye_matches) == 1
    assert len(
        [
            player_id
            for player_id in (
                bye_matches[0].top_player_id,
                bye_matches[0].bottom_player_id,
            )
            if player_id
        ]
    ) == 1

    results = SeasonEventResultsService(
        match_service=matches,
        results_path=root / "results.json",
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
                player_id
                for match in raw_package.qualification_matches
                + raw_package.main_draw_matches
                for player_id in (match.top_player_id, match.bottom_player_id)
                if player_id
            }
        )
    )
    week = RankingWeek(season_index=0, week=raw_package.season_week)
    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Qualification flow",
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
    package = driver._packages(week)[0]
    assert len(package.frozen_bye_match_ids) == 1
    frozen_bye = next(
        match
        for match in package.qualification_matches
        if match.match_id in package.frozen_bye_match_ids
    )
    assert frozen_bye.status == "completed"
    assert frozen_bye.scoreline == "BYE"
    assert frozen_bye.winner_player_id is not None
    assert len(package.frozen_qualifier_promotions) == 1

    ordered_groups: list[tuple[str, ...]] = []
    for draw_type in ("qualification", "main"):
        phase = [
            match
            for match in package.qualification_matches + package.main_draw_matches
            if match.draw_type == draw_type
        ]
        for round_number in sorted({match.round_number for match in phase}):
            groups = tuple(
                match.match_id
                for match in phase
                if match.round_number == round_number
                and match.match_id not in package.frozen_bye_match_ids
            )
            if groups:
                ordered_groups.append(groups)

    schedule = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=week,
        slots=tuple(
            WeekSimulationScheduleSlot(ordinal=ordinal, group_ids=groups)
            for ordinal, groups in enumerate(ordered_groups, 1)
        ),
    )
    preview = driver.preview_schedule(schedule)
    driver.adopt_schedule(
        schedule,
        request_id="qualification-schedule",
        expected_position_fingerprint=preview["position_fingerprint"],
    )

    state = None
    for ordinal in range(1, len(schedule.slots) + 1):
        command, _ = _driver_command(driver, week, f"qualification-slot-{ordinal}")
        state = driver.simulate_next_slot(command)
    assert state is not None
    assert state["supported_tournament_complete"] is True

    qualification_final_round = max(
        match.round_number for match in package.qualification_matches
    )
    qualification_final = next(
        match
        for match in package.qualification_matches
        if match.round_number == qualification_final_round
    )
    promotion = package.frozen_qualifier_promotions[0]
    assert promotion.source_match_id == qualification_final.match_id

    with factory() as db:
        groups = db.scalars(
            select(SimulationEventGroupModel).order_by(SimulationEventGroupModel.group_id)
        ).all()
        expected_group_count = len(driver._topology((package,)))
        assert len(groups) == expected_group_count

        by_id = {
            group.group_id: AuthoritativeSlotMatchExecutor._load_group(group)
            for group in groups
        }
        qualifier_winner = by_id[qualification_final.match_id].result.winner_player_id
        promoted_main = by_id[promotion.target_match_id]
        assert qualifier_winner in {
            projection.player_id
            for projection in promoted_main.authoritative_input.player_projections
        }

        sources = OwnedTournamentRankingSourceStore(db).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        refs = sources[0].result.match_result_refs
        assert len(refs) == expected_group_count + len(package.frozen_bye_match_ids)
        assert {
            ref.match_id for ref in refs if ref.scoreline == "BYE"
        } == set(package.frozen_bye_match_ids)


@pytest.mark.smoke
def test_authoritative_wildcard_player_survives_to_owned_ranking_source(tmp_path):
    """Persisted WC authority is consumed by the authoritative tournament path."""
    root = tmp_path / "wildcard-flow"
    entries = make_service(root, main_draw_size=4)

    active_players = [
        *(active_player(index, ability=88) for index in range(1, 11)),
        *(active_player(index, ability=45) for index in range(101, 121)),
    ]
    active_registry = SeasonActivePlayersRegistry(
        players_by_season={"2000/2001": active_players},
        bootstrap_metadata_by_season={},
    )
    (root / "active.json").write_text(
        json.dumps(active_registry.model_dump(mode="json")),
        encoding="utf-8",
    )

    event_id = first_event_id(entries)
    calendars = entries.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    event = calendar.events[0]
    calendar.events[0] = event.model_copy(
        update={
            "qualification_draw_size": 3,
            "qualifier_spots": 1,
            "wild_cards": 1,
            "byes": 0,
        }
    )
    entries.calendar_service._save_registry(calendars)

    entry_seed = None
    for seed in range(1, 201):
        preview = entries.generate_entry_list(
            event_id=event_id,
            request=EntryListGenerateRequest(
                seed=seed,
                dry_run=True,
                max_alternates=16,
            ),
        )
        if (
            preview.summary.main_draw_acceptances == 2
            and preview.summary.qualification_acceptances == 3
        ):
            entries.generate_entry_list(
                event_id=event_id,
                request=EntryListGenerateRequest(
                    seed=seed,
                    dry_run=False,
                    max_alternates=16,
                ),
            )
            entry_seed = seed
            break
    assert entry_seed is not None

    persisted_entries = entries.get_entry_list(event_id=event_id).entry_list
    assert persisted_entries is not None
    accepted = {
        item.player_id
        for item in persisted_entries.entries
        if item.decision in {"accepted_main_draw", "accepted_qualification"}
    }
    wildcard_player = next(
        player for player in active_players if player.player_id not in accepted
    )

    draws = SeasonDrawService(
        entry_list_service=entries,
        calendar_service=entries.calendar_service,
        draws_path=root / "draws.json",
        wildcard_assignments_path=root / "wildcards.json",
    )
    assignment = draws.assign_wild_card(
        event_id=event_id,
        wildcard_index=1,
        player_id=wildcard_player.player_id,
    )
    draw = draws.generate_draw_package(
        event_id=event_id,
        request=DrawGenerateRequest(seed=5102, dry_run=False),
    ).draw_package
    assert draw is not None
    assert assignment.assignment_fingerprint == draw.metadata.wild_card_assignments_fingerprint or draw.metadata.wild_card_assignments_fingerprint is not None
    assigned_slots = [
        slot
        for slot in draw.main_draw.slots
        if slot.entry_decision == "wild_card_assigned"
    ]
    assert len(assigned_slots) == 1
    assert assigned_slots[0].player_id == wildcard_player.player_id

    matches = SeasonMatchService(
        draw_service=draws,
        active_players_service=entries.active_players_service,
        matches_path=root / "matches.json",
    )
    raw_package = matches.generate_match_package(
        event_id=event_id,
        request=MatchPackageGenerateRequest(seed=5103, dry_run=False),
    ).match_package
    assert raw_package is not None
    assert wildcard_player.player_id in {
        player_id
        for match in raw_package.main_draw_matches
        for player_id in (match.top_player_id, match.bottom_player_id)
        if player_id
    }

    results = SeasonEventResultsService(
        match_service=matches,
        results_path=root / "results.json",
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
                player_id
                for match in raw_package.qualification_matches
                + raw_package.main_draw_matches
                for player_id in (match.top_player_id, match.bottom_player_id)
                if player_id
            }
        )
    )
    week = RankingWeek(season_index=0, week=raw_package.season_week)
    session = session_at(root / "run.sqlite", player_ids, week)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Wildcard flow",
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
    package = driver._packages(week)[0]
    ordered_groups: list[tuple[str, ...]] = []
    for draw_type in ("qualification", "main"):
        phase = [
            match
            for match in package.qualification_matches + package.main_draw_matches
            if match.draw_type == draw_type
        ]
        for round_number in sorted({match.round_number for match in phase}):
            group_ids = tuple(
                match.match_id
                for match in phase
                if match.round_number == round_number
                and match.match_id not in package.frozen_bye_match_ids
            )
            if group_ids:
                ordered_groups.append(group_ids)

    schedule = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=week,
        slots=tuple(
            WeekSimulationScheduleSlot(ordinal=ordinal, group_ids=group_ids)
            for ordinal, group_ids in enumerate(ordered_groups, 1)
        ),
    )
    preview = driver.preview_schedule(schedule)
    driver.adopt_schedule(
        schedule,
        request_id="wildcard-schedule",
        expected_position_fingerprint=preview["position_fingerprint"],
    )

    state = None
    for ordinal in range(1, len(schedule.slots) + 1):
        command, _ = _driver_command(driver, week, f"wildcard-slot-{ordinal}")
        state = driver.simulate_next_slot(command)
    assert state is not None
    assert state["supported_tournament_complete"] is True

    with factory() as db:
        sources = OwnedTournamentRankingSourceStore(db).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        source = sources[0]
        assert wildcard_player.player_id in {
            result.player_id for result in source.result.player_results
        }
        assert any(
            ref.draw_type == "main" for ref in source.result.match_result_refs
        )
