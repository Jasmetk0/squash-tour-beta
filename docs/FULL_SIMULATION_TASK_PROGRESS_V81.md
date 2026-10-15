# Measured Full Simulation Task Center progress — 15 October 2026

This bounded PR adds **read-only, source-labeled** task progress. It does not change the sporting driver, command target, worker, lease, RNG or Save.

## What Admin sees

- For a pending, active, paused, waiting, failed or recoverable server task, the real current **Run/Branch week**, number of week transitions since the original reviewed start, and current-week completed match-slot receipts and committed match-group receipts read from SQLite. They represent **all stored receipts in this Branch and week**, not work attributable exclusively to this task or a claim that a tournament/whole week is complete. No time estimate or percentage is invented.
- For a stopped or target-reached Full Simulation, the **historical end week** frozen in the validated immutable #1469/#1473 terminal summary; for a fully closed 50-season Run, the final week from the versioned complete receipt. Later Save, Branch progression and reopening Task Center cannot rewrite the historical position.
- For legacy terminal parents **without frozen summary evidence**, history is explicitly unavailable, not projected from today's Branch. No match/slot receipt counts are fabricated for terminal tasks because the older summary did not capture a frozen count.
- The existing exact operator checkpoint and explicit continuation controls remain unchanged. CS/EN UI distinguishes current-Branch receipts, terminal evidence and unavailable history.

## Read-only contract

`full_simulation_task_view.v1` includes `progress_evidence` with schema `full_simulation_task_progress_evidence.v1` and the fields `kind=live_branch|terminal_frozen|unavailable`, `week`, `weeks_advanced_since_start`, `completed_slot_receipts_this_week`, `committed_group_receipts_this_week`, and `receipt_scope=branch_current_week|null`. A completed slot is counted only with both status `complete` and a terminal checkpoint; groups count committed canonical group receipt rows, not guessed matches. `current_week` matches the selected evidence source (today's Branch for live tasks, frozen historical end for terminals, null for legacy unavailable).

No GET writes, task command mutation or new database table. Invalid chronology or corrupt complete receipts fail closed. TypeScript enforces the shape, nullability and consistency with the original reviewed start week; tests cover forged negative/fractional/contradictory counters.

## Acceptance

Production TCP/file-backed SQLite and real MatchEngine server-task controls exercise stored Group/Slot counts, lost-response idempotency and stopped terminal summary. CS/EN React tests assert correct labels. The final-head Fast CI and existing dedicated Full Simulation/Hybrid/Saved Group browser regressions must pass. This is **not** full 50-season or pre-alpha release acceptance.
