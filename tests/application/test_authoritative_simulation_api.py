"""Real HTTP/file-backed SQLite coverage for authoritative simulation routes."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from urllib import request

import pytest
from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.initial_world_state import (
    get_initial_world,
    put_initial_world,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    get_sporting,
    put_sporting,
)

from test_authoritative_slot_matches import session_at, _multi_driver_fixture
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    PlayerSportingWeekStateModel,
    SimulationEventGroupModel,
)
from sqlalchemy import select
from test_season_point_awards_service import make_points_service


def _real_eight_points(tmp_path):
    """Build the production Entry -> Draw -> Match chain used by PR #733."""
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

    entries = make_service(tmp_path, main_draw_size=8)
    event_id = first_event_id(entries)
    calendars = entries.calendar_service._load_registry()
    event = calendars.calendars_by_season["2000/2001"].events[0]
    calendars.calendars_by_season["2000/2001"].events[0] = event.model_copy(
        update={
            "season_week": 1,
            "start_season_week": 1,
            "end_season_week": 1,
            "qualification_draw_size": 0,
            "qualifier_spots": 0,
            "wild_cards": 0,
            "byes": 0,
        }
    )
    entries.calendar_service._save_registry(calendars)
    entries.generate_entry_list(
        event_id=event_id, request=EntryListGenerateRequest(seed=4201, dry_run=False)
    )
    draws = SeasonDrawService(
        entries, entries.calendar_service, tmp_path / "draws.json"
    )
    draws.generate_draw_package(
        event_id=event_id, request=DrawGenerateRequest(seed=4202, dry_run=False)
    )
    matches = SeasonMatchService(
        draws, entries.active_players_service, tmp_path / "matches.json"
    )
    package = matches.generate_match_package(
        event_id=event_id, request=MatchPackageGenerateRequest(seed=4203, dry_run=False)
    ).match_package
    assert package and len(package.main_draw_matches) == 7
    results = SeasonEventResultsService(
        match_service=matches, results_path=tmp_path / "results.json"
    )
    points = SeasonPointAwardsService(
        result_service=results,
        active_players_service=entries.active_players_service,
        calendar_service=entries.calendar_service,
        template_service=entries.calendar_service.template_service,
        awards_path=tmp_path / "awards.json",
        points_config_path=tmp_path / "points.json",
    )
    return points, package


def _add_legacy_four_player_event(points, eight, tmp_path):
    """Add the reviewed four-player compatibility event beside the real draw."""
    legacy_points, legacy_event_id = make_points_service(tmp_path)
    package = (
        legacy_points.result_service.match_service._load_registry()
        .matches_by_event_id[legacy_event_id]
        .model_copy(deep=True)
    )
    package.qualification_matches = []
    package.event_id = f"{eight.event_id}-FOUR"
    package.metadata.event_id = package.event_id
    package.season_week = eight.season_week
    id_map = {
        match.match_id: f"{package.event_id}:{match.match_id.rsplit(':', 3)[-3]}:{match.match_id.rsplit(':', 2)[-2]}:{match.match_id.rsplit(':', 1)[-1]}"
        for match in package.main_draw_matches
    }
    used = {
        p
        for match in eight.main_draw_matches
        for p in (match.top_player_id, match.bottom_player_id)
        if p
    }
    player_ids = [
        player.player_id
        for player in points.active_players_service.get_active_players(
            season=eight.season
        ).players
        if player.player_id not in used
    ][:4]
    assert len(player_ids) == 4
    legacy_matches = sorted(
        package.main_draw_matches, key=lambda m: (m.round_number, m.bracket_position)
    )
    for match in legacy_matches:
        original_id = match.match_id
        match.match_id = id_map[original_id]
        if match.winner_to_match_id:
            match.winner_to_match_id = id_map[match.winner_to_match_id]
        match.event_id = package.event_id
    for match, pair in zip(
        legacy_matches[:2], (player_ids[:2], player_ids[2:]), strict=True
    ):
        match.top_player_id, match.bottom_player_id = pair
    registry = points.result_service.match_service._load_registry()
    registry.matches_by_event_id[package.event_id] = package
    points.result_service.match_service._save_registry(registry)
    calendars = points.calendar_service._load_registry()
    event = calendars.calendars_by_season["2000/2001"].events[0]
    calendars.calendars_by_season["2000/2001"].events.append(
        event.model_copy(update={"event_id": package.event_id, "main_draw_size": 4})
    )
    points.calendar_service._save_registry(calendars)
    return package


def confirm(url, command, preview):
    req = request.Request(
        url,
        data=json.dumps(command).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Week-Transition-Request-Fingerprint": preview["request_fingerprint"],
            "X-Week-Transition-Ranking-Fingerprint": preview["result"][
                "official_ranking_fingerprint"
            ],
        },
    )
    with request.urlopen(req) as response:
        return response.status, json.loads(response.read())


def initial():
    return {
        "command_id": "prepare-initial",
        "run_id": "run",
        "branch_id": "branch",
        "discipline": "stored_zeros",
        "policy": {"policy_id": "policy", "best_n": 15},
        "players": [],
        "audit": {
            "actor_label": "Admin operator",
            "reason": "Prepare reviewed ranking inputs",
        },
    }


def _server_state(tmp_path):
    points, event_id = make_points_service(tmp_path / "source")
    matches = points.result_service.match_service
    registry = matches._load_registry()
    week_two = registry.matches_by_event_id[event_id]
    week_two.qualification_matches = []
    package = week_two.model_copy(deep=True)
    package.event_id = f"{event_id}-A"
    package.metadata.event_id = package.event_id
    package.season_week = 1
    id_map = {
        match.match_id: f"{match.match_id}-A" for match in package.main_draw_matches
    }
    for match in package.main_draw_matches:
        match.match_id = id_map[match.match_id]
        if match.winner_to_match_id:
            match.winner_to_match_id = id_map[match.winner_to_match_id]
        match.event_id = package.event_id
    registry.matches_by_event_id[event_id] = week_two
    registry.matches_by_event_id[package.event_id] = package
    matches._save_registry(registry)
    calendars = points.calendar_service._load_registry()
    event = calendars.calendars_by_season["2000/2001"].events[0]
    first = event.model_copy(deep=True)
    first.event_id = package.event_id
    first.season_week = first.start_season_week = first.end_season_week = 1
    calendars.calendars_by_season["2000/2001"].events.insert(0, first)
    points.calendar_service._save_registry(calendars)
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'api.sqlite'}")
    server.app.dependency_overrides[get_season_match_service] = lambda: matches
    server.app.dependency_overrides[get_season_point_awards_service] = lambda: points
    return server, package


