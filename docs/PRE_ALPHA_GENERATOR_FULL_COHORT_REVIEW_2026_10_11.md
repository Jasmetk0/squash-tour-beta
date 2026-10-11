# Single Run → Players → Generate: full-cohort review and inspector

11 October 2026. Integrated from #1372 into `buuk` after #1372 was merged into its intermediate parent PR branch, not into `buuk`. **This is presentation only**, not editable preview / session Keep / permanent locks. The user alone merges.

## Implemented workflow

The existing production generator, exact Run/Branch/HEAD/World provenance, side-effect-free Preview → explicit Adopt → separate manual Save are unchanged. A dedicated, read-only GeneratedPlayerReviewInspector displays exact facts from the entire **verified** InitialWorld preview, rather than a sample, with:

- Six compact cards: batch total, distinct sporting country count, opening-week age average/min/max, mean source current and potential abilities.
- All-country distribution with count bars (compact first six and an explicit All option); fixed five-band first-week age distribution; source potential-tier counts and available source career-stage counts.
- A complete 1–128-player roster with name/ID, sporting country, first-week age, source current/potential abilities and tier. The roster is searchable by name/ID, filterable by country and source potential tier, and sortable by name/country/age/current/potential; empty results are explicit. Clear resets display controls.
- Counts/stats use the entire verified preview **regardless of UI filter**, and the Adopt request always uses the original complete and unchanged preview fingerprint. Sorting/display filters never become hard generation constraints, an unsaved editable Working Draft, a Keep, or a permanent lock.
- Correct provenance disclaimer: current/potential numbers are legacy **source 1–99**, **not** canonical 0–200 OVR, Official Ranking, estimated career outcomes or future knowledge. Player hidden traits and future-only layers are not displayed.
- Compact 3-column summary/distribution layouts collapse responsively on smaller screens; only the roster scrolls vertically.

## Verification

- New `tests/application/test_generated_review_source_projection.py` PR-critical check: real first-week age, source 1–99 abilities, career stage, potential tier, initial unranked zero-point state and deterministic replay survive the production pool → InitialWorld conversion.
- New pure summary utility and Vitest inspector tests: counts, age bands, potential tiers, deterministic ordering, empty preview, source immutability, country/tier/name/ID filters, no-match state, sort and show-all.
- Existing generator integration Vitest now filters the UI to one player before confirming the original entire two-player reviewed command and separately saving.
- Real Chromium acceptance views the 64-player inspector, filters and resets the display without changing the authority of Confirm, then verifies unchanged Saved Revision, tournament and replay after restart.
- Final-head Fast CI, Pre-alpha Shell Browser (if triggered) and Pre-alpha Saved Player Replay Browser must pass before this stacked PR is marked ready for merge. Do not confuse focused checks with the full 50-season internal release gate.

## Follow-up (not silently decided)

Actual preview **Keep** needs a Run/Branch/session-scoped mutable selection bound to the exact reviewed preview, production regeneration that preserves selected real players and the semantics of a new seed/condition. This inspector does not implement permanent locks, partial cohort regeneration, canonical 0–200 OVR or historical career attributes. Master v78 §9.6 has since decided simultaneous partial constraints within one group and explicit-total remainder completion; broader group mechanics remain OPEN. #1374 adds one-pass session Keep only on an intermediate branch and is absent from the v78 audited buuk; see the v78 checkpoint. They must be implemented with authoritative persisted fingerprints and product decisions, not with a superficial frontend checkbox.
