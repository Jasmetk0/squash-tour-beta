"""Production HTTP/SQLite slots computed by the opt-in spawn workers.

Real uvicorn servers on disposable copies of the real prepared global-slot Run
(two overlapping 4-player Editions). Workers never touch SQLite; every result
is rebound and fully decoded by the parent. Sequential and worker runs must
produce identical sporting checkpoints, receipts and inspections; only the
random Saved revision id differs between any two Saves.
"""

from __future__ import annotations

import json
import re
import threading

import pytest

from beta_engine.domain.matches import slot_batch
from beta_engine.infrastructure.match_workers import ENVIRONMENT_VARIABLE
from tests.api.test_calendar_global_slots import copy_database, sporting
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke


_SAVED_ID = re.compile(r"saved-revision-[0-9a-f]{32}")
# Values that hash a random Saved revision id (a later command's expected head).
_DERIVED = {"tour_fingerprint", "save_projection_fingerprint",
            "expected_preview_fingerprint", "expected_tour_fingerprint"}


def _normalized(value):
    """Replace random Saved revision ids by their order of appearance."""
    order = {}
    text = _SAVED_ID.sub(lambda m: "saved-revision-#%d" % order.setdefault(m.group(), len(order)),
                         json.dumps(value, sort_keys=True))

    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in _DERIVED}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node
    return strip(json.loads(text))


def _view(server):
    return _normalized(inspect(server))


def _play(path, workers, monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(workers))
    before = slot_batch.batch_counters()
    db = f"sqlite:///{path}"
    receipts = []
    with ApiServer(database_url=db) as server:
        assert (server.app.state.match_workers is not None) == bool(workers)
        # One selected match stays on the original single-match call.
        receipts.append(execute(server, command(inspect(server), "next-match", name="one-match"))[0])
        save_tour(server)
        partial = _view(server)
    with ApiServer(database_url=db) as server:
        # Warm/cold restart of the partially played slot; the remaining three
        # matches of the same frozen snapshot are one batch.
        assert _view(server) == partial
        receipts.append(execute(server, command(inspect(server), "next-slot", name="rest-of-slot"))[0])
        save_tour(server)
        receipts.append(execute(server, command(inspect(server), "next-slot", name="finals"))[0])
        save_tour(server)
        saved = _view(server)
        if workers:
            assert 1 <= len(server.app.state.match_workers.worker_pids()) <= workers
    assert slot_batch.installed_executor() is None
    with ApiServer(database_url=db) as server:
        restarted = _view(server)
        checkpoint = sporting(server)
    after = slot_batch.batch_counters()
    used = {k: after[k] - before[k] for k in after}
    return receipts, saved, restarted, checkpoint, used


def test_worker_slots_equal_sequential_through_save_and_restart(tmp_path, prepared_slots, monkeypatch):
    outcomes = {}
    for workers in (0, 2):
        path = tmp_path / f"workers-{workers}.db"
        copy_database(prepared_slots, path)
        outcomes[workers] = _play(path, workers, monkeypatch)
    sequential, parallel = outcomes[0], outcomes[2]
    assert sequential[:4] == parallel[:4]
    assert sequential[1] == sequential[2]  # restart reads the identical state
    assert len(sequential[3].tournaments[-2:]) == 2
    assert sequential[4]["executor_batches"] == 0
    # rest-of-slot (3) and finals (2): execute + post-write verification each,
    # then the cold restart verification replays them again.
    assert parallel[4]["executor_batches"] >= 4 and parallel[4]["fallback_batches"] == 0


def test_concurrent_independent_runs_share_one_bounded_pool(tmp_path, prepared_slots, monkeypatch):
    first, later = tmp_path / "first.db", tmp_path / "later.db"
    copy_database(prepared_slots, first)
    copy_database(prepared_slots, later)
    with ApiServer(database_url=f"sqlite:///{later}") as server:
        execute(server, command(inspect(server), "next-slot", name="earlier-slot"))
        save_tour(server)
    expected = {}
    for name, path in (("first", first), ("later", later)):
        reference = tmp_path / f"{name}-sequential.db"
        copy_database(path, reference)
        with ApiServer(database_url=f"sqlite:///{reference}") as server:
            expected[name] = execute(server, command(inspect(server), "next-slot", name="concurrent"))[0]
            save_tour(server)
            expected[name] = (expected[name], sporting(server))
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "2")
    actual, errors = {}, []
    with ApiServer(database_url=f"sqlite:///{first}") as a, ApiServer(database_url=f"sqlite:///{later}") as b:
        pool = a.app.state.match_workers
        assert pool is not None and b.app.state.match_workers is None  # one shared pool
        assert slot_batch.installed_executor() is pool
        views = {"first": (a, inspect(a)), "later": (b, inspect(b))}
        barrier = threading.Barrier(2)

        def run(name):
            server, view = views[name]
            try:
                barrier.wait()
                result = execute(server, command(view, "next-slot", name="concurrent"))[0]
                save_tour(server)
                actual[name] = (result, sporting(server))
            except BaseException as error:  # noqa: BLE001
                errors.append(error)

        threads = [threading.Thread(target=run, args=(n,)) for n in views]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert not errors, errors
        assert len(pool.worker_pids()) <= 2
    assert actual == expected
    assert slot_batch.installed_executor() is None