def _install_owned_state(server, package, run_id, branch_id, additional_packages=()):
    ids = tuple(
        dict.fromkeys(
            player_id
            for owned_package in (package, *additional_packages)
            for match in sorted(
                (m for m in owned_package.main_draw_matches if m.round_number == 1),
                key=lambda m: m.bracket_position,
            )
            for player_id in (match.top_player_id, match.bottom_player_id)
        )
    )
    week = RankingWeek(season_index=0, week=package.season_week)
    source = session_at(
        Path(server.app.state.runtime.repository._engine.url.database + ".source"),
        ids,
        week,
    )
    world = get_initial_world(source, run_id="run", branch_id="branch")
    lifecycle = get_lifecycle(source, run_id="run", branch_id="branch", week=week)
    sporting = get_sporting(source, run_id="run", branch_id="branch", week=week)
    source.close()
    owned_world = world.model_copy(update={"run_id": run_id, "branch_id": branch_id})
    with server.app.state.runtime.repository._session_factory.begin() as session:
        put_initial_world(session, owned_world)
        put_lifecycle(
            session,
            lifecycle.model_copy(
                update={
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "source_initial_world_fingerprint": owned_world.fingerprint,
                }
            ),
        )
        put_sporting(
            session,
            sporting.model_copy(
                update={
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "source_initial_world_fingerprint": owned_world.fingerprint,
                    "completed_context_fingerprint": "bootstrap:not-a-completed-week",
                }
            ),
        )
    return week


@pytest.mark.pr_critical
def test_authoritative_simulation_http_guards_retry_and_close(tmp_path):
    server, package = _server_state(tmp_path)
    legacy_hash = hashlib.sha256(
        server.app.dependency_overrides[
            get_season_match_service
        ]().matches_path.read_bytes()
    ).hexdigest()
    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="Authoritative HTTP"
        )
        week = _install_owned_state(server, package, run_id, branch_id)
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        status, opening = _request("GET", root + "/position")
        assert status == 200 and len(opening["eligible_match_ids"]) == 2
        before_preflight = Path(
            server.app.state.runtime.repository._engine.url.database
        ).read_bytes()
        status, season_preflight = _request(
            "GET", root + "/season-transition/preflight"
        )
        assert status == 200
        assert (
            season_preflight["schema_version"]
            == "authoritative_season_transition_preflight.v1"
        )
        assert season_preflight["completed_week"] == {
            "season_index": 0,
            "week": 1,
        }
        assert season_preflight["target_week"] is None
        assert season_preflight["final_season"] is False
        assert "not_at_season_boundary" in season_preflight["state_blockers"]
        assert season_preflight["ready_for_execution"] is False
        assert (
            "season_transition_atomic_writer_not_implemented"
            in season_preflight["implementation_gaps"]
        )
        assert len(season_preflight["preflight_fingerprint"]) == 64
        assert Path(
            server.app.state.runtime.repository._engine.url.database
        ).read_bytes() == before_preflight
        base = {
            "command_id": "sf",
            "run_id": run_id,
            "branch_id": branch_id,
            "expected_week": week.model_dump(mode="json"),
            "expected_position_fingerprint": opening["position_fingerprint"],
            "expected_revision_id": revision,
        }
        assert _request("POST", root + "/simulate-next-match", base)[0] == 409
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                base
                | {"command_id": "later", "group_id": opening["blocked_match_ids"][0]},
            )[0]
            == 409
        )
        command = base | {"group_id": opening["eligible_match_ids"][0]}
        status, first = _request("POST", root + "/simulate-next-match", command)
        assert status == 200
        assert _request("POST", root + "/simulate-next-match", command) == (200, first)
        save_preview = _request("GET", root + "/save/preview")[1]
        assert save_preview["can_save"] is True
        status, saved = _request(
            "POST",
            root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_simulation_fingerprint": save_preview[
                    "simulation_fingerprint"
                ],
            },
        )
        assert status == 201, saved
        revision = saved["saved_revision"]["revision_id"]
        base["expected_revision_id"] = revision
        command["expected_revision_id"] = revision
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command | {"group_id": opening["eligible_match_ids"][1]},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command
                | {"command_id": "stale", "group_id": opening["eligible_match_ids"][1]},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command
                | {
                    "command_id": "week",
                    "expected_week": {"season_index": 0, "week": 1},
                },
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command | {"command_id": "head", "expected_revision_id": "stale"},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST", root.replace(run_id, "wrong") + "/simulate-next-match", command
            )[0]
            == 409
        )
        status, current = _request("GET", root + "/position")
        second = base | {
            "command_id": "sf2",
            "expected_position_fingerprint": current["position_fingerprint"],
            "group_id": current["eligible_match_ids"][0],
        }
        assert _request("POST", root + "/simulate-next-match", second)[0] == 200
        current = _request("GET", root + "/position")[1]
        final = base | {
            "command_id": "final",
            "expected_position_fingerprint": current["position_fingerprint"],
        }
        status, closed = _request("POST", root + "/simulate-next-slot", final)
        assert status == 200 and closed["week_ready_for_transition"] is False
        assert "ranking_transition_authority_missing" in closed["transition_blockers"]
    assert (
        hashlib.sha256(
            server.app.dependency_overrides[
                get_season_match_service
            ]().matches_path.read_bytes()
        ).hexdigest()
        == legacy_hash
    )


