"""Native W12 CPU/call-graph diagnosis of one REAL production HTTP manual Save.

Read/verify the exact original 256-player, 8 authentic Edition, 24 played
match, 46-Saved physical W12 database on a fresh disposable copy only.
The original copy SHA-256 is checked before the server starts.

Instrument exactly the real repository.save_viewer_branch_selection_atomically
method used by the native calendar-tour POST /save, with cProfile ENABLED on
the actual server request-handling thread. No mocked persistence, bypassed
Saved checks, production schema changes, or fake sporting outcomes.

Report nonadditive cumulative methods separately from additive exclusive
cProfile function time, SQL cursor execute time (not fetch), HTTP wall/CPU,
RSS, physical SQLite/WAL, and real 47th Saved payload bytes. This is a
DIAGNOSTIC and its profiling overhead must NOT be mistaken for the
unprofiled production POST latency or a season throughput benchmark.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import resource
import sqlite3
import sys
import threading
import time
from urllib import error, request
from sqlalchemy import event

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from tests.api.test_saved_revision_history_api import ApiServer  # noqa: E402

SOURCE_SHA256 = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"
PREFIX = "W12_SAVE_CPU_CALLGRAPH "


def _emit(phase, **kwargs):
    print(PREFIX + json.dumps({"phase": phase, **kwargs}, sort_keys=True), flush=True)


def _measure_db(database):
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as con:
        rev, payload_bytes = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))), 0) "
            "FROM branch_saved_revisions"
        ).fetchone()
    wal = Path(str(database) + "-wal")
    return {
        "revisions": int(rev),
        "payload_bytes": int(payload_bytes),
        "sqlite_bytes": database.stat().st_size,
        "wal_bytes": wal.stat().st_size if wal.exists() else 0,
    }


def _verify_actual_sport(view, week):
    assert len(view["players"]) == 256
    assert len(view["state"]["editions"]) == 8
    assert view["state"]["week"] == {
        "season_index": 1, "week": week
    }, view["state"]["week"]
    real_matches = 0
    for match_week in (4, 5):
        for index in range(4):
            eid = f"load-w{match_week}-{index}"
            entry = next(
                x for x in view["state"]["editions"]
                if x["edition"]["edition_id"] == eid
            )
            assert entry["result_confirmed"], eid
            matches = view["edition_evidence"][eid]["matches"]
            assert len(matches) == 3, (eid, len(matches))
            real_matches += len(matches)
    assert real_matches == 24
    return {
        "player_count": len(view["players"]),
        "editions": len(view["state"]["editions"]),
        "original_real_matches": real_matches,
    }


def _category(filename):
    name = filename.replace("\\", "/")
    if "pydantic" in name:
        return "pydantic"
    if "/json/" in name or name.endswith("/json/__init__.py") or "orjson" in name:
        return "json"
    if "sqlalchemy" in name or "sqlite3" in name:
        return "sqlalchemy_and_sqlite"
    if "run_revisions" in name or "/infrastructure/db/" in name:
        return "saved_revision_and_database_application"
    if "/calendar/" in name or "/tournaments/" in name or "/players/" in name:
        return "sporting_domain"
    if "/application/" in name or "/api/" in name:
        return "application_and_route"
    if filename.startswith("~"):
        return "builtin_functions"
    return "other"


def _format_profile(profile, limit=48):
    """Exclusive rows are additive; cumulative rows are INCLUSIVE, not additive."""
    stats = pstats.Stats(profile)
    rows = []
    exclusive = defaultdict(float)
    for (filename, line, function), (primitive, total, exclusive_s,
                                     inclusive_s, callers) in stats.stats.items():
        category = _category(filename)
        exclusive[category] += exclusive_s
        rows.append({
            "file": Path(filename).name if not filename.startswith("~") else filename,
            "function": function,
            "line": line,
            "calls": total,
            "primitive_calls": primitive,
            "exclusive_profile_s": round(exclusive_s, 4),
            "inclusive_profile_s": round(inclusive_s, 4),
            "category": category,
        })
    total_exclusive = sum(exclusive.values())
    return {
        "profile_total_exclusive_elapsed_s": round(total_exclusive, 4),
        "total_function_entries": len(rows),
        "top_inclusive": sorted(
            rows, key=lambda x: x["inclusive_profile_s"], reverse=True
        )[:limit],
        "top_exclusive": sorted(
            rows, key=lambda x: x["exclusive_profile_s"], reverse=True
        )[:limit],
        "exclusive_by_module_category_s": {
            k: round(v, 4) for k, v in
            sorted(exclusive.items(), key=lambda x: x[1], reverse=True)
        },
        "warning": (
            "cProfile runs in server thread and adds tracing overhead. "
            "Cumulative inclusive method times OVERLAP; do not add them. "
            "Category exclusive times can be added but include C/Python "
            "function instrumentation and are not pure CPU hardware counters."
        ),
    }


def _http(method, url, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=600) as response:
        data = response.read()
        return int(response.status), json.loads(data) if data else {}


def _rss_kib():
    with open("/proc/self/status", encoding="utf-8") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    database = args.database.resolve(strict=True)
    if database.name != "native-case.sqlite":
        raise ValueError("Profiling requires a disposable copy named native-case.sqlite")
    with database.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Not exact original audited 256-player physical SQLite")
    before = _measure_db(database)
    assert before["revisions"] == 46, before
    save_profiles = []
    sql = defaultdict(float)
    events_attached = False

    with ApiServer(database_url=f"sqlite:///{database}") as server:
        repository = server.app.state.runtime.repository
        assert callable(repository.save_viewer_branch_selection_atomically)
        original_writer = repository.save_viewer_branch_selection_atomically
        conn_engine = repository._engine

        # Instrument only the physical writer's actual server thread.
        def profile_writer(*pos, **kw):
            profile = cProfile.Profile()
            started, cpu_started = time.perf_counter(), time.thread_time()
            profile.enable()
            try:
                return original_writer(*pos, **kw)
            finally:
                profile.disable()
                save_profiles.append({
                    "wall_s": round(time.perf_counter() - started, 3),
                    "thread_cpu_s": round(time.thread_time() - cpu_started, 3),
                    "callgraph": _format_profile(profile),
                })

        def before_cursor(conn, cursor, sql_text, args, context, multiple):
            context._w12_actual_writer_sql_start = time.perf_counter()

        def after_cursor(conn, cursor, sql_text, args, context, multiple):
            sql["cursor_execute_count"] += 1
            sql["cursor_execute_wall_s"] += (
                time.perf_counter() - context._w12_actual_writer_sql_start
            )
            sql[sql_text.lstrip().split(None, 1)[0].upper() + "_count"] += 1

        timings = {}
        try:
            endpoint = server.base_url + "/admin/runs/run/branches/branch/calendar-tour"

            def timed(key, method, path, payload=None, expected=200):
                t0, c0 = time.perf_counter(), time.process_time()
                code, val = _http(method, endpoint + path, payload)
                timings[key] = {
                    "wall_s": round(time.perf_counter() - t0, 3),
                    "cpu_s": round(time.process_time() - c0, 3),
                    "http_status": code,
                }
                if code != expected:
                    raise AssertionError((key, code, str(val)[:300]))
                _emit(key, **timings[key])
                return val

            original = timed("cold-get", "GET", "")
            original_sport = _verify_actual_sport(original, 1)
            assert original["saved"]
            old_head = original["saved_head_revision_id"]
            cmd = {
                "action": "transition",
                "command_id": "profile-actual-w12-writer-s2w2",
                "edition_id": None,
                "expected_saved_head": old_head,
                "expected_checkpoint_fingerprint": original["checkpoint_fingerprint"],
                "expected_tour_fingerprint": original["tour_fingerprint"],
                "seed": 231,
                "operator_label": "Admin",
                "audit_reason": "Exactly reproducible signed Save CPU investigation",
                "data": {},
            }
            preview = timed("preview", "POST", "/preview", cmd)
            executed = timed("execute", "POST", "/execute", {
                "command": cmd,
                "expected_preview_fingerprint": preview["preview_fingerprint"],
                "explicit_confirmation": True,
            }, expected=201)
            assert executed["manual_save_required"]
            draft = timed("draft-get", "GET", "")
            assert not draft["saved"]
            assert draft["state"]["week"]["week"] == 2
            # Time SQL cursor.execute only for the actual writer. This does
            # NOT include SQL fetch or object decoding/Pydantic.
            event.listen(conn_engine, "before_cursor_execute", before_cursor)
            event.listen(conn_engine, "after_cursor_execute", after_cursor)
            events_attached = True
            repository.save_viewer_branch_selection_atomically = profile_writer
            try:
                receipt = timed("profiled-manual-save", "POST", "/save", {
                    "expected_draft_version": draft["draft_version"],
                    "expected_calendar_tour_fingerprint": draft["tour_fingerprint"],
                }, expected=201)
            finally:
                repository.save_viewer_branch_selection_atomically = original_writer
                event.remove(conn_engine, "after_cursor_execute", after_cursor)
                event.remove(conn_engine, "before_cursor_execute", before_cursor)
                events_attached = False

            if len(save_profiles) != 1:
                raise AssertionError(
                    ("Expected exactly one profiled original repository Save",
                     len(save_profiles))
                )
            final = timed("post-save-get", "GET", "")
            final_sport = _verify_actual_sport(final, 2)
            assert original_sport == final_sport
            assert final["saved"]
            assert final["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]
            assert final["saved_head_revision_id"] != old_head
            after = _measure_db(database)
            assert after["revisions"] == 47, after
            report = {
                "original_source_sha256": SOURCE_SHA256,
                "real_player_count": 256,
                "confirmed_real_editions": 8,
                "original_real_matchengine_matches": 24,
                "real_current_s2_week": 2,
                "exact_original_revision_count": 46,
                "new_verified_revision_count": after["revisions"],
                "baseline": before,
                "post_save": after,
                "new_saved_payload_bytes": (
                    after["payload_bytes"] - before["payload_bytes"]
                ),
                "request_timings": timings,
                "profiled_repository_writer": save_profiles[0],
                "sql_cursor_execute_count_during_save": int(
                    sql["cursor_execute_count"]
                ),
                "sql_cursor_execute_wall_s_during_save": round(
                    sql["cursor_execute_wall_s"], 4
                ),
                "sql_command_counts_during_save": {
                    k: int(v) for k, v in sql.items()
                    if k.endswith("_count") and k != "cursor_execute_count"
                },
                "process_peak_rss_kib": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
                "process_current_rss_kib": _rss_kib(),
                "production_implementation_changed": False,
                "notes": [
                    "Standalone cProfile adds instrumentation overhead.",
                    "Only repository physical Save is profiled; preceding Tour"
                    " preview/execute and post-save GET are unprofiled.",
                    "Cumulative callgraph methods overlap; exclusive category"
                    " times are additive.",
                    "SQL cursor execute excludes fetch and JSON/Pydantic decode.",
                    "Native Calendar Tour only, not Native Fork or giant W8.",
                ],
            }
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "w12-save-cpu-callgraph.json").write_text(
                json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
            )
            _emit("complete", **{
                k:v for k,v in report.items() if k not in
                ("profiled_repository_writer",)
            }, profiled_writer_wall_s=save_profiles[0]["wall_s"],
               profiled_writer_cpu_s=save_profiles[0]["thread_cpu_s"],
               top_cumulative_functions=save_profiles[0]["callgraph"]["top_inclusive"][:18],
               top_exclusive_functions=save_profiles[0]["callgraph"]["top_exclusive"][:18],
               exclusive_categories=save_profiles[0]["callgraph"]["exclusive_by_module_category_s"])
        finally:
            repository.save_viewer_branch_selection_atomically = original_writer
            if events_attached:
                event.remove(conn_engine, "after_cursor_execute", after_cursor)
                event.remove(conn_engine, "before_cursor_execute", before_cursor)


if __name__ == "__main__":
    main()
