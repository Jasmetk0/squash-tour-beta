# Pre-alpha Admin first-tournament milestone — 9 October 2026

This document supersedes older general next-task suggestions **for the immediate Admin usability milestone only**. Master and newer product decisions remain authoritative.

## Implemented in candidate PR (not yet merged)

- `/admin/runs/new` uses the production `POST /run-containers` empty Product Run command, with only a unique display name supplied by the operator.
- `/admin/runs` lists canonical Product Runs independently of legacy `GET /runs` Simulation Run entries. Legacy records stay explicitly labeled and usable during migration.
- `/admin/runs/:runId` handles a valid saved Product Run that has no legacy Simulation Run without treating the expected legacy 404 as a fatal Run error.
- A new Run is reopened by its API-assigned `run_id`, not by a guessed ID or a regenerated source.
- No generated player, calendar, match result or ranking is fabricated by the UI. Protected Runs remain read-only.
- No World/Calendar Package is implicitly installed at creation; Package acquisition is a later explicit reviewed operation.

## Verification

- Existing backend `POST /run-containers` contract was inspected; its creation service returns a persisted `RunContainerResponse`.
- New frontend component tests cover create success, duplicate-name error, mismatched API response, canonical list/reopen and empty Run legacy-404 fallback.
- Full browser clickthrough, real HTTP/SQLite save/restart and Fast CI on the **last PR commit** are **not yet verified** at authoring time. Do not infer them from mocked component tests.

## Still blocking the requested user journey

1. Inspect and complete the **existing Admin** World + Calendar source-preview/confirm operation from an empty Product Run, preserving Run/Branch ownership and snapshots.
2. Generate and review initial players through authoritative Run-backed state, then persist as a Saved Revision; the legacy global Initial Pool UI is **not** proof of that path.
3. Establish and publish the initial ranking using the recorded ranking authority.
4. Prepare one standard tournament through canonical entries, manual reviewed applications if necessary, field, draw, schedule and real match execution.
5. Verify point award, correct ranking-publication timing, save/reopen and continuation through real HTTP/SQLite/browser evidence.
6. Only then measure FIFA Earth / ATP Earth generation in existing Lab tools without changing unproven probabilities.

The automatic application validation gate (`application_validation_policy_unresolved`), multi-season Branch forks and long-run realism remain separately tracked. Passing a Run creation component test does not resolve any of them.