@pytest.mark.pr_critical
def test_topological_schedule_proposal_over_http_adopts_atomically(tmp_path):
    driver, _, week, first, second = _multi_driver_fixture(
        tmp_path / "proposal-http-source"
    )
    server = ApiServer(
        database_url=f"sqlite:///{tmp_path / 'proposal-http.sqlite'}"
    )
    server.app.dependency_overrides[get_season_match_service] = lambda: (
        driver.match_service
    )
    server.app.dependency_overrides[get_season_point_awards_service] = lambda: (
        driver.awards_service
    )

    with server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="HTTP topological proposal",
        )
        _install_owned_state(
            server,
            first,
            run_id,
            branch_id,
            additional_packages=(second,),
        )
        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/"
            "authoritative-simulation"
        )

        status, proposed = _request(
            "GET",
            root + "/week-schedule/proposal",
        )
        assert status == 200, proposed
        assert proposed["persisted"] is False
        assert len(proposed["schedule"]["slots"]) == 2

        adoption = {
            "request_id": "adopt-topological-proposal",
            "expected_week": proposed["schedule"]["week"],
            "expected_schedule_fingerprint": proposed[
                "schedule_fingerprint"
            ],
            "expected_position_fingerprint": proposed[
                "position_fingerprint"
            ],
        }
        status, adopted = _request(
            "POST",
            root + "/week-schedule/adopt-proposal",
            adoption,
        )
        assert status == 201, adopted
        assert adopted["adoption"] == "adopted_topological_proposal"
        assert (
            adopted["schedule_fingerprint"]
            == proposed["schedule_fingerprint"]
        )

        status, retry = _request(
            "POST",
            root + "/week-schedule/adopt-proposal",
            adoption,
        )
        assert status == 201, retry
        assert retry["adoption"] == "exact_retry"
        assert (
            retry["schedule_fingerprint"]
            == proposed["schedule_fingerprint"]
        )

        status, immutable = _request(
            "POST",
            root + "/week-schedule/adopt-proposal",
            adoption | {"request_id": "different-request"},
        )
        assert status == 409
        assert immutable["detail"]["code"] == "topological_schedule_adoption_conflict"

        status, conflict = _request(
            "GET",
            root + "/week-schedule/proposal",
        )
        assert status == 409
        assert (
            conflict["detail"]["code"]
            == "topological_schedule_proposal_conflict"
        )
        assert "already adopted" in conflict["detail"]["message"]


