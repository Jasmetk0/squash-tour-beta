# Unified Generate — first binding country/region conditions
11 October 2026 — implementation evidence, Master v77 §§9.4, 27.19.

## Supported, not simulated

The existing **single Run → Players → Generate** flow now supports two hard constraints for the **entire** 1–128-player, first-season (2000/01) batch: sport country and geographic region. Both default to **Automatic from World**. The actual detached Run-owned World country/region projection is the sole source of available options. The same production RunWorldInitialPoolPreviewService / InitialPlayerPoolGenerator applies either filter or their intersection; no alternate distribution engine, renormalized preset, synthetic country or silent default override is introduced.

- New read-only GET /admin/players/runs/{run_id}/branches/{branch_id}/initial-world/world-package/generation-options requires exact world_package_id, expected_head, expected_draft_version, and expected_package_fingerprint query context.
- Options are projected from the exact immutable Saved World Package component, rechecked against live Run Package state, scoped to a writable Run and Active Admin Branch with clean Working Draft. Foreign/changed sources return 409, never global World choices or a stale cache.
- The UI verifies response identity and fingerprint. It exposes actual country codes/names and region/travel-region names as selectors; empty selections mean automatic allocation.
- Incompatible country + region is a visible conflict and disables Preview. Unknown country or region passed directly to API raises an explicit conflict before the production generator is called. The production result is revalidated client-side: every generated player must belong to the selected country and/or eligible region.
- Exact conditions become part of the original preview/confirm request and therefore existing request, source and preview fingerprints. Changing either invalidates the current review, requires a fresh preview, and keeps manual separate Save.
- The existing source current_ability and potential_ability values remain labeled as source scale, **not** canonical 0–200 OVR. No invented prior career, ranking, development curves, national strength or future prospect generation.

## Verified coverage

- tests/api/test_run_world_generation_conditions.py: saved-world options, strict Run/Branch/HEAD/draft protection, explicit country/region conflicts, and binding to existing production generator.
- tests/api/test_earth_world_run_acceptance.py: actual FIFA Earth and ATP Earth packages, exact 30-player CZE+region deterministic preview plus incompatible selection rejection, alongside existing full 1000-player Save/fork/reopen acceptance.
- web/src/api/runInitialWorldSetup.test.ts: stale options, automatic defaults, compatible/incompatible combinations, per-player country and region fulfilment.
- web/src/components/RunInitialWorldSetupPanel.test.tsx: constrained real preview request and confirm, visible condition conflict, fail-closed mismatched result.
- scripts/admin_first_tournament_smoke.py: actual Chromium Run UI loads stored World eligible controls, selects and resets both then continues Generate → Confirm → manual Save → Tournament/Replay.
- Full Fast CI, Shell Browser and Saved Player Replay Browser must all be green on final PR HEAD before the PR is merge-ready.

## Not silently decided by this slice

Group inheritance and group exceptions, relative or exact proportions, interval distributions, ages, attributes, comprehensive 0–200 OVR, player Keep/regenerate/edit and temporal/birth-year constraints remain unimplemented. The unspecified remainder and overlapping/nested group accounting are expressly OPEN decisions in v77; this PR creates neither. The region filter matches source country.region **or** country.effective_travel_region, as the existing production generator does. No other country attribute or a manufactured regional strength is inferred.

This is a constrained first-cohort batch, not ordinary annual intake nor a full pre-alpha release test.
