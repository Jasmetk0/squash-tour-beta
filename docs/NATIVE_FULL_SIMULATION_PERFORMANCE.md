# Native Full Simulation history performance

Status: measurement and implementation in progress; **WAIT**, no merge recommendation.
Base: owner-merged `buuk` `e39d962bb6797960c47c1c659d57be1dc67bba6b`.
Only the owner merges. One implementation branch/PR; no auto-merge.

The baseline runs the existing genuine W52 worker/Save/season acceptance from an
immutable checkout. It preserves a SQLite backup immediately before task Start,
then idle early/middle/late week snapshots. Before/after full runs must start from
that same backup and retain every actual week, sporting assertion and manual Save.
A snapshot profile measures that section only, not end-to-end completion.

Capture total wall time, per-step Save/resume time, SQL count and statement/parameter
bytes, native context time, Saved payload bytes and process peak RSS. Separate
repository-cold from warm context reads; obtain CPU profiles separately so profiler
overhead is not counted as speed evidence. SQL text/parameter volume is not the
volume of query results. Record returned physical-history bytes separately.

The earlier W52/W61/W80 times in the task describe those individual integration
scenarios and are not a benchmark of every Run or the complete product.

Implementation, comparable measurements, integrity review and final-head test
ledger will be recorded here as they actually execute. Draft-skipped hosted jobs
are not successful acceptance evidence.