@pytest.mark.smoke
def test_multi_event_schedule_preview_adopt_stale_and_exact_retry_over_http(tmp_path):
    driver, _, week, first, second = _multi_driver_fixture(tmp_path / "multi-source")
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'multi-api.sqlite'}")
    server.app.dependency_overrides[get_season_match_service] = lambda: (
        driver.match_service
    )
    server.app.dependency_overrides[get_season_point_awards_service] = lambda: (
        driver.awards_service
    )
    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="HTTP multi schedule"
        )
        _install_owned_state(
            server, first, run_id, branch_id, additional_packages=(second,)
        )
        matches_a = sorted(
            first.main_draw_matches,
            key=lambda match: (match.round_number, match.bracket_position),
        )
        matches_b = sorted(
            second.main_draw_matches,
            key=lambda match: (match.round_number, match.bracket_position),
        )
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        schedule = {
            "schema_version": "week_simulation_schedule.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "week": week.model_dump(mode="json"),
            "slots": [
                {
                    "ordinal": 1,
                    "group_ids": [
                        match.match_id for match in (*matches_a[:2], *matches_b[:2])
                    ],
                },
                {"ordinal": 2, "group_ids": [matches_a[2].match_id]},
                {"ordinal": 3, "group_ids": [matches_b[2].match_id]},
            ],
        }
        status, preview = _request(
            "POST", root + "/week-schedule/preview", {"schedule": schedule}
        )
        assert status == 200, preview
        changed = json.loads(json.dumps(schedule))
        changed["slots"][1], changed["slots"][2] = (
            changed["slots"][2],
            changed["slots"][1],
        )
        changed["slots"][1]["ordinal"] = 2
        changed["slots"][2]["ordinal"] = 3
        assert (
            _request(
                "POST",
                root + "/week-schedule",
                {
                    "schedule": changed,
                    "request_id": "stale-proposal",
                    "expected_position_fingerprint": preview["position_fingerprint"],
                },
            )[0]
            == 409
        )
        adoption = {
            "schedule": schedule,
            "request_id": "adopt-schedule",
            "expected_position_fingerprint": preview["position_fingerprint"],
        }
        status, adopted = _request("POST", root + "/week-schedule", adoption)
        assert status == 201
        assert (
            _request("POST", root + "/week-schedule", adoption)[1][
                "schedule_fingerprint"
            ]
            == adopted["schedule_fingerprint"]
        )
        position = _request("GET", root + "/position")[1]
        assert (
            _request(
                "POST",
                root + "/simulate-next-slot",
                {
                    "command_id": "slot-one",
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "expected_week": week.model_dump(mode="json"),
                    "expected_position_fingerprint": position["position_fingerprint"],
                    "expected_revision_id": revision,
                },
            )[0]
            == 200
        )
        midweek_position = _request("GET", root + "/position")[1]
        save_preview = _request("GET", root + "/save/preview")[1]
        save_status, save_body = _request(
            "POST",
            root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_simulation_fingerprint": save_preview[
                    "simulation_fingerprint"
                ],
            },
        )
        assert save_status == 201, save_body
        revision = save_body["saved_revision"]["revision_id"]

    reopened = ApiServer(database_url=f"sqlite:///{tmp_path / 'multi-api.sqlite'}")
    reopened.app.dependency_overrides[get_season_match_service] = lambda: (
        driver.match_service
    )
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: (
        driver.awards_service
    )
    with reopened:
        root = f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        reopened_position = _request("GET", root + "/position")[1]
        assert {
            key: value
            for key, value in reopened_position.items()
            if key != "position_fingerprint"
        } == {
            key: value
            for key, value in midweek_position.items()
            if key != "position_fingerprint"
        }
        assert (
            reopened_position["position_fingerprint"]
            != midweek_position["position_fingerprint"]
        )  # Save changed the protected Branch-head/draft authority.

        ranking_root = f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        with reopened.app.state.runtime.repository._session_factory() as session:
            lifecycle = get_lifecycle(
                session, run_id=run_id, branch_id=branch_id, week=week
            )
            roster = [
                player.model_dump(mode="json") for player in lifecycle.ranking_roster()
            ]
        bootstrap = initial() | {
            "run_id": run_id,
            "branch_id": branch_id,
            "players": roster,
        }
        assert _request("POST", ranking_root + "/prepare/initial", bootstrap)[0] == 201
        ranking_save = _request("GET", ranking_root + "/save/preview")[1]
        saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": ranking_save["draft_version"],
                "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
            },
        )[1]
        revision = saved["saved_revision"]["revision_id"]

        slot_two_position = _request("GET", root + "/position")[1]
        assert (
            _request(
                "POST",
                root + "/simulate-next-slot",
                {
                    "command_id": "slot-two",
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "expected_week": week.model_dump(mode="json"),
                    "expected_position_fingerprint": slot_two_position[
                        "position_fingerprint"
                    ],
                    "expected_revision_id": revision,
                },
            )[0]
            == 200
        )
        after_a = _request("GET", root + "/position")[1]
        assert after_a["week_ready_for_transition"] is False
        assert "pending_authoritative_groups" in after_a["transition_blockers"]
        with reopened.app.state.runtime.repository._session_factory() as session:
            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id, branch_id=branch_id
            )
            assert len(sources) == 1
            assert sources[0].binding.event_id == first.event_id

        assert (
            _request(
                "POST",
                root + "/simulate-next-slot",
                {
                    "command_id": "slot-three",
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "expected_week": week.model_dump(mode="json"),
                    "expected_position_fingerprint": after_a["position_fingerprint"],
                    "expected_revision_id": revision,
                },
            )[0]
            == 200
        )
        with reopened.app.state.runtime.repository._session_factory() as session:
            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id, branch_id=branch_id
            )
            assert len(sources) == 2
            group_rows = session.execute(
                select(
                    SimulationEventGroupModel.slot_id,
                    SimulationEventGroupModel.group_id,
                    SimulationEventGroupModel.result_fingerprint,
                ).where(
                    SimulationEventGroupModel.run_id == run_id,
                    SimulationEventGroupModel.branch_id == branch_id,
                    SimulationEventGroupModel.week_ordinal == week.ordinal,
                )
            ).all()
            assert len(group_rows) == 6
            replay_evidence = {
                (slot_id, group_id): (
                    result_fingerprint,
                    AuthoritativeSlotMatchExecutor(session)
                    .replay(
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        slot_id=slot_id,
                        group_id=group_id,
                    )
                    .result_fingerprint,
                )
                for slot_id, group_id, result_fingerprint in group_rows
            }
            assert all(
                stored == replayed for stored, replayed in replay_evidence.values()
            )

        simulation_save = _request("GET", root + "/save/preview")[1]
        saved = _request(
            "POST",
            root + "/save",
            {
                "expected_draft_version": simulation_save["draft_version"],
                "expected_simulation_fingerprint": simulation_save[
                    "simulation_fingerprint"
                ],
            },
        )[1]
        revision = saved["saved_revision"]["revision_id"]
        target = {"season_index": 0, "week": 2}
        authority_payload = {
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": revision,
            "completed_week": week.model_dump(mode="json"),
            "target_week": target,
            "players": roster,
            "policy": bootstrap["policy"],
            "provenance": "Multi-event schedule acceptance",
            "adopted_by_command_id": "multi-authority",
            "audit": bootstrap["audit"],
        }
        status, authority = _request(
            "POST", ranking_root + "/transition-authorities", authority_payload
        )
        assert status == 201
        ranking_save = _request("GET", ranking_root + "/save/preview")[1]
        saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": ranking_save["draft_version"],
                "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
            },
        )[1]
        revision = saved["saved_revision"]["revision_id"]
        ready = _request("GET", root + "/position")[1]
        assert ready["week_ready_for_transition"] is True, ready["transition_blockers"]
        command = {
            "command_id": "multi-transition",
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": revision,
            "completed_week": week.model_dump(mode="json"),
            "target_week": target,
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                json.dumps(authority)
            ).fingerprint,
            "tournaments": [
                source.binding.model_dump(mode="json") for source in sources
            ],
            "audit": bootstrap["audit"],
        }
        transition_root = f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        transition_preview = _request("POST", transition_root + "/preview", command)[1]
        assert confirm(transition_root, command, transition_preview)[0] == 201
        ranking_save = _request("GET", ranking_root + "/save/preview")[1]
        assert (
            _request(
                "POST",
                ranking_root + "/save",
                {
                    "expected_draft_version": ranking_save["draft_version"],
                    "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
                },
            )[0]
            == 201
        )

    post_transition = ApiServer(
        database_url=f"sqlite:///{tmp_path / 'multi-api.sqlite'}"
    )
    post_transition.app.dependency_overrides[get_season_match_service] = lambda: (
        driver.match_service
    )
    post_transition.app.dependency_overrides[get_season_point_awards_service] = lambda: (
        driver.awards_service
    )
    with post_transition:
        root = f"{post_transition.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        assert _request("GET", root + "/position")[1]["current_week"] == {
            "season_index": 0,
            "week": 2,
        }
        with post_transition.app.state.runtime.repository._session_factory() as session:
            rankings = session.scalars(
                select(PublishedOfficialRankingModel)
                .where(
                    PublishedOfficialRankingModel.run_id == run_id,
                    PublishedOfficialRankingModel.branch_id == branch_id,
                )
                .order_by(PublishedOfficialRankingModel.week_ordinal)
            ).all()
            assert [row.week_ordinal for row in rankings] == [0, 1]
            assert (
                len(
                    OwnedTournamentRankingSourceStore(session).history(
                        run_id=run_id, branch_id=branch_id
                    )
                )
                == 2
            )
            for (slot_id, group_id), expected in replay_evidence.items():
                replayed = AuthoritativeSlotMatchExecutor(session).replay(
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    slot_id=slot_id,
                    group_id=group_id,
                )
                assert replayed.result_fingerprint == expected[0] == expected[1]


