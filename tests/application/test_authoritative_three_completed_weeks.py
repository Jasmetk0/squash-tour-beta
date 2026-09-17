"""Gate 3 acceptance for three fully completed authoritative RankingWeeks."""

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
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.models import (
    PlayerSportingWeekStateModel,
    PublishedOfficialRankingModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from tests.api.test_saved_revision_history_api import _create_run, _request

from test_authoritative_simulation_api import (
    _install_owned_state,
    _server_state,
    confirm,
    initial,
)


def _add_week_three_event(server):
    """Extend the disposable producer fixture before Run ownership begins.

    This is source-fixture preparation only. After the Run is created, all sporting,
    simulation, ranking and transition mutations go through production boundaries.
    """

    matches = server.app.dependency_overrides[get_season_match_service]()
    points = server.app.dependency_overrides[get_season_point_awards_service]()
    registry = matches._load_registry()
    week_two = next(
        package
        for package in registry.matches_by_event_id.values()
        if package.season == "2000/2001" and package.season_week == 2
    )
    week_three = week_two.model_copy(deep=True)
    week_three.event_id = f"{week_two.event_id}-W3"
    week_three.season_week = 3
    week_three.year_week = 3
    week_three.metadata.event_id = week_three.event_id
    week_three.summary.event_id = week_three.event_id

    all_matches = week_three.qualification_matches + week_three.main_draw_matches
    id_map = {match.match_id: f"{match.match_id}-W3" for match in all_matches}
    for match in all_matches:
        original_id = match.match_id
        match.match_id = id_map[original_id]
        if match.winner_to_match_id:
            match.winner_to_match_id = id_map[match.winner_to_match_id]
        match.event_id = week_three.event_id

    registry.matches_by_event_id[week_three.event_id] = week_three
    matches._save_registry(registry)

    calendars = points.calendar_service._load_registry()
    events = calendars.calendars_by_season["2000/2001"].events
    week_two_event = next(event for event in events if event.event_id == week_two.event_id)
    events.append(
        week_two_event.model_copy(
            update={
                "event_id": week_three.event_id,
                "season_week": 3,
                "start_season_week": 3,
                "end_season_week": 3,
            }
        )
    )
    points.calendar_service._save_registry(calendars)
    return week_three


def _save_ranking(server, ranking_root):
    preview = _request("GET", ranking_root + "/save/preview")[1]
    status, saved = _request(
        "POST",
        ranking_root + "/save",
        {
            "expected_draft_version": preview["draft_version"],
            "expected_ranking_fingerprint": preview["ranking_fingerprint"],
        },
    )
    assert status == 201, saved
    return saved["saved_revision"]["revision_id"]


def _save_simulation(sim_root):
    preview = _request("GET", sim_root + "/save/preview")[1]
    status, saved = _request(
        "POST",
        sim_root + "/save",
        {
            "expected_draft_version": preview["draft_version"],
            "expected_simulation_fingerprint": preview["simulation_fingerprint"],
        },
    )
    assert status == 201, saved
    return saved["saved_revision"]["revision_id"]


@pytest.mark.smoke
def test_three_completed_weeks_reach_week_four_without_state_repair(tmp_path):
    server, week_one_package = _server_state(tmp_path)
    _add_week_three_event(server)

    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="Three completed authoritative weeks"
        )
        week_one = _install_owned_state(
            server, week_one_package, run_id, branch_id
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

        week_one_replay = None
        completed_bindings = []

        for number in (1, 2, 3):
            position = _request("GET", sim_root + "/position")[1]
            assert position["current_week"] == {
                "season_index": 0,
                "week": number,
            }

            for slot_index in (1, 2):
                position = _request("GET", sim_root + "/position")[1]
                status, body = _request(
                    "POST",
                    sim_root + "/simulate-next-slot",
                    {
                        "command_id": f"week-{number}-slot-{slot_index}",
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "expected_week": position["current_week"],
                        "expected_position_fingerprint": position[
                            "position_fingerprint"
                        ],
                        "expected_revision_id": revision,
                    },
                )
                assert status == 200, body

            with server.app.state.runtime.repository._session_factory() as session:
                sources = OwnedTournamentRankingSourceStore(session).history(
                    run_id=run_id, branch_id=branch_id
                )
                source = next(
                    item
                    for item in sources
                    if item.binding.completed_week.week == number
                )
                completed_bindings.append(source.binding)
                if number == 1:
                    first_ref = source.result.match_result_refs[0]
                    week_one_replay = AuthoritativeSlotMatchExecutor(session).replay(
                        run_id=run_id,
                        branch_id=branch_id,
                        week=RankingWeek(season_index=0, week=1),
                        slot_id=f"{source.binding.event_id}:slot:1",
                        group_id=first_ref.match_id,
                    )
                lifecycle = get_lifecycle(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=RankingWeek(season_index=0, week=number),
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
                    "completed_week": {
                        "season_index": 0,
                        "week": number,
                    },
                    "target_week": target,
                    "players": roster,
                    "policy": bootstrap["policy"],
                    "provenance": "Three completed week Gate 3 acceptance",
                    "adopted_by_command_id": f"three-week-authority-{number}",
                    "audit": bootstrap["audit"],
                },
            )
            assert status == 201, authority
            revision = _save_ranking(server, ranking_root)

            ready = _request("GET", sim_root + "/position")[1]
            assert ready["week_ready_for_transition"] is True, ready[
                "transition_blockers"
            ]
            transition_command = {
                "command_id": f"three-week-transition-{number}",
                "run_id": run_id,
                "branch_id": branch_id,
                "base_revision_id": revision,
                "completed_week": {"season_index": 0, "week": number},
                "target_week": target,
                "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                    json.dumps(authority)
                ).fingerprint,
                "tournaments": [source.binding.model_dump(mode="json")],
                "audit": bootstrap["audit"],
            }
            preview = _request(
                "POST", transition_root + "/preview", transition_command
            )[1]
            assert confirm(transition_root, transition_command, preview)[0] == 201
            revision = _save_ranking(server, ranking_root)

        final_position = _request("GET", sim_root + "/position")[1]
        assert final_position["current_week"] == {
            "season_index": 0,
            "week": 4,
        }
        assert [binding.completed_week.week for binding in completed_bindings] == [
            1,
            2,
            3,
        ]

        with server.app.state.runtime.repository._session_factory() as session:
            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id, branch_id=branch_id
            )
            assert [source.binding.completed_week.week for source in sources] == [
                1,
                2,
                3,
            ]
            assert week_one_replay is not None
            replayed = AuthoritativeSlotMatchExecutor(session).replay(
                run_id=run_id,
                branch_id=branch_id,
                week=RankingWeek(season_index=0, week=1),
                slot_id=week_one_replay.authoritative_input.slot_id,
                group_id=week_one_replay.authoritative_input.group_id,
            )
            assert replayed.authoritative_input == week_one_replay.authoritative_input
            assert replayed.result == week_one_replay.result

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
