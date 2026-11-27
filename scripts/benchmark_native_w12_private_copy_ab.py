"""Same-real-source A–B–B–A for signed sporting DTO private copy only.

A = original production copy.deepcopy(value,memo), B = exact-type private
Pydantic/container copy candidate. Both use otherwise identical production
HTTP routes, original Saved lineage, physical SHA-256 and actual manual Save.

Run each case in a fresh Python process and independent disposable SQLite copy
of the SHA-256-pinned original played 256-player W12 46-Revision artifact.
Identical sports DTOs and the resulting real saved payload are required.
This benchmark is NOT a 1000-player season or a new Saved v2 format.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from hashlib import file_digest, sha256
import json
from pathlib import Path
import resource
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from beta_engine.domain.players.sporting import _SPORTING_ATTRIBUTE_COPY_MEMO_KEY  # noqa: E402
from beta_engine.infrastructure.db import native_fork_source_projection as projection  # noqa: E402
from tests.api import test_calendar_tour_flow as flow  # noqa: E402
from tests.api.test_saved_revision_history_api import ApiServer  # noqa: E402

SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"
EDITION_IDS = tuple(f"load-w{week}-{i}" for week in (4, 5) for i in range(4))


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()


def _physical(db_file):
    with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as db:
        revisions, blob_total = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))),0) "
            "FROM branch_saved_revisions"
        ).fetchone()
        row = db.execute(
            "SELECT payload_json, content_hash FROM branch_saved_revisions "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    wal = Path(str(db_file) + "-wal")
    return {
        "revisions": int(revisions),
        "saved_payload_bytes": int(blob_total),
        "last_raw_payload_sha256": sha256(row[0].encode()).hexdigest(),
        "last_content_hash": row[1],
        "sqlite_main_bytes": db_file.stat().st_size,
        "wal_bytes": wal.stat().st_size if wal.exists() else 0,
    }


def _sport(view, week):
    if (not view["saved"] or len(view["players"]) != 256
        or view["state"]["week"]["season_index"] != 1
        or view["state"]["week"]["week"] != week):
        raise AssertionError("Real Run/Week/Saved identity changed")
    if len(view["state"]["editions"]) != 8:
        raise AssertionError("Must retain all eight real sporting Editions")
    matches = 0
    for eid in EDITION_IDS:
        edition = next(x for x in view["state"]["editions"]
                       if x["edition"]["edition_id"] == eid)
        if not edition["result_confirmed"]:
            raise AssertionError(("Unconfirmed real Edition", eid))
        n = len(view["edition_evidence"][eid]["matches"])
        if n != 3:
            raise AssertionError((eid, n))
        matches += n
    if matches != 24:
        raise AssertionError(("Invalid real MatchEngine count", matches))
    return {
        "player_hash": _hash(view["players"]),
        "state_hash": _hash(view["state"]),
        "evidence_hash": _hash(view["edition_evidence"]),
        "rankings_hash": _hash(view.get("rankings")),
        "confirmed_editions": 8,
        "authentic_matches": matches,
    }


def _rss_kib():
    with open("/proc/self/status", encoding="utf-8") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return None


def _case(case, database, destination):
    if database.name != "native-case.sqlite":
        raise ValueError("Never open the original archived SQLite for writing")
    with database.open("rb") as f:
        if file_digest(f, "sha256").hexdigest() != SOURCE_SHA:
            raise AssertionError("Not the expected 46-Saved real source file")
    before = _physical(database)
    if before["revisions"] != 46:
        raise AssertionError(before)
    old_copy = projection._copy_decoded_value
    use_baseline = case.startswith("A")
    counts = defaultdict(float)

    def baseline(value, attribute_hints=None):
        memo = {_SPORTING_ATTRIBUTE_COPY_MEMO_KEY: dict(attribute_hints or {})}
        copied = deepcopy(value, memo)
        return copied, memo[_SPORTING_ATTRIBUTE_COPY_MEMO_KEY]

    chosen = baseline if use_baseline else old_copy

    def measured_copy(value, attribute_hints=None):
        wall = time.perf_counter()
        cpu = time.thread_time()
        try:
            return chosen(value, attribute_hints)
        finally:
            counts["calls"] += 1
            counts["wall_s"] += time.perf_counter() - wall
            counts["thread_cpu_s"] += time.thread_time() - cpu

    projection._copy_decoded_value = measured_copy
    phases = {}
    original_request = flow._request

    def timed(operation, method, url, body=None, expected=200):
        start, cpu = time.perf_counter(), time.process_time()
        status, value = original_request(method, url, body)
        phases[operation] = {
            "wall_s": round(time.perf_counter() - start, 3),
            "process_cpu_s": round(time.process_time() - cpu, 3),
            "status": status,
        }
        if status != expected:
            raise AssertionError((operation, status, str(value)[:300]))
        return value

    try:
        with ApiServer(database_url=f"sqlite:///{database}") as server:
            endpoint = flow.tour_url(server)
            wall_start, cpu_start = time.perf_counter(), time.process_time()
            initial = timed("cold-inspect", "GET", endpoint)
            old_sport = _sport(initial, week=1)
            old_head = initial["saved_head_revision_id"]
            command = flow.command(initial, "transition", name="copy-ab-s2w1-to-s2w2")
            preview = timed("preview", "POST", endpoint + "/preview", command)
            execute = timed("execute", "POST", endpoint + "/execute", {
                "command": command,
                "expected_preview_fingerprint": preview["preview_fingerprint"],
                "explicit_confirmation": True,
            }, expected=201)
            if not execute["manual_save_required"]:
                raise AssertionError("Manual Save was bypassed")
            draft = timed("draft-inspect", "GET", endpoint)
            if draft["saved"] or draft["state"]["week"]["week"] != 2:
                raise AssertionError("Expected real dirty Week2 draft")
            receipt = timed("manual-save", "POST", endpoint + "/save", {
                "expected_draft_version": draft["draft_version"],
                "expected_calendar_tour_fingerprint": draft["tour_fingerprint"],
            }, expected=201)
            final = timed("post-save-inspect", "GET", endpoint)
            after_sport = _sport(final, week=2)
            if old_sport["evidence_hash"] != after_sport["evidence_hash"]:
                raise AssertionError("Real previous match evidence changed")
            if (
                final["saved_head_revision_id"] != receipt["saved_revision"]["revision_id"]
                or final["saved_head_revision_id"] == old_head
            ):
                raise AssertionError("No real new and independently loaded Saved boundary")
            after = _physical(database)
            if after["revisions"] != 47:
                raise AssertionError(("Expected one physical new Saved", after))
            elapsed = time.perf_counter() - wall_start
            total_cpu = time.process_time() - cpu_start
            report = {
                "case": case,
                "comparison": "unchanged-deepcopy" if use_baseline
                else "exact-type-private-copy",
                "source_sha256": SOURCE_SHA,
                "source_original_saved": before,
                "actual_saved": after,
                "new_saved_payload_bytes": (
                    after["saved_payload_bytes"]-before["saved_payload_bytes"]),
                "real_player_count": 256,
                "original_real_sport": old_sport,
                "final_sport": after_sport,
                "request_phase_times": phases,
                "copy_calls": int(counts["calls"]),
                "copy_wall_s": round(counts["wall_s"], 3),
                "copy_server_thread_cpu_s": round(counts["thread_cpu_s"], 3),
                "complete_week_wall_s": round(elapsed, 3),
                "complete_week_process_cpu_s": round(total_cpu, 3),
                "peak_rss_kib": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
                "current_rss_kib": _rss_kib(),
                "production_sporting_logic_changed": False,
                "physical_saved_gates_bypassed": False,
                "notes": "A uses original private deepcopy; B exact typed copy. "
                "Both run production HTTP/SQLite with independent full Saved "
                "lineage verification and real manual Save; no synthetic matches.",
            }
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
            )
            print("NATIVE_PRIVATE_COPY_AB " + json.dumps(
                {"phase": "case", **report}, sort_keys=True
            ), flush=True)
    finally:
        projection._copy_decoded_value = old_copy


def _summary(directory):
    names = ("A1", "B1", "B2", "A2")
    cases = [json.loads((directory / (n + ".json")).read_text()) for n in names]
    # Signed revision IDs and wall times are allowed to differ.
    # Actual stored sporting payload, every player/ranking/stored Tour state
    # and immutable original MatchEngine evidence must be exactly identical.
    invariant = {
        (c["new_saved_payload_bytes"],
         c["actual_saved"]["last_raw_payload_sha256"],
         *tuple(c["final_sport"][key] for key in (
             "player_hash", "state_hash", "evidence_hash", "rankings_hash"
         )))
        for c in cases
    }
    if len(invariant) != 1:
        raise AssertionError("Actual Signed Saved/sporting output diverged across A/B")
    results = {}
    for group in ("A", "B"):
        selection = [c for c in cases if c["case"].startswith(group)]
        results[group] = {
            key: round(statistics.median(c[key] for c in selection), 3)
            for key in ("complete_week_wall_s", "copy_wall_s",
                        "complete_week_process_cpu_s", "peak_rss_kib")
        }
        results[group]["manual_save_wall_s"] = round(statistics.median(
            c["request_phase_times"]["manual-save"]["wall_s"]
            for c in selection), 3)
    a, b = results["A"]["complete_week_wall_s"], results["B"]["complete_week_wall_s"]
    save_a = results["A"]["manual_save_wall_s"]
    save_b = results["B"]["manual_save_wall_s"]
    summary = {
        "source_sha256": SOURCE_SHA,
        "original_complete_week_wall_s": a,
        "candidate_complete_week_wall_s": b,
        "complete_week_wall_percent_change": round(100*(b/a-1), 2),
        "original_manual_save_wall_s": save_a,
        "candidate_manual_save_wall_s": save_b,
        "manual_save_wall_percent_change": round(100*(save_b/save_a-1), 2),
        "A_medians": results["A"],
        "B_medians": results["B"],
        "cases": names,
        "same_saved_payload_and_complete_sportrun": True,
        "actual_24_real_match_results_preserved": True,
        "not_a_1000_player_or_52_week_test": True,
        "limits": "2 A + 2 B fresh processes; likely OS cache effects remain. "
                  "Results for real original 256-player W12 only, no giant W8.",
    }
    (directory / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print("NATIVE_PRIVATE_COPY_AB " + json.dumps(
        {"phase": "summary", **summary}, sort_keys=True
    ), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--case", choices=("A1", "B1", "B2", "A2"))
    mode.add_argument("--summarize", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--output", type=Path)
    a = parser.parse_args()
    if a.summarize is not None:
        _summary(a.summarize)
    elif a.database is not None and a.output is not None:
        _case(a.case, a.database.resolve(strict=True), a.output)
    else:
        parser.error("Case requires --database and --output")