@pytest.mark.smoke
def test_real_eight_player_week_transition_and_post_transition_replay(tmp_path):
    points, package = _real_eight_points(tmp_path / "eight-source")
    matches = points.result_service.match_service
    database_url = f"sqlite:///{tmp_path / 'eight-transition.sqlite'}"
    server = ApiServer(database_url=database_url)
    server.app.dependency_overrides[get_season_match_service] = lambda: matches
    server.app.dependency_overrides[get_season_point_awards_service] = lambda: points
    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="Eight transition"
        )
        week = _install_owned_state(server, package, run_id, branch_id)
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        rounds = {}
        for match in package.main_draw_matches:
            rounds.setdefault(match.round_number, []).append(match.match_id)
        schedule = {
            "schema_version": "week_simulation_schedule.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "week": week.model_dump(mode="json"),
            "slots": [
                {"ordinal": ordinal, "group_ids": rounds[number]}
                for ordinal, number in enumerate(sorted(rounds), 1)
            ],
        }
        preview = _request(
            "POST", root + "/week-schedule/preview", {"schedule": schedule}
        )[1]
        assert (
            _request(
                "POST",
                root + "/week-schedule",
                {
                    "schedule": schedule,
                    "request_id": "eight-schedule",
                    "expected_position_fingerprint": preview["position_fingerprint"],
                },
            )[0]
            == 201
        )
        for ordinal in range(1, 4):
            position = _request("GET", root + "/position")[1]
            assert (
                _request(
                    "POST",
                    root + "/simulate-next-slot",
                    {
                        "command_id": f"eight-slot-{ordinal}",
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "expected_week": week.model_dump(mode="json"),
                        "expected_position_fingerprint": position[
                            "position_fingerprint"
                        ],
                        "expected_revision_id": revision,
                    },
                )[0]
                == 200
            )
        with server.app.state.runtime.repository._session_factory() as session:
            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id, branch_id=branch_id
            )
            assert len(sources) == 1
            rows = session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == run_id,
                    SimulationEventGroupModel.branch_id == branch_id,
                    SimulationEventGroupModel.week_ordinal == week.ordinal,
                )
            ).all()
            assert len(rows) == 7
            replay_evidence = {
                (row.slot_id, row.group_id): (
                    row.result_fingerprint,
                    AuthoritativeSlotMatchExecutor._load_group(
                        row
                    ).authoritative_input.fingerprint,
                )
                for row in rows
            }
        save_preview = _request("GET", root + "/save/preview")[1]
        save_status, save_body = _request(
            "POST",
            root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_simulation_fingerprint": save_preview[
                    "simulation_fingerprint"
                ],
            },
        )
        assert save_status == 201, save_body
        revision = save_body["saved_revision"]["revision_id"]
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        with server.app.state.runtime.repository._session_factory() as session:
            lifecycle = get_lifecycle(
                session, run_id=run_id, branch_id=branch_id, week=week
            )
            roster = [
                player.model_dump(mode="json") for player in lifecycle.ranking_roster()
            ]
        bootstrap = initial() | {
            "run_id": run_id,
            "branch_id": branch_id,
            "players": roster,
        }
        assert _request("POST", ranking_root + "/prepare/initial", bootstrap)[0] == 201
        ranking_save = _request("GET", ranking_root + "/save/preview")[1]
        revision = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": ranking_save["draft_version"],
                "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
            },
        )[1]["saved_revision"]["revision_id"]
        target = {"season_index": 0, "week": 2}
        authority_payload = {
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": revision,
            "completed_week": week.model_dump(mode="json"),
            "target_week": target,
            "players": roster,
            "policy": bootstrap["policy"],
            "provenance": "Real eight-player transition acceptance",
            "adopted_by_command_id": "eight-authority",
            "audit": bootstrap["audit"],
        }
        authority = _request(
            "POST", ranking_root + "/transition-authorities", authority_payload
        )[1]
        ranking_save = _request("GET", ranking_root + "/save/preview")[1]
        revision = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": ranking_save["draft_version"],
                "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
            },
        )[1]["saved_revision"]["revision_id"]
        ready = _request("GET", root + "/position")[1]
        assert ready["week_ready_for_transition"] is True, ready["transition_blockers"]
        command = {
            "command_id": "eight-transition",
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": revision,
            "completed_week": week.model_dump(mode="json"),
            "target_week": target,
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                json.dumps(authority)
            ).fingerprint,
            "tournaments": [sources[0].binding.model_dump(mode="json")],
            "audit": bootstrap["audit"],
        }
        transition_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        transition_preview = _request("POST", transition_root + "/preview", command)[1]
        assert confirm(transition_root, command, transition_preview)[0] == 201

    reopened = ApiServer(database_url=database_url)
    reopened.app.dependency_overrides[get_season_match_service] = lambda: matches
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: points
    with reopened:
        root = f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        assert _request("GET", root + "/position")[1]["current_week"] == {
            "season_index": 0,
            "week": 2,
        }
        with reopened.app.state.runtime.repository._session_factory() as session:
            executor = AuthoritativeSlotMatchExecutor(session)
            for (slot_id, group_id), expected in replay_evidence.items():
                replayed = executor.replay(
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    slot_id=slot_id,
                    group_id=group_id,
                )
                assert replayed.result_fingerprint == expected[0]
                assert replayed.authoritative_input.fingerprint == expected[1]


