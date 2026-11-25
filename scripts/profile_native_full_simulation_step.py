"""Per-step cost of native Full Simulation over real HTTP, SQLite and Task Center.

Diagnostic only. It runs the unchanged production acceptance scenario
``test_native_task_actual_match_points_all_weeks_and_real_season_rollover``
and observes, for every worker invocation (one actual native child step from
next-step selection through Preview, Execute and the Task Center result):

* calls/inclusive wall time of the planning, match-preparation, pre-write
  verification and Task Center synchronization functions,
* how long each SQLite connection held the writer lock (``BEGIN IMMEDIATE``
  until COMMIT/ROLLBACK),
* thread CPU time and the sampled process RSS peak.

``--prepare`` stores the fixture right after the original command is reviewed.
``--input`` runs the same scenario from a fresh SQLite backup of such a
fixture, so two production trees can be compared on identical Run copies.
Persistence UUIDs come from a deterministic harness sequence (never sporting
RNG) so identical engines produce byte-identical history. Wrappers never
change arguments, results or exceptions. Use a fresh ``--root`` per run.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import functools
import hashlib
import json
import platform
import resource
import sqlite3
import subprocess
import threading
import time
import uuid
from collections import defaultdict

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--clock", choices=("short", "w52", "w61", "w80", "global"), default="short",
                    help="matrix clock, or 'global': W52 global-slot Tour v5 next-slot children")
parser.add_argument("--population", type=int, default=8, help="players for --clock global --prepare")
parser.add_argument("--input", type=Path, help="fixture directory written by --prepare")
parser.add_argument("--prepare", action="store_true", help="stop after writing the fixture")
parser.add_argument("--label", default="")
args = parser.parse_args()
args.root.mkdir(parents=True, exist_ok=True)
db = args.root / ("slot-worker.db" if args.clock == "global" else "matrix.db")
if db.exists() or (args.root / "start.db").exists():
    raise SystemExit("Use a fresh --root; existing SQLite files are never overwritten")

# ---- deterministic persistence identities (harness only) -------------------
_uuid_lock = threading.Lock()
_uuid_counters: dict[str, int] = defaultdict(int)


def _deterministic_uuid4(scope):
    def factory():
        with _uuid_lock:
            _uuid_counters[scope] += 1
            n = _uuid_counters[scope]
        return uuid.UUID(hashlib.sha256(f"{scope}:{n}".encode()).hexdigest()[:32], version=4)
    return factory


import beta_engine.api.deps as deps  # noqa: E402
import beta_engine.application.full_simulation_tasks as tasks  # noqa: E402
import beta_engine.infrastructure.db.full_simulation_invocation_lease as lease  # noqa: E402

for module in (deps, tasks, lease):
    module.uuid4 = _deterministic_uuid4(module.__name__)

from sqlalchemy import event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402

import beta_engine.application.calendar_global_slot_service as slots  # noqa: E402
import beta_engine.application.native_fork_runtime_service as fork_service  # noqa: E402
import beta_engine.application.native_full_simulation as native  # noqa: E402
from beta_engine.application.calendar_tour_service import CalendarTourService  # noqa: E402
from beta_engine.domain.calendar.run_calendar import RunCalendar  # noqa: E402
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository as SqlAlchemyRepository  # noqa: E402
from tests.api import test_calendar_tour_flow as tour  # noqa: E402
from tests.api import test_native_fork_public_continuation as fork_module  # noqa: E402
from tests.api import test_native_full_simulation_tasks as case  # noqa: E402

# ---- per-thread attribution -------------------------------------------------
_local = threading.local()
steps: list[dict] = []
other = {"calls": defaultdict(int), "seconds": defaultdict(float)}
_rss_peak = [0]


def _bucket():
    record = getattr(_local, "step", None)
    return record if record is not None else other


def _rss_kib():
    with open("/proc/self/statm") as handle:
        return int(handle.read().split()[1]) * (resource.getpagesize() // 1024)


def _sample_rss(stop):
    while not stop.wait(0.05):
        value = _rss_kib()
        if value > _rss_peak[0]:
            _rss_peak[0] = value
        record = getattr(_sampled, "step", None)
        if record is not None and value > record["rss_peak_kib"]:
            record["rss_peak_kib"] = value


class _Shared:
    step = None


_sampled = _Shared()


def observe(owner, name, label=None):
    original = getattr(owner, name)
    label = label or name

    @functools.wraps(original)
    def measured(*a, **kw):
        bucket = _bucket()
        start = time.perf_counter()
        try:
            return original(*a, **kw)
        finally:
            bucket["calls"][label] += 1
            bucket["seconds"][label] += time.perf_counter() - start

    import inspect as _inspect

    raw = _inspect.getattr_static(owner, name)
    if isinstance(raw, staticmethod):
        measured = staticmethod(measured)
    elif isinstance(raw, classmethod):
        raise TypeError(f"classmethod {name} is not observed by this harness")
    setattr(owner, name, measured)


# Planning / next-step selection
observe(native, "native_context")
observe(CalendarTourService, "_transition_blockers")
# Match/step preparation
observe(CalendarTourService, "_prepare_from_context")
observe(slots, "prepare_global_slot")
observe(CalendarTourService, "_transition_candidate")
observe(fork_service, "prepare_command", "fork.prepare_command")
observe(CalendarTourService, "_apply")
# Authoritative source verification (shared by planning and pre-write checks)
observe(CalendarTourService, "_context")
observe(fork_service.NativeForkRuntimeService, "_context", "fork._context")
observe(fork_service, "verify_runtime", "fork.verify_runtime")
observe(SqlAlchemyRepository, "_validated_saved_revision_in_session")
observe(SqlAlchemyRepository, "_validated_branch_revision_lineage_in_session")
# Preview/Execute boundaries
observe(CalendarTourService, "preview")
observe(CalendarTourService, "execute")
observe(fork_service.NativeForkRuntimeService, "preview", "fork.preview")
observe(fork_service.NativeForkRuntimeService, "execute", "fork.execute")
# Task Center / parent synchronization
for module in (native, tasks):
    observe(module, "validate_native_parent", "validate_native_parent")
    if hasattr(module, "resolve_revision_run_calendar"):
        # On the candidate this counts only first-sight (full) validations.
        observe(module, "resolve_revision_run_calendar", "resolve_revision_run_calendar")
observe(native, "read_native_task_progress")
observe(native, "authenticate_children")
observe(tasks.FullSimulationTaskWorker, "_finish", "task._finish")
observe(tasks.FullSimulationTaskWorker, "_heartbeat", "task._heartbeat")
observe(tasks, "inspect_tasks", "task.inspect_tasks(GET)")
# Candidate-only driver phases (absent on the base tree): attempts, successful
# prepared installs and the original complete path (incl. every fallback).
for optional in ("_read_prepared_step", "_install_prepared_step", "_install_calendar_step",
                 "_install_fork_step", "_simulate_full_path"):
    if hasattr(native.NativeFullSimulationDriver, optional):
        observe(native.NativeFullSimulationDriver, optional, "driver." + optional)

_worker_execute = tasks.FullSimulationTaskWorker._execute


def _execute(self, task_id, driver):
    record = {
        "calls": defaultdict(int), "seconds": defaultdict(float),
        "writer_lock_seconds": 0.0, "writer_lock_transactions": 0,
        "writer_lock_max_seconds": 0.0, "rss_peak_kib": _rss_kib(),
    }
    _local.step = _sampled.step = record
    wall, cpu = time.perf_counter(), time.thread_time()
    try:
        return _worker_execute(self, task_id, driver)
    finally:
        record["wall_seconds"] = time.perf_counter() - wall
        record["thread_cpu_seconds"] = time.thread_time() - cpu
        _local.step = _sampled.step = None
        steps.append(record)


tasks.FullSimulationTaskWorker._execute = _execute

# ---- writer-lock hold time ---------------------------------------------------
_locks: dict[int, float] = {}
_locks_guard = threading.Lock()


@event.listens_for(Engine, "after_cursor_execute")
def _lock_acquired(conn, cursor, statement, parameters, context, many):
    if statement.strip().upper() == "BEGIN IMMEDIATE":
        with _locks_guard:
            _locks[id(conn.connection.dbapi_connection)] = time.perf_counter()


def _released(dbapi_connection):
    with _locks_guard:
        started = _locks.pop(id(dbapi_connection), None)
    if started is None:
        return
    held = time.perf_counter() - started
    bucket = getattr(_local, "step", None)
    if bucket is None:
        other["seconds"]["writer_lock(other threads)"] += held
        other["calls"]["writer_lock(other threads)"] += 1
        return
    bucket["writer_lock_seconds"] += held
    bucket["writer_lock_transactions"] += 1
    bucket["writer_lock_max_seconds"] = max(bucket["writer_lock_max_seconds"], held)


@event.listens_for(Engine, "commit")
def _commit(conn):
    _released(conn.connection.dbapi_connection)


@event.listens_for(Engine, "rollback")
def _rollback(conn):
    _released(conn.connection.dbapi_connection)


# ---- fixture handling ----------------------------------------------------------
def backup(source, destination):
    with sqlite3.connect(source) as s, sqlite3.connect(destination) as d:
        s.backup(d)


meta: dict = {}
scenario: dict = {}
original_review = case.reviewed


class _Prepared(Exception):
    pass


def reviewed(server, *a, **kw):
    command = original_review(server, *a, **kw)
    if not meta:
        meta.update(branch=getattr(server, "native_task_branch", "branch"), command=command,
                    uuid_counters=dict(_uuid_counters))
        if args.prepare:
            backup(db, args.root / "start.db")
            (args.root / "input.json").write_text(json.dumps(meta, indent=2))
            raise _Prepared
        scenario["start"] = time.perf_counter()
        scenario["cpu"] = time.process_time()
    return command


case.reviewed = reviewed
if args.input:
    initial = json.loads((args.input / "input.json").read_text())
    if args.clock != "global":
        backup(args.input / "start.db", db)
    with _uuid_lock:
        _uuid_counters.update(initial["uuid_counters"])

    def setup(server, *a, **kw):
        return server.app.state.runtime.repository, None

    case.setup = setup
    tour.create_edition = lambda *a, **kw: None
    fork_module.fork = lambda *a, **kw: {"branch_id": initial["branch"]}

clock = None if args.clock == "global" else {
    "short": RunCalendar(7, 5, 2030, 2),
    "w52": RunCalendar(52, 51, 2030, 2),
    "w61": RunCalendar(61, 37, 2000, 2),
    "w80": RunCalendar(80, 80, 2100, 2),
}[args.clock]

source_tree = subprocess.check_output(["git", "rev-parse", "HEAD:src"], text=True).strip()
dirty = bool(subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src"]).returncode)
stop = threading.Event()
sampler = threading.Thread(target=_sample_rss, args=(stop,), daemon=True)
sampler.start()
passed = False
try:
    if args.clock != "global":
        case.test_native_task_actual_match_points_all_weeks_and_real_season_rollover(args.root, clock)
    elif args.prepare:
        from tests.api.test_calendar_global_slots import ready
        from tests.api.test_saved_revision_history_api import ApiServer

        with ApiServer(database_url=f"sqlite:///{args.root / 'start.db'}") as server:
            ready(server, 52, population=args.population)
        meta.update(branch="branch", uuid_counters=dict(_uuid_counters), population=args.population)
        (args.root / "input.json").write_text(json.dumps(meta, indent=2))
        raise _Prepared
    else:
        from tests.api.test_calendar_global_slots import test_full_simulation_uses_slot_children_and_frozen_target as global_case

        global_case(args.root, args.input / "start.db")
    passed = True
except _Prepared:
    print("PREPARED", args.root, flush=True)
    raise SystemExit(0)
finally:
    stop.set()


def _plain(record):
    return {
        **{k: v for k, v in record.items() if k not in {"calls", "seconds"}},
        "calls": dict(sorted(record["calls"].items())),
        "seconds": {k: round(v, 4) for k, v in sorted(record["seconds"].items())},
    }


def _sum(records):
    calls, seconds = defaultdict(int), defaultdict(float)
    for r in records:
        for k, v in r["calls"].items():
            calls[k] += v
        for k, v in r["seconds"].items():
            seconds[k] += v
    return dict(sorted(calls.items())), {k: round(v, 3) for k, v in sorted(seconds.items())}


def _history(path, branch):
    with sqlite3.connect(path) as c:
        tables = [r[0] for r in c.execute("select name from sqlite_master where type='table' order by name")]
        digests = {}
        for table in tables:
            columns = [r[1] for r in c.execute(f"pragma table_info('{table}')")]
            keep = [col for col in columns if col not in {"created_at", "updated_at"}]
            rows = c.execute(f"select {', '.join(chr(34) + k + chr(34) for k in keep)} from '{table}' order by 1, 2").fetchall()
            text = []
            for row in rows:
                values = []
                for column, value in zip(keep, row):
                    if isinstance(value, str) and column in {"payload_json", "result_json"} and table in {
                            "full_simulation_tasks", "full_simulation_execution_leases"}:
                        # Task Center audit events and heartbeats carry wall-clock seconds.
                        data = json.loads(value)
                        for e in data.get("events", []):
                            e.pop("at_unix", None)
                            e.pop("fingerprint", None)
                            e.pop("previous", None)
                        data.pop("heartbeat_unix", None)
                        value = json.dumps(data, sort_keys=True)
                    if table == "full_simulation_tasks" and column == "payload_fingerprint":
                        value = None
                    if column == "expires_at_unix":
                        value = None
                    values.append(value)
                text.append(json.dumps(values, default=str))
            digests[table] = hashlib.sha256("\n".join(text).encode()).hexdigest()
        revisions = c.execute("select count(*), sum(length(cast(payload_json as blob))) from branch_saved_revisions").fetchone()
    return {"tables": digests, "revision_count": revisions[0], "revision_payload_bytes": revisions[1]}


calls, seconds = _sum(steps)
report = {
    "label": args.label,
    "clock": args.clock,
    "passed": passed,
    "production_source_tree": source_tree,
    "uncommitted_source_changes": dirty,
    "python": sys.version.split()[0],
    "platform": platform.platform(),
    "scenario_wall_seconds": time.perf_counter() - scenario.get("start", time.perf_counter()),
    "scenario_process_cpu_seconds": time.process_time() - scenario.get("cpu", time.process_time()),
    "process_rss_peak_kib_sampled": _rss_peak[0],
    "process_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "worker_invocations": len(steps),
    "worker_wall_seconds": round(sum(s["wall_seconds"] for s in steps), 3),
    "worker_thread_cpu_seconds": round(sum(s["thread_cpu_seconds"] for s in steps), 3),
    "worker_writer_lock_seconds": round(sum(s["writer_lock_seconds"] for s in steps), 3),
    "worker_writer_lock_transactions": sum(s["writer_lock_transactions"] for s in steps),
    "worker_writer_lock_max_seconds": round(max((s["writer_lock_max_seconds"] for s in steps), default=0), 3),
    "worker_calls": calls,
    "worker_seconds": seconds,
    "other_threads": _plain(other),
    "history": _history(db, meta.get("branch", "branch")),
    "steps": [_plain(s) for s in steps],
}
(args.root / "report.json").write_text(json.dumps(report, indent=2))
summary = {k: v for k, v in report.items() if k not in {"steps", "other_threads"}}
print("REPORT", json.dumps(summary, indent=1), flush=True)
