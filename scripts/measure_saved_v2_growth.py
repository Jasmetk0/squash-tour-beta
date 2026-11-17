"""Real HTTP/SQLite growth measurement: inline v1 versus Saved v2 storage.

One case builds a NEW Run (storage fixed at creation) and plays the authentic
native workload of ``tests/api/test_native_season_archive_wide.py`` for one
fixed clock: population, health, real MatchEngine opening match, two overlapping
Tour Editions with real matches, confirmed results, then every Week Transition to
season end, each followed by an explicit Save. Every request is timed (wall and
process CPU). After every Save the physical SQLite main file and WAL sizes are
recorded. Finally a fresh process restarts on the result: cold and warm GET, with
full equality against the pre-restart inspection.

Entity IDs are deterministic (uuid4 replaced by a counter in this process only),
so v1 and v2 cases of the same parameters must produce identical Saved IDs,
content hashes and inspection; ``compare`` checks that from the outputs.

Run cases sequentially (never overlapping) in A-B-B-A order, for example::

    python scripts/measure_saved_v2_growth.py case --storage v1 --players 1000 --width 12 --root work/g-a1
    python scripts/measure_saved_v2_growth.py case --storage saved_v2 ... --root work/g-b1
    python scripts/measure_saved_v2_growth.py case --storage saved_v2 ... --root work/g-b2
    python scripts/measure_saved_v2_growth.py case --storage v1 ... --root work/g-a2
    python scripts/measure_saved_v2_growth.py compare work/g-a1 work/g-b1 work/g-b2 work/g-a2
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import multiprocessing
import os
import platform
import resource
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests" / "api")]


def proc_status():
    values = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in ("VmRSS", "VmHWM"):
            values[key] = int(rest.split()[0])
    return values


def file_sizes(db):
    path = Path(db)
    wal = path.with_name(path.name + "-wal")
    return {"sqlite_bytes": path.stat().st_size, "wal_bytes": wal.stat().st_size if wal.exists() else 0}


def logical_summary(db):
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT revision_id, content_hash, LENGTH(payload_json) FROM branch_saved_revisions "
                           "ORDER BY revision_id").fetchall()
        tables = {name for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        nodes = con.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(body)),0) FROM saved_revision_nodes").fetchone() \
            if "saved_revision_nodes" in tables else (0, 0)
        page = con.execute("PRAGMA page_size").fetchone()[0]
        pages = con.execute("PRAGMA page_count").fetchone()[0]
    finally:
        con.close()
    digest = hashlib.sha256(json.dumps([r[:2] for r in rows]).encode()).hexdigest()
    return {"revisions": len(rows), "identity_hash_digest": digest,
            "stored_payload_column_bytes": sum(r[2] for r in rows),
            "nodes": nodes[0], "node_body_bytes": nodes[1], "page_size": page, "page_count": pages}


def environment(storage):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    return {"git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
            "source_dirty": bool(git("status", "--porcelain", "--", "src")),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "storage": storage}


def case(args):
    os.environ["BETA_ENGINE_NEW_RUN_SAVED_STORAGE"] = args.storage
    import beta_engine.api.deps as deps

    counter = itertools.count(1)
    deps.uuid4 = lambda: SimpleNamespace(hex=f"{next(counter):032x}")
    from tests.api import test_calendar_tour_flow as flow
    from tests.api.test_calendar_global_slots import ready
    from tests.api.test_native_season_archive_wide import play_season_editions, run_to_season_end
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=False)
    db = root / "run.db"
    rows = []
    log = (root / "requests.jsonl").open("w")
    original_request = _request
    current = {"op": "prepare"}

    def timed(method, url, payload=None):
        wall, cpu = time.perf_counter(), time.process_time()
        code, body = original_request(method, url, payload)
        row = {"op": current["op"], "method": method, "path": url.split("/calendar-tour")[-1][:60] if
               "/calendar-tour" in url else url.split(":", 2)[-1][5:70],
               "status": code, "wall_s": round(time.perf_counter() - wall, 4),
               "cpu_s": round(time.process_time() - cpu, 4), **proc_status()}
        if method == "POST" and url.endswith("/save"):
            row.update(file_sizes(db))
        rows.append(row)
        log.write(json.dumps(row) + "\n")
        log.flush()
        return code, body

    # Patch every helper module that imported _request by name.
    import tests.api.test_saved_revision_history_api as history_api
    for module in list(sys.modules.values()):
        if getattr(module, "__name__", "").startswith("tests.") and getattr(module, "_request", None) is original_request:
            module._request = timed
    history_api._request = timed

    started = time.perf_counter()
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        current["op"] = "ready"
        ready(server, args.width, population=args.players)
        current["op"] = "editions"
        play_season_editions(server, ("parallel-a", "parallel-b"))
        current["op"] = "weeks"
        if args.weeks:
            for week in range(5, 5 + args.weeks):
                view = flow.inspect(server)
                flow.execute(server, flow.command(view, "transition", name=f"measured-w{week}"))
                flow.save_tour(server)
        else:
            run_to_season_end(server, args.width)
        current["op"] = "final"
        expected = flow.inspect(server)
    log.close()
    (root / "expected.json").write_text(json.dumps(expected, sort_keys=True))
    summary = {"environment": environment(args.storage), "args": vars(args),
               "build_wall_s": round(time.perf_counter() - started, 3),
               "build_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "files": file_sizes(db), "logical": logical_summary(db)}
    child = multiprocessing.get_context("spawn").Process(target=restart, args=(str(root), args.storage))
    child.start()
    child.join()
    if child.exitcode:
        raise SystemExit(f"restart failed: {child.exitcode}")
    summary["restart"] = json.loads((root / "restart.json").read_text())
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("build_wall_s", "build_peak_rss_kib", "files", "logical")}))


def restart(root, storage):
    sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests" / "api")]
    os.environ["BETA_ENGINE_NEW_RUN_SAVED_STORAGE"] = storage
    from tests.api.test_calendar_tour_flow import tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    root = Path(root)
    expected = json.loads((root / "expected.json").read_text())
    result = {}
    with ApiServer(database_url=f"sqlite:///{root / 'run.db'}") as server:
        for label in ("cold_get", "warm_get"):
            wall, cpu = time.perf_counter(), time.process_time()
            code, view = _request("GET", tour_url(server))
            result[label] = {"status": code, "wall_s": round(time.perf_counter() - wall, 3),
                             "cpu_s": round(time.process_time() - cpu, 3), **proc_status()}
            assert code == 200, view
            assert json.loads(json.dumps(view, sort_keys=True)) == expected, "restart inspection differs"
    result["equal_to_pre_restart"] = True
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    (root / "restart.json").write_text(json.dumps(result, indent=2))


def compare(args):
    cases = []
    for name in args.roots:
        root = Path(name)
        summary = json.loads((root / "summary.json").read_text())
        requests = [json.loads(line) for line in (root / "requests.jsonl").read_text().splitlines()]
        saves = [r for r in requests if r["method"] == "POST" and r["path"].endswith("/save")]
        cases.append((root.name, summary, requests, saves))
    identities = {c[1]["logical"]["identity_hash_digest"] for c in cases}
    expected = {hashlib.sha256((Path(name) / "expected.json").read_bytes()).hexdigest() for name in args.roots}
    report = {"identical_saved_ids_and_hashes": len(identities) == 1,
              "identical_final_inspection": len(expected) == 1, "cases": []}
    for name, summary, requests, saves in cases:
        report["cases"].append({
            "case": name, "storage": summary["environment"]["storage"],
            "git_sha": summary["environment"]["git_sha"], "dirty": summary["environment"]["source_dirty"],
            "build_wall_s": summary["build_wall_s"],
            "request_wall_s": round(sum(r["wall_s"] for r in requests), 3),
            "request_cpu_s": round(sum(r["cpu_s"] for r in requests), 3),
            "save_count": len(saves), "save_wall_s": round(sum(r["wall_s"] for r in saves), 3),
            "last5_save_wall_s": [r["wall_s"] for r in saves[-5:]],
            "get_wall_s": round(sum(r["wall_s"] for r in requests if r["method"] == "GET"), 3),
            "final_sqlite_bytes": summary["files"]["sqlite_bytes"], "final_wal_bytes": summary["files"]["wal_bytes"],
            "sqlite_after_each_save": [r["sqlite_bytes"] for r in saves],
            "build_peak_rss_kib": summary["build_peak_rss_kib"],
            "restart": summary["restart"], "logical": summary["logical"],
        })
    print(json.dumps(report, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("case")
    c.add_argument("--storage", choices=("v1", "saved_v2"), required=True)
    c.add_argument("--players", type=int, default=8)
    c.add_argument("--width", type=int, default=12)
    c.add_argument("--weeks", type=int, default=0, help="Week Transitions after the Editions (0 = to season end)")
    c.add_argument("--root", required=True)
    m = sub.add_parser("compare")
    m.add_argument("roots", nargs="+")
    args = parser.parse_args(argv)
    case(args) if args.command == "case" else compare(args)


if __name__ == "__main__":
    main()
