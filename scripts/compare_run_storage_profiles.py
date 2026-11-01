#!/usr/bin/env python3
"""Compare two offline Run storage profile.v1 reports without declaring a gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

INPUT_SCHEMA = "run_storage_profile.v1"
OUTPUT_SCHEMA = "run_storage_profile_comparison.v1"
SAVED_FIELDS = ("count", "payload_bytes_sum", "change_summary_bytes_sum", "payload_bytes_max")
PAGE_FIELDS = ("page_size", "page_count", "freelist_count", "allocated_bytes",
               "nonfreelist_page_bytes", "free_page_bytes")


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _number_delta(before: object, after: object, name: str) -> dict:
    first, last = _positive_int(before, f"before {name}"), _positive_int(after, f"after {name}")
    return {"before": first, "after": last, "delta": last - first,
            "percent_change": round(100 * (last - first) / first, 2) if first else None}


def _table(report: dict, name: str) -> dict:
    data = report.get(name)
    if not isinstance(data, dict):
        raise ValueError(f"{name} missing or malformed")
    return data


def _profile(report: object, which: str) -> dict:
    if not isinstance(report, dict) or report.get("schema_version") != INPUT_SCHEMA:
        raise ValueError(f"{which} is not a {INPUT_SCHEMA} report")
    scope = report.get("run_id_scope")
    if scope is not None and (not isinstance(scope, str) or not scope):
        raise ValueError(f"{which} has invalid Run scope")
    for name in ("physical_sizes", "page_metrics", "tables", "branch_saved_revisions", "branch_heads"):
        _table(report, name)
    if report["page_metrics"].get("scope") != "whole_database":
        raise ValueError(f"{which}: page metrics must be whole_database")
    if report.get("saved_revision_totals") is not None and not isinstance(report["saved_revision_totals"], dict):
        raise ValueError(f"{which}: invalid Saved revision totals")
    return report


def _compared_scalar(left: dict, right: dict, field: str, name: str) -> dict:
    return _number_delta(left.get(field), right.get(field), name)


def compare(before: dict, after: dict) -> dict:
    a, b = _profile(before, "before"), _profile(after, "after")
    if a.get("run_id_scope") != b.get("run_id_scope"):
        raise ValueError("Run ID scopes differ; cannot compare unrelated selections")
    measured, unavailable = {}, []

    physical = {}
    for kind in ("db", "wal", "shm"):
        old, new = a["physical_sizes"].get(kind), b["physical_sizes"].get(kind)
        if not isinstance(old, dict) or not isinstance(new, dict):
            raise ValueError(f"Invalid physical {kind} observation")
        if old.get("status") == new.get("status") == "observed":
            physical[kind] = _compared_scalar(old, new, "bytes", f"physical {kind}")
            measured[f"physical.{kind}"] = "whole_database_non_atomic"
        else:
            unavailable.append(f"physical.{kind}: not observed in both measurements")
    pages = {f: _compared_scalar(a["page_metrics"], b["page_metrics"], f, f"page {f}")
             for f in PAGE_FIELDS}
    for key in PAGE_FIELDS:
        measured[f"pages.{key}"] = "whole_database"

    tables = {}
    names = sorted(set(a["tables"]) | set(b["tables"]))
    for name in names:
        left, right = a["tables"].get(name), b["tables"].get(name)
        if not isinstance(left, dict) or not isinstance(right, dict):
            unavailable.append(f"tables.{name}: missing from one report")
            continue
        if left.get("status") != "observed" or right.get("status") != "observed":
            unavailable.append(f"tables.{name}: unavailable in at least one report")
            continue
        scope = left.get("scope")
        if scope not in ("whole_database", "selected_run") or right.get("scope") != scope:
            unavailable.append(f"tables.{name}: differing or unknown measurement scope")
            continue
        tables[name] = {"scope": scope, **_compared_scalar(left, right, "row_count", f"table {name}")}
        measured[f"tables.{name}"] = scope

    revisions = None
    if a.get("saved_revision_totals") is not None and b.get("saved_revision_totals") is not None:
        revisions = {field: _compared_scalar(a["saved_revision_totals"],
                                             b["saved_revision_totals"], field, f"revision {field}")
                     for field in SAVED_FIELDS}
        for field in SAVED_FIELDS:
            measured[f"saved_revisions.{field}"] = "selected_run" if a["run_id_scope"] else "whole_database"
    else:
        unavailable.append("saved_revisions: missing in one or both reports")

    left_branches, right_branches = a["branch_saved_revisions"], b["branch_saved_revisions"]
    common = sorted(left_branches.keys() & right_branches.keys())
    branches = {}
    for branch in common:
        old, new = left_branches[branch], right_branches[branch]
        if not isinstance(old, dict) or not isinstance(new, dict):
            raise ValueError(f"Malformed branch owner metrics for {branch}")
        branches[branch] = {field: _compared_scalar(old, new, field, f"branch {branch} {field}")
                            for field in SAVED_FIELDS}
    # An added or removed Branch is inventory change, not a zero-valued branch delta.
    branch_inventory = {"added": sorted(right_branches.keys() - left_branches.keys()),
                        "removed": sorted(left_branches.keys() - right_branches.keys()),
                        "common": common}
    if not measured:
        raise ValueError("No comparable metrics")
    return {
        "schema_version": OUTPUT_SCHEMA,
        "run_id_scope": a["run_id_scope"],
        "before": {"label": a.get("label"), "snapshot_end_utc": a.get("logical_snapshot_end_utc")},
        "after": {"label": b.get("label"), "snapshot_end_utc": b.get("logical_snapshot_end_utc")},
        "physical_sizes": physical, "pages": pages, "tables": tables,
        "saved_revision_totals": revisions, "common_branch_owner_metrics": branches,
        "branch_inventory": branch_inventory, "unavailable": unavailable,
        "metric_scopes": measured,
        "interpretation": [
            "Read-only observational comparison; no performance, storage or pre-alpha acceptance threshold.",
            "Run-scoped table/branch rows cannot be used to attribute whole-DB pages or file sizes to that Run.",
            "Physical db/WAL/SHM sizes are read after logical snapshots and not necessarily simultaneously.",
            "Saved Revision owners are counted once; common-Branch deltas exclude added/removed branches.",
            "Zero baseline has percent_change=null; differing paths/environments may prevent causal conclusions.",
            "This is not Saved integrity, reachability, state replay or Source proof."],
    }


def _read(path: Path) -> dict:
    if path.stat().st_size > 25_000_000:
        raise ValueError("Input report exceeds 25 MB")
    def no_nonfinite(value: str):
        raise ValueError(f"Non-finite JSON value {value} not allowed")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=no_nonfinite)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path, help="Create NEW comparison JSON; never overwrite")
    args = parser.parse_args(argv)
    try:
        report = compare(_read(args.before), _read(args.after))
        result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False, sort_keys=True) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(result)
        else:
            print(result, end="")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"Storage profile comparison failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
