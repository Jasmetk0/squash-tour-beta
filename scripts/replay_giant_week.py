"""Replay one real week of the giant five-season load on an existing snapshot.

Input is a verified on-line backup from the giant workflow (``after-WNN.sqlite``
with its ``manifest.jsonl``: SHA-256, Saved HEAD, position). The week that
follows the snapshot is replayed with exactly the pinned harness functions
(``giant_native_five_season_load.py`` at 51dbde8): plan the Editions two weeks
ahead (create-edition + Save each), submit/approve/draw + Save per Edition, every
shared ``next-slot`` + Save, ``confirm-result`` + Save per Edition, then the
week ``transition`` + Save. Real uvicorn HTTP + SQLite, one server process.

Each HTTP call is timed (wall to headers, process CPU, RSS); SQLite
``BEGIN IMMEDIATE``..commit/rollback (writer lock) is clocked by engine
listeners; a sampler records the peak RSS of the whole process group and the
largest DB+WAL size. The digest covers the final inspection, the complete live
sporting checkpoint and the Saved revision history, so A and B must produce
identical bytes (random Saved ids are normalized by order).

    python scripts/replay_giant_week.py --root <tree> --harness work/giant_harness.py \\
        --input snap/after-W12.sqlite --sha256 32d1dea... --workers 0 --out work/w13-A.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from pathlib import Path


def _use(root):
    root = Path(root).resolve()
    sys.path[:0] = [str(root / "src"), str(root)]
    os.chdir(root)
    return root


class GroupSampler:
    """Peak RSS of this process plus all descendants, and DB+WAL size."""

    def __init__(self, database):
        self.database = Path(database)
        self.peak_group = self.peak_parent = self.peak_db = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _rss(self, pid):
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except OSError:
            pass
        return 0

    def _children(self, pid):
        try:
            return [int(c) for c in Path(f"/proc/{pid}/task/{pid}/children").read_text().split()]
        except OSError:
            return []

    def _sample(self):
        me = os.getpid()
        pending, total = [me], 0
        while pending:
            pid = pending.pop()
            total += self._rss(pid)
            pending.extend(self._children(pid))
        self.peak_group = max(self.peak_group, total)
        self.peak_parent = max(self.peak_parent, self._rss(me))
        size = sum(p.stat().st_size for p in (self.database, Path(str(self.database) + "-wal")) if p.exists())
        self.peak_db = max(self.peak_db, size)

    def _run(self):
        while not self._stop.wait(0.05):
            self._sample()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self._sample()


def _io():
    values = {}
    for line in Path("/proc/self/io").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("rchar", "wchar", "read_bytes", "write_bytes"):
            values[key] = int(value)
    return values


def _children_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _observe_http(rows, clock):
    from urllib import request
    from urllib.parse import urlsplit

    original = request.urlopen

    def observed(req, *args, **kwargs):
        target = req.full_url if hasattr(req, "full_url") else str(req)
        endpoint = urlsplit(target).path
        method = req.get_method() if hasattr(req, "get_method") else "GET"
        cpu, wall = time.process_time(), time.perf_counter()
        lock_before = clock["held"]
        status = None
        try:
            response = original(req, *args, **kwargs)
            status = getattr(response, "status", None)
            return response
        except Exception as error:
            status = getattr(error, "code", None)
            raise
        finally:
            tail = endpoint.rsplit("/", 1)[-1]
            phase = {"preview": "Preview", "execute": "Execute", "save": "Save"}.get(
                tail, "GET" if method == "GET" else "other")
            rows.append({"method": method, "endpoint": endpoint, "phase": phase, "status": status,
                         "wall_s": time.perf_counter() - wall,
                         "process_cpu_s": time.process_time() - cpu,
                         "writer_lock_s": clock["held"] - lock_before})

    request.urlopen = observed
    return lambda: setattr(request, "urlopen", original)


def _lock_clock(engine, clock):
    from sqlalchemy import event

    starts = {}

    @event.listens_for(engine, "before_cursor_execute")
    def before(conn, cursor, statement, *args):
        if statement.strip().upper().startswith("BEGIN IMMEDIATE"):
            starts[id(conn.connection.dbapi_connection)] = time.perf_counter()

    def end(conn):
        start = starts.pop(id(conn.connection.dbapi_connection), None)
        if start is not None:
            held = time.perf_counter() - start
            clock["held"] += held
            clock["max"] = max(clock["max"], held)
            clock["count"] += 1

    event.listen(engine, "commit", end)
    event.listen(engine, "rollback", end)


def _week_plan(harness, position):
    schedule = harness["make_schedule"](5, 60, profile="compatible")
    by_play, by_plan = defaultdict(list), defaultdict(list)
    for event in schedule:
        by_play[(event.season, event.week)].append(event)
        by_plan[(event.season, event.week - 2)].append(event)
    key = (position["season_index"], position["week"])
    return tuple(by_plan[key]), tuple(by_play[key])


def replay(args, database):
    import runpy

    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    harness = runpy.run_path(str(Path(args.harness).resolve()), run_name="giant_week_replay")
    # Deterministic NEW product ids (Saved revisions, audit events, safety
    # checkpoints) so that values hashed over them are comparable between
    # trees; ids already stored in the snapshot are unchanged.
    import itertools
    import uuid

    from beta_engine.api import deps
    sequence = itertools.count()
    deps.uuid4 = lambda: uuid.uuid5(uuid.NAMESPACE_URL, f"giant-week-replay:{next(sequence)}")
    rows, clock = [], {"held": 0.0, "max": 0.0, "count": 0}
    cold = {}
    try:
        with GroupSampler(database) as sampler, ApiServer(database_url=f"sqlite:///{database}") as server:
            repository = server.app.state.runtime.repository
            _lock_clock(repository._engine, clock)
            # The giant run never restarts inside a week: open the snapshot
            # (cold strict verification of the whole lineage) once, outside the
            # measured week and without the 120 s client limit.
            from urllib import request as urllib_request
            t, c = time.perf_counter(), time.process_time()
            with urllib_request.urlopen(server.base_url + "/admin/runs/run/branches/branch/calendar-tour",
                                        timeout=7200) as response:
                assert response.status == 200
            cold = {"first_get_s": time.perf_counter() - t, "first_get_cpu_s": time.process_time() - c,
                    "writer_lock_s": clock["held"]}
            clock.update(held=0.0, max=0.0, count=0)
            restore = _observe_http(rows, clock)
            io_before = _io()
            started_children = _children_cpu()
            cpu0, wall0 = time.process_time(), time.perf_counter()
            view = inspect(server)
            position = view["state"]["week"]
            plan, play = _week_plan(harness, position)
            world = repository.get_initial_world(run_id="run", branch_id="branch")
            if world.lifecycle_policy.requires_turn_pro:
                pros = tuple(sorted(world.initial_turn_pro.professional_player_ids))
            else:
                pros = tuple(sorted(p.player_id for p in world.players))
            phases = {}
            t = time.perf_counter()
            for event in plan:
                harness["_plan_edition"](server, event)
            phases["plan"] = time.perf_counter() - t
            t = time.perf_counter()
            completed = harness["_play_week"](server, play, pros) if play else []
            phases["play"] = time.perf_counter() - t
            t = time.perf_counter()
            action = "transition" if position["week"] < harness["WEEKS_PER_SEASON"] else "season-transition"
            execute(server, command(inspect(server), action,
                                    name=f"load-s{position['season_index'] + 1}-week-{position['week']}-{action}"))
            save_tour(server)
            phases["transition"] = time.perf_counter() - t
            final = inspect(server)
            code, history = _request("GET", server.base_url + "/run-containers/run/branches/branch/saved-revisions")
            assert code == 200, history
            from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
            with repository._session_factory() as session:
                checkpoint = load_checkpoint(session, run_id="run", branch_id="branch").model_dump(mode="json")
            wall, cpu = time.perf_counter() - wall0, time.process_time() - cpu0
            io_after = _io()
            try:
                from beta_engine.infrastructure.db import checkpoint_part_decode
                part_stats = checkpoint_part_decode.stats()
            except ImportError:
                part_stats = None
            restore()
    finally:
        from urllib import request as urllib_request
        if getattr(urllib_request.urlopen, "__name__", "") == "observed":
            restore()
    return {"cold_open": cold, "io": {k: io_after[k] - io_before[k] for k in io_after},
            "part_decode": part_stats,
        "position": position, "plan_editions": [e.edition_id for e in plan],
        "played_editions": [e.edition_id for e in play],
        "matches": sum(item["match_count"] for item in completed),
        "slots": max((item["slots_in_week"] for item in completed), default=0),
        "wall_s": wall, "parent_cpu_s": cpu, "children_cpu_s": _children_cpu() - started_children,
        "phases_s": phases, "requests": rows, "writer_lock": clock,
        "peak_group_rss_mib": sampler.peak_group / 2 ** 20,
        "peak_parent_rss_mib": sampler.peak_parent / 2 ** 20,
        "peak_db_wal_bytes": sampler.peak_db,
        "digests": _digests(final, checkpoint, history, dump=getattr(args, "dump", None)),
    }


def _digests(final, checkpoint, history, dump=None):
    import re
    order = {}
    pattern = re.compile(r"saved-revision-[0-9a-f]{32}|safety-checkpoint-[0-9a-f]{32}")

    def norm(value):
        text = pattern.sub(lambda m: "saved-#%d" % order.setdefault(m.group(), len(order)),
                           json.dumps(value, sort_keys=True))
        drop = {"tour_fingerprint", "save_projection_fingerprint"}

        def strip(node):
            if isinstance(node, dict):
                return {k: strip(v) for k, v in node.items() if k not in drop and not k.endswith("_at")}
            if isinstance(node, list):
                return [strip(v) for v in node]
            return node
        return strip(json.loads(text))

    def digest(value):
        return hashlib.sha256(json.dumps(norm(value), sort_keys=True).encode()).hexdigest()

    if dump:
        import gzip
        with gzip.open(dump, "wt") as stream:
            json.dump({"inspection": norm(final), "checkpoint": norm(checkpoint), "history": norm(history)},
                      stream, sort_keys=True)
        order.clear()
    return {"inspection": digest(final), "checkpoint": digest(checkpoint),
            "saved_history": digest(history), "all": digest([final, checkpoint, history])}


def summarize(rows):
    by_phase = defaultdict(list)
    for row in rows:
        by_phase[row["phase"]].append(row)
    out = {}
    for phase, items in sorted(by_phase.items()):
        walls = sorted(r["wall_s"] for r in items)
        out[phase] = {"count": len(items), "total_s": round(sum(walls), 2),
                      "p50_s": round(statistics.median(walls), 3),
                      "p95_s": round(walls[min(len(walls) - 1, int(0.95 * len(walls)))], 3),
                      "max_s": round(walls[-1], 3),
                      "cpu_s": round(sum(r["process_cpu_s"] for r in items), 2),
                      "writer_lock_s": round(sum(r["writer_lock_s"] for r in items), 2)}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--harness", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--workers", default="0")
    parser.add_argument("--scratch", help="directory for the working copy (default: temp)")
    parser.add_argument("--dump", help="write the normalized final values (gzip JSON) here")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    source, out = Path(args.input).resolve(), Path(args.out).resolve()
    with source.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    assert actual == args.sha256, f"input SHA-256 {actual} != {args.sha256}"
    root = _use(args.root)
    os.environ["BETA_ENGINE_MATCH_WORKERS"] = args.workers
    with tempfile.TemporaryDirectory(dir=args.scratch) as tmp:
        database = Path(tmp) / "week.db"
        with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as a, sqlite3.connect(database) as b:
            a.backup(b)
        result = replay(args, database)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD:src"], capture_output=True, text=True).stdout.strip()
    import beta_engine
    assert Path(beta_engine.__file__).resolve().is_relative_to(root), beta_engine.__file__
    result.update(input_sha256=actual, root_head=head, src_tree=tree, workers=args.workers,
                  python=sys.version.split()[0], cpu_count=os.cpu_count(),
                  pythonhashseed=os.environ.get("PYTHONHASHSEED"), summary=summarize(result["requests"]))
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("wall_s", "parent_cpu_s", "children_cpu_s", "matches",
                                             "peak_group_rss_mib", "digests")}))


if __name__ == "__main__":
    shutil.os.environ.setdefault("PYTHONHASHSEED", "0")
    main()
