"""Baseline/after real acceptance, with immutable SQLite input and sampled snapshots."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import hashlib
import json
import platform
import resource
import sqlite3
import subprocess
import threading
import time
from collections import Counter

from sqlalchemy import event
from sqlalchemy.engine import Engine

from beta_engine.application import full_simulation_tasks as tasks
from beta_engine.application import native_full_simulation as native
from beta_engine.domain.calendar.run_calendar import RunCalendar
from scripts.profile_native_full_simulation_metrics import measure_calls
from tests.api import test_calendar_tour_flow as tour
from tests.api import test_native_fork_public_continuation as fork_module
from tests.api import test_native_full_simulation_tasks as case

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--weeks", type=int, choices=(52, 61, 80), default=52)
parser.add_argument("--input", type=Path)
a = parser.parse_args()
a.root.mkdir(parents=True, exist_ok=True)
db = a.root / "matrix.db"
if db.exists():
    raise ValueError(
        "Use a fresh output directory; existing SQLite fixtures are never overwritten"
    )


def backup(source, destination):
    with sqlite3.connect(source) as s, sqlite3.connect(destination) as d:
        s.backup(d)


if a.input:
    backup(a.input / "start.db", db)
rows = []
sql = Counter()
lock = threading.Lock()
contexts = []
read_cost = measure_calls(tasks, "_project")
heartbeat_cost = measure_calls(tasks.FullSimulationTaskWorker, "_heartbeat")


def count(conn, cursor, statement, parameters, context, many):
    with lock:
        sql["count"] += 1
        sql["statement_bytes"] += len(statement.encode())
        sql["parameter_bytes"] += len(str(parameters).encode())


event.listen(Engine, "before_cursor_execute", count)
original_context = native.native_context


def context(*args, **kwargs):
    t = time.perf_counter()
    try:
        return original_context(*args, **kwargs)
    finally:
        contexts.append(time.perf_counter() - t)


native.native_context = context
original_review = case.reviewed
meta = {}
scenario_start = None
scenario_sql = None


def reviewed(server, *args, **kw):
    global scenario_start, scenario_sql, previous, last_sql, last_context
    command = original_review(server, *args, **kw)
    if not meta:
        meta.update(branch=server.native_task_branch, command=command)
        backup(db, a.root / "start.db")
        (a.root / "input.json").write_text(json.dumps(meta, indent=2))
        scenario_start = previous = time.perf_counter()
        scenario_sql = last_sql = sql.copy()
        last_context = len(contexts)
    return command


case.reviewed = reviewed
if a.input:
    initial = json.loads((a.input / "input.json").read_text())

    def setup(server, *args, **kw):
        return server.app.state.runtime.repository, None

    case.setup = setup
    tour.create_edition = lambda *args, **kw: None
    fork_module.fork = lambda *args, **kw: {"branch_id": initial["branch"]}
original_wait = case.wait
previous = time.perf_counter()
last_sql = Counter()
last_context = 0
snapshots = set()


def wait(server, *args, **kw):
    global previous, last_sql, last_context
    task = original_wait(server, *args, **kw)
    now = time.perf_counter()
    week = task["current_week"]
    row = {
        "week": week,
        "state": task["state"],
        "checkpoint": task["checkpoint"],
        "seconds": now - previous,
        "sql": dict(sql - last_sql),
        "native_context_seconds": sum(contexts[last_context:]),
        "native_context_calls": len(contexts) - last_context,
        "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    with sqlite3.connect(db) as c:
        row["history"] = dict(
            zip(
                ("revisions", "payload_bytes"),
                c.execute(
                    "select count(*),sum(length(cast(payload_json as blob))) from branch_saved_revisions"
                ).fetchone(),
            )
        )
    rows.append(row)
    (a.root / "steps.json").write_text(json.dumps(rows, indent=2))
    print("MEASURE", json.dumps(row), flush=True)
    if (
        week["season_index"] == 0
        and week["week"] in {3, a.weeks // 2, a.weeks - 2}
        and week["week"] not in snapshots
    ):
        backup(db, a.root / f"week-{week['week']}.db")
        snapshots.add(week["week"])
    previous = time.perf_counter()
    last_sql = sql.copy()
    last_context = len(contexts)
    return task


case.wait = wait
start = time.perf_counter()
passed = False
try:
    clock = {
        52: RunCalendar(52, 51, 2030, 2),
        61: RunCalendar(61, 37, 2000, 2),
        80: RunCalendar(80, 80, 2100, 2),
    }[a.weeks]
    case.test_native_task_actual_match_points_all_weeks_and_real_season_rollover(
        a.root, clock
    )
    passed = True
finally:
    report = {
        "passed": passed,
        "total_seconds_including_fixture": time.perf_counter() - start,
        "execution_seconds_after_review": time.perf_counter() - scenario_start
        if scenario_start
        else None,
        "sql": dict(sql),
        "execution_sql": dict(sql - scenario_sql) if scenario_sql is not None else None,
        "native_context_calls": len(contexts),
        "native_context_seconds": sum(contexts),
        "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "task_read_cost": read_cost,
        "task_heartbeat_cost": heartbeat_cost,
        "python": sys.version,
        "platform": platform.platform(),
        "git_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
    }
    (a.root / "report.json").write_text(json.dumps(report, indent=2))
    print("REPORT", json.dumps(report), flush=True)
    if meta:
        # Compare all sport-bearing Saved facts. Generated Save/audit identities
        # and their review fingerprints differ between executions. Journal and
        # Tour receipt equality/replay remain checked by the original acceptance;
        # these digests separately compare every retained sporting state/history.
        sports = []
        with sqlite3.connect(db) as connection:
            for sequence, payload in connection.execute(
                "select sequence,payload_json from branch_saved_revisions where branch_id=? order by sequence",
                (meta["branch"],),
            ):
                state = json.loads(payload)["content"]["native_fork_runtime"]["state"]
                del state["journal"]
                state["tour"].pop("receipts", None)
                raw = json.dumps(
                    state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                sports.append(
                    {
                        "sequence": sequence,
                        "sporting_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                    }
                )
        (a.root / "sporting-history.json").write_text(json.dumps(sports, indent=2))
