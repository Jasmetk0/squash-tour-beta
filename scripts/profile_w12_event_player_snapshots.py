"""Read-only forensic sizes of repeated real sporting player snapshots in W12.

Measures individual PlayerSportingRecord JSON texts held inside the 15 unique
v13 GlobalCompetitionCheckpoint events on the 256-player original physical
SQLite; does not generate simulated outcomes or edit the original source.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path
import resource
import sqlite3
import time

SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def run(source, out):
    source = source.resolve(strict=True)
    with source.open("rb") as f:
        assert file_digest(f, "sha256").hexdigest() == SOURCE_SHA
    before=time.perf_counter()
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        raw=connection.execute(
            "SELECT payload_json FROM branch_saved_revisions ORDER BY sequence DESC LIMIT 1"
        ).fetchone()[0]
    events=json.loads(raw)["content"]["calendar_player_sporting_checkpoint"]["state"]["events"]
    assert len(events)==15
    original_event_bytes=sum(len(canonical(x)) for x in events)
    unique_snapshots={}
    kinds=defaultdict(lambda:{"events":0,"player_arrays":0,"player_snapshots":0,
                                  "all_player_object_bytes":0,"unique_snapshot_hashes":set(),
                                  "players_seen":set(),"unchanged_from_previous":0,
                                  "changed_from_previous":0,"all_array_bytes":0})
    entry_details=[]
    previous_by_player={}
    total_snapshots=0
    cumulative_player_bytes=0
    for ix, event in enumerate(events):
        kind=event.get("schema_version","unknown")
        # Real v13 event variants, not inferred from unrelated model versions.
        if kind=="calendar_native_sporting_week.v1":
            advance=event.get("advance")
            if not isinstance(advance,dict):
                raise AssertionError("Missing actual signed week advance")
            arrays={"completed_players":advance.get("completed_players"),
                    "target_players":advance.get("target_players")}
        elif kind=="calendar_global_slot.v1":
            arrays={"players":event.get("players")}
        else:
            raise AssertionError((ix,kind))
        stats=kinds[kind]
        stats["events"]+=1
        detail={"event_index":ix,"kind":kind,"event_bytes":len(canonical(event)),
                "player_arrays":{}}
        for field, players in arrays.items():
            if not isinstance(players,list):
                raise AssertionError((kind,field,"no physical player array"))
            stats["player_arrays"]+=1
            array_bytes=len(canonical(players))
            stats["all_array_bytes"]+=array_bytes
            total_player_objects=0
            per_array_unique=set()
            for player in players:
                if not isinstance(player,dict) or type(player.get("player_id")) is not str:
                    raise AssertionError((ix,field,"invalid player JSON"))
                text=canonical(player)
                digest=sha256(text).hexdigest()
                pid=player["player_id"]
                if digest not in unique_snapshots:
                    unique_snapshots[digest]=len(text)
                per_array_unique.add(digest)
                stats["unique_snapshot_hashes"].add(digest)
                stats["players_seen"].add(pid)
                stats["player_snapshots"]+=1
                stats["all_player_object_bytes"]+=len(text)
                total_snapshots+=1
                total_player_objects+=len(text)
                cumulative_player_bytes+=len(text)
                prior=previous_by_player.get(pid)
                if prior is not None:
                    if prior == digest:
                        stats["unchanged_from_previous"]+=1
                    else:
                        stats["changed_from_previous"]+=1
                previous_by_player[pid]=digest
            detail["player_arrays"][field]={
                "players":len(players),"array_bytes":array_bytes,
                "player_object_bytes":total_player_objects,
                "unique_snapshot_hashes_in_array":len(per_array_unique),
            }
        entry_details.append(detail)
    assert total_snapshots > 0
    result={
        "source_sha256":SOURCE_SHA,
        "distinct_v13_events":len(events),
        "all_unique_event_bytes":original_event_bytes,
        "player_object_occurrences":total_snapshots,
        "repeated_player_object_bytes":cumulative_player_bytes,
        "exact_unique_player_object_count":len(unique_snapshots),
        "exact_unique_player_object_bytes":sum(unique_snapshots.values()),
        "player_object_exact_dedup_percent":round(
            100*(1-sum(unique_snapshots.values())/cumulative_player_bytes),3),
        "kinds":{
            key:{**{k:v for k,v in val.items() if k not in
                    ("unique_snapshot_hashes","players_seen")},
                "exact_distinct_player_object_versions":len(val["unique_snapshot_hashes"]),
                "unique_player_ids":len(val["players_seen"])}
            for key,val in kinds.items()
        },
        "details":entry_details,
        "wall_s":round(time.perf_counter()-before,3),
        "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "caution":"Exact player-object duplication inside 15 already-distinct events "
                  "in one verified source. Not a safe serializer/schema change, "
                  "not a full SQLite DB or season speedup; cross-event snapshot "
                  "sharing requires owner-aware sporting state verification.",
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"player-snapshot-dedup.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("W12_EVENT_PLAYER_OBJECTS "+json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    run(args.database,args.out)
