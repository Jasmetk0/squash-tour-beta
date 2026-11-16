"""Replay actual W12/256/8-Edition Saved events through scoped SQLite prototype.

Runs on physical archived full-production Run from GitHub Actions #43919075227.
The original SQLite is opened READ-ONLY, every complete original Saved content
hash is independently revalidated, and every historical events array is exactly
rebuilt. New prototype tables live only in a disposable temporary SQLite DB.
No server/production code path is altered.
"""
from __future__ import annotations

import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path
import resource
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from beta_engine.domain.run_revisions import saved_revision_content_hash  # noqa: E402
from beta_engine.infrastructure.db import (  # noqa: E402
    calendar_event_content_store_prototype as ev,
)


SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"


def run(source_file: Path, output: Path):
    source_file = source_file.resolve(strict=True)
    with source_file.open("rb") as handle:
        if file_digest(handle, "sha256").hexdigest() != SOURCE_SHA:
            raise ValueError("Not the exact audited W12/256-player source SQLite")
    started = time.perf_counter()
    original_bytes = 0
    parent_manifest = None
    accepted = []
    state_schema_versions = {}
    sink = sqlite3.connect(":memory:")
    ev.create_schema(sink)
    with sqlite3.connect(f"file:{source_file}?mode=ro", uri=True) as source:
        source.execute("PRAGMA query_only=ON")
        cursor = source.execute(
            "SELECT revision_id,run_id,branch_id,sequence,parent_revision_id,"
            "kind,payload_schema_version,content_hash,payload_json,change_summary_json "
            "FROM branch_saved_revisions ORDER BY sequence"
        )
        all_rows = 0
        verified_saved_hashes = 0
        for (
            revision_id, run_id, branch_id, sequence, parent_revision_id,
            kind, payload_schema_version, source_hash, stored, summary,
        ) in cursor:
            all_rows += 1
            # Complete ordinary Saved hash is independently recomputed from the
            # physically stored text, including identity, ancestry and summary.
            payload = json.loads(stored)
            change_summary = json.loads(summary)
            actual_hash = saved_revision_content_hash(
                revision_id=revision_id, run_id=run_id, branch_id=branch_id,
                sequence=sequence, parent_revision_id=parent_revision_id,
                kind=kind, payload_schema_version=payload_schema_version,
                payload=payload, change_summary=change_summary,
            )
            if actual_hash != source_hash:
                raise ValueError("Original physical Saved hash mismatch")
            verified_saved_hashes += 1

            cp = payload.get("content", {}).get("calendar_player_sporting_checkpoint")
            if not isinstance(cp, dict) or not isinstance(cp.get("state"), dict):
                continue
            state = cp["state"]
            if not isinstance(state.get("events"), list):
                continue
            if state.get("schema_version") != "calendar_sporting_checkpoint.v13":
                raise ValueError("Unexpected sporting state event schema")
            state_schema_versions[state["schema_version"]] = (
                state_schema_versions.get(state["schema_version"], 0) + 1
            )
            events = state["events"]
            original_array_bytes = len(ev._canonical(events).encode())
            original_bytes += original_array_bytes
            ev.append(
                sink, run_id=run_id, branch_id=branch_id,
                revision_id=revision_id,
                independently_verified_source_hash=actual_hash,
                events=events, preceding_manifest_revision_id=parent_manifest,
            )
            rebuilt = ev.restore(
                sink, run_id=run_id, branch_id=branch_id,
                revision_id=revision_id,
                independently_verified_source_hash=actual_hash,
            )
            if ev._canonical(rebuilt) != ev._canonical(events):
                raise AssertionError("Reconstructed physical sport differs")
            accepted.append({
                "revision_id": revision_id, "content_hash": actual_hash,
                "original_event_array_sha256": sha256(ev._canonical(events).encode()).hexdigest(),
                "original_event_count": len(events),
                "original_event_array_bytes": original_array_bytes,
            })
            parent_manifest = revision_id
            if len(accepted) % 10 == 0:
                print("W12_SCOPED_EVENT_STORE " + json.dumps({
                    "phase": "checkpoint", "snapshots": len(accepted),
                    "latest_events": len(events),
                }), flush=True)

    if verified_saved_hashes != 46 or len(accepted) != 39:
        raise AssertionError((verified_saved_hashes, len(accepted)))
    expected_counts = {record["original_event_count"] for record in accepted}
    if max(expected_counts) != 15:
        raise AssertionError(expected_counts)

    metrics = ev.stats(sink)
    # Source owner is proofed against the complete physical Saved row and
    # replayed by the experimental store, but this is not production-integrated.
    latest = accepted[-1]
    node = sink.execute(
        "SELECT event_sha256, canonical_event_json FROM "
        "experimental_sporting_event_nodes LIMIT 1"
    ).fetchone()
    assert node is not None
    node_sha, original_node = node
    sink.execute(
        "UPDATE experimental_sporting_event_nodes SET canonical_event_json=? "
        "WHERE event_sha256=?", (original_node + " ", node_sha)
    )
    try:
        ev.restore(
            sink, run_id="run", branch_id="branch",
            revision_id=latest["revision_id"],
            independently_verified_source_hash=latest["content_hash"],
        )
    except ev.SportingEventStoreError:
        tampering_rejected = True
    else:
        raise AssertionError("Tampered physical node escaped verification")
    sink.execute(
        "UPDATE experimental_sporting_event_nodes SET canonical_event_json=? "
        "WHERE event_sha256=?", (original_node, node_sha)
    )
    if ev._canonical(ev.restore(
        sink, run_id="run", branch_id="branch",
        revision_id=latest["revision_id"],
        independently_verified_source_hash=latest["content_hash"],
    )) == "":
        raise AssertionError("Nonsensical repaired source")

    # The physical ancestor manifest must also be authenticated on every read,
    # and cannot be freely rewritten after successful warm reconstruction.
    first = accepted[0]
    sink.execute(
        "UPDATE experimental_sporting_event_manifests SET manifest_json='{}' "
        "WHERE revision_id=?", (first["revision_id"],)
    )
    try:
        ev.restore(
            sink, run_id="run", branch_id="branch",
            revision_id=latest["revision_id"],
            independently_verified_source_hash=latest["content_hash"],
        )
    except ev.SportingEventStoreError:
        ancestor_tamper_rejected = True
    else:
        raise AssertionError("Retroactive manifest edit escaped verification")

    report = {
        "source_run": 43919075227,
        "source_sqlite_sha256": SOURCE_SHA,
        "source_verified_saved_revisions": verified_saved_hashes,
        "original_competition_state_schemas": state_schema_versions,
        "restored_original_event_lists": len(accepted),
        "max_event_count": max(expected_counts),
        "all_historical_event_bytes": original_bytes,
        "prototype_node_bytes": metrics["node_bytes"],
        "prototype_manifest_bytes": metrics["manifest_bytes"],
        "prototype_total_text_bytes": metrics["total_payload_bytes"],
        "unique_physical_event_nodes": metrics["nodes"],
        "exact_authenticated_manifests": metrics["manifests"],
        "hypothetical_event_only_storage_reduction_percent": round(
            100 * (1 - metrics["total_payload_bytes"] / original_bytes), 3
        ),
        "physical_node_tamper_rejected": tampering_rejected,
        "ancestor_manifest_tamper_rejected": ancestor_tamper_rejected,
        "analysis_wall_s": round(time.perf_counter() - started, 3),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "production_integration": False,
        "not_measured": [
            "full per-revision Saved envelope compression",
            "production end-to-end season speed",
            "fork, restore, rollback, mixed-version migration on real source",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "w12-scoped-event-prototype.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print("W12_SCOPED_EVENT_STORE " + json.dumps({
        "phase": "complete", **report,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.database, args.out)
