# Unified Players → Generate: first executable slice (2026-10-11)

Status: implementation candidate on `feat/unified-player-generator-first-slice-20261011`, aligned with Master v77 (9.4, 27.19, 31.32). Not the final universal constrained generator.

## One entry, one production authority

The Run → Players primary screen provides exactly one **Generate** action. Run Home links to this same route; it no longer hosts another generation form. The existing production `RunInitialWorldSetupPanel` is reused under `/admin/runs/:runId/players/generate`; it is **not** a second custom generator or independent RNG. It uses the `RunWorldInitialWorldService` and existing Run-owned `InitialPlayerPoolGenerator` through `RunWorldInitialPoolPreviewService`.

First fully supported batch:
- Initial `2000/2001` players, explicitly specified **1–128 total players**, using the natural Run World distribution and one seed; optional country/group constraints and partial-batch remainder are not silently improvised.
- Requires a writable custom Run, valid selected Active Admin Branch, present time context, an existing saved/independent World Package, clean pre-generation generic Working Draft and no preexisting InitialWorld.
- **Generate preview** is read-only and shows real deterministic player identities, sport countries and legacy first-season current/potential abilities with their correct scale and provenance. It does **not** mislabel 1–99 values as 0–200 OVR or fabricate earlier careers, rankings or results.
- An explicit checked **Confirm** recomputes the same production state. The frontend and backend bind exact Run, Branch, saved revision HEAD, draft version, World state fingerprint, generation request/seed, production source and preview fingerprint. Server-side confirm checks the *immutable saved* World against live state, not only the current live Package.
- Confirmation stages the existing **Run-owned unsaved InitialWorld component**. The separate generic Working Draft may still report `clean` because the initial-world component uses its own operation-scoped Save preflight; this does **not** mean the player component has been saved. An explicit subsequent **Save InitialWorld revision** creates an immutable Saved Revision and verified clean draft. No auto-Save or Viewer Branch switch.
- Reopening an existing unsaved InitialWorld via the same screen uses the real server Save preflight and never regenerates it or overwrites players.

## Safety / regression evidence

- `tests/api/test_reviewed_player_generation_context.py`: reject stale saved HEAD, draft changes, dirty draft, foreign saved snapshot, changed live or saved World, and protected Run; allow only exact reviewed context.
- `web/src/components/RunInitialWorldSetupPanel.test.tsx`: actual preview/approve/confirm/Save ordering and header-bound review.
- `web/src/pages/RunPlayerGeneratorPage.test.tsx`: current Run/Branch only; historical checkpoint and foreign Branch prohibited.
- `web/src/pages/RunPage.test.tsx`: canonical single entry link.
- `scripts/admin_first_tournament_smoke.py`: real Chromium → saved World/Calendar → Players/Generate → preview → confirm → manual Save → ranking → tournament → saved replay after restart.

Required final-head CI/browser workflows must pass before PR is marked merge-ready. This is a narrow first supported operational slice, not the full pre-alpha release gate.

## Follow-up PR scope, still open product decisions

Support constraints/groups, generated-player amendments, session `Keep` and regeneration of the remainder, richer validation/summary and named presets without changing the generator authority. Automatic remainder assignment and nested/overlapping group accounting remain explicitly OPEN. Current player generation supports **only initial cohort creation on a Run not yet owning InitialWorld**; it does not append to arbitrary later cohorts or replace existing players. Full canonical 0–200 OVR read projection and existing playing-season time/attribute scope remain separate prerequisite contracts.
