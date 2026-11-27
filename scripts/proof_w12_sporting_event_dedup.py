"""Offline proof of exact historical W12 sporting-event reconstruction.

NOT a production schema, not a replacement Saved hash, not a migration.
Reads the real signed 256-player W12 physical SQLite database read-only.
All 39 historical v13 events arrays must rebuild byte-for-byte from unique
sha256-named canonical event objects. Tampering and order changes must fail.
"""
from __future__ import annotations

import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sqlite3
import time

SOURCE_SHA256 = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()


def reconstruct(manifest, objects, expected_hash):
    chunks = []
    for event_hash in manifest:
        stored = objects.get(event_hash)
        if stored is None or sha256(stored).hexdigest() != event_hash:
            raise ValueError("Missing or physically corrupted event content")
        chunks.append(stored)
    full = b"[" + b",".join(chunks) + b"]"
    if sha256(full).hexdigest() != expected_hash:
        raise ValueError("Authenticated historical array changed")
    return full


def run(source, out):
    source = source.resolve(strict=True)
    with source.open("rb") as handle:
        assert file_digest(handle, "sha256").hexdigest() == SOURCE_SHA256
    objects = {}
    manifests = []
    full_snapshot_bytes = 0
    max_size = 0
    prefix_checks = 0
    prior = None
    start = time.perf_counter()

    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as db:
        for seq, raw in db.execute(
            "SELECT sequence, payload_json FROM branch_saved_revisions ORDER BY sequence"
        ):
            decoded = json.loads(raw)
            cp = decoded.get("content", {}).get("calendar_player_sporting_checkpoint")
            if not isinstance(cp, dict):
                continue
            state = cp.get("state")
            if not isinstance(state, dict) or not isinstance(state.get("events"), list):
                continue
            events = state["events"]
            manifest = []
            for event in events:
                blob = canonical(event)
                digest = sha256(blob).hexdigest()
                if digest in objects and objects[digest] != blob:
                    raise AssertionError("SHA-256 event identity collision")
                objects[digest] = blob
                manifest.append(digest)
            actual_encoded = canonical(events)
            if prior is not None:
                if manifest[:len(prior)] != prior or len(manifest) < len(prior):
                    raise ValueError(f"Non-append-only event edit at Saved sequence {seq}")
                prefix_checks += 1
            prior = manifest
            manifests.append({
                "sequence": int(seq), "manifest": manifest,
                "original_array_sha256": sha256(actual_encoded).hexdigest(),
                "original_array_bytes": len(actual_encoded),
            })
            full_snapshot_bytes += len(actual_encoded)
            max_size = max(max_size, len(actual_encoded))

    assert len(manifests) == 39 and prefix_checks == 38
    started_reconstruct = time.perf_counter()
    for row in manifests:
        assert len(reconstruct(
            row["manifest"], objects, row["original_array_sha256"]
        )) == row["original_array_bytes"]
    reconstruct_wall = time.perf_counter() - started_reconstruct

    # Deliberately corrupt the originally archived first event object's actual
    # content, then verify there is NO trusted replay even with the same key.
    bad_key = manifests[-1]["manifest"][0]
    original = objects[bad_key]
    objects[bad_key] = original + b" "
    try:
        reconstruct(manifests[-1]["manifest"], objects,
                    manifests[-1]["original_array_sha256"])
    except ValueError:
        corrupted_content_rejected = True
    else:
        raise AssertionError("Physically corrupted event bytes were accepted")
    finally:
        objects[bad_key] = original

    # A reordered historic manifest must never reconstruct under its original
    # authenticated array hash even though every individual event is valid.
    reversed_manifest = list(reversed(manifests[-1]["manifest"]))
    try:
        reconstruct(reversed_manifest, objects,
                    manifests[-1]["original_array_sha256"])
    except ValueError:
        reordered_events_rejected = True
    else:
        raise AssertionError("Reordered sporting event history was accepted")

    unique_bytes = sum(map(len, objects.values()))
    manifests_bytes = sum(len(canonical(x["manifest"])) for x in manifests)
    result = {
        "source_sha256": SOURCE_SHA256,
        "historical_event_snapshots": len(manifests),
        "validated_prefix_pairs": prefix_checks,
        "unique_verified_events": len(objects),
        "original_all_snapshot_event_bytes": full_snapshot_bytes,
        "unique_event_bytes": unique_bytes,
        "manifest_json_bytes": manifests_bytes,
        "hypothetical_event_storage_bytes": unique_bytes + manifests_bytes,
        "hypothetical_event_only_reduction_percent": round(
            100 * (1 - (unique_bytes + manifests_bytes) / full_snapshot_bytes), 3
        ),
        "max_single_original_event_array_bytes": max_size,
        "full_exact_historical_reconstructions": len(manifests),
        "reconstruction_wall_s": round(reconstruct_wall, 3),
        "total_analysis_wall_s": round(time.perf_counter() - start, 3),
        "corrupted_content_rejected": corrupted_content_rejected,
        "reordered_events_rejected": reordered_events_rejected,
        "production_integration": False,
        "caution": "Potential bytes for event-list only, excluding DB indexes, "
                   "full Saved envelope/ancestor verification and authenticated "
                   "manifest ownership. Other Runs can mutate histories. "
                   "Never use this as unverified production storage.",
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "event-dedup-proof.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("W12_EVENT_DEDUP_PROOF " + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    run(args.database, args.out)
