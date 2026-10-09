# Pre-alpha Admin first-tournament milestone — 9 October 2026

This document supersedes older general next-task suggestions **for the immediate Admin usability milestone only**. Master and newer product decisions remain authoritative.

## Implemented and merged — PR #1331 (9 October 2026)

- `/admin/runs/new` uses the production `POST /run-containers` empty Product Run command, with only a unique display name supplied by the operator.
- `/admin/runs` lists canonical Product Runs independently of legacy `GET /runs` Simulation Run entries. Legacy records stay explicitly labeled and usable during migration.
- `/admin/runs/:runId` handles a valid saved Product Run that has no legacy Simulation Run without treating the expected legacy 404 as a fatal Run error.
- A new Run is reopened by its API-assigned `run_id`, not by a guessed ID or a regenerated source.
- No generated player, calendar, match result or ranking is fabricated by the UI. Protected Runs remain read-only.
- No World/Calendar Package is implicitly installed at creation; Package acquisition is a later explicit reviewed operation.

## Verification

- Existing backend `POST /run-containers` contract was inspected; its creation service returns a persisted `RunContainerResponse`.
- New frontend component tests cover create success, duplicate-name error, mismatched API response, canonical list/reopen and empty Run legacy-404 fallback.
- PR #1331 passed final-HEAD Fast CI: 153 stable frontend critical tests, 74 changed-module tests and production build. Real full browser clickthrough of an empty Run remains unverified; existing backend Run creation coverage is separate from frontend mocks.

## Implemented in candidate PR #1332 — World/Calendar source copy

- Run Home offers World Package selection and persisted 2000/01 Calendar source preview using the pre-existing Run/Branch source adapters.
- Explicit Confirm applies reviewed source content only to a Working Draft with Run, Branch, Saved Revision, Draft-version and Package-state verification; conflicts/invalid entities block.
- Explicit Save creates a recoverable Saved Revision after confirming the current Working Draft and recorded applied Package fingerprint.
- Applied snapshots are independent of source mutation by production Package service design; no simulation, Player or Ranking state is fabricated.
- Frontend preview/confirm/save and cross-identity protection are newly exercised by focused component tests. Existing backend `tests/api/test_run_package_api.py`, `test_world_package_run_adapter.py` and `test_calendar_package_run_adapter.py` establish production HTTP/SQLite behavior separately.
- This frontend change is not a proven browser end-to-end run, and source-calendar 2000/01 must exist and be valid in the selected environment. Calibration and tournament policy remain unchanged.

## Still blocking the requested user journey

1. Browser-check World and Calendar source import with a real disposable Product Run, using validated source season files and save/restart, not only mocked frontend tests and existing backend adapters.
2. Generate and review initial players through authoritative Run-backed state, then persist as a Saved Revision; the legacy global Initial Pool UI is **not** proof of that path.
3. Establish and publish the initial ranking using the recorded ranking authority.
4. Prepare one standard tournament through canonical entries, manual reviewed applications if necessary, field, draw, schedule and real match execution.
5. Verify point award, correct ranking-publication timing, save/reopen and continuation through real HTTP/SQLite/browser evidence.
6. Only then measure FIFA Earth / ATP Earth generation in existing Lab tools without changing unproven probabilities.

The automatic application validation gate (`application_validation_policy_unresolved`), multi-season Branch forks and long-run realism remain separately tracked. Passing a Run creation component test does not resolve any of them.