def test_mixed_real_eight_and_four_player_week_is_order_independent(
    tmp_path, monkeypatch
):
    import beta_engine.api.deps as api_deps

    snapshots = []
    for label, reverse in (("forward", False), ("reverse", True)):
        identities = iter(f"{index:032x}" for index in range(1, 100))
        monkeypatch.setattr(
            api_deps, "uuid4", lambda: SimpleNamespace(hex=next(identities))
        )
        points, eight = _real_eight_points(tmp_path / label / "eight")
        four = _add_legacy_four_player_event(points, eight, tmp_path / label / "four")
        matches = points.result_service.match_service
        server = ApiServer(
            database_url=f"sqlite:///{tmp_path / label / 'mixed.sqlite'}"
        )
        server.app.dependency_overrides[get_season_match_service] = lambda: matches
        server.app.dependency_overrides[get_season_point_awards_service] = lambda: (
            points
        )
        with server:
            run_id, branch_id, revision = _create_run(
                server, display_name=f"Mixed {label}"
            )
            week = _install_owned_state(
                server, eight, run_id, branch_id, additional_packages=(four,)
            )
            eight_rounds = {
                number: [
                    m.match_id
                    for m in eight.main_draw_matches
                    if m.round_number == number
                ]
                for number in sorted({m.round_number for m in eight.main_draw_matches})
            }
            four_matches = sorted(
                four.main_draw_matches,
                key=lambda m: (m.round_number, m.bracket_position),
            )
            slot_one = eight_rounds[1] + [m.match_id for m in four_matches[:2]]
            schedule = {
                "schema_version": "week_simulation_schedule.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "slots": [
                    {"ordinal": 1, "group_ids": slot_one},
                    {
                        "ordinal": 2,
                        "group_ids": [four_matches[2].match_id, *eight_rounds[2]],
                    },
                    {"ordinal": 3, "group_ids": eight_rounds[3]},
                ],
            }
            root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
            preview_status, preview = _request(
                "POST", root + "/week-schedule/preview", {"schedule": schedule}
            )
            assert preview_status == 200, preview
            assert (
                _request(
                    "POST",
                    root + "/week-schedule",
                    {
                        "schedule": schedule,
                        "request_id": f"mixed-{label}",
                        "expected_position_fingerprint": preview[
                            "position_fingerprint"
                        ],
                    },
                )[0]
                == 201
            )
            execution = list(slot_one)
            if reverse:
                execution.reverse()
            for index, group_id in enumerate(execution):
                position = _request("GET", root + "/position")[1]
                group_status, group_body = _request(
                    "POST",
                    root + "/simulate-next-match",
                    {
                        "command_id": f"mixed-{label}-{index}",
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "expected_week": week.model_dump(mode="json"),
                        "expected_position_fingerprint": position[
                            "position_fingerprint"
                        ],
                        "expected_revision_id": revision,
                        "group_id": group_id,
                    },
                )
                assert group_status == 200, group_body
            with server.app.state.runtime.repository._session_factory() as session:
                rows = session.scalars(
                    select(SimulationEventGroupModel).where(
                        SimulationEventGroupModel.run_id == run_id,
                        SimulationEventGroupModel.branch_id == branch_id,
                    )
                ).all()
                loaded = [
                    AuthoritativeSlotMatchExecutor._load_group(row) for row in rows
                ]
                assert (
                    len(
                        {
                            group.authoritative_input.slot_start_fingerprint
                            for group in loaded
                        }
                    )
                    == 1
                )
                snapshots.append(
                    tuple(
                        sorted(
                            (
                                group.authoritative_input.match_id,
                                group.result_fingerprint,
                                tuple(effect.fingerprint for effect in group.effects),
                            )
                            for group in loaded
                        )
                    )
                )
            position = _request("GET", root + "/position")[1]
            assert (
                _request(
                    "POST",
                    root + "/simulate-next-slot",
                    {
                        "command_id": f"mixed-{label}-slot-two",
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "expected_week": week.model_dump(mode="json"),
                        "expected_position_fingerprint": position[
                            "position_fingerprint"
                        ],
                        "expected_revision_id": revision,
                    },
                )[0]
                == 200
            )
            mid = _request("GET", root + "/position")[1]
            assert mid["week_ready_for_transition"] is False
            with server.app.state.runtime.repository._session_factory() as session:
                assert (
                    len(
                        OwnedTournamentRankingSourceStore(session).history(
                            run_id=run_id, branch_id=branch_id
                        )
                    )
                    == 1
                )
            assert (
                _request(
                    "POST",
                    root + "/simulate-next-slot",
                    {
                        "command_id": f"mixed-{label}-slot-three",
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "expected_week": week.model_dump(mode="json"),
                        "expected_position_fingerprint": mid["position_fingerprint"],
                        "expected_revision_id": revision,
                    },
                )[0]
                == 200
            )
            with server.app.state.runtime.repository._session_factory() as session:
                sources = OwnedTournamentRankingSourceStore(session).history(
                    run_id=run_id, branch_id=branch_id
                )
                assert len(sources) == 2
                all_rows = session.scalars(
                    select(SimulationEventGroupModel).where(
                        SimulationEventGroupModel.run_id == run_id,
                        SimulationEventGroupModel.branch_id == branch_id,
                    )
                ).all()
                historical = {
                    (row.slot_id, row.group_id): row.result_fingerprint
                    for row in all_rows
                }
            if not reverse:
                save_preview = _request("GET", root + "/save/preview")[1]
                save_status, save_body = _request(
                    "POST",
                    root + "/save",
                    {
                        "expected_draft_version": save_preview["draft_version"],
                        "expected_simulation_fingerprint": save_preview[
                            "simulation_fingerprint"
                        ],
                    },
                )
                assert save_status == 201, save_body
                revision = save_body["saved_revision"]["revision_id"]
                ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
                with server.app.state.runtime.repository._session_factory() as session:
                    lifecycle = get_lifecycle(
                        session, run_id=run_id, branch_id=branch_id, week=week
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
                assert (
                    _request("POST", ranking_root + "/prepare/initial", bootstrap)[0]
                    == 201
                )
                ranking_save = _request("GET", ranking_root + "/save/preview")[1]
                revision = _request(
                    "POST",
                    ranking_root + "/save",
                    {
                        "expected_draft_version": ranking_save["draft_version"],
                        "expected_ranking_fingerprint": ranking_save[
                            "ranking_fingerprint"
                        ],
                    },
                )[1]["saved_revision"]["revision_id"]
                target = {"season_index": 0, "week": 2}
                authority = _request(
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
                        "provenance": "Mixed real-eight transition",
                        "adopted_by_command_id": "mixed-authority",
                        "audit": bootstrap["audit"],
                    },
                )[1]
                ranking_save = _request("GET", ranking_root + "/save/preview")[1]
                revision = _request(
                    "POST",
                    ranking_root + "/save",
                    {
                        "expected_draft_version": ranking_save["draft_version"],
                        "expected_ranking_fingerprint": ranking_save[
                            "ranking_fingerprint"
                        ],
                    },
                )[1]["saved_revision"]["revision_id"]
                transition_command = {
                    "command_id": "mixed-real-transition",
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "base_revision_id": revision,
                    "completed_week": week.model_dump(mode="json"),
                    "target_week": target,
                    "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                        json.dumps(authority)
                    ).fingerprint,
                    "tournaments": [
                        source.binding.model_dump(mode="json") for source in sources
                    ],
                    "audit": bootstrap["audit"],
                }
                transition_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
                transition_preview = _request(
                    "POST", transition_root + "/preview", transition_command
                )[1]
                assert (
                    confirm(transition_root, transition_command, transition_preview)[0]
                    == 201
                )
                with server.app.state.runtime.repository._session_factory() as session:
                    executor = AuthoritativeSlotMatchExecutor(session)
                    for (slot_id, group_id), result_fp in historical.items():
                        assert (
                            executor.replay(
                                run_id=run_id,
                                branch_id=branch_id,
                                week=week,
                                slot_id=slot_id,
                                group_id=group_id,
                            ).result_fingerprint
                            == result_fp
                        )
    assert snapshots[0] == snapshots[1]


