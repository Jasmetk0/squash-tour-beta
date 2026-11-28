"""Trace every batch of the HTTP fault scenario (diagnostic, Nov 28 #1941).

Runs the exact faulty half of
``tests/api/test_slot_worker_faults_http.py::test_faulty_shared_pool_equals_sequential_over_http_saved_v2``
(same ``FaultScript``, same script, same two-Run/fork/barrier scenario over
real uvicorn HTTP + SQLite, Saved v2) on the tree given by ``--root`` and
records one JSON line per event:

* ``batch``: scripted fault, pool generation, size, request thread, live pool
  processes at submission, deadline, end, outcome, ``timed_out`` and the state
  of every future when the batch ended;
* ``discard``: generation, whether it was already retired, whether the batch
  timed out;
* ``declined``: a batch computed sequentially without submission (cooldown,
  replacement, full queue);
* ``summary``: executor stats, applied faults, alive ``_ExecutorManagerThread``
  objects after ``close()``.

It never waits for a blocked manager thread at interpreter exit: when one is
left alive it is reported and the process ends with exit code 3 (a tree
without the #1941 fix may otherwise hang at exit exactly like the pytest step).
Nothing in the engine is changed.

    python scripts/trace_slot_worker_faults.py --root . --out work/trace.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

_T0 = time.monotonic()
_rows = []
_rows_lock = threading.Lock()


def _now():
    return round(time.monotonic() - _T0, 3)


def _record(**row):
    with _rows_lock:
        _rows.append(row)


class _Env:
    """The two ``monkeypatch`` calls ``_run`` makes, without pytest."""

    def setenv(self, key, value):
        os.environ[key] = value

    def delenv(self, key, raising=True):
        os.environ.pop(key, None)


def _traced_executor(faults_module, match_workers):
    class _TracedBatch:
        def __init__(self, inner, info):
            self.inner, self.info, self.generation = inner, info, inner.generation

        @property
        def timed_out(self):
            return self.inner.timed_out

        @property
        def futures(self):
            return self.inner.futures

        def __iter__(self):
            outcome = "ok"
            try:
                yield from self.inner
            except BaseException as error:
                outcome = repr(error)
                raise
            finally:
                _record(event="batch", **self.info, t_end=_now(),
                        elapsed=round(_now() - self.info["t_submit"], 3), outcome=outcome,
                        timed_out=self.inner.timed_out,
                        future_states=dict(Counter(f._state for f in self.inner.futures)))

        def close(self):
            self.inner.close()

    class Traced(faults_module.FaultScript):
        def run(self, requests):
            fault = self.script[0] if self.script else None
            submitted = _now()
            try:
                batch = super().run(requests)
            except Exception as error:
                _record(event="declined", fault=fault, size=len(requests), t=submitted,
                        thread=threading.current_thread().name, error=repr(error))
                raise
            generation = batch.generation
            return _TracedBatch(batch, {
                "fault": self.applied[-1], "generation": generation.number, "size": len(requests),
                "t_submit": submitted, "deadline_s": round(batch.deadline - time.monotonic(), 3),
                "thread": threading.current_thread().name,
                "live_pool_processes": len(getattr(generation.pool, "_processes", None) or {}),
            })

        def discard(self, batch=None):
            inner = batch.inner if isinstance(batch, _TracedBatch) else batch
            generation = getattr(inner, "generation", None)
            _record(event="discard", t=_now(), generation=getattr(generation, "number", None),
                    already_retired=getattr(generation, "retired", None),
                    timed_out=getattr(inner, "timed_out", None))
            return super().discard(inner)

    return Traced


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    os.chdir(root)
    sys.path[:0] = [str(root / "src"), str(root), str(root / "tests" / "api")]
    from beta_engine.infrastructure import match_workers
    from scripts import verify_slot_worker_parity as parity
    from tests.api import test_slot_worker_faults_http as faults

    script = ["crash", "duplicate", "missing", "foreign", "shuffled", "timeout"]
    executor = _traced_executor(faults, match_workers)(args.workers, script)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = tmp / "parity.db"
        parity.prepare(source)
        started = _now()
        try:
            faults._run(tmp, source, "faulty", _Env(), executor)
            stats = executor.stats()
        finally:
            executor.close()
    managers = [t.name for t in threading.enumerate() if type(t).__name__ == "_ExecutorManagerThread"]
    summary = {"event": "summary", "root": str(root), "python": sys.version.split()[0],
               "stats": stats, "applied": executor.applied, "scenario_s": round(_now() - started, 3),
               "timed_out": [(r["fault"], r["generation"], r["size"]) for r in _rows
                             if r.get("event") == "batch" and r["timed_out"]],
               "live_worker_pids_after_close": executor.live_worker_pids(),
               "alive_manager_threads_after_close": managers}
    with out.open("w") as stream:
        for row in sorted(_rows, key=lambda r: r.get("t_submit", r.get("t", 0))):
            stream.write(json.dumps(row) + "\n")
        stream.write(json.dumps(summary) + "\n")
    print(json.dumps(summary), flush=True)
    if managers:
        print("BLOCKED MANAGER THREAD LEFT; exiting without joining it", file=sys.stderr, flush=True)
        os._exit(3)


if __name__ == "__main__":
    main()
