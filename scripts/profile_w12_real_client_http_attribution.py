"""Isolate costly *test-harness* HTTP calls from needed native engine work.

This diagnostic runs on disposable independent copies of the original W12
256-player / eight played Editions / 24 authentic matches SQLite from #1815.

A: the EXACT existing GIANT #1820 helper sequence for a no-match week:
   inspect -> test helper preview + execute + redundant execute idempotency
   -> helper Save (inspection + Save + inspection) -> inspection.
B: same sporting command, preview, execution and explicit Save but no extra
   idempotency-retry POST and one fewer redundant inspection. This is NOT
   a recommendation to drop idempotency acceptance tests.

Each process handles ONE case. Workflow orders fresh-process A-B-B-A clones.
No edits to #1820 or any production source, v1 format or stored history.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sqlalchemy import event
from tests.api import test_calendar_tour_flow as flow
from tests.api.test_saved_revision_history_api import ApiServer

EXPECTED_SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"
EDITION_IDS = tuple(f"load-w{week}-{index}" for week in (4, 5) for index in range(4))


def _sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _physical_size(db_file):
    with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as con:
        revs, payload = con.execute(
            "SELECT COUNT(*),COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))),0) "
            "FROM branch_saved_revisions"
        ).fetchone()
    return {
        "revision_count": int(revs),
        "saved_payload_bytes": int(payload),
        "sqlite_main_bytes": db_file.stat().st_size,
        "wal_bytes": (db_file.parent / (db_file.name + "-wal")).stat().st_size
        if (db_file.parent / (db_file.name + "-wal")).exists() else 0,
    }


def _rss_kib():
    # Linux GitHub runner; VmRSS is current and ru_maxrss is lifetime peak.
    with open("/proc/self/status", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    raise RuntimeError("Linux /proc/self/status VmRSS unavailable")


def _assert_real_sporting(view, *, week):
    assert view["saved"], "Original and final Run must be explicitly Saved"
    assert len(view["players"]) == 256
    assert (view["state"]["week"]["season_index"],
            view["state"]["week"]["week"]) == (1, week)
    assert len(view["state"]["editions"]) == 8
    for eid in EDITION_IDS:
        assert len(view["edition_evidence"][eid]["matches"]) == 3
        assert next(
            x["result_confirmed"]
            for x in view["state"]["editions"]
            if x["edition"]["edition_id"] == eid
        )
    return {
        "players_sha256": _sha(view["players"]),
        "edition_evidence_sha256": _sha(
            {eid: view["edition_evidence"][eid] for eid in EDITION_IDS}
        ),
        "original_completed_match_count": 24,
        "confirmed_editions": 8,
    }


def _route_name(method, url, *, execute_index):
    path = urlsplit(url).path
    if path.endswith("/calendar-tour"):
        return "inspection-get" if method == "GET" else "other-calendar-tour"
    if path.endswith("/calendar-tour/preview"):
        return "preview-post"
    if path.endswith("/calendar-tour/execute"):
        return (
            "execute-first-post" if execute_index == 1
            else "execute-idempotency-retry-post"
        )
    if path.endswith("/calendar-tour/save"):
        return "manual-save-post"
    return "other-" + method.lower()


def _case(case_name, db_path, out):
    from tests.api import test_saved_revision_history_api as history

    db_path = db_path.resolve(strict=True)
    if db_path.name != "native-case.sqlite":
        raise ValueError("Never profile the original unmodified archived SQLite")
    with db_path.open("rb") as fh:
        original_sha = hashlib.file_digest(fh, "sha256").hexdigest()
    if original_sha != EXPECTED_SOURCE_SHA:
        raise ValueError("Incorrect source physical Saved database")
    before_sqlite = _physical_size(db_path)
    assert before_sqlite["revision_count"] == 46

    legacy = case_name.startswith("A")
    request_rows = []
    sql_counters = defaultdict(float)
    execute_counter = 0

    with ApiServer(database_url=f"sqlite:///{db_path}") as server:
        engine = server.app.state.runtime.repository._engine

        def before_sql(conn, cursor, statement, parameters, context, executemany):
            context._w12_profiler_start = time.perf_counter()

        def after_sql(conn, cursor, statement, parameters, context, executemany):
            elapsed = time.perf_counter() - context._w12_profiler_start
            sql_counters["cursor_execute_count"] += 1
            sql_counters["cursor_execute_wall_s"] += elapsed
            stmt = statement.lstrip().split(None, 1)[0].upper()
            sql_counters[stmt + "_count"] += 1

        event.listen(engine, "before_cursor_execute", before_sql)
        event.listen(engine, "after_cursor_execute", after_sql)
        # The route helpers imported _request by value. Patch only this test
        # module's helper symbol; the application/server remains unmodified.
        ordinary_request = flow._request

        def traced_request(method, url, payload=None):
            nonlocal execute_counter
            if urlsplit(url).path.endswith("/calendar-tour/execute"):
                execute_counter += 1
            operation = _route_name(method, url, execute_index=execute_counter)
            wall_start, cpu_start = time.perf_counter(), time.process_time()
            try:
                result = ordinary_request(method, url, payload)
            finally:
                request_rows.append({
                    "operation": operation, "method": method,
                    "wall_s": round(time.perf_counter() - wall_start, 3),
                    "process_cpu_s": round(time.process_time() - cpu_start, 3),
                })
            return result

        flow._request = traced_request
        try:
            started, cpu_started = time.perf_counter(), time.process_time()
            initial = flow.inspect(server)
            check_before = _assert_real_sporting(initial, week=1)
            old_head = initial["saved_head_revision_id"]
            command = flow.command(
                initial, "transition", name="harness-cost-s2w1-to-s2w2",
            )
            if legacy:
                # Exactly the real GIANT helper's command execution and
                # manual Save path, including an explicit idempotency retry.
                flow.execute(server, command)
                flow.save_tour(server)
                final = flow.inspect(server)
            else:
                endpoint = flow.tour_url(server)
                status, preview = traced_request(
                    "POST", endpoint + "/preview", command
                )
                assert status == 200, preview
                request = {
                    "command": command,
                    "expected_preview_fingerprint": preview["preview_fingerprint"],
                    "explicit_confirmation": True,
                }
                status, executed = traced_request(
                    "POST", endpoint + "/execute", request
                )
                assert status == 201, executed
                draft = flow.inspect(server)
                assert not draft["saved"]
                status, saved = traced_request(
                    "POST", endpoint + "/save", {
                        "expected_draft_version": draft["draft_version"],
                        "expected_calendar_tour_fingerprint": draft["tour_fingerprint"],
                    },
                )
                assert status == 201 and "saved_revision" in saved, saved
                final = flow.inspect(server)

            total_wall_s = time.perf_counter() - started
            total_cpu_s = time.process_time() - cpu_started
            check_after = _assert_real_sporting(final, week=2)
            # A real native week transition MAY develop/change player
            # attributes. Preserve old match evidence, not the previous
            # week's player state; compare resulting players BETWEEN A/B.
            assert (
                check_before["edition_evidence_sha256"]
                == check_after["edition_evidence_sha256"]
            )
            assert final["saved_head_revision_id"] != old_head
            counters = {}
            for row in request_rows:
                d = counters.setdefault(
                    row["operation"],
                    {"count": 0, "sum_wall_s": 0.0, "sum_cpu_s": 0.0}
                )
                d["count"] += 1
                d["sum_wall_s"] += row["wall_s"]
                d["sum_cpu_s"] += row["process_cpu_s"]
            expected_calls = {
                "inspection-get": 4 if legacy else 3,
                "preview-post": 1,
                "execute-first-post": 1,
                "manual-save-post": 1,
            }
            if legacy:
                expected_calls["execute-idempotency-retry-post"] = 1
            actual_calls = {k: v["count"] for k, v in counters.items()}
            assert actual_calls == expected_calls, (actual_calls, expected_calls)
            after_sqlite = _physical_size(db_path)
            assert after_sqlite["revision_count"] == 47, after_sqlite
            report = {
                "case": case_name,
                "scenario": "original-gigantic-test-helpers" if legacy
                else "minimal-necessary-HTTP-steps",
                "source_run": 43919075227,
                "source_sha256": original_sha,
                "original": before_sqlite,
                "after": after_sqlite,
                "added_saved_payload_bytes": (
                    after_sqlite["saved_payload_bytes"]
                    - before_sqlite["saved_payload_bytes"]
                ),
                "total_wall_s": round(total_wall_s, 3),
                "total_process_cpu_s": round(total_cpu_s, 3),
                "request_time_wall_s": round(
                    sum(x["wall_s"] for x in request_rows), 3),
                "non_request_wall_s": round(
                    total_wall_s - sum(x["wall_s"] for x in request_rows), 3),
                "calls": counters,
                "call_sequence": request_rows,
                "sql_execute_only": {
                    k: round(v, 3) for k, v in sql_counters.items()
                },
                "current_rss_kib": _rss_kib(),
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "unchanged_256_player_24_match_evidence": check_after,
                "manual_save": True,
                "production_code_changed": False,
                "test_helper_behavior_changed": False,
                "does_not_measure": (
                    "MatchEngine-specific CPU, full giant season, "
                    "database fetch/decode within cursor-execute timing"
                ),
            }
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("x", encoding="utf-8") as f:
                json.dump(report, f, indent=2, sort_keys=True)
            print(
                "W12_HTTP_ATTRIBUTION " + json.dumps(
                    {"phase": "case", **report}, sort_keys=True
                ),
                flush=True,
            )
        finally:
            flow._request = ordinary_request
            event.remove(engine, "after_cursor_execute", after_sql)
            event.remove(engine, "before_cursor_execute", before_sql)


def _summary(directory):
    import statistics

    names = ("A1", "B1", "B2", "A2")
    items = {
        key: json.loads((directory / (key + ".json")).read_text(encoding="utf-8"))
        for key in names
    }
    identity = {
        (
            item["unchanged_256_player_24_match_evidence"]["players_sha256"],
            item["unchanged_256_player_24_match_evidence"]["edition_evidence_sha256"],
            item["added_saved_payload_bytes"],
        )
        for item in items.values()
    }
    if len(identity) != 1:
        raise AssertionError("Sporting content or physical Saved payload changed")
    def median(which, key):
        return statistics.median(
            item[key] for item in items.values() if item["case"].startswith(which)
        )
    a, b = median("A", "total_wall_s"), median("B", "total_wall_s")
    def op_median(kind, which):
        return statistics.median(
            item["calls"].get(kind, {"sum_wall_s": 0.0})["sum_wall_s"]
            for item in items.values() if item["case"].startswith(which)
        )
    report = {
        "source_original_sha256": EXPECTED_SOURCE_SHA,
        "order": names,
        "cases": items,
        "legacy_median_total_wall_s": round(a, 3),
        "minimal_median_total_wall_s": round(b, 3),
        "observed_harness_footprint_percent": round(
            100 * (a - b) / a, 2
        ),
        "legacy_extra_get_wall_s_median": round(
            op_median("inspection-get", "A")
            - op_median("inspection-get", "B"), 3
        ),
        "legacy_duplicate_execute_wall_s_median": round(
            op_median("execute-idempotency-retry-post", "A"), 3
        ),
        "same_sporting_output_in_all_cases": True,
        "safety": (
            "Minimal case is an analytical control, not a recommended "
            "replacement of GIANT's deliberate idempotency checks"
        ),
        "not_a_production_engine_speedup": True,
    }
    (directory / "summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print("W12_HTTP_ATTRIBUTION " + json.dumps(
        {"phase": "summary", **{k:v for k,v in report.items() if k!="cases"}},
        sort_keys=True,
    ), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--case", choices=("A1","B1","B2","A2"))
    mode.add_argument("--summarize", type=Path)
    p.add_argument("--database", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.summarize:
        _summary(args.summarize)
    else:
        if args.database is None or args.out is None:
            p.error("--case needs --database and --out")
        _case(args.case, args.database, args.out)
