"""Real HTTP/SQLite/Task Center: a prepared worker child verifies only its append.

The production worker prepares an ordinary native next-slot child in a read
snapshot and installs it in a separate BEGIN IMMEDIATE writer only after its
data_version, parent, Saved HEAD, Working Draft and lease checks. These cases
show that the narrow post-write verification of that child gives exactly the
committed rows of the complete post-write context, falls back to it for any
unproven write, never swallows a Full Simulation control fence, and keeps the
manual Save / restart sequence unchanged.
"""

from itertools import count
from uuid import NAMESPACE_URL, uuid5

import pytest

from beta_engine.application import calendar_tour_appended_slot_verification as appended
from beta_engine.application.calendar_tour_service import CalendarTourService
from tests.api.test_calendar_tour_appended_slot_verification import (
    _earlier_event,
    _install_then,
    _rehash_checkpoint,
)
from tests.api.test_native_full_simulation_prepared_step import (
    _copy,
    _parent,
    _rows,
    _sporting,
    _watch_driver,
    start_failed,
)
from tests.api.test_native_full_simulation_tasks import (
    inspect,
    resume,
    reviewed,
    save_tour,
    start,
)
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module")
def worker_slot_source(prepared_slots, tmp_path_factory):
    """The shared real W52 global-slot Run and one reviewed week-5 task."""
    path = tmp_path_factory.mktemp("appended-worker-source") / "source.db"
    _copy(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        command = reviewed(server, {"season_index": 0, "week": 5}, name="appended-worker")
    return path, command


def _stable_ids(patch, label):
    """Deterministic API/Task Center identities so two copies are comparable."""
    import beta_engine.application.full_simulation_tasks as tasks
    import beta_engine.infrastructure.db.full_simulation_invocation_lease as lease
    from beta_engine.api import deps

    for module in (deps, tasks, lease):
        ids = count()
        patch.setattr(module, "uuid4", lambda ids=ids, name=module.__name__:
                      uuid5(NAMESPACE_URL, f"{label}:{name}:{next(ids)}"))


def test_worker_appended_slots_equal_the_complete_context_through_saves_and_restart(
    tmp_path, worker_slot_source, monkeypatch,
):
    source, command = worker_slot_source
    outcomes = {}
    for mode in ("narrow", "complete"):
        path = tmp_path / f"{mode}.db"
        _copy(source, path)
        with monkeypatch.context() as patch:
            _stable_ids(patch, "appended-worker")
            calls = _watch_driver(patch)
            if mode == "complete":
                patch.setattr(appended, "begin_appended_slot", lambda *args: None)
            with ApiServer(database_url=f"sqlite:///{path}") as server:
                task = start(server, command)
                assert task["checkpoint"] == "native_manual_save_required", task
                save_tour(server)
                task = resume(server, task, "saved-first-slot")
                assert task["checkpoint"] == "native_manual_save_required", task
                assert inspect(server)["next_slot"] is None
                save_tour(server)
                task = resume(server, task, "saved-finals-slot")
                assert task["checkpoint"] == "native_result_review_required", task
                view = inspect(server)
            with ApiServer(database_url=f"sqlite:///{path}") as restarted:
                assert inspect(restarted) == view
        outcomes[mode] = (dict(calls.counts), _rows(path), _parent(path, command["command_id"]), view)
    narrow, complete = outcomes["narrow"], outcomes["complete"]
    # Two worker next-slot children: accepted narrowly, or by the complete
    # post-write context (which then runs once more per child).
    assert narrow[0].get("appended_slot", 0) == 2 and complete[0].get("appended_slot", 0) == 0
    assert narrow[0]["prepared_install"] == complete[0]["prepared_install"] == 2
    assert narrow[0]["context"] + 2 == complete[0]["context"]
    assert narrow[1] == complete[1]  # every sporting, Saved, draft and parent row
    assert narrow[2] == complete[2] and narrow[3] == complete[3]
    status, parent = narrow[2]
    actions = [c["request"]["command"]["action"] for c in parent["children"]]
    assert status == "pending" and actions == ["next-slot", "next-slot"]


def test_corrupt_worker_append_uses_the_complete_context_and_rolls_back(
    tmp_path, worker_slot_source, monkeypatch,
):
    source, command = worker_slot_source
    path = tmp_path / "corrupt.db"
    _copy(source, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        task = start(server, command)
        save_tour(server)
        before = _sporting(path)
        parent_before = _parent(path, command["command_id"])
        with monkeypatch.context() as patch:
            calls = _watch_driver(patch)
            patch.setattr(CalendarTourService, "_install_prepared",
                          _install_then(lambda s: _rehash_checkpoint(s, _earlier_event)))
            from tests.api.test_native_full_simulation_tasks import scope, wait
            from tests.api.test_saved_revision_history_api import _request

            body = {"request_id": "corrupt-append", "action": "resume", "expected_revision": task["revision"],
                    "operator_label": "Admin", "audit_reason": "Saved and reviewed; continue the same original task"}
            code, result = _request("POST", scope(server) + "/tasks/" + task["task_id"] + "/continue", body)
            assert code == 202, result
            task = wait(server, task["task_id"], allow_failed=True)
        assert task["state"] == "failed", task
        # The narrow path proved nothing; the complete post-write context ran
        # in the same writer transaction and rejected the corrupted rows.
        assert calls.counts.get("appended_slot", 0) == 0 and calls["prepared_install"] == 1
        assert _sporting(path) == before
        assert _parent(path, command["command_id"]) == parent_before
        task = resume(server, task, "recover-after-corrupt-append", action="recover")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert inspect(server)["next_slot"] is None


@pytest.mark.parametrize("fence", ["FullSimulationPauseRequested", "FullSimulationStopped",
                                   "FullSimulationTargetReached"])
def test_control_fences_are_never_treated_as_an_unproven_append(monkeypatch, fence):
    from beta_engine.infrastructure.db import full_simulation_execution_guard as guard

    error = getattr(guard, fence)

    def raised(*_args, **_kwargs):
        raise error("fence inside the writer transaction")

    monkeypatch.setattr(appended, "_verify", raised)
    with pytest.raises(error):
        appended.verify_appended_slot(None, None, "run", "branch", None, {})

    def unproven(*_args, **_kwargs):
        raise ValueError("an ordinary mismatch")

    monkeypatch.setattr(appended, "_verify", unproven)
    assert appended.verify_appended_slot(None, None, "run", "branch", None, {}) is None


def test_mutated_private_prefix_is_rejected_by_the_complete_hash(tmp_path, worker_slot_source, monkeypatch):
    """A nested value changed after authentication cannot pass the narrow path."""
    from beta_engine.application import native_full_simulation as native

    source, command = worker_slot_source
    path = tmp_path / "mutated.db"
    _copy(source, path)
    original = native.NativeFullSimulationDriver._read_prepared_step

    def read(self, connection, task_command, token):
        step = original(self, connection, task_command, token)
        if step is not None and step.get("kind") == "child" and step.get("loaded"):
            state = step["loaded"][1]
            # Mutate a nested dict of the authenticated Tour prefix in place.
            state.editions[0].edition.point_table["champion"] += 1
        return step

    with monkeypatch.context() as patch:
        calls = _watch_driver(patch)
        patch.setattr(native.NativeFullSimulationDriver, "_read_prepared_step", read)
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            before = _sporting(path)
            task = start_failed(server, command)
            assert calls.counts.get("appended_slot", 0) == 0
            assert _sporting(path) == before, task
