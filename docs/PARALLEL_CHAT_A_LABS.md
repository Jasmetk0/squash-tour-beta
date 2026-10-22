# Parallel Chat A — Test Labs guided authoring (22 October 2026)

## Ownership
- Draft PR: https://github.com/Jasmetk0/squash-tour-beta/pull/1633
- Branch: feat/test-labs-guided-authoring-20261022
- Base: buuk 0bd062166150283e22163f52a97aa96649bcbf04
- Files: three TestLabPage.tsx pages, their tests, web/src/components/labAuthoring/ and this handoff.
- Concurrent chats own World Packages and simulation controls. Do not edit their files. Assistant never merges.

## Implemented
1. Shared guided authoring connected to the unchanged LabSessionEditor text buffer in Match, Tournament and Player pages. Guided controls and the legacy JSON textarea now appear together by default (combined mode); the user can select guided-only or JSON-only without altering the draft. This preserves existing keyboard/regression flows while making basic editing discoverable without entering JSON.
2. Supported existing fields: scenario ID; Match seed, best-of, games-to, win-by, upset variance; Tournament name, draw seed, match seed and match format; Player v2 seed, per-variant existing weekly competitive-match counts (0–32 per week), and unified 1–61 week experiment duration.
3. Player Lab offers both a one-week-at-a-time variant/week selector with an explicit Apply and an optional full weekly-count list for experienced users. Workload edits preserve all other variants and any original Health timeline. Player duration also requires an explicit Apply after typing, avoiding accidental truncation on partially entered numbers; it changes all variants together and added weeks carry zero completed competitive matches. A scenario with an explicit Health timeline blocks guided duration edits instead of fabricating new medical history. Backend alone validates calendar horizon and sporting semantics.
4. Guided field patches preserve nested unknown data, source_snapshot, source_reference, source_fingerprint and other provenance untouched. No new simulation authority, Run live link or browser-stored fingerprint.
5. Import a scenario JSON file (not a Session or result), validate Lab kind/schema version and basic shape, limit file to 2 MiB and refuse delayed reads if local editor or Session changed meanwhile. File import now stages a read-only proposal with file/type/scenario identity and changed-path preview. It does not replace even the editor text until the user explicitly clicks Apply. Cancel, editor edits, selection changes and saved Session fingerprint advances invalidate the proposal, including same-text remote Save acknowledgement. Apply edits only the draft buffer; no Save/Run.
6. Explicit JSON export from current editor with a filename sanitized from the scenario ID; Saved Session review shows changed JSON paths, small before/after scalar values and display name without dumping deep sporting/Health objects. Scratch, Session and historical-copy states labeled separately.
7. Match and Tournament scratch editors now offer an explicit 'Create Test Session from scratch' command using their existing scenario-taking create API, including imported JSON. The backend still creates an isolated Session; no automatic Run/Save/Apply. The existing editor ticket controls delayed create response installation.
8. Existing concurrent Save/import selection tickets, backend fingerprint checks and isolated sources remain intact.
9. Scalar guided inputs and Player workload/duration controls stage local values until Apply. Form inputs cannot trigger an implicit Run via the Enter key. Staged Player inputs reset when another scenario edit or Session selection supersedes them.
10. Editor editing stays available while a Run computation is pending; existing mutation snapshot and late-reply guards still protect the submitted command/result.
11. A blank scenario shows a useful Load/Import prompt, and English/Czech editor messages have focused coverage; invalid JSON does not add a duplicate alert over the page-level validation.
12. Pure/frontend regression tests added for version checks, exact unrelated-field/provenance preservation, numeric bounds, Player Health-duration guard, weekly-match editing, explicit duration Apply, form/JSON switch, file staging, explicit Apply, cancel, wrong-type rejection, stale selection, JSON export, saved-Session before/after review, scratch-to-Session creation and late file read. These are not real API integration tests.

## Status and merge policy
- This PR is intentionally **Draft** and NOT merge-ready.
- Dedicated genuine Lab API/Chromium acceptance skips Draft PRs. Skipped jobs are not passes.
- Verify latest-head Fast CI / TypeScript and focused frontend tests, then relevant exact-head Ready/manual real API/Chromium acceptance before the owner merges.
- The historical 78 failures in 13 Viewer tests documented in CURRENT_STATE are baseline and may not be hidden or described as passing.
- Complex participants, tournament topology/qualification, Health and career AI still need Advanced JSON or separate canonical contracts. The guided editor is an explicit small subset, not a new schema.
- No backend, shared editor, client, routes, global styles, i18n resources, CI, Master, CURRENT_STATE or ROADMAP modifications.

## Exact-head checks and next work in this SAME PR
- Last confirmed Fast CI success: commit 2c478043 (199 stable + 51 focused frontend tests, TypeScript/Vite build). Newer combined-mode/Player-week commits need current-head verification; never reuse an older run as evidence.
- GitHub-hosted Fast CI runs focused frontend Vitest and web build. No local node_modules checkout is available in this chat; local TypeScript/build execution was not performed. Hosted job logs are the evidence.
- Verify latest-head CI test/build; a combined-mode invalid JSON duplicate-alert regression was fixed after Fast CI exposed three matching-alert failures. Re-run exact-head tests.
- Real HTTP/SQLite and Chromium Test Lab workflow is skipped automatically on Draft; a required Ready/manual run is still **not executed**. It must pass on the final SHA before owner merge. Draft skips are not green acceptance.
- Continue changes in PR #1633 only. Never merge, never claim success solely from mocked tests or historical head checks.
