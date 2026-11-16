"""Compare Claude's unchanged generic Merkle prototype node thresholds on REAL W12 events.

Proof-only: loads the authentic 256-player/8-Edition original final Saved state
read-only, then constructs independent in-memory Merkle node stores for 15
real v13 sporting events at thresholds 4096/2048/1024/512 bytes. This does NOT
write production DB or assert sports-semantic integrity from Merkle alone.
"""
from __future__ import annotations

import argparse
from hashlib import file_digest
import importlib.util
import json
from pathlib import Path
import resource
import sqlite3
import time

SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76db96ab39fb0ae51ab78e7"
# Correct pinned real source digest is below; use the exact audited database.
SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"


def load_module(path):
    spec=importlib.util.spec_from_file_location("claude_original_merkle_prototype",path)
    assert spec is not None and spec.loader is not None
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(db_file, original_module_file, out):
    db_file=db_file.resolve(strict=True)
    with db_file.open("rb") as f:
        assert file_digest(f,"sha256").hexdigest()==SOURCE_SHA
    mj=load_module(original_module_file.resolve(strict=True))
    with sqlite3.connect(f"file:{db_file}?mode=ro",uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        (payload_json,)=db.execute(
            "SELECT payload_json FROM branch_saved_revisions ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    events=json.loads(payload_json)["content"]["calendar_player_sporting_checkpoint"]["state"]["events"]
    if len(events)!=15:
        raise AssertionError("Expected 15 authentic v13 events only")
    originals=[mj.canonical(x) for x in events]
    original_event_bytes=sum(len(x.encode()) for x in originals)
    reports=[]
    for threshold in (4096,2048,1024,512):
        store={}
        roots=[]
        started=time.perf_counter()
        new_nodes_total=0
        writer_bytes=0
        for item in events:
            root, stats=mj.encode(item,store,threshold=threshold)
            roots.append(root)
            new_nodes_total+=stats["new_nodes"]
            writer_bytes+=stats["new_bytes"]
        writer_wall=time.perf_counter()-started
        stored=sum(len(v.encode()) for v in store.values())
        started=time.perf_counter()
        reader=mj.Reader(store)
        for root in roots:
            if "digest" in root:
                reader.verify(root["digest"])
        cold_verify_wall=time.perf_counter()-started
        started=time.perf_counter()
        for root,original in zip(roots,originals):
            restored=mj.decode_root(root,mj.Reader(store))
            if mj.canonical(restored)!=original:
                raise AssertionError((threshold,"original event changed"))
        exact_rebuild_wall=time.perf_counter()-started
        if len(store)==0:
            raise AssertionError("Expected actual Merkle nodes")
        root_key=roots[-1]["digest"]
        original_root_body=store[root_key]
        store[root_key]=original_root_body+" "
        try:
            mj.Reader(store).verify(root_key)
        except mj.MerkleError:
            corrupted_last_root_rejected=True
        else:
            raise AssertionError("Modified actual physical node survived digest gate")
        finally:
            store[root_key]=original_root_body
        item={
            "threshold_bytes":threshold,"original_unique_event_bytes":original_event_bytes,
            "new_node_count":len(store),"inserted_nodes":new_nodes_total,
            "new_node_text_bytes":stored,"writer_observed_bytes":writer_bytes,
            "new_node_bytes_percent_of_original":round(100*stored/original_event_bytes,3),
            "hypothetical_nested_unique_event_reduction_percent":round(
                100*(1-stored/original_event_bytes),3),
            "writer_wall_s":round(writer_wall,3),
            "cold_physical_all_node_verification_wall_s":round(cold_verify_wall,3),
            "cold_verified_node_bytes":reader.hashed_bytes,
            "exact_15_event_reconstruction_wall_s":round(exact_rebuild_wall,3),
            "exact_event_reconstructions":15,
            "corrupted_node_rejected":corrupted_last_root_rejected,
        }
        reports.append(item)
        print("W12_MERKLE_THRESHOLD "+json.dumps({"phase":"case",**item},sort_keys=True),flush=True)
    result={
        "source_run":43919075227,
        "physical_source_sha256":SOURCE_SHA,
        "claude_generic_prototype_sha":"4c7271144e02580d8d33a9b2bfb56f12d9ad2156",
        "event_count":15,
        "original_unique_event_bytes":original_event_bytes,
        "results":reports,
        "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "production_integration":False,
        "limits":"Pure in-memory Merkle prototype on 15 already unique events. "
                 "Not full Saved v2 storage, not SQL indexes/metadata, "
                 "not per-revision source replay, not native week/season speed.",
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"original-event-merkle-thresholds.json").write_text(
        json.dumps(result,indent=2),encoding="utf-8"
    )
    print("W12_MERKLE_THRESHOLD "+json.dumps({"phase":"complete",**result},sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database",type=Path,required=True)
    p.add_argument("--claude-module",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.database,a.claude_module,a.out)