def test_product_save_reopen_mid_slot_preserves_frozen_position(tmp_path):
    server, package = _server_state(tmp_path)
    matches = server.app.dependency_overrides[get_season_match_service]()
    points = server.app.dependency_overrides[get_season_point_awards_service]()
    database_url = f"sqlite:///{tmp_path / 'api.sqlite'}"
    with server:
        run_id, branch_id, revision = _create_run(server, display_name="Mid-slot Save")
        week = _install_owned_state(server, package, run_id, branch_id)
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        opening = _request("GET", root + "/position")[1]
        command = {
            "command_id": "sf1",
            "run_id": run_id,
            "branch_id": branch_id,
            "expected_week": week.model_dump(mode="json"),
            "expected_position_fingerprint": opening["position_fingerprint"],
            "expected_revision_id": revision,
            "group_id": opening["eligible_match_ids"][0],
        }
        assert _request("POST", root + "/simulate-next-match", command)[0] == 200
        preview = _request("GET", root + "/save/preview")[1]
        saved = _request(
            "POST",
            root + "/save",
            {
                "expected_draft_version": preview["draft_version"],
                "expected_simulation_fingerprint": preview["simulation_fingerprint"],
            },
        )[1]
        revision = saved["saved_revision"]["revision_id"]

    reopened = ApiServer(database_url=database_url)
    reopened.app.dependency_overrides[get_season_match_service] = lambda: matches
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: points
    with reopened:
        root = f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        position = _request("GET", root + "/position")[1]
        assert len(position["eligible_match_ids"]) == 1
        assert position["blocked_match_ids"]
        command.update(
            command_id="sf2",
            expected_revision_id=revision,
            expected_position_fingerprint=position["position_fingerprint"],
            group_id=position["eligible_match_ids"][0],
        )
        assert _request("POST", root + "/simulate-next-match", command)[0] == 200


