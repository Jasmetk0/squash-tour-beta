"""Actual all-week global-slot calendars, final closure and immutable extension."""

import pytest

from tests.api.test_calendar_global_slots import copy_database, ready
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    tour_url,
)
from tests.api.test_native_full_simulation_tasks import (
    resume,
    reviewed,
    scope,
    start,
    wait,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def finish(server):
    for index in (1, 2):
        execute(
            server, command(inspect(server), "next-slot", name=f"boundary-slot-{index}")
        )
        save_tour(server)
    for eid in ("parallel-a", "parallel-b"):
        result, _ = execute(
            server,
            command(
                inspect(server),
                "confirm-result",
                name=eid + ":boundary-confirm",
                edition_id=eid,
            ),
        )
        save_tour(server)
        yield result


def test_global_slots_all_weeks_and_actual_season_boundary(tmp_path, prepared_slots):
    path = tmp_path / "whole-calendar.db"
    copy_database(prepared_slots, path)
    database = f"sqlite:///{path}"
    with ApiServer(database_url=database) as server:
        list(finish(server))
        view = inspect(server)
        width = view["run_calendar"]["weeks_per_year"]
        for week in range(5, width + 1):
            execute(
                server, command(inspect(server), "transition", name=f"real-week-{week}")
            )
            save_tour(server)
            print(f"global W{width}: actual week {week}", flush=True)
        execute(
            server,
            command(
                inspect(server), "season-transition", name="actual-season-transition"
            ),
        )
        save_tour(server)
        final = inspect(server)
        assert (
            final["state"]["week"]["season_index"] == 1
            and final["state"]["week"]["week"] == 1
        )
        assert sorted(r["points"] for r in final["state"]["rankings"][-1]["rows"]) == [
            30,
            30,
            30,
            30,
            60,
            60,
            100,
            100,
        ]
        code, summary = _request("GET", tour_url(server) + "/seasons/0")
        assert code == 200, summary
        assert summary["selected"]["completed_edition_count"] == 2
        assert sum(p["awarded_points"] for p in summary["selected"]["players"]) == 440
    with ApiServer(database_url=database) as server:
        assert inspect(server)["state"] == final["state"]


def test_global_original_final_week_closing_restart_extension_once(tmp_path):
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension

    path = tmp_path / "global-terminal.db"
    database = f"sqlite:///{path}"
    with ApiServer(database_url=database) as server:
        ready(server, 4, seasons=1)
        results = list(finish(server))
        assert all(
            r["schema_version"] == "calendar_terminal_edition_result.v1"
            and "first_publication_week" not in r
            for result in results
            for r in result["results"]
        )
        original = reviewed(server, name="close-global-final-week")
        task = start(server, original)
        assert task["checkpoint"] == "native_final_closure_review_required", task
        url = scope(server) + "/native/close-global-final-week/closure"
        code, review = _request("GET", url)
        assert code == 200, review
        assert review["season_summary"]["played_match_count"] == 6
        assert review["season_summary"]["awarded_points"] == 440
        assert sorted(r["points"] for r in review["closing_ranking"]["rows"]) == [
            30,
            30,
            30,
            30,
            60,
            60,
            100,
            100,
        ]
        body = {
            "request_id": "global-approve-closure",
            "review_fingerprint": review["review_fingerprint"],
            "operator_label": "Admin",
            "audit_reason": "Actual simultaneous final-week tournaments",
            "explicit_confirmation": True,
        }
        assert _request("POST", url + "/save", body)[0] == 409
        assert _request("POST", url + "/approve", body)[0] == 200
        code, closed = _request(
            "POST", url + "/save", {**body, "request_id": "global-final-save"}
        )
        assert code == 201, closed
        task = resume(server, task, "global-final-save-complete")
        assert task["state"] == "complete", task
        state = inspect(server)["state"]
        assert state["week"]["week"] == 4 and state["week"]["season_index"] == 0
        task_id = task["task_id"]
        closed_source = server.app.state.runtime.repository.get_branch_saved_revision(
            revision_id=closed["revision_id"]
        )
    with ApiServer(database_url=database) as server:
        assert wait(server, task_id)["state"] == "complete"
        assert inspect(server)["state"] == state
        code, review = extension(server, 2)
        assert code == 200 and review["can_save"], review
        assert extend(server, review, "global-explicit-extension")[0] == 200
        assert (
            server.app.state.runtime.repository.get_branch_saved_revision(
                revision_id=closed_source.revision_id
            )
            == closed_source
        )
        assert wait(server, task_id)["original_command"] == original
        continued = start(
            server,
            reviewed(
                server, {"season_index": 1, "week": 1}, name="global-explicit-continue"
            ),
        )
        assert continued["checkpoint"] == "native_season_transition_review_required", (
            continued
        )
        url = scope(server) + "/native/global-explicit-continue/season-transition"
        code, review = _request("GET", url)
        assert code == 200, review
        body["review_fingerprint"] = review["review_fingerprint"]
        body["request_id"] = "global-approve-season"
        assert _request("POST", url + "/approve", body)[0] == 200
        continued = resume(server, continued, "global-season-approved")
        assert continued["checkpoint"] == "native_manual_save_required", continued
        save_tour(server)
        continued = resume(server, continued, "global-next-season-saved")
        assert continued["state"] == "target_reached", continued
        rows = inspect(server)["state"]["rankings"][-1]["rows"]
        assert sorted(r["points"] for r in rows) == [30, 30, 30, 30, 60, 60, 100, 100]
        assert all(len(r["counted_results"]) == 1 for r in rows)
        assert wait(server, task_id)["state"] == "complete"
