# Calendar-owned initial population — Master v82

## Scope and usable flow

Built on merged #1499 (`buuk` `10dafd09295b4582c1031ad379ff67f289f3421e`).
The existing custom-calendar Players → Generate page now supports generate →
review → explicit confirmation → separate manual Save → reload/open saved players.
CS/EN text explains the boundary. The exact legacy FAX sporting geometry
(61 weeks, offset 37, start 2000, 50 seasons) retains its V1 workflow.

This is population preparation, not custom-calendar sporting support. No historical
Tour entry, results, ranking, health or annual development are fabricated. Sporting
and time-progression guards remain. Master product decisions are unchanged.

## Contracts and authority

- `initial_world_state.v2` and `season_active_player.v2` store the full Run clock
  and explicit generation time basis. Signed years, W > 61 and year zero are valid.
  All adopted players turned 15 strictly before opening Week 1, remain active,
  and are below the explicitly stored lifecycle retirement age.
- `RunWeekPosition` uses the stored Run calendar for ordinal and conversion.
  `player_lifecycle_calendar_state.v2` accepts only opening population bootstrap,
  stores correct birth/age identities and `initialization_stage=population_only`.
  It has no Tour-entry or retirement-event fields. Legacy `RankingWeek` cannot
  read a V2 lifecycle even when both ordinals happen to be zero.
- The raw calendar pool preview remains read-only with `adoption_supported=false`.
  Separate `/initial-world/calendar-adoption/preview` and `/calendar-adoption`
  endpoints provide review and installation authority. GET reads actual installed
  population. All paths are scoped by Run and Branch.
- Review binds command, normalized generation/policy, exact Saved head, clean
  Working Draft version and the copied package fingerprint. The source must already
  be manually saved. Expensive generation runs outside the writer transaction.
  Confirmation revalidates target/source under `BEGIN IMMEDIATE`, installs world
  and lifecycle atomically, and leaves the Saved head untouched.
- An exact committed retry returns installed data without regeneration, including
  after manual Save. A changed command/content is rejected. Writer failure rolls
  back both components. Concurrent identical commands install once.
- UI freezes the server-normalized reviewed request and requires explicit consent.
  Source/target/preview changes revoke review; late responses are discarded.
  Failure cannot silently create a new command or reuse consent. Save has its own
  checkbox and validates the actual Saved component and clean returned draft.
- The existing explicit InitialWorld Save captures both components. Saved clock,
  player identities, component hashes and policy must agree. Fork preserves source
  provenance, scopes actual copies to the target Branch, and retains original
  source adoption fields. Restore never backfills legacy sporting/health for V2.
- V1 schemas, stored JSON, fingerprints, replay and historical ownership stay
  unchanged. The inherited generation kernel is not cross-Python-runtime bitwise
  portable; V2 preview records runtime provenance as described in the preview spec.

## Verification

Real HTTP/SQLite tests cover W52 with crossing seasons, W80/horizon300, W1/year0,
review non-mutation, exact retries, manual Save, restart, materialized fork,
restore to empty/back, concurrency, atomic rollback, stale proof, target drift
between generation and write, damaged lifecycle and refusal by legacy sporting
writers. Actual ATP Earth with 1,000 players exercises review/adopt/Save/restart
without substituting fixtures for its country source.

Focused legacy lifecycle/fork/restore/Saved-player/ranking tests and health,
sporting-fork, standalone-match, default-clock guard and pinned generation-replay
regressions preserve old behavior. Frontend contract/component tests cover
review/consent, normalized frozen policy, exact retry, stale proof and late response;
production TypeScript/Vite build is required.

The extended existing Shell Chromium scenario uses a disposable W52/O35/2030 Run,
copies and manually saves the FAX World, reviews/confirms 1,000 actual players,
checks no implicit Save, explicitly saves, reloads and opens saved player inventory.
It records `custom_calendar_population_adopt_save_reload` plus screenshots 11/12.
Final-HEAD workflow results and browser artifacts must be verified before handoff;
unit/component tests alone do not establish browser acceptance.

## Remaining migration

Health/state initialization, annual development in 1/W units, ranking inputs and
W-week validity, authoritative Week/Season transitions, Tour-entry timing and
frozen Full Simulation controls still need explicit versioned migration and actual
sporting acceptance. Prestart calendar edits, shared horizon extension, import
compatibility, complete pre-alpha release tests and realism calibration remain.
