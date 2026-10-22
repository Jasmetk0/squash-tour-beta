# Parallel Chat A — Test Labs guided authoring (22 October 2026)

## Ownership
- Draft PR: https://github.com/Jasmetk0/squash-tour-beta/pull/1633
- Branch: feat/test-labs-guided-authoring-20261022
- Base: buuk 0bd062166150283e22163f52a97aa96649bcbf04
- Files: three TestLabPage.tsx pages, their tests, web/src/components/labAuthoring/ and this handoff.
- Concurrent chats own World Packages and simulation controls. Do not edit their files. Assistant never merges.

## Implemented
1. Shared guided authoring connected to the unchanged LabSessionEditor text buffer in Match, Tournament and Player pages. Existing raw JSON stays available and opens initially for test/keyboard compatibility; a one-click guided form and explicit mode switch are available.
2. Supported existing fields: scenario ID; Match seed, best-of, games-to, win-by, upset variance; Tournament name, draw seed, match seed and match format; Player v2 seed, per-variant existing weekly competitive-match counts (0–32 per week), and unified 1–61 week experiment duration.
3. Weekly workload edits require one explicit Apply and preserve all other variants and any original Health timeline. Player duration also requires an explicit Apply after typing, avoiding accidental truncation on partially entered numbers; it changes all variants together and added weeks carry zero completed competitive matches. A scenario with an explicit Health timeline blocks guided duration edits instead of fabricating new medical history. Backend alone validates calendar horizon and sporting semantics.
4. Guided field patches preserve nested unknown data, source_snapshot, source_reference, source_fingerprint and other provenance untouched. No new simulation authority, Run live link or browser-stored fingerprint.
5. Import a scenario JSON file (not a Session or result), validate Lab kind/schema version and basic shape, limit file to 2 MiB and refuse delayed reads if local editor or Session changed meanwhile. Import only edits the draft buffer; no Save/Run.
6. Explicit JSON export from current editor; Saved Session change review by changed JSON paths and display name. Scratch, Session and historical-copy states labeled separately.
7. Match and Tournament scratch editors now offer an explicit 'Create Test Session from scratch' command using their existing scenario-taking create API, including imported JSON. The backend still creates an isolated Session; no automatic Run/Save/Apply. The existing editor ticket controls delayed create response installation.
8. Existing concurrent Save/import selection tickets, backend fingerprint checks and isolated sources remain intact.
8. Form inputs cannot trigger an implicit Run via the Enter key. Staged Player inputs reset when another scenario edit or Session selection supersedes them.
10. Pure/frontend regression tests added for version checks, exact unrelated-field/provenance preservation, numeric bounds, Player Health-duration guard, weekly-match editing, explicit duration Apply, form/JSON switch, successful and invalid file import, saved-Session change review, scratch-to-Session creation and late file read. These are not real API integration tests.

## Status and merge policy
- This PR is intentionally **Draft** and NOT merge-ready.
- Dedicated genuine Lab API/Chromium acceptance skips Draft PRs. Skipped jobs are not passes.
- Verify latest-head Fast CI / TypeScript and focused frontend tests, then relevant exact-head Ready/manual real API/Chromium acceptance before the owner merges.
- The historical 78 failures in 13 Viewer tests documented in CURRENT_STATE are baseline and may not be hidden or described as passing.
- Complex participants, tournament topology/qualification, Health and career AI still need Advanced JSON or separate canonical contracts. The guided editor is an explicit small subset, not a new schema.
- No backend, shared editor, client, routes, global styles, i18n resources, CI, Master, CURRENT_STATE or ROADMAP modifications.

## Next work in this SAME PR
Check exact-head CI, fix failures, add success-path import/export and Save change review tests; inspect real supported scenarios in browser once possible. Keep continuing changes on PR #1633 only. Do not produce merge claims from mock-only tests.
