"""Acceptance coverage for explicit authoritative zero-match weeks."""

from __future__ import annotations

import json

import pytest

from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.application.authoritative_run_simulation_driver import (
    AUTHORITATIVE_EMPTY_WEEK_PROVENANCE,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import get_completed_context
from tests.api.test_saved_revision_history_api import _create_run, _request

from test_authoritative_simulation_api import (
    _install_owned_state,
    _server_state,
    confirm,
    initial,
)
from test_authoritative_three_completed_weeks import (
    _save_ranking,
    _save_simulation,
)


def _remove_week_two_source_fixture(server) -> None:
    """Make Week 2 genuinely event-free before Run ownership begins."""

    matches = server.app.dependency_overrides[get_season_match_service]()
    registry = matches._load_registry()
    registry.matches_by_event_id = {
        event_id: package
        for event_id, package in registry.matches_by_event_id.items()
        if not (package.season == "2000/2001" and package.season_week == 2)
    }
    matches._save_registry(registry)

    awards = server.app.dependency_overrides[get_season_point_awards_service]()
    calendars = awards.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    calendar.events = [
        event
        for event in calendar.events
        if event.season_week != 2
    ]
    awards.calendar_service._save_registry(calendars)


def _roster(server, run_id: str, branch_id: str, week: RankingWeek):
    with server.app.state.runtime.repository._session_factory() as session:
        lifecycle = get_lifecycle(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        assert lifecycle is not None
        return [
            player.model_dump(mode="json")
            for player in lifecycle.ranking_roster()
        ]


def _complete_tournament_week(
    server,
    *,
    run_id: str,
    branch_id: str,
    revision: str,
    number: int,
    bootstrap: dict,
):
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

    for slot_index in (1, 2):
        position = _request("GET", sim_root + "/position")[1]
        assert position["current_week"] == {
            "season_index": 0,
            "week": number,
        }
        status, body = _request(
            "POST",
            sim_root + "/simulate-next-slot",
            {
                "command_id": f"empty-week-prelude-{number}-{slot_index}",
                "run_id": run_id,
                "branch_id": branch_id,
                "expected_week": position["current_week"],
                "expected_position_fingerprint": position["position_fingerprint"],
                "expected_revision_id": revision,
            },
        )
        assert status == 200, body

    completed = RankingWeek(season_index=0, week=number)
    with server.app.state.runtime.repository._session_factory() as session:
        source = next(
            item
            for item in OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
            )
            if item.binding.completed_week == completed
        )
    revision = _save_simulation(sim_root)

    roster = _roster(server, run_id, branch_id, completed)
    target = {"season_index": 0, "week": number + 1}
    status, authority = _request(
        "POST",
        ranking_root + "/transition-authorities",
        {
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": revision,
            "completed_week": completed.model_dump(mode="json"),
            "target_week": target,
            "players": roster,
            "policy": bootstrap["policy"],
            "provenance": "Empty-week acceptance tournament prelude",
            "adopted_by_command_id": f"empty-week-authority-{number}",
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
        "command_id": f"empty-week-transition-{number}",
        "run_id": run_id,
        "branch_id": branch_id,
        "base_revision_id": revision,
        "completed_week": completed.model_dump(mode="json"),
        "target_week": target,
        "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
            json.dumps(authority)
        ).fingerprint,
        "tournaments": [source.binding.model_dump(mode="json")],
        "audit": bootstrap["audit"],
    }
    preview = _request(
        "POST",
        transition_root + "/preview",
        transition_command,
    )[1]
    assert confirm(transition_root, transition_command, preview)[0] == 201
    return _save_ranking(server, ranking_root)


@pytest.mark.pr_critical
def test_explicit_empty_week_advances_without_manual_database_repair(tmp_path):
    server, package = _server_state(tmp_path)
    _remove_week_two_source_fixture(server)

    with server:
        run_id, branch_id, revision = _create_run(
            server,
            display_name="Authoritative empty week acceptance",
        )
        week_one = _install_owned_state(
            server,
            package,
            run_id,
            branch_id,
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
        bootstrap = initial() | {
            "run_id": run_id,
            "branch_id": branch_id,
            "players": _roster(server, run_id, branch_id, week_one),
        }
        assert _request(
            "POST",
            ranking_root + "/prepare/initial",
            bootstrap,
        )[0] == 201
        revision = _save_ranking(server, ranking_root)

        for number in (1,):
            revision = _complete_tournament_week(
                server,
                run_id=run_id,
                branch_id=branch_id,
                revision=revision,
                number=number,
                bootstrap=bootstrap,
            )

        empty_week = RankingWeek(season_index=0, week=2)
        before = _request("GET", sim_root + "/position")[1]
        assert before["current_week"] == empty_week.model_dump(mode="json")
        assert "week_schedule_missing" in before["transition_blockers"]
        assert "terminal_sporting_checkpoint_missing" in before[
            "transition_blockers"
        ]

        command = {
            "command_id": "complete-empty-week-2",
            "expected_week": empty_week.model_dump(mode="json"),
            "expected_position_fingerprint": before["position_fingerprint"],
            "expected_revision_id": revision,
            "operator_label": "Acceptance Admin",
            "audit_reason": "Confirm the Calendar has no competitive work in Week 2",
        }
        status, completed = _request(
            "POST",
            sim_root + "/empty-week/complete",
            command,
        )
        assert status == 201, completed
        assert completed["schema_version"] == "authoritative_empty_week_completion.v1"
        assert completed["competitive_match_count"] == 0
        assert completed["position"]["current_week"] == empty_week.model_dump(
            mode="json"
        )
        assert "week_schedule_missing" not in completed["position"][
            "transition_blockers"
        ]
        assert "terminal_sporting_checkpoint_missing" not in completed["position"][
            "transition_blockers"
        ]

        assert _request(
            "POST",
            sim_root + "/empty-week/complete",
            command,
        ) == (201, completed)

        with server.app.state.runtime.repository._session_factory() as session:
            context = get_completed_context(
                session,
                run_id=run_id,
                branch_id=branch_id,
                completed_week=empty_week,
            )
            assert context.provenance == AUTHORITATIVE_EMPTY_WEEK_PROVENANCE
            assert len(context.source_fingerprints) == 1
            assert all(
                item.count == 0 for item in context.competitive_match_counts
            )
            assert context.terminal_sporting_fingerprint is None
            assert context.match_effect_fingerprints == ()

        # Persist the explicit evidence through the ordinary Saved Revision path.
        revision = _save_simulation(sim_root)

        roster = _roster(server, run_id, branch_id, empty_week)
        target = {"season_index": 0, "week": 3}
        status, authority = _request(
            "POST",
            ranking_root + "/transition-authorities",
            {
                "run_id": run_id,
                "branch_id": branch_id,
                "base_revision_id": revision,
                "completed_week": empty_week.model_dump(mode="json"),
                "target_week": target,
                "players": roster,
                "policy": bootstrap["policy"],
                "provenance": "Explicit empty-week acceptance",
                "adopted_by_command_id": "empty-week-authority-2",
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
            "command_id": "transition-empty-week-2",
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": revision,
            "completed_week": empty_week.model_dump(mode="json"),
            "target_week": target,
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                json.dumps(authority)
            ).fingerprint,
            "tournaments": [],
            "audit": bootstrap["audit"],
        }
        preview = _request(
            "POST",
            transition_root + "/preview",
            transition_command,
        )[1]
        assert confirm(transition_root, transition_command, preview)[0] == 201
        _save_ranking(server, ranking_root)

        after = _request("GET", sim_root + "/position")[1]
        assert after["current_week"] == {
            "season_index": 0,
            "week": 3,
        }


@pytest.mark.pr_critical
def test_empty_week_completion_rejects_a_calendar_tournament(tmp_path):
    server, package = _server_state(tmp_path)

    with server:
        run_id, branch_id, revision = _create_run(
            server,
            display_name="Reject false empty week",
        )
        _install_owned_state(server, package, run_id, branch_id)
        sim_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )
        position = _request("GET", sim_root + "/position")[1]
        status, body = _request(
            "POST",
            sim_root + "/empty-week/complete",
            {
                "command_id": "false-empty-week",
                "expected_week": position["current_week"],
                "expected_position_fingerprint": position[
                    "position_fingerprint"
                ],
                "expected_revision_id": revision,
                "operator_label": "Acceptance Admin",
                "audit_reason": "This must fail because Week 1 has a tournament",
            },
        )
        assert status == 409
        assert body["detail"]["code"] == (
            "authoritative_empty_week_completion_conflict"
        )
        assert "Calendar events" in body["detail"]["message"]
