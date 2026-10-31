# RUN_STORAGE_MEASUREMENT.md — Run Storage Measurement

This document details the usage and limitations of the independent command-line diagnostic tool for measuring the storage profile of a Squash Engine SQLite database Run.

## Scope and Limitations
*   The collector is an independent diagnostic, meaning it executes in read-only (`mode=ro`) and does not modify the physical DB files, change journals, checkpoint the WAL, or vacuum.
*   The observed physical sizes might not be perfectly synchronized logically because the underlying file system sizes are collected independently of the internal SQLite `PRAGMA page_count` metrics.
*   `branch_saved_revisions` logic tracks the bytes using the UTF-8 storage footprint representations of text strings natively inside SQLite.
*   The sum of JSON bytes across the tables and the estimated SQLite metrics DO NOT translate exactly to maximum filesystem size, archive size, peak RAM footprint (RSS), or long-term growth bounds. They are purely point-in-time metrics of SQLite allocations and logical row boundaries.
*   It operates independently from the main orchestrator runs (50-season campaigns) and can be triggered directly at arbitrary checkpoints.

## Usage
The command-line interface expects you to provide the `--database` path. The other fields are optional.

### Arguments
*   `--database` (Required): The path to the Squash Engine Run database.
*   `--run-id` (Optional): Run ID used to filter only specific records if multiple runs share the database. Note that the DB overall file size applies across the entire DB.
*   `--label` (Optional): Custom label to inject into the output.
*   `--output` (Optional): The file path where the JSON report will be saved. Outputting to stdout by default. Overwrites existing files but fails if trying to overwrite the target `.db`, `-wal`, or `-shm` files.

### Suggested Execution
For season checkpoints or weekly storage assertions, invoke this script alongside the engine process.

```bash
python scripts/profile_run_storage.py --database data/my_run.db --run-id run-x --output report.json
```

## Sample JSON Report

```json
{
  "schema_version": "1.0",
  "observation_start_utc": "2026-10-31T14:15:00.721185+00:00",
  "observation_end_utc": "2026-10-31T14:15:00.722469+00:00",
  "elapsed_seconds": 0.0013,
  "python_version": "3.12.13",
  "sqlite_version": "3.45.1",
  "database_path": "/app/test.db",
  "label": null,
  "run_id_scope": "run-1",
  "physical_sizes": {
    "db_bytes": 24576,
    "wal_bytes": null,
    "shm_bytes": null
  },
  "page_metrics": {
    "page_size": 4096,
    "page_count": 6,
    "freelist_count": 0,
    "allocated_bytes": 24576,
    "free_bytes": 0
  },
  "dbstat_supported": true,
  "tables": {
    "branch_saved_revisions": {
      "row_count": 2,
      "physical_bytes": 4096
    },
    "branch_working_drafts": {
      "row_count": 1,
      "physical_bytes": 4096
    }
  },
  "branch_saved_revisions": {
    "b1": {
      "count": 2,
      "payload_bytes_sum": 24,
      "change_summary_bytes_sum": 4,
      "payload_bytes_max": 16,
      "payload_bytes_mean": 12.0,
      "head_payload_bytes": 16
    }
  }
}
```
*Note: The preceding is synthetic data output from tests. No claims are made that it benchmarks 1000 players or 50 seasons.*
