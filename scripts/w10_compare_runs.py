#!/usr/bin/env python3
"""Byte-level comparison of two W10 benchmark outputs (same deterministic IDs).

    python scripts/w10_compare_runs.py FIXTURE.sqlite RUN_A RUN_B [OUT.json]

RUN_A/RUN_B are ``scripts/w10_continuation_benchmark.py`` output directories.
Checks, read-only: every fixture revision row is byte-identical in both runs
(including created_at); every fixture node still exists unchanged; all
revision rows except created_at, all nodes, audit events, Working Drafts and
the final Tour inspection are identical between A and B. When one run stopped
early, the common revision prefix is compared and reported.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REVISION = ("SELECT revision_id, run_id, branch_id, sequence, parent_revision_id, kind, payload_schema_version, "
            "content_hash_algorithm, content_hash, payload_json, change_summary_json{} FROM branch_saved_revisions "
            "ORDER BY sequence")


def connect(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def table(connection, sql):
    return connection.execute(sql).fetchall()


def main(argv):
    fixture, run_a, run_b = Path(argv[0]), Path(argv[1]), Path(argv[2])
    base = connect(fixture)
    fixture_rows = table(base, REVISION.format(", created_at"))
    fixture_nodes = dict(((r, d), b) for r, d, b in base.execute(
        "SELECT run_id, digest, body FROM saved_revision_nodes"))
    result = {}
    loaded = {}
    for name, run in (("A", run_a), ("B", run_b)):
        c = connect(run / "run.sqlite")
        rows = table(c, REVISION.format(", created_at"))
        nodes = dict(((r, d), b) for r, d, b in c.execute("SELECT run_id, digest, body FROM saved_revision_nodes"))
        result[name] = {
            "fixture_revisions_unchanged": rows[:len(fixture_rows)] == fixture_rows,
            "fixture_nodes_unchanged": all(nodes.get(k) == v for k, v in fixture_nodes.items()),
            "revisions": len(rows), "nodes": len(nodes),
        }
        loaded[name] = {
            "rows": [r[:-1] for r in rows],
            "nodes": nodes,
            "audit": table(c, "SELECT audit_event_id, run_id, branch_id, saved_revision_id, event_kind, "
                              "payload_json FROM branch_revision_audit_events ORDER BY audit_event_id"),
            "drafts": table(c, "SELECT draft_id, branch_id, base_revision_id, status, change_count, "
                               "draft_version, changes_json FROM branch_working_drafts ORDER BY draft_id"),
            "final": (run / "final-inspection.json").read_text() if (run / "final-inspection.json").exists() else None,
        }
    a, b = loaded["A"], loaded["B"]
    common = min(len(a["rows"]), len(b["rows"]))
    result["common_revisions"] = common
    result["revision_rows_identical_in_common_prefix"] = a["rows"][:common] == b["rows"][:common]
    result["same_revision_count"] = len(a["rows"]) == len(b["rows"])
    complete = result["same_revision_count"]
    result["nodes_identical"] = a["nodes"] == b["nodes"] if complete else None
    result["audit_identical"] = a["audit"] == b["audit"] if complete else None
    result["drafts_identical"] = a["drafts"] == b["drafts"] if complete else None
    result["final_inspection_identical"] = (a["final"] == b["final"]) if a["final"] and b["final"] else None
    result["new_content_hashes"] = [r[8][:16] for r in b["rows"][len(fixture_rows):]]
    result["identical"] = bool(complete and result["revision_rows_identical_in_common_prefix"]
                               and result["nodes_identical"] and result["audit_identical"]
                               and result["drafts_identical"] and result["final_inspection_identical"]
                               and all(v["fixture_revisions_unchanged"] and v["fixture_nodes_unchanged"]
                                       for v in (result["A"], result["B"])))
    text = json.dumps(result, indent=1)
    print(text)
    if len(argv) > 3:
        Path(argv[3]).write_text(text + "\n")
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
