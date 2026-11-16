"""Read-only cold HTTP/SQLite cProfile of the completed 256-player W12 Run.

Input is the *actual disposable SQLite file* archived by successful GitHub
Actions run 43919075227 (#1815), not a reconstructed or fabricated fixture.
No execution, no Saved writes, no production optimization claims by itself.
"""
from __future__ import annotations

import argparse
import cProfile
from collections import Counter
import hashlib
import json
from pathlib import Path
import pstats
import resource
import sqlite3
import threading
import time
from urllib import request

from sqlalchemy import event

from beta_engine.application.calendar_tour_service import CalendarTourService
from tests.api.test_saved_revision_history_api import ApiServer


def _report(label, **values):
    print("NATIVE_SAVED_COLD_PROFILE " + json.dumps(
        {"phase": label, **values}, sort_keys=True
    ), flush=True)


def _source_metrics(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        n, raw_bytes = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))), 0) "
            "FROM branch_saved_revisions"
        ).fetchone()
        sizes = db.execute(
            "SELECT LENGTH(CAST(payload_json AS BLOB)) AS n "
            "FROM branch_saved_revisions ORDER BY n DESC LIMIT 5"
        ).fetchall()
    return {
        "sqlite_file_bytes": path.stat().st_size,
        "saved_revision_count": n,
        "saved_payload_bytes": raw_bytes,
        "five_largest_saved_bytes": [int(item[0]) for item in sizes],
    }


def _http_inspect(server):
    endpoint = server.base_url + "/admin/runs/run/branches/branch/calendar-tour"
    with request.urlopen(endpoint, timeout=600) as response:
        assert response.status == 200
        value = json.loads(response.read())
    assert value["saved"], "Baseline should be the last signed Saved state"
    assert len(value["players"]) == 256
    assert len(value["state"]["editions"]) == 8
    assert (value["state"]["week"]["season_index"],
            value["state"]["week"]["week"]) == (1, 1)
    for edition_id in [f"load-w{week}-{i}" for week in (4, 5) for i in range(4)]:
        assert len(value["edition_evidence"][edition_id]["matches"]) == 3
        assert next(
            x["result_confirmed"] for x in value["state"]["editions"]
            if x["edition"]["edition_id"] == edition_id
        )
    return value


def _profile_to_json(stats, top=45):
    ranked = sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)
    self_ranked = sorted(stats.stats.items(), key=lambda item: item[1][2], reverse=True)

    def select(rows):
        return [
            {
                "source_file": Path(key[0]).name,
                "line": key[1],
                "function": key[2],
                "calls": int(details[1]),
                "self_profile_s": round(details[2], 3),
                "cumulative_profile_s": round(details[3], 3),
            }
            for key, details in rows[:top]
        ]
    return {"top_cumulative": select(ranked), "top_self": select(self_ranked)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    original_db = args.database.resolve(strict=True)
    if not original_db.is_file() or original_db.name != "populated-w12-256.db":
        raise ValueError("Expected only the archived disposable populated-w12-256.db")
    out = args.report_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Input identity and validity. No interpolation of any user-controlled SQL.
    with original_db.open("rb") as source_stream:
        input_sha256 = hashlib.file_digest(source_stream, "sha256").hexdigest()
    sizes = _source_metrics(original_db)
    assert sizes["saved_revision_count"] == 46, sizes
    _report("input-verified", sha256=input_sha256, **sizes)

    original = CalendarTourService.inspect
    first_profile = {"captured": False}
    profiler = cProfile.Profile()
    guard = threading.Lock()

    def instrumented_inspect(self, *, run_id, branch_id):
        with guard:
            do_profile = not first_profile["captured"]
            if do_profile:
                first_profile["captured"] = True
        if do_profile:
            return profiler.runcall(
                original, self, run_id=run_id, branch_id=branch_id
            )
        return original(self, run_id=run_id, branch_id=branch_id)

    CalendarTourService.inspect = instrumented_inspect
    sql = Counter()
    sql_lock = threading.Lock()

    try:
        with ApiServer(database_url=f"sqlite:///{original_db}") as server:
            engine = server.app.state.runtime.repository._engine

            def before_sql(conn, cursor, statement, parameters, context, executemany):
                context._native_profile_query_start = time.perf_counter()

            def after_sql(conn, cursor, statement, parameters, context, executemany):
                elapsed = time.perf_counter() - context._native_profile_query_start
                kind = statement.lstrip().split(None, 1)[0].upper()
                with sql_lock:
                    sql["statements"] += 1
                    sql[f"{kind}_statements"] += 1
                    sql["execute_wall_ms"] += elapsed * 1000

            event.listen(engine, "before_cursor_execute", before_sql)
            event.listen(engine, "after_cursor_execute", after_sql)

            before = time.perf_counter()
            cpu_before = time.process_time()
            _http_inspect(server)
            cold_wall = time.perf_counter() - before
            cold_cpu = time.process_time() - cpu_before
            cold_sql = dict(sql)
            profiler.dump_stats(str(out / "cold-inspect.pstats"))
            with (out / "cold-inspect-cumulative.txt").open("w") as stream:
                pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats(
                    "cumulative"
                ).print_stats(80)
            with (out / "cold-inspect-self.txt").open("w") as stream:
                pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats(
                    "tottime"
                ).print_stats(80)
            hotspots = _profile_to_json(pstats.Stats(profiler))
            (out / "hotspots.json").write_text(
                json.dumps(hotspots, indent=2), encoding="utf-8"
            )
            _report(
                "cold-inspect", wall_s=round(cold_wall, 3),
                process_cpu_s=round(cold_cpu, 3),
                sql=cold_sql, top_cumulative=hotspots["top_cumulative"][:15],
                top_self=hotspots["top_self"][:15],
            )

            # A warm GET is deliberately *not* profiled. It must still
            # verify all eight immutable actual tournament histories.
            before = time.perf_counter()
            cpu_before = time.process_time()
            _http_inspect(server)
            warm_wall = time.perf_counter() - before
            warm_cpu = time.process_time() - cpu_before
            warm_sql = {
                key: round(sql[key] - cold_sql.get(key, 0), 3) for key in sql
            }
            report = {
                "source_action_run": 43919075227,
                "source_pull_request": 1815,
                "source_db_sha256": input_sha256,
                "source": sizes,
                "cold_inspect": {
                    "wall_s": round(cold_wall, 3),
                    "process_cpu_s": round(cold_cpu, 3),
                    "sql": cold_sql,
                },
                "warm_inspect": {
                    "wall_s": round(warm_wall, 3),
                    "process_cpu_s": round(warm_cpu, 3),
                    "sql": warm_sql,
                },
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "read_only_requests": True,
                "production_code_changed": False,
                "full_w52_simulation": False,
            }
            (out / "summary.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            _report("complete", **report)
    finally:
        CalendarTourService.inspect = original


if __name__ == "__main__":
    main()
