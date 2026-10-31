#!/usr/bin/env python3
"""Read-only, point-in-time storage observations; not a Saved integrity validator."""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = "run_storage_profile.v1"
# Deliberately bounded inventory, not arbitrary schema/view/virtual-table SQL.
KNOWN_TABLES = (
    "runs", "run_branches", "branch_saved_revisions", "branch_working_drafts",
    "branch_revision_audit_events", "branch_saved_revision_checkpoints",
    "branch_checkpoints", "run_package_states", "full_simulation_tasks",
)
REQUIRED_COLUMNS = {
    "runs": {"run_id"},
    "run_branches": {"run_id", "branch_id", "saved_head_revision_id"},
    "branch_saved_revisions": {
        "run_id", "branch_id", "revision_id", "payload_json", "change_summary_json",
    },
}
PAYLOAD_SIZE = "length(cast(payload_json AS BLOB))"
SUMMARY_SIZE = "length(cast(change_summary_json AS BLOB))"


def _size(path: Path) -> dict:
    try:
        return {"bytes": path.stat().st_size, "status": "observed"}
    except FileNotFoundError:
        return {"bytes": None, "status": "absent"}
    except OSError as exc:
        return {"bytes": None, "status": "unavailable", "reason": str(exc)}


def _schema(connection: sqlite3.Connection) -> dict[str, set[str]]:
    objects = {
        row[0]: row[1:] for row in connection.execute(
            "SELECT name, type, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        )
    }
    tables = {}
    for name in KNOWN_TABLES:
        entry = objects.get(name)
        if entry is None:
            continue
        kind, sql = entry
        if kind != "table" or not sql or "CREATE VIRTUAL TABLE" in sql.upper():
            raise ValueError(f"Expected a persisted table, not a view/virtual table: {name}")
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{name}")')}
        missing = REQUIRED_COLUMNS.get(name, set()) - columns
        if missing:
            raise ValueError(f"Incompatible {name} schema; missing: {', '.join(sorted(missing))}")
        tables[name] = columns
    if not tables:
        raise ValueError("No supported Run tables found; this is not a supported Run database")
    return tables


def _aggregates(connection: sqlite3.Connection, run_id: str | None) -> tuple[dict, dict]:
    where = " WHERE run_id = ?" if run_id is not None else ""
    params = (run_id,) if run_id is not None else ()
    metrics = f"COUNT(*), SUM({PAYLOAD_SIZE}), SUM({SUMMARY_SIZE}), MAX({PAYLOAD_SIZE}), AVG({PAYLOAD_SIZE})"

    def value(row):
        return dict(zip(
            ("count", "payload_bytes_sum", "change_summary_bytes_sum",
             "payload_bytes_max", "payload_bytes_mean"),
            (row[0], row[1] or 0, row[2] or 0, row[3] or 0, row[4] or 0.0),
        ))

    totals = value(connection.execute(
        f"SELECT {metrics} FROM branch_saved_revisions{where}", params
    ).fetchone())
    owners = {
        branch: value(row) for branch, *row in connection.execute(
            f"SELECT branch_id, {metrics} FROM branch_saved_revisions{where} GROUP BY branch_id",
            params,
        )
    }
    return totals, owners


def _heads(connection: sqlite3.Connection, run_id: str | None) -> dict:
    # Read the actual persisted Branch pointer, NEVER a mutable draft's base.
    query = """
        SELECT b.branch_id, b.run_id, b.saved_head_revision_id,
               r.run_id, r.branch_id, length(cast(r.payload_json AS BLOB))
        FROM run_branches b
        LEFT JOIN branch_saved_revisions r ON r.revision_id = b.saved_head_revision_id
    """
    params = ()
    if run_id is not None:
        query += " WHERE b.run_id = ?"
        params = (run_id,)
    result = {}
    for branch, owner_run, revision, saved_run, saved_owner, size in connection.execute(query, params):
        if revision is not None and (saved_run is None or saved_run != owner_run):
            raise ValueError(f"Branch {branch} has a missing or foreign-Run HEAD reference")
        result[branch] = {
            "run_id": owner_run, "revision_id": revision,
            "original_owner_branch_id": saved_owner, "payload_bytes": size,
            "status": "referenced_not_integrity_validated" if revision else "no_head",
        }
    return result


def collect(database: Path, run_id: str | None = None, label: str | None = None) -> dict:
    database = database.resolve(strict=True)
    if not database.is_file() or database.stat().st_size == 0:
        raise ValueError("Database must be an existing nonempty SQLite file")
    started = datetime.now(UTC).isoformat()
    clock = time.perf_counter()
    # as_uri escapes spaces, #, ?, %, and Windows drive paths correctly.
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=2.0)
    try:
        connection.execute("PRAGMA query_only = ON")
        connection.execute("BEGIN")
        tables = _schema(connection)  # establishes the logical read snapshot
        encoding = connection.execute("PRAGMA encoding").fetchone()[0]
        if encoding.upper().replace("-", "") != "UTF8":
            raise ValueError(f"Unsupported text encoding {encoding}; no UTF-8 byte report produced")
        if (run_id is not None and "runs" in tables
                and connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone() is None):
            raise ValueError(f"Unknown Run ID: {run_id}")
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        page_count = connection.execute("PRAGMA page_count").fetchone()[0]
        free = connection.execute("PRAGMA freelist_count").fetchone()[0]
        table_metrics = {}
        for name in KNOWN_TABLES:
            if name not in tables:
                table_metrics[name] = {"status": "unavailable", "reason": "table_absent"}
                continue
            scoped = run_id is not None and "run_id" in tables[name]
            where = " WHERE run_id = ?" if scoped else ""
            params = (run_id,) if scoped else ()
            table_metrics[name] = {
                "status": "observed",
                "scope": "selected_run" if scoped else "whole_database",
                "row_count": connection.execute(f'SELECT COUNT(*) FROM "{name}"{where}', params).fetchone()[0],
            }
        totals, owners, heads = None, {}, {}
        if "branch_saved_revisions" in tables:
            totals, owners = _aggregates(connection, run_id)
            if "run_branches" in tables:
                heads = _heads(connection, run_id)
        logical_end = datetime.now(UTC).isoformat()
    finally:
        # sqlite3 connection context managers do not close the connection.
        connection.close()
    physical_start = datetime.now(UTC).isoformat()
    sizes = {
        "db": _size(database),
        "wal": _size(database.with_name(database.name + "-wal")),
        "shm": _size(database.with_name(database.name + "-shm")),
    }
    ended = datetime.now(UTC).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "observation_start_utc": started, "logical_snapshot_end_utc": logical_end,
        "physical_observation_start_utc": physical_start, "observation_end_utc": ended,
        "elapsed_seconds": time.perf_counter() - clock,
        "python_version": platform.python_version(), "sqlite_version": sqlite3.sqlite_version,
        "database_path": str(database), "label": label, "run_id_scope": run_id,
        "text_encoding": encoding, "physical_sizes": sizes,
        "page_metrics": {
            "scope": "whole_database", "page_size": page_size, "page_count": page_count,
            "freelist_count": free, "allocated_bytes": page_count * page_size,
            "nonfreelist_page_bytes": (page_count - free) * page_size,
            "free_page_bytes": free * page_size,
        },
        "dbstat": {"status": "not_collected", "reason": "No per-table/index physical attribution in v1"},
        "tables": table_metrics, "saved_revision_totals": totals,
        "branch_saved_revisions": owners, "branch_heads": heads,
        "limitations": [
            "File sizes are whole-database observations after the logical snapshot, not a simultaneous snapshot.",
            "Counts group persisted revision owners once; HEAD references do not add duplicated ancestry rows.",
            "HEAD references are not a reachability, hash, source or sporting replay proof.",
            "No temporary-directory, archive-size, RAM/RSS or growth-complexity measurement is made.",
            "SQLite WAL readers can update normal shared-memory coordination; application data is never written.",
        ],
    }


def _output_path(raw: str | None, database: Path) -> Path | None:
    if raw is None:
        return None
    output = Path(raw).absolute()
    protected = {database, database.with_name(database.name + "-wal"),
                 database.with_name(database.name + "-shm")}
    if output.resolve() in protected:
        raise ValueError("Output path cannot overwrite the database or its sidecar files")
    # lexists catches a dangling symlink; exclusive open also guards races/hard links.
    if output.exists() or output.is_symlink():
        raise ValueError("Output file already exists")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--label")
    parser.add_argument("--output", help="Create a NEW JSON report; existing files are never overwritten")
    args = parser.parse_args()
    try:
        database = Path(args.database).resolve(strict=True)
        output = _output_path(args.output, database)
        report = collect(database, args.run_id, args.label)
        encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if output is None:
            print(encoded, end="")
        else:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
