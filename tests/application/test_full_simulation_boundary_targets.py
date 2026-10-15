"""Actual production TCP/SQLite/MatchEngine boundaries, not synthetic commits."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from beta_engine.application.full_simulation_boundary_targets import (
    FullSimulationBoundaryTarget,
    selector,
)
from beta_engine.infrastructure.db.models import AuthoritativeSimulationCommandModel
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.application.test_full_simulation_http_flow import reviewed_command
from tests.application.test_full_simulation_server_tasks import wait_task
from tests.support.full_simulation_http_flow import (
    initialize,
    make_server,
    routes,
    snapshot,
)


def select_option(server, root, parent, kind):
    status, review = _request(
        "GET", root + "/full-simulation/target-options?command_id=" + parent
    )
    assert status == 200, review
    options = [o for o in review["options"] if o["kind"] == kind]
    assert options, review
    return options[-1]


def target_request(command, option, request_id="precise-target"):
    return {
        "control_command_id": request_id,
        "target_command_id": command["command_id"],
        "boundary_target": option,
        "operator_label": "Auditor",
        "audit_reason": "Exact committed boundary",
    }


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    "kind,expected_groups", [("before_slot", 2), ("after_tournament", 3)]
)
def test_real_server_worker_retarget_and_frozen_replay(
    tmp_path, monkeypatch, kind, expected_groups
):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        reference_path = tmp_path / "baseline.sqlite"
        with (
            sqlite3.connect(tmp_path / "api.sqlite") as source,
            sqlite3.connect(reference_path) as reference,
        ):
            source.backup(reference)
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202, ack
        assert gate.reached.wait(40)
        try:
            option = select_option(server, root, command["command_id"], kind)
            request = target_request(command, option)
            status, accepted = _request(
                "POST", root + "/full-simulation/target", request
            )
            assert status == 200, accepted
            assert (
                accepted["schema_version"]
                == "authoritative_full_simulation_target_result.v2"
            )
            assert _request("POST", root + "/full-simulation/target", request)[
                1
            ] == accepted | {"replayed": True}
            assert (
                _request(
                    "POST",
                    root + "/full-simulation/target",
                    request | {"audit_reason": "different"},
                )[0]
                == 409
            )
            assert (
                _request(
                    "POST",
                    server.base_url + flow["other_scope"] + "/full-simulation/target",
                    request,
                )[0]
                == 409
            )
            pending = _request("GET", root + "/full-simulation/pending")[1]
            assert pending["operations"][0]["effective_boundary_target"] == option
            inventory = _request(
                "GET", server.base_url + "/run-containers/full-simulation/operations"
            )
            assert inventory[0] == 200, inventory
            assert inventory[1]["operations"][0]["effective_boundary_target"] == option
        finally:
            gate.release.set()
        task = wait_task(
            server,
            flow["scope"],
            ack["task_id"],
            {"target_reached", "failed", "awaiting_operator"},
        )
        assert task["state"] == "target_reached", task
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert len(after["groups"]) == expected_groups
        assert after["saved"] == before["saved"]
        summary_url = (
            root + "/full-simulation/parents/" + command["command_id"] + "/summary"
        )
        status, summary = _request("GET", summary_url)
        assert status == 200 and summary["available"], summary
        receipt = summary["summary"]
        assert receipt["schema_version"] == "full_simulation_terminal_summary.v2"
        assert receipt["effective_boundary_target"] == option
        trigger = receipt["target_trigger_evidence"]
        if kind == "before_slot":
            assert trigger["slot_ordinal"] == option["slot_ordinal"]
            assert option["slot_id"] not in after["slots"]
        else:
            assert trigger["edition_id"] == option["edition_id"]
            assert len(receipt["completed_tournaments"]) == 1
            assert (
                trigger["source_fingerprint"]
                == receipt["completed_tournaments"][0]["source_fingerprint"]
            )
        assert _request("POST", root + "/full-simulation/target", request)[
            1
        ] == accepted | {"replayed": True}
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
        # Uninterrupted same command/input/RNG produces the identical committed prefix.
        baseline = ApiServer(database_url=f"sqlite:///{reference_path}")
        baseline.app.dependency_overrides.update(server.app.dependency_overrides)
        with baseline:
            result = _request(
                "POST",
                baseline.base_url + flow["scope"] + "/simulate-full-simulation",
                command,
            )
            assert result[0] == 201, result
            baseline_data = snapshot(
                baseline.app.state.runtime.repository._session_factory,
                flow["run_id"],
                flow["branch_id"],
            )
            assert all(
                baseline_data["groups"][key] == value
                for key, value in after["groups"].items()
            )

        if kind == "after_tournament":
            preview = _request("GET", root + "/save/preview")[1]
            status, saved = _request(
                "POST",
                root + "/save",
                {
                    "expected_draft_version": preview["draft_version"],
                    "expected_simulation_fingerprint": preview[
                        "simulation_fingerprint"
                    ],
                },
            )
            assert status == 201, saved
            assert _request("GET", summary_url) == (200, summary)

        # Historical receipt must not consult later current Position or source state.
        def forbidden(*args, **kwargs):
            raise AssertionError("Current Position is not terminal history")

        monkeypatch.setattr(
            type(gate.driver(server.app.state.runtime, None, None)),
            "_position",
            forbidden,
        )
        assert _request("GET", summary_url) == (200, summary)
        assert _request("POST", root + "/full-simulation/target", request)[
            1
        ] == accepted | {"replayed": True}


@pytest.mark.pr_critical
def test_boundary_exact_retry_after_later_revision_and_week_reset(
    tmp_path, monkeypatch
):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=1) as pool:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        invocation = pool.submit(
            _request, "POST", root + "/simulate-full-simulation", command
        )
        assert gate.reached.wait(40)
        try:
            option = select_option(server, root, command["command_id"], "before_slot")
            request = target_request(command, option)
            status, original = _request(
                "POST", root + "/full-simulation/target", request
            )
            assert status == 200, original
            weekly = {k: v for k, v in request.items() if k != "boundary_target"} | {
                "control_command_id": "reset",
                "target_week": {"season_index": 49, "week": 61},
            }
            assert _request("POST", root + "/full-simulation/target", weekly)[0] == 200
            assert _request("POST", root + "/full-simulation/target", request)[
                1
            ] == original | {"replayed": True}
            pending = _request("GET", root + "/full-simulation/pending")[1][
                "operations"
            ][0]
            assert (
                pending["effective_boundary_target"] is None
                and pending["target_revision"] == 2
            )
        finally:
            gate.release.set()
        assert invocation.result(40)[0] == 201
        # A fresh request cannot claim a boundary after its match was committed.
        assert (
            _request(
                "POST",
                root + "/full-simulation/target",
                request | {"control_command_id": "late"},
            )[0]
            == 409
        )
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(
                AuthoritativeSimulationCommandModel,
                (flow["run_id"], flow["branch_id"], command["command_id"]),
            )
            payload = json.loads(row.result_json)
            payload["effective_boundary_target"] = option
            row.result_json = json.dumps(payload)
        assert _request("GET", root + "/full-simulation/pending")[0] == 409


@pytest.mark.pr_critical
def test_selector_validation_and_no_label_based_final():
    from pydantic import ValidationError

    from beta_engine.domain.rankings.official import RankingWeek

    value = selector(
        kind="before_slot",
        week=RankingWeek(season_index=0, week=1),
        schedule_fingerprint="a" * 64,
        slot_ordinal=3,
        slot_id="week-0:slot:3",
        slot_kind="match",
        group_ids=("a", "b"),
    )
    for change in (
        {"slot_ordinal": True},
        {"slot_id": None},
        {"group_ids": ("b", "a")},
        {"edition_id": "Final"},
        {"kind": "before_final"},
    ):
        with pytest.raises(ValidationError):
            FullSimulationBoundaryTarget.model_validate(value.model_dump() | change)


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    "kind,expected_groups", [("before_slot", 2), ("after_tournament", 3)]
)
def test_recovery_retains_effective_precise_target_and_fences_old_child(
    tmp_path, monkeypatch, kind, expected_groups
):
    from beta_engine.application.full_simulation_tasks import FullSimulationTaskWorker
    from tests.application.test_full_simulation_server_tasks import continuation
    from tests.support.full_simulation_http_flow import expire

    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            target = select_option(server, root, command["command_id"], kind)
            request = target_request(command, target)
            assert _request("POST", root + "/full-simulation/target", request)[0] == 200
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            active = wait_task(server, flow["scope"], ack["task_id"], {"active"})
            recovery_url, recovery = continuation(
                server, flow, active, "recover", "recover-target"
            )
            assert _request("POST", recovery_url, recovery)[0] == 409
            expire(factory)
            recoverable = wait_task(
                server, flow["scope"], ack["task_id"], {"recoverable"}
            )
            recovery_url, recovery = continuation(
                server, flow, recoverable, "recover", "recover-target"
            )
            old = server.app.state.full_simulation_worker
            server.app.state.full_simulation_worker = FullSimulationTaskWorker(factory)
            status, recovered = _request("POST", recovery_url, recovery)
            assert status == 202, recovered
            assert _request("POST", recovery_url, recovery) == (status, recovered)
            terminal = wait_task(
                server,
                flow["scope"],
                ack["task_id"],
                {"target_reached", "failed", "awaiting_operator"},
            )
            assert terminal["state"] == "target_reached", terminal
            assert terminal["effective_boundary_target"] == target
            after = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert len(after["groups"]) == expected_groups
            assert all(after["groups"][k] == v for k, v in before["groups"].items())
            assert before["saved"] == after["saved"]
        finally:
            gate.release.set()
            if "old" in locals():
                old.close()
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after


@pytest.mark.pr_critical
def test_canonical_final_is_actual_terminal_topology_not_round_or_display_label():
    from types import SimpleNamespace

    from beta_engine.application.canonical_tournament_topology import (
        project_canonical_draw_to_match_topology,
    )
    from beta_engine.application.full_simulation_boundary_targets import _final
    from beta_engine.domain.tournaments.draw_authority import (
        TournamentDrawAuthorityBuilder,
    )
    from tests.application.test_canonical_tournament_topology import (
        _draw_input,
        _package,
    )
    from tests.application.test_hybrid_knockout_execution import bracket

    scope = {"run_id": "run", "branch_id": "branch", "week": None}
    for kwargs in ({}, {"with_qualification": True}, {"with_bye": True}):
        draw = TournamentDrawAuthorityBuilder.build(
            draw_input=_draw_input(**kwargs), command_id="draw"
        )
        package = _package(draw)
        driver = SimpleNamespace(
            _hybrid_knockout_brackets_for_week=lambda *a, **k: (),
            _canonical_draw_binding=lambda *a, draw=draw, **k: draw,
            _packages=lambda *a, package=package, **k: (package,),
        )
        group, fp = _final(driver, None, scope, "event")
        projection = project_canonical_draw_to_match_topology(
            draw=draw, package=package
        )
        assert (group, fp) == (projection.terminal_group_id, projection.fingerprint)
    hybrid = bracket()
    driver = SimpleNamespace(
        _hybrid_knockout_brackets_for_week=lambda *a, **k: (
            (SimpleNamespace(event_id=hybrid.event_id), hybrid),
        )
    )
    assert _final(driver, None, scope, hybrid.event_id) == (
        hybrid.terminal_match_id,
        hybrid.fingerprint,
    )
    assert hybrid.round_count == 2
    driver = SimpleNamespace(
        _hybrid_knockout_brackets_for_week=lambda *a, **k: (),
        _canonical_draw_binding=lambda *a, **k: None,
    )
    with pytest.raises(ValueError, match="not_frozen"):
        _final(driver, None, scope, "Final — last displayed match")


@pytest.mark.pr_critical
def test_two_interleaved_tournaments_do_not_skip_transit_slots(tmp_path, monkeypatch):
    from beta_engine.api.deps import (
        get_season_match_service,
        get_season_point_awards_service,
    )

    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    matches = server.app.dependency_overrides[get_season_match_service]()
    points = server.app.dependency_overrides[get_season_point_awards_service]()
    first = server.flow_package
    second = first.model_copy(deep=True)
    second.event_id += "-B"
    second.metadata.event_id = second.event_id
    id_map = {m.match_id: m.match_id + "-B" for m in second.main_draw_matches}
    for m in second.main_draw_matches:
        m.match_id = id_map[m.match_id]
        m.event_id = second.event_id
        if m.winner_to_match_id:
            m.winner_to_match_id = id_map[m.winner_to_match_id]
    semis = sorted(
        (m for m in second.main_draw_matches if m.round_number == 1),
        key=lambda m: m.bracket_position,
    )
    used = {
        p
        for m in first.main_draw_matches
        for p in (m.top_player_id, m.bottom_player_id)
        if p
    }
    players = [
        p.player_id
        for p in points.active_players_service.get_active_players(
            season=first.season
        ).players
        if p.player_id not in used
    ][:4]
    assert len(players) == 4
    for m, pair in zip(semis, (players[:2], players[2:]), strict=True):
        m.top_player_id, m.bottom_player_id = pair
    registry = matches._load_registry()
    registry.matches_by_event_id[second.event_id] = second
    matches._save_registry(registry)
    calendar = points.calendar_service._load_registry()
    event = next(
        e
        for e in calendar.calendars_by_season[first.season].events
        if e.event_id == first.event_id
    )
    calendar.calendars_by_season[first.season].events.append(
        event.model_copy(update={"event_id": second.event_id})
    )
    points.calendar_service._save_registry(calendar)
    with server:
        flow = initialize(server, tmp_path, additional_packages=(second,))
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        schedule = _request("GET", root + "/week-schedule")[1]
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "multi-start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            status, review = _request(
                "GET",
                root
                + "/full-simulation/target-options?command_id="
                + command["command_id"],
            )
            assert status == 200, review
            chosen = next(
                o
                for o in review["options"]
                if o["kind"] == "after_tournament" and o["event_id"] == first.event_id
            )
            status, target = _request(
                "POST",
                root + "/full-simulation/target",
                target_request(command, chosen),
            )
            assert status == 200, target
        finally:
            gate.release.set()
        task = wait_task(
            server,
            flow["scope"],
            ack["task_id"],
            {"target_reached", "failed", "awaiting_operator"},
        )
        assert task["state"] == "target_reached", task
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        specs = schedule["schedule"]["slots"]
        terminal = next(
            s["ordinal"]
            for s in specs
            if s["event_id"] == first.event_id and s["round_number"] == 2
        )
        prefix = {g for s in specs if s["ordinal"] <= terminal for g in s["group_ids"]}
        assert set(after["groups"]) == prefix
        transit = {
            g
            for s in specs
            if s["ordinal"] < terminal and s["event_id"] == second.event_id
            for g in s["group_ids"]
        }
        assert transit and transit <= set(after["groups"])


@pytest.mark.pr_critical
def test_entry_prefix_is_an_actual_boundary_and_blocks_later_matches(tmp_path):
    from beta_engine.application.full_simulation_boundary_targets import (
        boundary_evidence,
        boundary_options,
    )
    from beta_engine.domain.tournaments.run_entry_decision_slot import (
        RunEntryDecisionSlotAuthority,
    )
    from beta_engine.infrastructure.db.run_entry_decision_slots import (
        RunEntryDecisionSlotStore,
    )
    from tests.application.test_authoritative_slot_matches import _multi_driver_fixture

    driver, factory, week, first, second = _multi_driver_fixture(tmp_path / "entry")
    with factory.begin() as session:
        entry = RunEntryDecisionSlotAuthority(
            run_id="run",
            branch_id="branch",
            week=week,
            decision_slot_ordinal=1,
            source_entry_batch_fingerprint="a" * 64,
            source_application_decisions_fingerprint="b" * 64,
            source_active_players_fingerprint="c" * 64,
            decisions=(),
        )
        RunEntryDecisionSlotStore(session).append(entry)
    with factory() as session:
        options = boundary_options(
            driver,
            session,
            run_id="run",
            branch_id="branch",
            parent_command_id="parent",
        )
        target = next(o for o in options["options"] if o["slot_kind"] == "entry")
        assert (
            target["slot_ordinal"] == 1 and target["slot_id"] == "week-0:entry-slot:1"
        )
        frozen = {
            "final_week": {"season_index": 49, "week": 61},
            "effective_target_week": {"season_index": 49, "week": 61},
            "target_revision": 1,
            "target_events": [{"boundary_target": target}],
            "effective_boundary_target": target,
        }
        evidence = boundary_evidence(
            driver, session, frozen, run_id="run", branch_id="branch"
        )
        assert evidence["slot_ordinal"] == 1
    from beta_engine.domain.simulation_slots import (
        WeekSimulationSchedule,
        WeekSimulationScheduleSlot,
    )

    roots = tuple(
        sorted(
            m.match_id
            for package in (first, second)
            for m in package.main_draw_matches
            if m.round_number == 1
        )
    )
    finals = tuple(
        m.match_id
        for package in (first, second)
        for m in package.main_draw_matches
        if m.round_number == 2
    )
    schedule = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=week,
        slots=(
            WeekSimulationScheduleSlot(ordinal=2, group_ids=tuple(reversed(roots))),
            WeekSimulationScheduleSlot(ordinal=3, group_ids=(finals[0],)),
            WeekSimulationScheduleSlot(ordinal=4, group_ids=(finals[1],)),
        ),
    )
    preview = driver.preview_schedule(schedule)
    driver.adopt_schedule(
        schedule,
        request_id="mixed-schedule",
        expected_position_fingerprint=preview["position_fingerprint"],
    )
    with factory() as session:
        options = boundary_options(
            driver,
            session,
            run_id="run",
            branch_id="branch",
            parent_command_id="parent",
        )
        simultaneous = next(o for o in options["options"] if o["slot_ordinal"] == 2)
        assert simultaneous["group_ids"] == sorted(roots)
        target = next(o for o in options["options"] if o["slot_ordinal"] == 3)
        assert target["slot_id"] == "week-0:slot:3"
        frozen["effective_boundary_target"] = target
        frozen["target_events"] = [{"boundary_target": target}]
        # A reserved, unresolved Entry prefix prevents reaching a later match
        # boundary. No dense match-only ordinal interpretation is permitted.
        assert (
            boundary_evidence(driver, session, frozen, run_id="run", branch_id="branch")
            is None
        )


@pytest.mark.pr_critical
def test_retarget_between_boundary_detection_and_terminal_commit_is_not_false_success(
    tmp_path, monkeypatch
):
    from threading import Event

    from beta_engine.application.authoritative_run_simulation_driver import (
        AuthoritativeRunSimulationDriver,
    )
    from tests.application.test_full_simulation_server_tasks import continuation

    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    closing, release = Event(), Event()
    original = AuthoritativeRunSimulationDriver._close_full_simulation_target

    def held_close(self, *args, **kwargs):
        closing.set()
        assert release.wait(40)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver, "_close_full_simulation_target", held_close
    )
    with server:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            first = select_option(server, root, command["command_id"], "before_slot")
            assert (
                _request(
                    "POST",
                    root + "/full-simulation/target",
                    target_request(command, first),
                )[0]
                == 200
            )
            gate.release.set()
            assert closing.wait(40)
            later = select_option(
                server, root, command["command_id"], "after_tournament"
            )
            status, changed = _request(
                "POST",
                root + "/full-simulation/target",
                target_request(command, later, "later-target"),
            )
            assert status == 200, changed
        finally:
            gate.release.set()
            release.set()
        waiting = wait_task(
            server,
            flow["scope"],
            ack["task_id"],
            {"awaiting_operator", "target_reached", "failed"},
        )
        assert (
            waiting["state"] == "awaiting_operator"
            and waiting["checkpoint"] == "target_changed_before_completion"
        ), waiting
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert len(before["groups"]) == 2
        url, resume = continuation(server, flow, waiting)
        assert _request("POST", url, resume)[0] == 202
        reached = wait_task(
            server,
            flow["scope"],
            ack["task_id"],
            {"target_reached", "failed", "awaiting_operator"},
        )
        assert reached["state"] == "target_reached", reached
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert len(after["groups"]) == 3 and after["saved"] == before["saved"]


@pytest.mark.pr_critical
def test_safe_stop_preserves_precise_selector_without_claiming_target_reached(
    tmp_path, monkeypatch
):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            chosen = select_option(server, root, command["command_id"], "before_slot")
            request = target_request(command, chosen)
            assert _request("POST", root + "/full-simulation/target", request)[0] == 200
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            status, stopped = _request(
                "POST",
                root + "/full-simulation/control",
                {
                    "control_command_id": "stop",
                    "target_command_id": command["command_id"],
                    "action": "stop",
                    "operator_label": "Stop operator",
                    "audit_reason": "Stop before the precise goal",
                },
            )
            assert status == 200, stopped
        finally:
            gate.release.set()
        terminal = wait_task(
            server, flow["scope"], ack["task_id"], {"stopped", "failed"}
        )
        assert terminal["state"] == "stopped", terminal
        summary = _request(
            "GET",
            root + "/full-simulation/parents/" + command["command_id"] + "/summary",
        )[1]["summary"]
        assert summary["schema_version"] == "full_simulation_terminal_summary.v2"
        assert summary["effective_boundary_target"] == chosen
        assert (
            summary["target_trigger_evidence"] is None
            and summary["target_reached"] is False
        )
        assert summary["reason"] == "operator_stop"
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == before["groups"] and after["saved"] == before["saved"]
        assert (
            _request("POST", root + "/full-simulation/target", request)[1]["replayed"]
            is True
        )


@pytest.mark.pr_critical
def test_corrupt_owned_source_cannot_become_success_and_recovery_revalidates_it(
    tmp_path, monkeypatch
):
    from threading import Event

    from beta_engine.infrastructure.db.models import OwnedTournamentRankingSourceModel
    from tests.application.test_full_simulation_server_tasks import continuation

    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            selected = select_option(
                server, root, command["command_id"], "after_tournament"
            )
            assert (
                _request(
                    "POST",
                    root + "/full-simulation/target",
                    target_request(command, selected),
                )[0]
                == 200
            )
            previous_release = gate.release
            gate.release = Event()
            gate.arm(after_groups=2, after_sources=0)
            previous_release.set()
            assert gate.reached.wait(40), (
                "Hold only after the genuine third match and actual source closure"
            )
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert len(before["groups"]) == 3
            with factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                source = session.get(
                    OwnedTournamentRankingSourceModel,
                    (flow["run_id"], flow["branch_id"], selected["edition_id"]),
                )
                original_owner = source.adopted_by_command_id
                source.adopted_by_command_id = "another-parent"
        finally:
            gate.release.set()
        failed = wait_task(
            server, flow["scope"], ack["task_id"], {"failed", "target_reached"}
        )
        assert failed["state"] == "failed" and "ownership" in failed["error"], failed
        assert (
            _request(
                "GET",
                root + "/full-simulation/parents/" + command["command_id"] + "/summary",
            )[1]["available"]
            is False
        )
        # Repair only the deliberately corrupted test evidence. Recovery then
        # revalidates the actual original sporting source, never adopts a fake one.
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            source = session.get(
                OwnedTournamentRankingSourceModel,
                (flow["run_id"], flow["branch_id"], selected["edition_id"]),
            )
            source.adopted_by_command_id = original_owner
        url, recover = continuation(
            server, flow, failed, "recover", "source-revalidated"
        )
        status, result = _request("POST", url, recover)
        assert status == 202, result
        reached = wait_task(
            server, flow["scope"], ack["task_id"], {"target_reached", "failed"}
        )
        assert reached["state"] == "target_reached", reached
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == before["groups"] and after["saved"] == before["saved"]


@pytest.mark.pr_critical
def test_changed_frozen_week_review_is_explicitly_unavailable_and_fences_new_work(
    tmp_path, monkeypatch
):
    from sqlalchemy import select

    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        root = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        status, ack = _request(
            "POST",
            root + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            selected = select_option(server, root, command["command_id"], "before_slot")
            assert (
                _request(
                    "POST",
                    root + "/full-simulation/target",
                    target_request(command, selected),
                )[0]
                == 200
            )
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            # Alter only a wider frozen review, never a sporting output. This
            # models the incompatibility that later hybrid materialization can expose.
            with factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                rows = session.scalars(
                    select(AuthoritativeSimulationCommandModel).where(
                        AuthoritativeSimulationCommandModel.run_id == flow["run_id"],
                        AuthoritativeSimulationCommandModel.branch_id
                        == flow["branch_id"],
                    )
                ).all()
                weekly = next(
                    row
                    for row in rows
                    if json.loads(row.result_json).get("schema_version")
                    == "authoritative_week_operation.v1"
                )
                payload = json.loads(weekly.result_json)
                payload["schedule_fingerprint"] = "e" * 64
                weekly.result_json = json.dumps(payload)
            status, options = _request(
                "GET",
                root
                + "/full-simulation/target-options?command_id="
                + command["command_id"],
            )
            assert status == 200 and not options["options"], options
            assert all(
                u["reason"] == "parent_week_schedule_review_changed"
                for u in options["unavailable"]
            )
        finally:
            gate.release.set()
        task = wait_task(
            server,
            flow["scope"],
            ack["task_id"],
            {"awaiting_operator", "failed", "target_reached"},
        )
        assert (
            task["state"] == "awaiting_operator"
            and task["checkpoint"] == "target_boundary_review_required"
        ), task
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert before["groups"] == after["groups"] and before["saved"] == after["saved"]
