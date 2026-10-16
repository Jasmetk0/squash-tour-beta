# Reviewed Run-wide horizon extension — V83

This command applies only to validated, editable, versioned custom Runs. It is one Run-wide manual Save, not per-Branch editing or a simulation command.

## Operator flow

1. Open Admin → Run Home, enter a strictly greater *total season count*.
2. Select **Review all Branches**. The read-only GET /run-containers/{run_id}/calendar/extension-review?new_season_count=N inventories every Branch and Saved head, clean drafts, live component parity, task and lease blockers, and binds the exact cohort in a review fingerprint.
3. Resolve every blocker, inspect the affected Branches and explicitly tick consent.
4. **Confirm & Save entire Run** sends POST /run-containers/{run_id}/calendar/extension-save with command_id, review_fingerprint, new_season_count and explicit_confirmation=true.
5. Within one SQLite BEGIN IMMEDIATE transaction, revalidate everything. Append every new hash-signed Branch Saved revision, refresh all clean Working Draft baselines, update Run end/calendar, write Branch audit and one durable idempotent receipt. Any error rolls back the entire operation.
6. Read the receipt and reload the Run. An identical command retry returns its original receipt without writing again; different use of the same command identity is rejected.

## Exact history and lifecycle

Original Run calendars, all old Saved Revisions/hashes, historical fork ancestry, player and match states, frozen Full Simulation task targets and status remain unchanged. New head snapshots describe the extended calendar. If a saved calendar-owned InitialWorld was created under the old clock, its new snapshot explicitly declares hash-protected run_calendar_content_origin; validation requires identical W/offset/start and a strictly greater current horizon. No old population is regenerated or silently relocated. Compatible historical restore/fork creates a current-clock child without modifying old source bytes.

Existing lifecycle status, including Completed, is not changed. Any future work or resumption requires a separate operator action; the extension itself starts no simulation. Dirty or unsaved Branch state, invalid ancestry, incompatible clock or active tasks fail closed.

**Important limitation:** calendar extension does not authorize sporting execution by legacy fixed-clock ranking/transition drivers, even when the new horizon is saved. Sporting writer guards remain active until the separate migration is complete. This is not a claim of full pre-alpha readiness.

## Targeted tests

Real SQLite: two-Branch Save + hashes + restart + exact receipt retry; stale and dirty drafts, membership or head changes, partial transaction rollback, task/lease blockers, historical compatibility. UI: Czech/English, consent, stale review, failure and receipt. Full historical suite remains the separate release gate.