def test_week_one_to_three_repeated_authoritative_api_flow(tmp_path):
    server, package = _server_state(tmp_path)
    matches = server.app.dependency_overrides[get_season_match_service]()
    points = server.app.dependency_overrides[get_season_point_awards_service]()
    reopened_server = None
    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="Repeated sporting flow"
        )
        week = _install_owned_state(server, package, run_id, branch_id)
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        with server.app.state.runtime.repository._session_factory() as session:
            lifecycle = get_lifecycle(
                session, run_id=run_id, branch_id=branch_id, week=week
            )
            roster = [p.model_dump(mode="json") for p in lifecycle.ranking_roster()]
        bootstrap = initial() | {
            "run_id": run_id,
            "branch_id": branch_id,
            "players": roster,
        }
        assert _request("POST", ranking_root + "/prepare/initial", bootstrap)[0] == 201
        preview = _request("GET", ranking_root + "/save/preview")[1]
        saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": preview["draft_version"],
                "expected_ranking_fingerprint": preview["ranking_fingerprint"],
            },
        )[1]
        revision = saved["saved_revision"]["revision_id"]

        historical_week_one = None
        for number in (1, 2):
            sim_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
            position = _request("GET", sim_root + "/position")[1]
            assert position["current_week"]["week"] == number
            base = {
                "command_id": f"w{number}-sf",
                "run_id": run_id,
                "branch_id": branch_id,
                "expected_week": position["current_week"],
                "expected_position_fingerprint": position["position_fingerprint"],
                "expected_revision_id": revision,
            }
            assert _request("POST", sim_root + "/simulate-next-slot", base)[0] == 200
            position = _request("GET", sim_root + "/position")[1]
            final = base | {
                "command_id": f"w{number}-final",
                "expected_position_fingerprint": position["position_fingerprint"],
            }
            assert _request("POST", sim_root + "/simulate-next-slot", final)[0] == 200
            with server.app.state.runtime.repository._session_factory() as session:
                sources = OwnedTournamentRankingSourceStore(session).history(
                    run_id=run_id, branch_id=branch_id
                )
                source = next(
                    item
                    for item in sources
                    if item.binding.completed_week.week == number
                )
                if number == 1:
                    from beta_engine.application.authoritative_slot_matches import (
                        AuthoritativeSlotMatchExecutor,
                    )

                    historical_week_one = AuthoritativeSlotMatchExecutor(
                        session
                    ).replay(
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        slot_id=f"{source.binding.event_id}:slot:1",
                        group_id=source.result.match_result_refs[0].match_id,
                    )
                lifecycle = get_lifecycle(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=RankingWeek(season_index=0, week=number),
                )
                roster = [p.model_dump(mode="json") for p in lifecycle.ranking_roster()]
            sim_preview = _request("GET", sim_root + "/save/preview")[1]
            saved = _request(
                "POST",
                sim_root + "/save",
                {
                    "expected_draft_version": sim_preview["draft_version"],
                    "expected_simulation_fingerprint": sim_preview[
                        "simulation_fingerprint"
                    ],
                },
            )[1]
            revision = saved["saved_revision"]["revision_id"]
            target = {"season_index": 0, "week": number + 1}
            authority_payload = {
                "run_id": run_id,
                "branch_id": branch_id,
                "base_revision_id": revision,
                "completed_week": position["current_week"],
                "target_week": target,
                "players": roster,
                "policy": bootstrap["policy"],
                "provenance": "Repeated driver acceptance",
                "adopted_by_command_id": f"authority-{number}",
                "audit": bootstrap["audit"],
            }
            status, authority = _request(
                "POST", ranking_root + "/transition-authorities", authority_payload
            )
            assert status == 201
            ranking_save = _request("GET", ranking_root + "/save/preview")[1]
            saved = _request(
                "POST",
                ranking_root + "/save",
                {
                    "expected_draft_version": ranking_save["draft_version"],
                    "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
                },
            )[1]
            revision = saved["saved_revision"]["revision_id"]
            ready = _request("GET", sim_root + "/position")[1]
            assert ready["week_ready_for_transition"] is True, ready[
                "transition_blockers"
            ]
            command = {
                "command_id": f"transition-{number}",
                "run_id": run_id,
                "branch_id": branch_id,
                "base_revision_id": revision,
                "completed_week": position["current_week"],
                "target_week": target,
                "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                    json.dumps(authority)
                ).fingerprint,
                "tournaments": [source.binding.model_dump(mode="json")],
                "audit": bootstrap["audit"],
            }
            transition_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
            transition_preview = _request(
                "POST", transition_root + "/preview", command
            )[1]
            assert confirm(transition_root, command, transition_preview)[0] == 201
            ranking_save = _request("GET", ranking_root + "/save/preview")[1]
            saved = _request(
                "POST",
                ranking_root + "/save",
                {
                    "expected_draft_version": ranking_save["draft_version"],
                    "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
                },
            )[1]
            revision = saved["saved_revision"]["revision_id"]
            if number == 1:
                server.__exit__(None, None, None)
                reopened_server = ApiServer(
                    database_url=f"sqlite:///{tmp_path / 'api.sqlite'}"
                )
                reopened_server.app.dependency_overrides[get_season_match_service] = (
                    lambda: matches
                )
                reopened_server.app.dependency_overrides[
                    get_season_point_awards_service
                ] = lambda: points
                server = reopened_server.__enter__()
                ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
                reopened_position = _request(
                    "GET",
                    f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation/position",
                )[1]
                assert reopened_position["current_week"] == {
                    "season_index": 0,
                    "week": 2,
                }
                with server.app.state.runtime.repository._session_factory() as session:
                    assert (
                        len(
                            OwnedTournamentRankingSourceStore(session).history(
                                run_id=run_id, branch_id=branch_id
                            )
                        )
                        == 1
                    )

        final_position = _request("GET", sim_root + "/position")[1]
        assert final_position["current_week"] == {"season_index": 0, "week": 3}
        with server.app.state.runtime.repository._session_factory() as session:
            assert (
                len(
                    OwnedTournamentRankingSourceStore(session).history(
                        run_id=run_id, branch_id=branch_id
                    )
                )
                == 2
            )
            replay = AuthoritativeSlotMatchExecutor(session).replay(
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                slot_id=historical_week_one.authoritative_input.slot_id,
                group_id=historical_week_one.authoritative_input.group_id,
            )
            assert replay.authoritative_input == historical_week_one.authoritative_input
            assert replay.result == historical_week_one.result
            rankings = session.scalars(
                select(PublishedOfficialRankingModel)
                .where(
                    PublishedOfficialRankingModel.run_id == run_id,
                    PublishedOfficialRankingModel.branch_id == branch_id,
                )
                .order_by(PublishedOfficialRankingModel.week_ordinal)
            ).all()
            assert [row.week_ordinal for row in rankings] == [0, 1, 2]
            sporting_rows = session.scalars(
                select(PlayerSportingWeekStateModel)
                .where(
                    PlayerSportingWeekStateModel.run_id == run_id,
                    PlayerSportingWeekStateModel.branch_id == branch_id,
                )
                .order_by(PlayerSportingWeekStateModel.week_ordinal)
            ).all()
            assert [row.week_ordinal for row in sporting_rows] == [0, 1, 2]
            states = [json.loads(row.payload_json) for row in sporting_rows]
            assert states[1]["predecessor_fingerprint"]
            assert states[2]["predecessor_fingerprint"]
            assert (
                states[1]["completed_context_fingerprint"]
                != states[2]["completed_context_fingerprint"]
            )
            assert any(
                (
                    player["current_form"],
                    player["match_sharpness"],
                    player["long_term_fatigue"],
                )
                != (100, 50, 0)
                for player in states[2]["players"]
            )
        if reopened_server is not None:
            reopened_server.__exit__(None, None, None)
