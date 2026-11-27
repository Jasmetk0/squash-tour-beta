"""Diagnostic only: real W12/256 Saved growth and one authentic manual Save.

Works on disposable copies of the original *played* W12/256 SQLite artifact.
Uses production HTTP / SQLite and authentic revision integrity; never changes
history hash format, sporting results or shipped engine code.
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
import threading
import time
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.api.test_saved_revision_history_api import ApiServer  # noqa: E402

PREFIX = "W12_SAVED_GROWTH_WRITE "
SOURCE_DIGEST = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"


def emit(name, **data):
    print(PREFIX + json.dumps({"phase": name, **data}, sort_keys=True), flush=True)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def assert_input(db_file):
    db_file = db_file.resolve(strict=True)
    with db_file.open("rb") as inp:
        actual = hashlib.file_digest(inp, "sha256").hexdigest()
    if actual != SOURCE_DIGEST:
        raise ValueError(f"Unexpected source SQLite SHA-256 {actual}")
    return db_file


def rows_ro(db_file):
    with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as db:
        return db.execute(
            "SELECT revision_id, sequence, payload_json, content_hash "
            "FROM branch_saved_revisions ORDER BY sequence ASC"
        ).fetchall()


def sizes_ro(db_file):
    with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as db:
        n, bytes_total = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))),0) "
            "FROM branch_saved_revisions"
        ).fetchone()
    return {"revision_count": int(n), "payload_json_bytes": int(bytes_total),
            "sqlite_file_bytes": db_file.stat().st_size}


def storage_profile(db_file, output):
    """Exact, per-field re-encoding accounting, with no deduplication claims."""
    source = assert_input(db_file)
    metrics = {}
    previous_fingerprints = {}
    overall = defaultdict(lambda: {"total_encoded_bytes": 0, "revisions": 0,
                                   "unchanged_from_previous_bytes": 0,
                                   "unchanged_transitions": 0,
                                   "distinct_exact_values": set(),
                                   "last_encoded_bytes": 0})
    revision_sizes = []
    started = time.perf_counter()
    # Fetching all 708 MiB into memory would inflate RSS; read one row at a time.
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as db:
        cursor = db.execute(
            "SELECT sequence, kind, payload_json FROM branch_saved_revisions "
            "ORDER BY sequence"
        )
        for sequence, kind, raw in cursor:
            doc = json.loads(raw)
            raw_n = len(raw.encode())
            revision_sizes.append({"sequence": int(sequence), "kind": kind,
                                   "raw_bytes": raw_n})
            layers = {}
            for root in ("run", "branch", "content"):
                if root in doc:
                    layers["root." + root] = doc[root]
            if isinstance(doc.get("content"), dict):
                for key, subtree in doc["content"].items():
                    layers["content." + key] = subtree
                for parent in ("calendar_tour", "native_fork_runtime"):
                    if isinstance(doc["content"].get(parent), dict):
                        value = doc["content"][parent]
                        if isinstance(value.get("state"), dict):
                            for key, subtree in value["state"].items():
                                layers[f"{parent}.state.{key}"] = subtree

            for layer, value in layers.items():
                encoded = canonical_bytes(value)
                length = len(encoded)
                digest = hashlib.sha256(encoded).hexdigest()
                info = overall[layer]
                info["total_encoded_bytes"] += length
                info["revisions"] += 1
                info["last_encoded_bytes"] = length
                info["distinct_exact_values"].add(digest)
                if previous_fingerprints.get(layer) == digest:
                    info["unchanged_from_previous_bytes"] += length
                    info["unchanged_transitions"] += 1
                previous_fingerprints[layer] = digest
            # Keep no JSON trees from previous revision; the hashes suffice.
            if int(sequence) % 10 == 0:
                emit("storage-scan", sequence=int(sequence), kind=kind,
                     raw_payload_bytes=raw_n)
    assert len(revision_sizes) == 46, revision_sizes
    data = {
        "source_sha256": SOURCE_DIGEST,
        "source": sizes_ro(source),
        "first_revision_bytes": revision_sizes[0]["raw_bytes"],
        "final_revision_bytes": revision_sizes[-1]["raw_bytes"],
        "payload_growth_factor": round(revision_sizes[-1]["raw_bytes"]
                                       / revision_sizes[0]["raw_bytes"], 3),
        "all_revision_sizes": revision_sizes,
        "components": {
            key: {**{k: v for k, v in d.items() if k != "distinct_exact_values"},
                  "distinct_exact_values": len(d["distinct_exact_values"])}
            for key, d in sorted(overall.items(),
                                 key=lambda kv: kv[1]["total_encoded_bytes"],
                                 reverse=True)
        },
        "analysis_wall_s": round(time.perf_counter() - started, 3),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "interpretation": (
            "unchanged_from_previous_bytes counts replicated identical component "
            "values, NOT directly reclaimable bytes: integrity and recovery require "
            "a separately proven authenticated deduplication storage design"
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "storage.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    emit("storage-complete", first_revision_bytes=data["first_revision_bytes"],
         final_revision_bytes=data["final_revision_bytes"],
         growth_factor=data["payload_growth_factor"],
         largest_components=[{"name": name, **values}
                             for name, values in list(data["components"].items())[:15]],
         peak_rss_kib=data["peak_rss_kib"])
    return data


def call(method, url, payload=None):
    body = None if payload is None else canonical_bytes(payload)
    r = request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(r, timeout=600) as resp:
            raw = resp.read()
            return int(resp.status), json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read()
        return int(exc.code), json.loads(raw) if raw else {}


def assert_view(view, *, week):
    assert view["saved"] is True
    assert len(view["players"]) == 256
    assert len(view["state"]["editions"]) == 8
    assert view["state"]["week"]["season_index"] == 1
    assert view["state"]["week"]["week"] == week
    for target_week in (4, 5):
        for index in range(4):
            name = f"load-w{target_week}-{index}"
            assert len(view["edition_evidence"][name]["matches"]) == 3
            assert next(e["result_confirmed"] for e in view["state"]["editions"]
                        if e["edition"]["edition_id"] == name)


def write_profile(db_file, output):
    """Apply one real S2 W1->W2 week transition + explicit Save to disposable DB."""
    source = db_file.resolve(strict=True)
    if source.name != "native-case.sqlite":
        raise ValueError("Write profile accepts only the disposable native-case.sqlite")
    baseline = sizes_ro(source)
    assert baseline["revision_count"] == 46, baseline

    from beta_engine.application.calendar_tour_service import CalendarTourService
    # Method timers include nested measures and do not add up.
    measures = defaultdict(lambda: {"calls": 0, "wall_s": 0.0, "cpu_s": 0.0})
    patches = []
    lock = threading.Lock()

    def track(obj, method):
        original = getattr(obj, method)

        def wrapper(*args, **kwargs):
            t0, cpu = time.perf_counter(), time.thread_time()
            try:
                return original(*args, **kwargs)
            finally:
                with lock:
                    m = measures[method]
                    m["calls"] += 1
                    m["wall_s"] += time.perf_counter() - t0
                    m["cpu_s"] += time.thread_time() - cpu

        setattr(obj, method, wrapper)
        patches.append((obj, method, original))

    # Track the real server route's native Tour read/preview/execute, as well
    # as the exact repository Save and lineage operations, with no bypasses.
    try:
        with ApiServer(database_url=f"sqlite:///{source}") as server:
            repository = server.app.state.runtime.repository
            track(CalendarTourService, "inspect")
            track(CalendarTourService, "preview")
            track(CalendarTourService, "execute")
            track(repository, "save_viewer_branch_selection_atomically")
            track(repository, "_validated_saved_revision_core_in_session")
            track(repository, "_validated_branch_revision_lineage_core_in_session")
            address = server.base_url + "/admin/runs/run/branches/branch/calendar-tour"

            def timed(label, method, url, payload=None):
                before, cpu = time.perf_counter(), time.process_time()
                code, response = call(method, url, payload)
                result = {
                    "http_code": code,
                    "wall_s": round(time.perf_counter() - before, 3),
                    "process_cpu_s": round(time.process_time() - cpu, 3),
                }
                emit(label, **result)
                if code != (201 if label in ("execute", "manual-save") else 200):
                    raise AssertionError((label, code, response))
                return response, result

            before, cold = timed("cold-inspect", "GET", address)
            assert_view(before, week=1)
            previous_head = before["saved_head_revision_id"]

            command = {
                "action": "transition", "command_id": "profiler-w12-s2w2-transition",
                "edition_id": None,
                "expected_saved_head": previous_head,
                "expected_checkpoint_fingerprint": before["checkpoint_fingerprint"],
                "expected_tour_fingerprint": before["tour_fingerprint"],
                "seed": 231,
                "operator_label": "Admin",
                "audit_reason": "Reviewed S2 W1 to W2 in disposable W12 profiling",
                "data": {},
            }
            preview, preview_metric = timed("preview", "POST",
                                            address + "/preview", command)
            execution, execute_metric = timed("execute", "POST", address + "/execute", {
                "command": command,
                "expected_preview_fingerprint": preview["preview_fingerprint"],
                "explicit_confirmation": True,
            })
            assert execution["manual_save_required"]
            unsaved, unsaved_metric = timed("draft-inspect", "GET", address)
            assert not unsaved["saved"]
            assert unsaved["state"]["week"]["week"] == 2
            receipt, save_metric = timed("manual-save", "POST", address + "/save", {
                "expected_draft_version": unsaved["draft_version"],
                "expected_calendar_tour_fingerprint": unsaved["tour_fingerprint"],
            })
            assert receipt["saved_revision"]["revision_id"] != previous_head
            final, final_metric = timed("post-save-inspect", "GET", address)
            assert_view(final, week=2)
            assert final["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]
            # Observe only a newly added immutable Saved revision; old 46 untouched.
            after = sizes_ro(source)
            assert after["revision_count"] == baseline["revision_count"] + 1, after

            report = {
                "source_sha256": SOURCE_DIGEST, "run_preserved": True,
                "original_tournaments": 8, "original_real_matches": 24,
                "old_saved_head": previous_head,
                "new_saved_head": final["saved_head_revision_id"],
                "original_sqlite": baseline, "after_sqlite": after,
                "added_database_bytes": after["sqlite_file_bytes"] - baseline["sqlite_file_bytes"],
                "added_saved_payload_bytes": after["payload_json_bytes"] - baseline["payload_json_bytes"],
                "timing": {
                    "cold_inspect": cold, "preview": preview_metric,
                    "execute": execute_metric, "draft_inspect": unsaved_metric,
                    "manual_save": save_metric, "post_save_inspect": final_metric,
                },
                "nested_methods": {
                    name: {"calls": int(v["calls"]),
                           "wall_s": round(v["wall_s"], 3),
                           "thread_cpu_s": round(v["cpu_s"], 3)}
                    for name, v in measures.items()
                },
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "note": "Single real production HTTP S2W1->W2+manual Save. "
                        "Nested method timers overlap; baseline unmodified."
            }
            output.mkdir(parents=True, exist_ok=True)
            (output / "write.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            emit("write-complete", **report)
    finally:
        for obj, method, original in reversed(patches):
            setattr(obj, method, original)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("storage", "write"), required=True)
    ap.add_argument("--database", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.mode == "storage":
        storage_profile(args.database, args.out)
    else:
        write_profile(args.database, args.out)


if __name__ == "__main__":
    main()
