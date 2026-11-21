#!/usr/bin/env python3
"""Real HTTP/SQLite continuation of the retained 1,000-player Saved v2 W9 fixture.

Diagnostic benchmark for PR review, never a normal pytest test.

    python scripts/w10_continuation_benchmark.py --checkout TREE \\
        --fixture before-restart.sqlite --meta before-restart.json \\
        --out OUTDIR --weeks 10 [--weeks 11 ...] [--deterministic-ids]

TREE is the engine checkout under test (its ``src`` and ``tests`` are used).
The fixture is copied to OUTDIR/run.sqlite first and never opened for writing.
Each week runs exactly the giant runner's sequence
(``scripts/giant_native_five_season_load.py``, compatible profile, season 0):
plan the Editions of week+2, submit/approve/draw/slots/confirm the week's
Editions, then the Week Transition, each followed by its explicit Tour Save.

Every request keeps the production 120-second client deadline. A client
timeout stops the run; the server's completion of that request is awaited and
the actual SQLite HEAD is recorded (a write after the deadline is a timeout).
``--deterministic-ids`` replaces only the random persistence UUIDs (revision,
audit and draft IDs) by a fixed sequence so two trees can be compared byte by
byte; the simulation RNG never uses them directly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from contextlib import closing
from pathlib import Path

PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument("--checkout", type=Path, required=True)
PARSER.add_argument("--fixture", type=Path, required=True)
PARSER.add_argument("--meta", type=Path, required=True)
PARSER.add_argument("--out", type=Path, required=True)
PARSER.add_argument("--start-db", type=Path, help="continue from a previous OUTDIR/run.sqlite")
PARSER.add_argument("--weeks", type=int, action="append", required=True)
PARSER.add_argument("--client-timeout", type=float, default=120.0)
PARSER.add_argument("--first-inspect-timeout", type=float, default=None,
                    help="measure the cold first GET past the deadline; it is still reported against --client-timeout")
PARSER.add_argument("--deterministic-ids", action="store_true")
PARSER.add_argument("--id-offset", type=int, default=0, help="first deterministic ID index (continuations)")
ARGS = PARSER.parse_args()

CHECKOUT = ARGS.checkout.resolve()
HERE = Path(__file__).resolve().parent
OUT = ARGS.out.resolve()
OUT.mkdir(parents=True, exist_ok=True)
DATABASE = OUT / "run.sqlite"
LOG = OUT / "requests.jsonl"
STARTED = time.perf_counter()
STATE = {"save_index": 0, "request_index": 0, "phase": "start", "in_flight": 0,
         "last_confirmed": None, "revisions": None}
LOCK = threading.Lock()


def initial_professionals(database: Path):
    """Computed in a separate process so the measured process starts cold."""
    code = (
        "import json,shutil,sys,tempfile;from pathlib import Path;"
        "sys.path[:0]=[sys.argv[1]+'/src'];"
        "from beta_engine.api.deps import build_runtime;"
        "d=tempfile.mkdtemp();db=Path(d)/'c.sqlite';shutil.copyfile(sys.argv[2],db);"
        "w=build_runtime(database_url=f'sqlite:///{db}').repository.get_initial_world(run_id='run',branch_id='branch');"
        "p=sorted(w.initial_turn_pro.professional_player_ids) if w.lifecycle_policy.requires_turn_pro "
        "else sorted(x.player_id for x in w.players);print(json.dumps(p))"
    )
    out = subprocess.run([sys.executable, "-c", code, str(CHECKOUT), str(database)],
                         capture_output=True, text=True, check=True).stdout
    return tuple(json.loads(out.strip().splitlines()[-1]))


SOURCE = ARGS.start_db or ARGS.fixture
shutil.copyfile(SOURCE, DATABASE)
PROS = initial_professionals(DATABASE)

sys.path[:0] = [str(CHECKOUT / "src"), str(CHECKOUT), str(HERE)]
import uvicorn  # noqa: E402
from urllib import request as urlrequest  # noqa: E402
from urllib.parse import urlsplit  # noqa: E402

from beta_engine.main import create_app  # noqa: E402
import giant_native_five_season_load as giant  # noqa: E402

if ARGS.deterministic_ids:
    import itertools
    import uuid

    import beta_engine.api.deps as deps

    _ids = itertools.count(ARGS.id_offset)
    deps.uuid4 = lambda: uuid.UUID(hashlib.sha256(f"w10-id-{next(_ids)}".encode()).hexdigest()[:32])


def rss_mib():
    with open("/proc/self/status") as stream:
        for line in stream:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def emit(kind, **fields):
    record = {"kind": kind, "t": round(time.perf_counter() - STARTED, 3), "rss_mib": round(rss_mib(), 1),
              "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
              "revisions": STATE["revisions"], **fields}
    with LOCK, LOG.open("a") as stream:
        stream.write(json.dumps(record, default=str) + "\n")
    print("W10 " + json.dumps(record, default=str), flush=True)


def head_and_count():
    with closing(sqlite3.connect(DATABASE.as_uri() + "?mode=ro", uri=True, timeout=600)) as c:
        head = c.execute("SELECT saved_head_revision_id FROM run_branches "
                         "WHERE run_id='run' AND branch_id='branch'").fetchone()[0]
        count = c.execute("SELECT COUNT(*) FROM branch_saved_revisions WHERE run_id='run'").fetchone()[0]
    return head, count


class Timing:
    """ASGI wrapper: server-side duration and completion of every request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        number = dict(scope.get("headers") or []).get(b"x-w10-request")
        status = {}

        async def tracking_send(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        with LOCK:
            STATE["in_flight"] += 1
        started = time.perf_counter()
        try:
            await self.app(scope, receive, tracking_send)
        finally:
            with LOCK:
                STATE["in_flight"] -= 1
            emit("server", request=int(number) if number else None, method=scope["method"],
                 path=scope["path"], status=status.get("code"),
                 server_seconds=round(time.perf_counter() - started, 3))


ORIGINAL = urlrequest.urlopen


class Server:
    def __init__(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(database_url=f"sqlite:///{DATABASE}")
        self.server = uvicorn.Server(uvicorn.Config(app=Timing(app), host="127.0.0.1", port=self.port,
                                                    log_level="error", lifespan="on"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with ORIGINAL(self.base_url + "/health", timeout=5):
                    return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=30)


class StopRun(Exception):
    pass


def timed_urlopen(req, *args, **kwargs):
    """The production transport and deadline; adds only a number and timing."""
    if not hasattr(req, "full_url"):
        return ORIGINAL(req, *args, **kwargs)
    cold_first = STATE["phase"] == "cold-inspect" and ARGS.first_inspect_timeout
    kwargs["timeout"] = ARGS.first_inspect_timeout if cold_first else ARGS.client_timeout
    path = urlsplit(req.full_url).path
    method = req.get_method()
    with LOCK:
        STATE["request_index"] += 1
        number = STATE["request_index"]
    is_save = method == "POST" and path.endswith("/save")
    if is_save:
        STATE["save_index"] += 1
    req.add_header("x-w10-request", str(number))
    started = time.perf_counter()
    status, error = None, None
    try:
        response = ORIGINAL(req, *args, **kwargs)
        status = response.status
        return response
    except BaseException as exc:
        status, error = getattr(exc, "code", None), f"{type(exc).__name__}: {exc}"
        raise
    finally:
        emit("client", request=number, phase=STATE["phase"], method=method, path=path,
             save_index=STATE["save_index"] if is_save else None, status=status,
             client_seconds=round(time.perf_counter() - started, 3), error=error,
             over_client_deadline=(time.perf_counter() - started) > ARGS.client_timeout)
        if is_save and status == 201:
            head, count = head_and_count()
            STATE["revisions"] = count
            STATE["last_confirmed"] = {"save_index": STATE["save_index"], "request": number,
                                       "phase": STATE["phase"], "head": head, "revisions": count}
            emit("save_confirmed", **STATE["last_confirmed"])


def history_digest():
    with closing(sqlite3.connect(DATABASE.as_uri() + "?mode=ro", uri=True)) as c:
        rows = c.execute("SELECT revision_id, parent_revision_id, sequence, content_hash, kind, payload_json, "
                         "change_summary_json FROM branch_saved_revisions WHERE run_id='run' "
                         "ORDER BY sequence").fetchall()
        nodes = hashlib.sha256()
        count = 0
        for row in c.execute("SELECT run_id, digest, body FROM saved_revision_nodes ORDER BY run_id, digest"):
            nodes.update(json.dumps(row).encode())
            count += 1
    return {"revisions": [[r[0], r[1], r[2], r[3], r[4], hashlib.sha256(r[5].encode()).hexdigest(),
                           hashlib.sha256(r[6].encode()).hexdigest()] for r in rows],
            "node_count": count, "node_table_sha256": nodes.hexdigest()}


def run_week(server, week, schedule, inspect, execute, command, save_tour):
    for event in (e for e in schedule if (e.season, e.week - 2) == (0, week)):
        STATE["phase"] = f"w{week}:plan:{event.edition_id}"
        giant._plan_edition(server, event)
    play = tuple(e for e in schedule if (e.season, e.week) == (0, week))
    if play:
        STATE["phase"] = f"w{week}:play"
        giant._play_week(server, play, PROS)
    STATE["phase"] = f"w{week}:transition"
    execute(server, command(inspect(server), "transition", name=f"load-s1-week-{week}-transition"))
    save_tour(server)


def main():
    meta = json.loads(ARGS.meta.read_text())
    digest = hashlib.sha256(DATABASE.read_bytes()).hexdigest()
    if ARGS.start_db is None and digest != meta["sha256"]:
        raise SystemExit("fixture digest mismatch")
    tree = subprocess.run(["git", "-C", str(CHECKOUT), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    before = history_digest()
    STATE["revisions"] = len(before["revisions"])
    emit("start", checkout=str(CHECKOUT), head=tree, source=str(SOURCE), source_sha256=digest,
         weeks=ARGS.weeks, client_timeout=ARGS.client_timeout, python=sys.version.split()[0])
    urlrequest.urlopen = timed_urlopen
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour

    schedule = giant.make_schedule(1, 60, profile="compatible")
    outcome, failure, final = "complete", None, None
    with Server() as server:
        try:
            STATE["phase"] = "cold-inspect"
            view = inspect(server)
            if ARGS.start_db is None:
                emit("cold_inspection", exact_expected=view == meta["expected_inspection"])
            for week in ARGS.weeks:
                week_started = time.perf_counter()
                run_week(server, week, schedule, inspect, execute, command, save_tour)
                emit("week_completed", week=week, seconds=round(time.perf_counter() - week_started, 1))
            STATE["phase"] = "final-inspect"
            final = inspect(server)
        except BaseException as exc:
            outcome = "failed"
            failure = {"error": f"{type(exc).__name__}: {exc}", "phase": STATE["phase"],
                       "traceback": traceback.format_exc()}
            emit("failure", **failure)
            deadline = time.time() + 3600
            while STATE["in_flight"] and time.time() < deadline:
                time.sleep(1)
            head, count = head_and_count()
            emit("after_abandoned_request", in_flight=STATE["in_flight"], head=head, revisions_now=count)
    # The run is over: fold the WAL into the main file so the database can be
    # copied as one file for a later cold-read measurement (no logical change).
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    after = history_digest()
    prior = {r[0]: r for r in before["revisions"]}
    changed = [r[0] for r in after["revisions"] if r[0] in prior and prior[r[0]] != r]
    if final is not None:
        (OUT / "final-inspection.json").write_text(json.dumps(final, sort_keys=True) + "\n")
        (OUT / "final-meta.json").write_text(json.dumps({
            "sha256": hashlib.sha256(DATABASE.read_bytes()).hexdigest(),
            "expected_inspection": final}) + "\n")
    (OUT / "history.json").write_text(json.dumps(after) + "\n")
    summary = {"outcome": outcome, "failure": failure, "last_confirmed": STATE["last_confirmed"],
               "saves": STATE["save_index"], "revisions_before": len(before["revisions"]),
               "revisions_after": len(after["revisions"]), "changed_prior_revisions": changed,
               "node_count": after["node_count"], "node_table_sha256": after["node_table_sha256"],
               "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
               "final_inspection_sha256": hashlib.sha256(json.dumps(final, sort_keys=True).encode()).hexdigest()
               if final is not None else None,
               "wall_seconds": round(time.perf_counter() - STARTED, 1), "engine_head": tree}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    emit("summary", **{k: v for k, v in summary.items() if k != "failure"})
    return 0 if outcome == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
