# Pre-alpha Admin navigation and World Apply guard — 11 October 2026

Status: implementation candidate in draft PR #1367 against `buuk`; implementation evidence, not new product canon or an internal-release gate.

## Problem and fix

- Declining an imperative `?branch=` transition previously left the URL on the rejected Branch while the provider retained the old Branch. The provider now restores the last accepted same-Run URL and keeps form state. A foreign/stale explicit Branch remains fail-closed, with an explanation, unless the dirty transition is first declined.
- An explicit Branch selector change replaces an existing `?branch=` query with the selected Branch, preserving unrelated query parameters. A confirmed Run/Branch selector decision is consumed once; it does not produce another router prompt.
- The production shell now uses the existing React Router data-router blocking API. The guard executes *before* links, imperative `navigate`, and Back/Forward transitions discard Run components. A clean read and read-only search filters still do not prompt. A matching successful Save remains the only way to clear local form-edit evidence.
- The global World Package Apply page has a separate guard for changed target Run/Branch, local review/approval, staged server drafts, browser navigation and unload. Rejecting a target switch restores the select value. Existing server Working Drafts can be inspected and explicitly reopened for a guarded manual Save after leaving and returning. A stale head, draft version or state fingerprint blocks Save; this does not create a Saved Revision without explicit user action.

## Safety boundaries

The UI does not change the Viewer Branch, underlying Run snapshot, stored Saved Revision or immutable history simply by navigating. There is no new sporting calibration, parallel source-of-truth player generator, automatic Save or hidden package mutation. A recovered draft may include other staged edits: the UI says so and exposes the current server state before the user opts to reopen it.

## Focused verification

- `AdminBranchContext.test.tsx`: rejection restores URL, selected Branch and edited inputs; invalid explicit Branch fails closed; selector URL and browser history stay coherent.
- `RunNavigationSafeguard.test.tsx` and `runContextGuard.test.ts`: native fallback, local edit tracking, read-only filters, single-use confirmed links.
- `AdminTransitionBlocker.test.tsx`: data-router link, imperative, Back/Forward cancellation/acceptance and clean navigation.
- `web/acceptance/prealpha_shell_browser_smoke.py`: real Chromium + FastAPI/SQLite Run edits, Back cancellation/approval, target guard, staged World selection, full route exit, persisted Working Draft reopen and manual Saved Revision Save.

At implementation review, the first green real-browser run on the candidate was `38135589653` at head `f9074c271e4a8fa76219eecdff11ccba6e29e56e`. Validate all required checks again on the **final** PR head before sharing it as merge-ready. The full pre-alpha release gate (50-season acceptance, full backend/frontend regressions, recovery) is separate.

## Next coherent PR

Build the canonical Branch/Saved Revision/time-scoped Players inventory and profile (Overview / Attributes / Career & results), without passing Run-only legacy Explorer data off as canonical or inventing historical fields. Confirm latest `buuk` and open PRs after #1367 is merged by the owner.
