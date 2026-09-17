"""Gate 3 acceptance for repeated generalized mixed-event sporting flow."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.application.season_draw_service import DrawGenerateRequest
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from beta_engine.application.season_match_service import MatchPackageGenerateRequest
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.models import (
    PlayerSportingWeekStateModel,
    PublishedOfficialRankingModel,
    SimulationEventGroupModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

from test_authoritative_simulation_api import (
    _install_owned_state,
    _real_eight_points,
    confirm,
    initial,
)
from test_authoritative_three_completed_weeks import _save_ranking, _save_simulation


def _accepted_player_ids(points, event_id: str) -> set[str]:
    entries = points.result_service.match_service.draw_service.entry_list_service
    persisted = entries.get_entry_list(event_id=event_id).entry_list
    assert persisted is not None
    return {
        entry.player_id
        for entry in persisted.entries
        if entry.decision in {"accepted_main_draw", "accepted_qualification"}
    }


def _add_real_event(
    points,
    *,
    source_event_id: str,
    event_id: str,
    week_number: int,
    main_draw_size: int,
    seed_base: int,
    avoid_player_ids: set[str] | None = None,
):
    """Create Calendar -> Entry -> Draw -> Match evidence for one event.

    Seed selection is deterministic and uses the production Entry Engine.  For a
    same-week companion event we only accept a seed whose persisted entrants do
    not overlap the already accepted event; no player IDs are injected manually.
    """

    avoid_player_ids = avoid_player_ids or set()
    matches = points.result_service.match_service
    draws = matches.draw_service
    entries = draws.entry_list_service

    calendars = points.calendar_service._load_registry()
    events = calendars.calendars_by_season["2000/2001"].events
    source_event = next(event for event in events if event.event_id == source_event_id)
    events.append(
        source_event.model_copy(
            update={
                "event_id": event_id,
                "event_name": event_id,
                "season_week": week_number,
                "start_season_week": week_number,
                "end_season_week": week_number,
                "year_week": week_number,
                "main_draw_size": main_draw_size,
                "qualification_draw_size": 0,
                "qualifier_spots": 0,
                "wild_cards": 0,
                "byes": 0,
                "seeds_count": min(source_event.seeds_count, main_draw_size),
            }
        )
    )
    points.calendar_service._save_registry(calendars)

    selected_seed = None
    for seed in range(seed_base, seed_base + 1000):
        preview = entries.generate_entry_list(
            event_id=event_id,
            request=EntryListGenerateRequest(
                seed=seed,
                dry_run=True,
                max_alternates=0,
            ),
        )
        candidate = preview.entry_list
        assert candidate is not None
        accepted = {
            entry.player_id
            for entry in candidate.entries
            if entry.decision in {"accepted_main_draw", "accepted_qualification"}
        }
        if (
            not preview.validation_errors
            and candidate.summary.main_draw_acceptances == main_draw_size
            and len(accepted) == main_draw_size
            and not (accepted & avoid_player_ids)
        ):
            selected_seed = seed
            break
    assert selected_seed is not None, (
        f"no deterministic full non-overlapping entry seed found for {event_id}"
    )

    persisted_entries = entries.generate_entry_list(
        event_id=event_id,
        request=EntryListGenerateRequest(
            seed=selected_seed,
            dry_run=False,
            max_alternates=0,
        ),
    ).entry_list
    assert persisted_entries is not None
    assert persisted_entries.summary.main_draw_acceptances == main_draw_size

    draw = draws.generate_draw_package(
        event_id=event_id,
        request=DrawGenerateRequest(seed=selected_seed + 10_000, dry_run=False),
    ).draw_package
    assert draw is not None
    package = matches.generate_match_package(
        event_id=event_id,
        request=MatchPackageGenerateRequest(seed=selected_seed + 20_000, dry_run=False),
    ).match_package
    assert package is not None
    assert len(package.qualification_matches) == 0
    assert len(package.main_draw_matches) == main_draw_size - 1
    return package


def _mixed_schedule(*, run_id: str, branch_id: str, week: RankingWeek, eight, four):
    eight_rounds = {
        number: sorted(
            match.match_id
            for match in eight.main_draw_matches
            if match.round_number == number
        )
        for number in sorted({match.round_number for match in eight.main_draw_matches})
    }
    four_matches = sorted(
        four.main_draw_matches,
        key=lambda match: (match.round_number, match.bracket_position),
    )
    return {
        "schema_version": "week_simulation_schedule.v1",
        "run_id": run_id,
        "branch_id": branch_id,
        "week": week.model_dump(mode="json"),
        "slots": [
            {
                "ordinal": 1,
                "group_ids": [*eight_rounds[1], *(m.match_id for m in four_matches[:2])],
            },
            {
                "ordinal": 2,
                "group_ids": [*eight_rounds[2], four_matches[2].match_id],
            },
            {"ordinal": 3, "group_ids": eight_rounds[3]},
        ],
    }


@pytest.mark.smoke
def test_three_mixed_generalized_weeks_reach_week_four(tmp_path):
    points, week_one_eight = _real_eight_points(tmp_path / "producer" / "eight")
    source_event_id = week_one_eight.event_id
    week_one_four = _add_real_event(
        points,
        source_event_id=source_event_id,
        event_id=f"{source_event_id}-FOUR-W1",
        week_number=1,
        main_draw_size=4,
        seed_base=51_000,
        avoid_player_ids=_accepted_player_ids(points, week_one_eight.event_id),
    )
    week_two_eight = _add_real_event(
        points,
        source_event_id=source_event_id,
        event_id=f"{source_event_id}-EIGHT-W2",
        week_number=2,
        main_draw_size=8,
        seed_base=52_000,
    )
    week_two_four = _add_real_event(
        points,
        source_event_id=source_event_id,
        event_id=f"{source_event_id}-FOUR-W2",
        week_number=2,
        main_draw_size=4,
        seed_base=53_000,
        avoid_player_ids=_accepted_player_ids(points, week_two_eight.event_id),
    )
    week_three_eight = _add_real_event(
        points,
        source_event_id=source_event_id,
        event_id=f"{source_event_id}-EIGHT-W3",
        week_number=3,
        main_draw_size=8,
        seed_base=54_000,
    )
    week_three_four = _add_real_event(
        points,
        source_event_id=source_event_id,
        event_id=f"{source_event_id}-FOUR-W3",
        week_number=3,
        main_draw_size=4,
        seed_base=55_000,
        avoid_player_ids=_accepted_player_ids(points, week_three_eight.event_id),
    )
    packages = {
        1: (week_one_eight, week_one_four),
        2: (week_two_eight, week_two_four),
        3: (week_three_eight, week_three_four),
    }

    matches = points.result_service.match_service
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'mixed-repeated.sqlite'}")
    server.app.dependency_overrides[get_season_match_service] = lambda: matches
    server.app.dependency_overrides[get_season_point_awards_service] = lambda: points

    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="Three mixed generalized weeks"
        )
        week_one = _install_owned_state(
            server,
            week_one_eight,
            run_id,
            branch_id,
            additional_packages=(week_one_four,),
        )
        ranking_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/ranking-candidates"
        )
        transition_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/week-transitions"
        )
        sim_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )

        with server.app.state.runtime.repository._session_factory() as session:
            lifecycle = get_lifecycle(
                session, run_id=run_id, branch_id=branch_id, week=week_one
            )
            roster = [
                player.model_dump(mode="json")
                for player in lifecycle.ranking_roster()
            ]
        bootstrap = initial() | {
            "run_id": run_id,
            "branch_id": branch_id,
            "players": roster,
        }
        assert _request(
            "POST", ranking_root + "/prepare/initial", bootstrap
        )[0] == 201
        revision = _save_ranking(server, ranking_root)

        historical_week_one = None

        for number in (1, 2, 3):
            week = RankingWeek(season_index=0, week=number)
            eight, four = packages[number]
            status, position = _request("GET", sim_root + "/position")
            assert status == 200, position
            assert position["current_week"] == week.model_dump(mode="json")

            schedule = _mixed_schedule(
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                eight=eight,
                four=four,
            )
            status, preview = _request(
                "POST", sim_root + "/week-schedule/preview", {"schedule": schedule}
            )
            assert status == 200, preview
            status, adopted = _request(
                "POST",
                sim_root + "/week-schedule",
                {
                    "schedule": schedule,
                    "request_id": f"mixed-week-{number}-schedule",
                    "expected_position_fingerprint": preview["position_fingerprint"],
                },
            )
            assert status == 201, adopted

            for slot_ordinal in (1, 2, 3):
                status, position = _request("GET", sim_root + "/position")
                assert status == 200, position
                status, body = _request(
                    "POST",
                    sim_root + "/simulate-next-slot",
                    {
                        "command_id": f"mixed-week-{number}-slot-{slot_ordinal}",
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "expected_week": week.model_dump(mode="json"),
                        "expected_position_fingerprint": position[
                            "position_fingerprint"
                        ],
                        "expected_revision_id": revision,
                    },
                )
                assert status == 200, body

            with server.app.state.runtime.repository._session_factory() as session:
                week_sources = [
                    source
                    for source in OwnedTournamentRankingSourceStore(session).history(
                        run_id=run_id, branch_id=branch_id
                    )
                    if source.binding.completed_week == week
                ]
                assert len(week_sources) == 2
                week_rows = session.scalars(
                    select(SimulationEventGroupModel).where(
                        SimulationEventGroupModel.run_id == run_id,
                        SimulationEventGroupModel.branch_id == branch_id,
                        SimulationEventGroupModel.week_ordinal == week.ordinal,
                    )
                ).all()
                assert len(week_rows) == 10
                if number == 1:
                    row = sorted(
                        week_rows, key=lambda value: (value.slot_id, value.group_id)
                    )[0]
                    replay = AuthoritativeSlotMatchExecutor(session).replay(
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        slot_id=row.slot_id,
                        group_id=row.group_id,
                    )
                    historical_week_one = (
                        row.slot_id,
                        row.group_id,
                        replay.result_fingerprint,
                        replay.authoritative_input.fingerprint,
                    )
                lifecycle = get_lifecycle(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                )
                roster = [
                    player.model_dump(mode="json")
                    for player in lifecycle.ranking_roster()
                ]

            revision = _save_simulation(sim_root)
            target = {"season_index": 0, "week": number + 1}
            status, authority = _request(
                "POST",
                ranking_root + "/transition-authorities",
                {
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "base_revision_id": revision,
                    "completed_week": week.model_dump(mode="json"),
                    "target_week": target,
                    "players": roster,
                    "policy": bootstrap["policy"],
                    "provenance": "Repeated mixed generalized Gate 3 acceptance",
                    "adopted_by_command_id": f"mixed-week-{number}-authority",
                    "audit": bootstrap["audit"],
                },
            )
            assert status == 201, authority
            revision = _save_ranking(server, ranking_root)

            status, ready = _request("GET", sim_root + "/position")
            assert status == 200, ready
            assert ready["week_ready_for_transition"] is True, ready[
                "transition_blockers"
            ]
            ordered_sources = sorted(
                week_sources, key=lambda source: source.binding.event_id
            )
            transition_command = {
                "command_id": f"mixed-week-{number}-transition",
                "run_id": run_id,
                "branch_id": branch_id,
                "base_revision_id": revision,
                "completed_week": week.model_dump(mode="json"),
                "target_week": target,
                "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                    json.dumps(authority)
                ).fingerprint,
                "tournaments": [
                    source.binding.model_dump(mode="json") for source in ordered_sources
                ],
                "audit": bootstrap["audit"],
            }
            status, transition_preview = _request(
                "POST", transition_root + "/preview", transition_command
            )
            assert status == 200, transition_preview
            assert (
                confirm(transition_root, transition_command, transition_preview)[0]
                == 201
            )
            revision = _save_ranking(server, ranking_root)

        status, final_position = _request("GET", sim_root + "/position")
        assert status == 200, final_position
        assert final_position["current_week"] == {
            "season_index": 0,
            "week": 4,
        }

        with server.app.state.runtime.repository._session_factory() as session:
            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id, branch_id=branch_id
            )
            assert len(sources) == 6
            assert sorted(
                source.binding.completed_week.week for source in sources
            ) == [1, 1, 2, 2, 3, 3]

            rows = session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == run_id,
                    SimulationEventGroupModel.branch_id == branch_id,
                )
            ).all()
            assert len(rows) == 30

            assert historical_week_one is not None
            slot_id, group_id, result_fp, input_fp = historical_week_one
            replay = AuthoritativeSlotMatchExecutor(session).replay(
                run_id=run_id,
                branch_id=branch_id,
                week=RankingWeek(season_index=0, week=1),
                slot_id=slot_id,
                group_id=group_id,
            )
            assert replay.result_fingerprint == result_fp
            assert replay.authoritative_input.fingerprint == input_fp

            rankings = session.scalars(
                select(PublishedOfficialRankingModel)
                .where(
                    PublishedOfficialRankingModel.run_id == run_id,
                    PublishedOfficialRankingModel.branch_id == branch_id,
                )
                .order_by(PublishedOfficialRankingModel.week_ordinal)
            ).all()
            assert [row.week_ordinal for row in rankings] == [0, 1, 2, 3]

            sporting_rows = session.scalars(
                select(PlayerSportingWeekStateModel)
                .where(
                    PlayerSportingWeekStateModel.run_id == run_id,
                    PlayerSportingWeekStateModel.branch_id == branch_id,
                )
                .order_by(PlayerSportingWeekStateModel.week_ordinal)
            ).all()
            assert [row.week_ordinal for row in sporting_rows] == [0, 1, 2, 3]
            states = [json.loads(row.payload_json) for row in sporting_rows]
            assert all(state["predecessor_fingerprint"] for state in states[1:])
            assert len(
                {state["completed_context_fingerprint"] for state in states[1:]}
            ) == 3
