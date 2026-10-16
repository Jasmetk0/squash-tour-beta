"""Real reviewed calendar health, separate Save, restore, fork and restart."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_initial_world_adoption import (
    confirm,
    request,
    review,
    root,
)
from tests.api.test_player_generation_calendar_gate import _dump, _world
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def setup(server, clock):
    repo, _ = _world(server, clock)
    population_request = request(server)
    code, adopted = confirm(
        server, population_request, review(server, population_request)
    )
    assert code == 201, adopted
    code, saved = _request(
        "POST",
        root(server) + "/save",
        {
            "expected_draft_version": population_request["expected_draft_version"],
            "expected_initial_world_fingerprint": adopted["fingerprint"],
        },
    )
    assert code == 201, saved
    payload = {
        "command_id": "initial-health",
        "expected_saved_head": saved["saved_revision"]["revision_id"],
        "expected_draft_version": saved["working_draft"]["draft_version"],
        "expected_population_fingerprint": adopted["fingerprint"],
        "audit_label": "Admin",
        "audit_reason": "Reviewed fresh baseline, no invented health history",
    }
    return repo, saved, payload


def health_root(server, branch="branch"):
    return server.base_url + f"/admin/runs/run/branches/{branch}/player-health"


def preview(server, payload):
    code, result = _request(
        "POST", health_root(server) + "/calendar-initial/preview", payload
    )
    assert code == 200, result
    return {
        "review": result["request"],
        "expected_health_fingerprint": result["health_fingerprint"],
    }


@pytest.mark.parametrize(
    "clock",
    [
        RunCalendar(52, 35, 2030, 3),
        RunCalendar(80, 80, 2100, 300),
        RunCalendar(1, 1, 0, 1),
    ],
)
def test_review_confirm_save_fork_restore_restart(tmp_path, clock):
    from beta_engine.application.run_saved_revision_restore_service import (
        RunSavedRevisionRestoreService,
    )
    from tests.application.test_run_package_review_acceptance import _ids

    path = tmp_path / "health.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, population_saved, payload = setup(server, clock)
        before = _dump(path)
        command = preview(server, payload)
        assert _dump(path) == before
        code, installed = _request(
            "POST", health_root(server) + "/calendar-initial", command
        )
        assert code == 201, installed
        assert installed["saved"] is False and installed["draft_status"] == "dirty"
        assert installed["saved_head_revision_id"] == payload["expected_saved_head"]
        assert installed["run_calendar"] == clock.to_metadata()
        assert all(
            not p["records"] and not p["permanent_consequences"]
            for p in installed["state"]["players"]
        )
        after = _dump(path)
        assert _request("POST", health_root(server) + "/calendar-initial", command) == (
            201,
            installed,
        )
        assert _dump(path) == after
        code, proof = _request("GET", health_root(server) + "/save/preview")
        assert code == 200 and proof["can_save"], proof
        code, saved = _request(
            "POST",
            health_root(server) + "/save",
            {
                "expected_draft_version": proof["draft_version"],
                "expected_player_health_fingerprint": proof[
                    "health_component_fingerprint"
                ],
            },
        )
        assert code == 201, saved
        health_saved_id = saved["saved_revision"]["revision_id"]
        assert repo.verify_branch_saved_revision_hash(revision_id=health_saved_id)
        code, view = _request("GET", health_root(server) + "/calendar-initial")
        assert code == 200 and view["saved"] and view["state"] == installed["state"], (
            view
        )
        after = _dump(path)
        assert _request("POST", health_root(server) + "/calendar-initial", command) == (
            201,
            view,
        )
        assert _dump(path) == after
        code, fork = _request(
            "POST",
            server.base_url + "/run-containers/run/branches",
            {"source_branch_id": "branch", "source_saved_revision_id": health_saved_id},
        )
        assert code == 201, fork
        code, copied = _request(
            "GET", health_root(server, fork["branch_id"]) + "/calendar-initial"
        )
        assert code == 200 and copied["saved"], copied
        assert copied["state"]["players"] == installed["state"]["players"]
        assert (
            copied["state"]["source_initial_world_fingerprint"]
            == installed["state"]["source_initial_world_fingerprint"]
        )
        # Restore to a genuinely saved population with no health, then back.
        empty = RunSavedRevisionRestoreService(
            repo, _ids("c1", "r2", "a2")
        ).restore_current_branch(
            run_id="run",
            branch_id="branch",
            target_saved_revision_id=payload["expected_saved_head"],
            expected_head_saved_revision_id=health_saved_id,
            expected_draft_version=saved["working_draft"]["draft_version"],
            expected_current_viewer_branch_id="branch",
            explicit_confirmation=True,
        )
        assert (
            _request("GET", health_root(server) + "/calendar-initial")[1]["state"]
            is None
        )
        restored = RunSavedRevisionRestoreService(
            repo, _ids("c2", "r3", "a3")
        ).restore_current_branch(
            run_id="run",
            branch_id="branch",
            target_saved_revision_id=health_saved_id,
            expected_head_saved_revision_id=empty.saved_revision.revision_id,
            expected_draft_version=empty.working_draft.draft_version,
            expected_current_viewer_branch_id="branch",
            explicit_confirmation=True,
        )
        code, view = _request("GET", health_root(server) + "/calendar-initial")
        assert code == 200 and view["saved"] and view["state"] == installed["state"], (
            view
        )
        assert repo.verify_branch_saved_revision_hash(
            revision_id=restored.saved_revision.revision_id
        )
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("GET", health_root(server) + "/calendar-initial") == (200, view)
        assert _request(
            "GET", health_root(server, fork["branch_id"]) + "/calendar-initial"
        ) == (200, copied)


def test_stale_review_and_legacy_health_reads_fail_without_writes(tmp_path):
    path = tmp_path / "stale.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _, _, payload = setup(server, RunCalendar.earth_default())
        command = preview(server, payload)
        before = _dump(path)
        for changes in (
            {"command_id": "other"},
            {"expected_saved_head": "r0"},
            {"expected_draft_version": 0},
        ):
            code, error = _request(
                "POST",
                health_root(server) + "/calendar-initial",
                {**command, "review": {**command["review"], **changes}},
            )
            assert code == 409, error
            assert _dump(path) == before
        code, installed = _request(
            "POST", health_root(server) + "/calendar-initial", command
        )
        assert code == 201, installed
        before = _dump(path)
        player = installed["state"]["players"][0]["player_id"]
        code, error = _request(
            "GET",
            server.base_url
            + f"/admin/runs/run/branches/branch/players/{player}/health",
        )
        assert code == 409, error
        assert _dump(path) == before


def test_concurrent_identical_commands_only_dirty_draft_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "concurrent.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _, _, payload = setup(server, RunCalendar.earth_default())
        command = preview(server, payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: _request(
                        "POST", health_root(server) + "/calendar-initial", command
                    ),
                    range(2),
                )
            )
        assert results[0] == results[1] and results[0][0] == 201, results
        assert results[0][1]["draft_version"] == payload["expected_draft_version"] + 1


def test_health_write_failure_rolls_back_entire_command(tmp_path, monkeypatch):
    from beta_engine.application import calendar_initial_health_service as module

    path = tmp_path / "rollback.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _, _, payload = setup(server, RunCalendar.earth_default())
        command = preview(server, payload)
        before = _dump(path)
        original = module.put_health

        def fail_after_write(session, state):
            original(session, state)
            raise ValueError("Injected post-write failure")

        monkeypatch.setattr(module, "put_health", fail_after_write)
        code, result = _request(
            "POST", health_root(server) + "/calendar-initial", command
        )
        assert code == 409 and "Injected" in str(result)
        assert _dump(path) == before
        monkeypatch.setattr(module, "put_health", original)
        assert (
            _request("POST", health_root(server) + "/calendar-initial", command)[0]
            == 201
        )


def test_late_draft_change_invalidates_review_without_health_write(tmp_path):
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import BranchWorkingDraftModel

    path = tmp_path / "late-drift.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _, payload = setup(server, RunCalendar.earth_default())
        command = preview(server, payload)
        with repo._session_factory.begin() as session:
            draft = session.scalar(
                select(BranchWorkingDraftModel).where(
                    BranchWorkingDraftModel.branch_id == "branch"
                )
            )
            draft.draft_version += 1
        before = _dump(path)
        code, result = _request(
            "POST", health_root(server) + "/calendar-initial", command
        )
        assert code == 409, result
        assert _dump(path) == before
