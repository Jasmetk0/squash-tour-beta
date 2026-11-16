"""Same-SQLite native Saved cold GET, paired baseline/Claude #1803 A/B.

Production code in each process comes exclusively from its checkout
(PYTHONPATH set by CI). This script never writes results or bypasses validation.
The archived source DB is copied separately before every fresh interpreter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import statistics
import sys
import time
from urllib import request


def _fingerprint_json(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def run_one(args):
    from tests.api.test_saved_revision_history_api import ApiServer

    source = args.database.resolve(strict=True)
    assert source.is_file() and source.name == "native-case.sqlite"
    started = time.perf_counter()
    cpu_started = time.process_time()
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        setup_wall_s = time.perf_counter() - started
        endpoint = server.base_url + "/admin/runs/run/branches/branch/calendar-tour"
        before = time.perf_counter()
        cpu_before = time.process_time()
        with request.urlopen(endpoint, timeout=600) as response:
            assert response.status == 200
            body = response.read()
        cold_wall = time.perf_counter() - before
        cold_cpu = time.process_time() - cpu_before
        state = json.loads(body)
        assert state["saved"]
        assert len(state["players"]) == 256
        assert (state["state"]["week"]["season_index"],
                state["state"]["week"]["week"]) == (1, 1)
        assert len(state["state"]["editions"]) == 8
        for week in (4, 5):
            for index in range(4):
                edition = f"load-w{week}-{index}"
                assert len(state["edition_evidence"][edition]["matches"]) == 3
                assert next(
                    item["result_confirmed"]
                    for item in state["state"]["editions"]
                    if item["edition"]["edition_id"] == edition
                )
        output = {
            "case": args.case,
            "cold_http_wall_s": round(cold_wall, 3),
            "cold_http_process_cpu_s": round(cold_cpu, 3),
            "application_setup_wall_s": round(setup_wall_s, 3),
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "response_bytes": len(body),
            "complete_inspection_sha256": _fingerprint_json(state),
            "saved_head_revision_id": state["saved_head_revision_id"],
            "player_count": len(state["players"]),
            "played_edition_count": 8,
            "genuine_match_count": 24,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as out:
        json.dump(output, out, indent=2, sort_keys=True)
    print("W12_SAVED_AB_CASE " + json.dumps(output, sort_keys=True), flush=True)


def summarize(args):
    root = args.summary.resolve(strict=True)
    results = {name: json.loads((root / f"{name}.json").read_text())
               for name in ("A1", "B1", "B2", "A2")}
    fingerprints = {x["complete_inspection_sha256"] for x in results.values()}
    heads = {x["saved_head_revision_id"] for x in results.values()}
    assert len(fingerprints) == len(heads) == 1, (
        "Production response changed between original and candidate!",
        results,
    )
    before = [results[x]["cold_http_wall_s"] for x in ("A1", "A2")]
    after = [results[x]["cold_http_wall_s"] for x in ("B1", "B2")]
    before_cpu = [results[x]["cold_http_process_cpu_s"] for x in ("A1", "A2")]
    after_cpu = [results[x]["cold_http_process_cpu_s"] for x in ("B1", "B2")]
    median_a, median_b = statistics.median(before), statistics.median(after)
    report = {
        "base_commit": "320e4766ec8ba78e3de20153b8aaada90585b0cf",
        "candidate_commit": "136b277a6b246da8bd01bca7b2e1668f35983fad",
        "source_run": 43919075227,
        "same_saved_response_sha256": next(iter(fingerprints)),
        "original_cold_wall_s": before,
        "candidate_cold_wall_s": after,
        "original_cold_cpu_s": before_cpu,
        "candidate_cold_cpu_s": after_cpu,
        "original_median_cold_wall_s": round(median_a, 3),
        "candidate_median_cold_wall_s": round(median_b, 3),
        "median_wall_percent_change": round(100 * (median_b / median_a - 1), 2),
        "paired_order": ["original A1", "candidate B1",
                         "candidate B2", "original A2"],
        "result_provenance": "same original archived W12 SQLite; new file copy per case",
        "measurements": results,
        "note": "Two fresh-process samples per arm; exploratory A/B, not production certification",
    }
    with (root / "summary.json").open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
    print("W12_SAVED_AB_SUMMARY " + json.dumps(report, sort_keys=True), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", choices=["A1", "B1", "B2", "A2"])
    group.add_argument("--summary", type=Path)
    p.add_argument("--database", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.summary is not None:
        summarize(args)
    else:
        if args.database is None or args.out is None:
            p.error("--database and --out required for one case")
        run_one(args)


if __name__ == "__main__":
    main()
