"""Controlled A-B-B-A comparison of original vs authenticated sporting event append.

Two real implementations are loaded as isolated Python modules. All input
events come from the original W12/256-player physical Saved SQLite artifact.
Preflight independently verifies every original physical Saved envelope once.
Each A/B arm uses new SQLite tables; no production code or source is mutated.

Measure ONLY the per-Save prototype append and exact read, NOT full simulation.
"""
from __future__ import annotations

import argparse
from hashlib import file_digest, sha256
import importlib.util
import inspect
import json
from pathlib import Path
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from beta_engine.domain.run_revisions import saved_revision_content_hash  # noqa: E402

EXPECTED_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"
MODULE_NAME = "calendar_event_content_store_prototype.py"


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def saved_rows(source):
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        for row in db.execute(
            "SELECT revision_id,run_id,branch_id,sequence,parent_revision_id,"
            "kind,payload_schema_version,content_hash,payload_json,change_summary_json "
            "FROM branch_saved_revisions ORDER BY sequence"
        ):
            yield row


def preflight(source):
    proofs = {}
    validated = 0
    for rid, run, branch, seq, parent, kind, schema, saved_hash, body, summary in saved_rows(source):
        decoded = json.loads(body)
        changes = json.loads(summary)
        actual = saved_revision_content_hash(
            revision_id=rid, run_id=run, branch_id=branch, sequence=seq,
            parent_revision_id=parent, kind=kind,
            payload_schema_version=schema, payload=decoded,
            change_summary=changes,
        )
        if actual != saved_hash:
            raise ValueError("Original physical Saved hash mismatch")
        validated += 1
        cp = decoded.get("content", {}).get("calendar_player_sporting_checkpoint")
        state = cp.get("state") if isinstance(cp, dict) else None
        if isinstance(state, dict) and isinstance(state.get("events"), list):
            if state.get("schema_version") != "calendar_sporting_checkpoint.v13":
                raise AssertionError("Expected only global v13 events")
            event_bytes = json.dumps(
                state["events"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            proofs[rid] = (actual, sha256(event_bytes).hexdigest())
    if validated != 46 or len(proofs) != 39:
        raise AssertionError((validated, len(proofs)))
    return proofs


def run_case(module, source, proofs, label):
    con = sqlite3.connect(":memory:")
    module.create_schema(con)
    append_s = 0
    restore_s = 0
    previous = None
    restored_count = 0
    accept_predecessor = "preceding_independently_verified_source_hash" in inspect.signature(module.append).parameters
    accept_array_auth = "independently_verified_event_array_sha256" in inspect.signature(module.restore).parameters
    try:
        for rid, run, branch, seq, parent, kind, schema, saved_hash, body, summary in saved_rows(source):
            verified = proofs.get(rid)
            if verified is None:
                continue
            if verified[0] != saved_hash:
                raise AssertionError("Previous immutable Saved source changed")
            events = json.loads(body)["content"]["calendar_player_sporting_checkpoint"]["state"]["events"]
            args = dict(
                run_id=run, branch_id=branch, revision_id=rid,
                independently_verified_source_hash=saved_hash, events=events,
                preceding_manifest_revision_id=previous,
            )
            if accept_predecessor:
                prior_proof = proofs[previous] if previous is not None else (None,None)
                args.update(
                    preceding_independently_verified_source_hash=prior_proof[0],
                    preceding_independently_verified_event_array_sha256=prior_proof[1],
                )
            start = time.perf_counter()
            module.append(con, **args)
            append_s += time.perf_counter() - start
            read_args = {
                "run_id":run, "branch_id":branch, "revision_id":rid,
                "independently_verified_source_hash":saved_hash,
            }
            if accept_array_auth:
                read_args["independently_verified_event_array_sha256"] = verified[1]
            start = time.perf_counter()
            replay = module.restore(con, **read_args)
            restore_s += time.perf_counter() - start
            if module._canonical(replay) != module._canonical(events):
                raise AssertionError("Exact historic events were not reconstructed")
            previous = rid
            restored_count += 1
        metrics = module.stats(con)
        if metrics["nodes"] != 15 or metrics["manifests"] != 39:
            raise AssertionError((label, metrics))
        return {
            "case":label,
            "append_only_wall_s":round(append_s,3),
            "authentic_restore_wall_s":round(restore_s,3),
            "same_source_authenticated_proofs":len(proofs),
            "exactly_reconstructed":restored_count,
            "nodes":metrics["nodes"],
            "manifests":metrics["manifests"],
            "physical_node_bytes":metrics["node_bytes"],
            "physical_manifest_bytes":metrics["manifest_bytes"],
            "independent_array_binding":accept_array_auth,
            "preceding_signed_array_check":accept_predecessor,
        }
    finally:
        con.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database",type=Path,required=True)
    p.add_argument("--original-module",type=Path,required=True)
    p.add_argument("--candidate-module",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    source=args.database.resolve(strict=True)
    with source.open("rb") as f:
        assert file_digest(f, "sha256").hexdigest() == EXPECTED_SHA
    start=time.perf_counter()
    proofs=preflight(source)
    print("W12_EVENT_APPEND_AB "+json.dumps({"phase":"preflight","source_sha256":EXPECTED_SHA,
        "verified_saved_revisions":46,"authenticated_original_event_arrays":len(proofs)}),flush=True)
    original=load_file("event_store_before",args.original_module.resolve(strict=True))
    candidate=load_file("event_store_after",args.candidate_module.resolve(strict=True))
    cases=[]
    for label, module in [("A1", original),("B1",candidate),("B2",candidate),("A2",original)]:
        result=run_case(module, source,proofs,label)
        cases.append(result)
        print("W12_EVENT_APPEND_AB "+json.dumps({"phase":"case",**result},sort_keys=True),flush=True)
    assert len({(x["nodes"],x["manifests"],x["physical_node_bytes"],x["physical_manifest_bytes"])
                for x in cases}) == 1
    a=statistics.median(x["append_only_wall_s"] for x in cases if x["case"].startswith("A"))
    b=statistics.median(x["append_only_wall_s"] for x in cases if x["case"].startswith("B"))
    report={
        "source_run":43919075227,
        "original_module_commit":"c7f631e102e20d849214d900885326ebcb564c79",
        "production_integration":False,
        "source_sha256":EXPECTED_SHA,
        "verified_original_saved_revisions":46,
        "exact_historical_reconstructions_per_case":39,
        "case_order":[x["case"] for x in cases],
        "original_median_append_s":round(a,3),
        "candidate_median_append_s":round(b,3),
        "candidate_append_percent_change":round(100*(b/a-1),2),
        "cases":cases,
        "total_wall_s":round(time.perf_counter()-start,3),
        "limits":"Only isolated prototype append; not production Saved, not full season. "
                 "Two samples per arm; security baseline differs because candidate "
                 "also requires independent original array binding.",
    }
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"paired-appends.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("W12_EVENT_APPEND_AB "+json.dumps({"phase":"summary",**report},sort_keys=True),flush=True)


if __name__=="__main__":
    main()
