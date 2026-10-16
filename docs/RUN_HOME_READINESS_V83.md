# V83 — Current Run Home saved-content readiness

Goal: one practical, collapsible current-state Admin guide to the *selected* Branch, before and after sporting operations, without creating a second Lab, duplicating Task Center or promising that a data checklist can start simulation.

## Sources and strict boundaries

`GET /admin/runs/{run_id}/branches/{branch_id}/home-readiness` starts one SQLite read snapshot, validates complete Saved Revision lineage and the selected HEAD/draft identity, resolves the current Run calendar against the immutable Saved head, and reads its signed components. World and Calendar count only actual Run-owned Package entities from the correct typed source; a Package-version record alone is not readiness. Population and Health must validate their Saved component fingerprints/identities. Prepared ranking candidates do not count as *published* ranking; publication/transition evidence is taken from the Saved ranking revision's authoritative state. Current nonterminal Full Simulation task evidence is separately read and validated from durable task receipts, not UI or process memory. No Viewer Branch fallback and no legacy simulation owner fallback.

The six checks are World, Calendar, population, Health (optional for no/v1 population), published ranking, and Working Draft. Health is required only for calendar-owned v2 population. A selected Branch still referencing nonempty content in another Branch's historical head fails closed rather than relabeling it. Unsupported clocks (including extended horizons outside reference FAX 61x50) explicitly show a sporting limit. Even a fully checked FAX guide is **never** permission to start a match or Full Simulation: exact operation-scoped validation remains authoritative.

## Usable Admin flow

Run Home present view loads the guide using a Branch-ID + Saved-head-query-key, checks identity and draft-version consistency, and provides manual Refresh. A collapsed details section shows original HEAD/hash/versions and saved transitions/tasks; actionable missing/unsaved/candidate entries link directly to existing Run Management, Generator, player, Simulation or Branch controls. CS and EN are supported. In historical viewing the current-state guide is deliberately absent. No data changes, simulation, task scheduling, or hidden Save.

## Checks and limitations

Real SQLite tests cover empty FAX, unsupported W52, dirty drafts, wrong identities, tampered Saved hash and completed Run. Production HTTP/SQLite tests cover fresh Run, another Branch, cross-Run rejection and cold restart. UI tests verify link destinations, localization, refresh and malformed/stale response refusal. The existing real Chromium shell acceptance covers empty/new and populated/extended Run with 1,000 players and Health; it must never claim W52 sporting support. Counts/statuses here are diagnostic source facts; checklists do not replace operation-specific readiness or complete pre-alpha release acceptance.
