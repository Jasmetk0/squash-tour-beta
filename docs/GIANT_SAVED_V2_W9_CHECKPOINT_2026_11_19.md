# Bounded 1,000-player W9 HTTP/SQLite benchmark with Saved v2

**Source:** port of the real compatible runner from Draft PR #1820 onto current
`buuk` (including merged production Saved v2 #1827). This is **test-only**:
no production engine, sporting, persistence or migration files are modified.

## What this run really exercises

The exact existing `--profile compatible` real runner performs an HTTP/SQLite
Run with 1,000 initial players, four signed annual prospect waves, approved
4/8-player native Main-only Editions, real MatchEngine global slots and explicit
Save after each relevant command. The full five-season schedule remains a
*plan*, not an execution claim. The bounded mode plays only season 1 through W9.

Saved v2 is opted in **at NEW Run creation** via
`BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2`, selected by the new
`--saved-v2` switch; it is confirmed from `run_saved_storage_formats`,
physical Saved-v2 envelopes and Merkle node existence. The original authenticated
HTTP Saved inspection/history readers remain in force.

**Checkpoint semantics:** W9 is complete only after its genuine
`transition` to W10 and the following explicit Save. Then the loop stops
*before any W10 planning, sport or Save*. The summary records
`last_completed_season=1`, `last_completed_week=9`, and
`last_position` at **season index 0, week 10**. It does **not** report
five finished seasons. After stopping, the script verifies the v2 physical
Saved chain and head and performs a true cold HTTP restart with exact inspection
equality and a history-endpoint read.

## Run locally (manual, never in ordinary PR CI)

```bash
PYTHONPATH=src:. python -m pytest -q \
  tests/application/test_giant_native_load_plan.py \
  tests/application/test_giant_native_load_w9.py

# Safe: prints a plan and never creates a Run.
python scripts/giant_native_five_season_load.py \
  --profile compatible --plan-only

# EXPLICIT manual, potentially long and RAM-heavy real W9 run:
PYTHONPATH=src:.:tests/api python scripts/giant_native_five_season_load.py \
  --profile compatible --players 1000 --seasons 5 \
  --editions-per-season 60 --born-per-season 80 \
  --saved-v2 --stop-after-week 9 --budget-minutes 315 \
  --output-dir work/w9-saved-v2-manual
```

Use a **new empty output directory** for each attempt. This script refuses
to overwrite an existing SQLite Run. Real Saved v2 from the first revision is
required in W9 mode. All original command preview/confirmation, explicit Save,
native sporting verification, 120-second HTTP transport timeout and 315-minute
internal budget are retained. The original 350-minute Actions job timeout is
retained for the bounded manual workflow too.

## Telemetry, including failures

`timeline.jsonl` contains one `kind=save` event for **each HTTP /save
request** (initial setup, cohort-source and Tour Saves), with sequence number,
endpoint, elapsed HTTP wall time, HTTP status, SQLite main/WAL/total bytes and
process high-water RSS in KiB. The request and its original timeout pass through
unchanged. Other events include per-operation timings, real completed Editions,
week completions and the terminal `stopped_after_week` event.

`summary.json` is atomically refreshed, including after individual Saves,
with `save_count`, `last_completed_week`, `last_position`,
`saved_revision_count`, `sqlite_bytes`, `sqlite_wal_bytes`,
`sqlite_total_bytes` and `peak_rss_kib`. It distinguishes `running`,
`budget_exhausted`, `failed` and `stopped_after_week`. Main-file bytes
alone under WAL journaling are **not** the complete physical file footprint.

## Safeguards against unintended five-season runs

The new `.github/workflows/giant-w9-saved-v2.yml` has **only**
`workflow_dispatch`, with a typed confirmation
`RUN_W9_SAVED_V2_1000`. It **never** has a push/PR/synchronize trigger and
does **not** pass the five-season authorization flag. The ordinary targeted
tests mock any execution and exercise only small/synthetic state.

Any full five-season real run through this script now requires
`--allow-five-season-run` with **no** `--stop-after-week`. Do **not**
insert this flag into PR checks, the W9 workflow or any automatic job.
The legacy #1820 workflow still exists on its separate Draft branch and
should not be copied unchanged or synchronized casually: its former PR
trigger can automatically start five seasons. This patch does not update
that other PR, precisely to avoid firing its old trigger.

No W9 measurement is claimed until the explicitly invoked HTTP/SQLite job
finishes and its raw timeline and history checks are reviewed.
