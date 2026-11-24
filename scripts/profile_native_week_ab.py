"""One real native Tour week, two immutable commits, isolated processes.

Linux, Python 3.11+, installed project/test dependencies, clean committed Git
trees. Run this driver from the diagnostic branch, not from either candidate.
Use prepare once, then ab with the emitted SHA. No multi-season task is started.
Timings include identical fetch instrumentation; history verification is separate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import sqlite3
from statistics import median
import subprocess
import sys
import tempfile
import time
from uuid import NAMESPACE_URL, uuid5
from itertools import count

SCRIPT = Path(__file__).resolve()
METRICS = SCRIPT.with_name("profile_native_full_simulation_metrics.py")
W12_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"
SCHEMA = 2
PLANS = {
    "w6": [("play", "ab-cup"), ("confirm-result", "ab-cup"), ("transition", None)],
    "w12-1822": [("transition", None)],
}
SEED = 231


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def exact_commit(value):
    require(re.fullmatch(r"[0-9a-f]{40}", value) is not None,
            "Use full lowercase 40-character commit SHA, not a moving ref")
    require(git("rev-parse", value + "^{commit}") == value, "Unknown commit")
    return value


def sidecar(path, suffix):
    return path.with_name(path.name + suffix)


def physical(path):
    # WAL can disappear between stat calls when SQLite checkpoints/closes it.
    try:
        wal = sidecar(path, "-wal").stat().st_size
    except FileNotFoundError:
        wal = 0
    return {"db_bytes": path.stat().st_size, "wal_bytes": wal}


def copy_fixture(source, target, expected):
    require(source.is_file() and not target.exists(), "Need immutable source and fresh target")
    require(not sidecar(source, "-wal").exists() and not sidecar(source, "-shm").exists(),
            "Fixture must be a closed, checkpointed standalone SQLite backup")
    require(file_sha(source) == expected, "Input SHA-256 mismatch")
    with source.open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst)
    require(not sidecar(source, "-wal").exists() and not sidecar(source, "-shm").exists(),
            "Fixture acquired SQLite sidecars while copying")
    require(file_sha(target) == expected and file_sha(source) == expected,
            "Fixture changed while copying")


def sql_stats(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as con:
        n, size = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))),0) "
            "FROM branch_saved_revisions"
        ).fetchone()
    return {**physical(path), "revisions": n, "stored_payload_column_bytes": size}


def target_imports():
    root = Path.cwd().resolve()
    sys.path[:0] = [str(root / "src"), str(root)]
    import beta_engine
    require(Path(beta_engine.__file__).resolve().is_relative_to(root / "src"),
            "Imported engine does not come from the requested checkout")
    from tests.api import test_calendar_tour_flow as flow
    from tests.api.test_saved_revision_history_api import ApiServer, _request
    require(Path(flow.__file__).resolve().is_relative_to(root / "tests"),
            "Imported test helper does not come from the requested checkout")
    return flow, ApiServer, _request


def metadata():
    require(not git("status", "--porcelain", "--untracked-files=no"),
            "Candidate checkout has tracked modifications")
    return {"commit": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
            "runner_sha256": file_sha(SCRIPT), "metrics_sha256": file_sha(METRICS),
            "python": sys.version, "platform": platform.platform(),
            "machine": platform.machine(), "cpu_count": os.cpu_count(),
            "dependencies": {name: importlib.metadata.version(name) for name in
                             ("fastapi", "pydantic", "sqlalchemy", "uvicorn", "pytest")},
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
            "new_run_storage": os.environ.get("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "v1")}


def history(repo):
    # Production repository verifies the reachable lineage, including v2
    # materialization. Compare whole logical payloads and change summaries,
    # not physical SQL wrappers. Only row creation time is excluded.
    value = repo.get_branch_saved_revision_history(run_id="run", branch_id="branch")
    return [{"sequence": x.sequence, "id": x.revision_id, "parent": x.parent_revision_id,
             "kind": x.kind, "schema": x.payload_schema_version,
             "content_hash": x.content_hash, "algorithm": x.content_hash_algorithm,
             "payload_sha256": digest(x.payload), "summary_sha256": digest(x.change_summary)}
            for x in value.saved_revisions]


def position(view):
    w = view["state"]["week"]
    return [w["season_index"], w["week"]]


def evidence(view):
    # Preserve array order, all result and ranking fields, and player state.
    editions = view["edition_evidence"]
    return {"position": position(view), "players": len(view["players"]),
            "players_sha256": digest(view["players"]),
            "editions_sha256": digest(view["state"]["editions"]),
            "matches_sha256": digest({k: v["matches"] for k, v in editions.items()}),
            "match_count": sum(len(v["matches"]) for v in editions.values()),
            "edition_evidence_sha256": digest(editions),
            "rankings_sha256": digest(view["state"]["rankings"]),
            "inspection_sha256": digest(view), "head": view["saved_head_revision_id"]}


def prepare(path):
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from tests.api.test_native_full_simulation_tasks import approve_draw
    flow, ApiServer, _ = target_imports()
    producer = metadata()
    require(not path.exists(), "Never overwrite a fixture")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        local = Path(temp) / "prepare.db"
        with ApiServer(database_url=f"sqlite:///{local}") as server:
            flow.setup(server, RunCalendar(6, 6, 2030, 2), count=8)
            flow.create_edition(server, "ab-cup", size=4)
            for week in (3, 4):
                flow.execute(server, flow.command(flow.inspect(server), "transition",
                                                   name=f"ab-prepare-{week}"))
                flow.save_tour(server)
            approve_draw(server, name="ab-cup")
            v = flow.inspect(server)
            require(v["saved"] and position(v) == [0, 4] and len(v["players"]) == 8,
                    "Unexpected W6 fixture")
            require("ab-cup" not in v["edition_evidence"] and
                    not v["state"]["editions"][0]["result_confirmed"],
                    "Fixture already played or completed")
            with closing(sqlite3.connect(local.as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(path)) as target:
                    source.backup(target)
                    require(target.execute("PRAGMA journal_mode=DELETE").fetchone() == ("delete",),
                            "Could not produce standalone SQLite backup")
    require(not sidecar(path, "-wal").exists() and not sidecar(path, "-shm").exists(),
            "Fixture unexpectedly has sidecars")
    print(json.dumps({"fixture": str(path), "sha256": file_sha(path),
                      "producer": producer, "position": [0, 4],
                      "players": 8, "seed": SEED, "physical": sql_stats(path)}, indent=2))


def expected_calls(scenario, mode):
    calls = ["initial_get"]
    for action, _ in PLANS[scenario]:
        calls += [action + ":preview", action + ":execute"]
        if mode == "retry" and action in {"play", "transition"}:
            calls += [action + ":retry"]
        calls += [action + ":draft_get", action + ":save", action + ":saved_get"]
    return calls


def worker(args):
    require(sys.platform.startswith("linux"), "RSS accounting requires Linux")
    require(args.scenario in PLANS, "Unknown scenario")
    require(args.scenario != "w12-1822" or args.sha256 == W12_SHA, "Wrong archived W12 hash")
    meta = metadata()
    require(meta["commit"] == args.commit, "Wrong checkout")
    db = args.database.resolve()
    require(file_sha(db) == args.sha256, "Wrong disposable copy")
    before = sql_stats(db)
    flow, ApiServer, request = target_imports()
    from beta_engine.api import deps
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    spec = importlib.util.spec_from_file_location("_ab_metrics", METRICS)
    metrics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metrics)
    fetched = metrics.measure_fetches(Engine)
    sql = Counter()

    def before_sql(conn, cursor, statement, parameters, context, many):
        context._ab_start = time.perf_counter()
        sql["count"] += 1

    def after_sql(conn, cursor, statement, parameters, context, many):
        sql["cursor_wall_s"] += time.perf_counter() - context._ab_start

    event.listen(Engine, "before_cursor_execute", before_sql)
    event.listen(Engine, "after_cursor_execute", after_sql)
    ids = count()
    original_uuid4 = deps.uuid4
    # Same ID factory as profile_native_cold_saved_read; never bypass a gate.
    deps.uuid4 = lambda: uuid5(NAMESPACE_URL, f"week-ab:{args.sha256}:{next(ids)}")
    rows = []
    report = {"schema": SCHEMA, "status": "failed", "metadata": meta,
              "input_sha256": args.sha256, "scenario": args.scenario, "seed": SEED,
              "mode": args.mode, "plan": PLANS[args.scenario], "before": before,
              "calls": rows}
    try:
        with ApiServer(database_url=f"sqlite:///{db}") as server:
            repo = server.app.state.runtime.repository
            url = flow.tour_url(server)

            def call(label, method, suffix="", payload=None, status=200):
                request_sha256 = digest(payload)
                sql_before, fetch_before = sql.copy(), fetched.copy()
                wall, cpu = time.perf_counter(), time.process_time()
                code = None
                try:
                    code, value = request(method, url + suffix, payload)
                    require(code == status, f"{label}: unexpected HTTP {code}")
                    return value
                finally:
                    rows.append({"label": label, "method": method, "status": code,
                                 "request_sha256": request_sha256,
                                 "wall_s": time.perf_counter() - wall,
                                 "cpu_s": time.process_time() - cpu,
                                 "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                 "sql_calls": sql["count"] - sql_before["count"],
                                 "sql_cursor_wall_s": sql["cursor_wall_s"] - sql_before["cursor_wall_s"],
                                 "fetch_rows": fetched["rows"] - fetch_before["rows"],
                                 "fetch_text_blob_bytes": fetched["text_blob_bytes"] - fetch_before["text_blob_bytes"],
                                 **physical(db)})

            started, cpu = time.perf_counter(), time.process_time()
            view = call("initial_get", "GET")
            require(view["saved"], "Input is not Saved")
            initial_position = position(view)
            initial_players = len(view["players"])
            if args.scenario == "w6":
                require(initial_position == [0, 4] and initial_players == 8
                        and view["state"]["week"]["calendar"]["weeks_per_year"] == 6,
                        "Unexpected W6 fixture position/players/calendar")
            else:
                require(initial_position == [1, 1] and initial_players == 256
                        and before["revisions"] == 46, "Unexpected archived W12 fixture")
            initial_evidence = evidence(view)
            report["initial_evidence"] = initial_evidence
            old_head = view["saved_head_revision_id"]
            for action, edition in PLANS[args.scenario]:
                cmd = flow.command(view, action, name="ab-week:" + action, edition_id=edition)
                cmd["seed"] = SEED
                preview = call(action + ":preview", "POST", "/preview", cmd)
                approved = {"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
                            "explicit_confirmation": True}
                executed = call(action + ":execute", "POST", "/execute", approved, 201)
                if args.mode == "retry" and action in {"play", "transition"}:
                    repeated = call(action + ":retry", "POST", "/execute", approved, 201)
                    require(repeated == executed, "Idempotent response changed")
                draft = call(action + ":draft_get", "GET")
                require(not draft["saved"], "Execution did not produce a Working Draft")
                receipt = call(action + ":save", "POST", "/save",
                               {"expected_draft_version": draft["draft_version"],
                                "expected_calendar_tour_fingerprint": draft["tour_fingerprint"]}, 201)
                view = call(action + ":saved_get", "GET")
                require(view["saved"] and view["saved_head_revision_id"] ==
                        receipt["saved_revision"]["revision_id"], "Save head not visible")
            report["elapsed_wall_s"] = time.perf_counter() - started
            report["wall_s"] = sum(row["wall_s"] for row in rows)
            report["elapsed_cpu_s"] = time.process_time() - cpu
            report["cpu_s"] = sum(row["cpu_s"] for row in rows)
            report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report["after"] = sql_stats(db)
            require([x["label"] for x in rows] == expected_calls(args.scenario, args.mode),
                    "Unexpected request sequence")
            require(position(view) == [initial_position[0], initial_position[1] + 1],
                    "Did not advance exactly one week")
            require(view["saved_head_revision_id"] != old_head and
                    report["after"]["revisions"] == before["revisions"] + len(PLANS[args.scenario]),
                    "Unexpected Saved revision growth")
            check_started = time.perf_counter()
            report["evidence"] = evidence(view)
            if args.scenario == "w6":
                cup = view["edition_evidence"]["ab-cup"]
                require(len(cup["matches"]) == 3 and len(cup["results"]) == 4 and
                        view["state"]["rankings"], "Missing real matches/results/ranking")
            else:
                require(report["evidence"]["match_count"] == 24 and
                        initial_evidence["edition_evidence_sha256"] == report["evidence"]["edition_evidence_sha256"],
                        "Archived evidence differs")
            report["history"] = history(repo)
            require(report["history"][-1]["id"] == view["saved_head_revision_id"],
                    "Verified history head differs from inspection")
            require(sum(row["sql_calls"] for row in rows) > 0 and
                    sum(row["fetch_text_blob_bytes"] for row in rows) > 0,
                    "Expected SQL/fetch instrumentation to observe real reads")
            report["check_wall_s"] = time.perf_counter() - check_started
            report["check_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Run after server shutdown: ensure the physical file itself is sound.
        with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as con:
            require(con.execute("PRAGMA quick_check").fetchall() == [("ok",)], "SQLite quick_check failed")
        require(metadata() == meta, "Code or environment changed during measurement")
        report["status"] = "ok"
    except BaseException as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        deps.uuid4 = original_uuid4
        write(args.out, report)


def validate_report(item):
    require(item["schema"] == SCHEMA and item["status"] == "ok", "failed/incomplete report")
    scenario, mode = item["scenario"], item["mode"]
    require(scenario in PLANS and mode in ("normal", "retry"), "unknown scenario/mode")
    require(digest(item["plan"]) == digest(PLANS[scenario]), "unexpected action plan")
    require(type(item["seed"]) is int and item["seed"] == SEED, "unexpected seed")
    require(re.fullmatch(r"[0-9a-f]{64}", item["input_sha256"]), "invalid fixture hash")
    require(scenario != "w12-1822" or item["input_sha256"] == W12_SHA, "wrong W12 fixture")
    require([row["label"] for row in item["calls"]] == expected_calls(scenario, mode),
            "unexpected operation sequence")
    for row in item["calls"]:
        label = row["label"]
        get = label.endswith("get")
        status = 200 if get or label.endswith(":preview") else 201
        require(row["method"] == ("GET" if get else "POST") and row["status"] == status,
                "unexpected request method/status")
        require(re.fullmatch(r"[0-9a-f]{64}", row["request_sha256"]), "invalid request digest")
        if get:
            require(row["request_sha256"] == digest(None), "unexpected GET body")
        for key in ("wall_s", "cpu_s", "peak_rss_kib", "sql_calls", "sql_cursor_wall_s",
                    "fetch_rows", "fetch_text_blob_bytes", "db_bytes", "wal_bytes"):
            require(type(row[key]) in (int, float) and math.isfinite(row[key]) and row[key] >= 0,
                    "invalid phase metric " + key)
    for key in ("wall_s", "cpu_s", "elapsed_wall_s", "elapsed_cpu_s",
                "peak_rss_kib", "check_wall_s"):
        require(type(item[key]) in (int, float) and math.isfinite(item[key]) and item[key] >= 0,
                "invalid total metric " + key)
    by_label = {row["label"]: row for row in item["calls"]}
    for label, row in by_label.items():
        if label.endswith(":retry"):
            require(row["request_sha256"] == by_label[label.replace(":retry", ":execute")]["request_sha256"],
                    "retry request differs from original")
    for key in ("wall_s", "cpu_s"):
        require(math.isclose(item[key], sum(row[key] for row in item["calls"]), rel_tol=1e-9),
                "total does not match phase metrics")
        require(item["elapsed_" + key] >= item[key], "elapsed time below measured request total")
    require(sum(row["sql_calls"] for row in item["calls"]) > 0 and
            sum(row["fetch_text_blob_bytes"] for row in item["calls"]) > 0,
            "missing observed SQL/fetch activity")
    for snapshot in (item["before"], item["after"]):
        for key in ("db_bytes", "wal_bytes", "revisions", "stored_payload_column_bytes"):
            require(type(snapshot[key]) is int and snapshot[key] >= 0, "invalid SQLite metric")
    require(item["after"]["revisions"] == item["before"]["revisions"] + len(PLANS[scenario]),
            "invalid revision growth")
    require(re.fullmatch(r"[0-9a-f]{40}", item["metadata"]["commit"]), "invalid commit")
    require(re.fullmatch(r"[0-9a-f]{40}", item["metadata"]["source_tree"]), "invalid tree")
    for ev in (item["initial_evidence"], item["evidence"]):
        for key in ("players_sha256", "editions_sha256", "matches_sha256",
                    "edition_evidence_sha256", "rankings_sha256", "inspection_sha256"):
            require(re.fullmatch(r"[0-9a-f]{64}", ev[key]), "missing/invalid sporting evidence")
        require(type(ev["players"]) is int and type(ev["match_count"]) is int
                and ev["players"] > 0 and ev["match_count"] >= 0, "invalid sporting counts")
    require(item["history"] and item["history"][-1]["id"] == item["evidence"]["head"],
            "missing/mismatched history")
    for row in item["history"]:
        for key in ("payload_sha256", "summary_sha256", "content_hash"):
            require(re.fullmatch(r"[0-9a-f]{64}", row[key]), "invalid logical history digest")


def comparable(a, b, *, cross_mode=False):
    """Fail closed; no performance delta for an invalid experiment."""
    reasons = []
    for label, item in (("A", a), ("B", b)):
        try:
            validate_report(item)
        except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
            reasons.append(label + ": " + str(exc))
    if reasons:
        return reasons
    if cross_mode and (a["metadata"]["commit"] != b["metadata"]["commit"] or
                       (a["mode"], b["mode"]) != ("normal", "retry")):
        reasons.append("retry overhead requires normal/retry on the same commit")
    keys = ["input_sha256", "scenario", "seed", "plan", "before", "initial_evidence"]
    if not cross_mode:
        keys += ["mode"]
    for key in keys:
        if key not in a or key not in b or a[key] != b[key]:
            reasons.append("different/missing " + key)
    # Compare actual HTTP bodies as well as labels. Preview fingerprints and
    # expected Saved/draft IDs are deterministic for the supported A/B scenario.
    # If a candidate legitimately changes a fingerprint protocol, reject rather
    # than silently claiming that different requests are equivalent.
    def requests(item):
        return [(r["label"], r["request_sha256"]) for r in item["calls"]
                if not (cross_mode and r["label"].endswith(":retry"))]
    if requests(a) != requests(b):
        reasons.append("different actual HTTP request bodies")
    for key in ("runner_sha256", "metrics_sha256", "python", "platform", "machine",
                "cpu_count", "dependencies", "pythonhashseed", "new_run_storage"):
        if key not in a.get("metadata", {}) or key not in b.get("metadata", {}) or a["metadata"][key] != b["metadata"][key]:
            reasons.append("different/missing environment: " + key)
    return reasons


def totals(report):
    return {**{k: report[k] for k in ("wall_s", "cpu_s", "elapsed_wall_s", "elapsed_cpu_s",
                                              "peak_rss_kib", "check_wall_s")},
            "http_calls": len(report["calls"]),
            **{k: sum(row[k] for row in report["calls"])
               for k in ("sql_calls", "sql_cursor_wall_s", "fetch_rows", "fetch_text_blob_bytes")},
            **report["after"]}


def compare(a, b, *, cross_mode=False):
    reasons = comparable(a, b, cross_mode=cross_mode)
    if reasons:
        return {"verdict": "not_comparable", "reasons": reasons}
    if a["evidence"] != b["evidence"] or a["history"] != b["history"]:
        return {"verdict": "different_results", "evidence_equal": a["evidence"] == b["evidence"],
                "history_equal": a["history"] == b["history"]}
    x, y = totals(a), totals(b)
    by_label = {row["label"]: row for row in b["calls"]}
    return {"verdict": "equal", "a": x, "b": y,
            "delta_b_minus_a": {k: y[k] - x[k] for k in x},
            "phase_delta_wall_s": {
                ra["label"]: by_label[ra["label"]]["wall_s"] - ra["wall_s"]
                for ra in a["calls"] if ra["label"] in by_label},
            "deliberate_retry_wall_s": sum(row["wall_s"] for row in b["calls"]
                                           if row["label"].endswith(":retry"))}


def child_env():
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env.pop("PYTHONPATH", None)
    return env


def trial_order(repetition):
    # Each commit/mode gets the opposite early/late position in the next trial.
    forward = [("A", "normal"), ("B", "normal"), ("B", "retry"), ("A", "retry")]
    return forward if repetition % 2 == 0 else list(reversed(forward))


def summarize_trials(trials):
    """Aggregate only when every comparison and repeated result agrees."""
    require(bool(trials), "No trials")
    comparisons = []
    for trial in trials:
        pairs = {mode: compare(trial["A-" + mode], trial["B-" + mode])
                 for mode in ("normal", "retry")}
        for label in ("A", "B"):
            pairs[label + "-retry-overhead"] = compare(
                trial[label + "-normal"], trial[label + "-retry"], cross_mode=True)
        comparisons.append(pairs)
    repeat_checks = []
    for i, trial in enumerate(trials[1:], start=2):
        for name, original in trials[0].items():
            current = trial[name]
            result = compare(original, current)
            if original["metadata"]["commit"] != current["metadata"]["commit"]:
                result = {"verdict": "not_comparable", "reasons": ["commit changed across trials"]}
            repeat_checks.append({"trial": i, "case": name, "result": result})
    valid = (all(v["verdict"] == "equal" for trial in comparisons for v in trial.values())
             and all(r["result"]["verdict"] == "equal" for r in repeat_checks))
    result = {"verdict": "equal" if valid else "invalid_experiment",
              "repetitions": len(trials), "trials": comparisons,
              "repeat_checks": repeat_checks}
    if not valid:
        return result

    def stats(values):
        return {"median": median(values), "min": min(values), "max": max(values)}

    result["aggregate"] = {}
    for case in comparisons[0]:
        rows = [trial[case] for trial in comparisons]
        result["aggregate"][case] = {
            group: {key: stats([row[group][key] for row in rows]) for key in rows[0][group]}
            for group in ("a", "b", "delta_b_minus_a", "phase_delta_wall_s")
        }
        result["aggregate"][case]["deliberate_retry_wall_s"] = stats(
            [row["deliberate_retry_wall_s"] for row in rows])
    return result


def run_ab(args):
    a, b = exact_commit(args.a), exact_commit(args.b)
    require(1 <= args.repetitions <= 3, "Use 1-3 isolated repetitions")
    require(1 <= args.worker_timeout <= 1800, "Worker timeout must be 1-1800 seconds")
    require(re.fullmatch(r"[0-9a-f]{64}", args.sha256) is not None, "Need exact fixture SHA-256")
    require(args.scenario != "w12-1822" or args.sha256 == W12_SHA, "Wrong W12 fixture")
    source, out = args.input.resolve(strict=True), args.out.resolve()
    require(not out.exists(), "Output directory must be fresh")
    require(file_sha(source) == args.sha256, "Wrong fixture before experiment")
    out.mkdir(parents=True)
    commits = {"A": a, "B": b}
    manifest = {"schema": SCHEMA, "commits": commits, "scenario": args.scenario,
                "input_sha256": args.sha256, "repetitions": args.repetitions,
                "worker_timeout_s": args.worker_timeout, "cases": [],
                "status": "failed"}
    trials = []
    try:
        with tempfile.TemporaryDirectory(prefix="native-week-ab-") as temporary:
            temp = Path(temporary)
            trees = {}
            try:
                for label, commit in commits.items():
                    tree = temp / label
                    git("worktree", "add", "--detach", str(tree), commit)
                    trees[label] = tree
                for repetition in range(args.repetitions):
                    reports = {}
                    case_dir = out if args.repetitions == 1 else out / f"trial-{repetition + 1:02d}"
                    case_dir.mkdir(exist_ok=args.repetitions == 1)
                    for label, mode in trial_order(repetition):
                        name = f"{label}-{mode}"
                        db = temp / f"{repetition}-{name}.db"
                        dest = case_dir / (name + ".json")
                        case = {"trial": repetition + 1, "case": name,
                                "report": str(dest.relative_to(out)), "status": "started"}
                        manifest["cases"].append(case)
                        try:
                            copy_fixture(source, db, args.sha256)
                            with (case_dir / (name + ".log")).open("x", encoding="utf-8") as log:
                                proc = subprocess.run(
                                    [sys.executable, str(SCRIPT), "_worker", "--database", str(db),
                                     "--commit", commits[label], "--scenario", args.scenario,
                                     "--mode", mode, "--sha256", args.sha256, "--out", str(dest)],
                                    cwd=trees[label], env=child_env(), stdout=log,
                                    stderr=subprocess.STDOUT, timeout=args.worker_timeout, check=False)
                            case["returncode"] = proc.returncode
                            require(proc.returncode == 0, f"{name}: worker failed ({proc.returncode})")
                            reports[name] = json.loads(dest.read_text())
                            validate_report(reports[name])
                            require(reports[name]["metadata"]["commit"] == commits[label] and
                                    reports[name]["mode"] == mode and
                                    reports[name]["scenario"] == args.scenario and
                                    reports[name]["input_sha256"] == args.sha256,
                                    "Worker report does not match scheduled case")
                            case["status"] = "ok"
                        except BaseException as exc:
                            case["status"] = "failed"
                            case["error"] = type(exc).__name__ + ": " + str(exc)
                            raise
                        finally:
                            # Fresh copy per case; retain only evidence/logs, not private DBs.
                            for file in (db, sidecar(db, "-wal"), sidecar(db, "-shm")):
                                file.unlink(missing_ok=True)
                    trials.append(reports)
            finally:
                for tree in reversed(list(trees.values())):
                    git("worktree", "remove", "--force", str(tree))
        require(file_sha(source) == args.sha256, "Original fixture changed")
        summary = summarize_trials(trials)
        write(out / "comparison.json", summary)
        print(json.dumps(summary, indent=2))
        manifest["status"] = summary["verdict"]
        return 0 if summary["verdict"] == "equal" else 2
    except BaseException as exc:
        manifest["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        write(out / "manifest.json", manifest)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="action", required=True)
    prep = subs.add_parser("prepare")
    prep.add_argument("--database", type=Path, required=True)
    ab = subs.add_parser("ab")
    for key in ("a", "b", "sha256"):
        ab.add_argument("--" + key, required=True)
    ab.add_argument("--scenario", choices=PLANS, default="w6")
    ab.add_argument("--input", type=Path, required=True)
    ab.add_argument("--out", type=Path, required=True)
    ab.add_argument("--repetitions", type=int, default=1, help="1-3 independent A/B trials")
    ab.add_argument("--worker-timeout", type=int, default=600, help="Per-process seconds, 1-1800")
    comp = subs.add_parser("compare")
    comp.add_argument("a", type=Path)
    comp.add_argument("b", type=Path)
    worker_p = subs.add_parser("_worker")
    for key in ("commit", "sha256"):
        worker_p.add_argument("--" + key, required=True)
    worker_p.add_argument("--database", type=Path, required=True)
    worker_p.add_argument("--out", type=Path, required=True)
    worker_p.add_argument("--scenario", choices=PLANS, required=True)
    worker_p.add_argument("--mode", choices=("normal", "retry"), required=True)
    args = p.parse_args(argv)
    if args.action == "prepare":
        target_imports()
        prepare(args.database.resolve())
        return 0
    if args.action == "_worker":
        worker(args)
        return 0
    if args.action == "compare":
        result = compare(json.loads(args.a.read_text()), json.loads(args.b.read_text()))
        print(json.dumps(result, indent=2))
        return 0 if result["verdict"] == "equal" else 2
    return run_ab(args)


if __name__ == "__main__":
    raise SystemExit(main())
