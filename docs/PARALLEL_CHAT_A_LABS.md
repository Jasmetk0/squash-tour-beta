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

### Subsequent guided editing (22 October 2026)

- Match and Tournament now offer direct changes to the five canonical participant context modifiers (form, sharpness, fatigue, health and travel; each −0.35 to +0.35). The selector targets exactly one existing player by immutable player_id. Only that context input changes; the player record, opponent, seeding, historical source/snapshot, Session and Run are preserved.
- Tournament offers an explicit stop-after-round control (no limit, or rounds 1–7), with Apply; the backend remains the authority on tournament compatibility and draw topology.
- Saved Session review now descends equal-length participant and weekly workload arrays to identify the exact scalar path and old/new value (for example participants.1.sharpness_modifier or variants.0.competitive_match_counts.2). Whole-array length changes stay summarized, long change sets remain capped.
- Focused tests include both Lab modifier boundaries, unknown-field/provenance protection, single-player and single-week isolation, round-limit bounds, staged UI Apply, and scalar diff. This changes no backend/API schema.
- Verify Fast CI on the final commit; genuine real HTTP/SQLite/Chromium gates skip the Draft PR and remain required before user merge.

### Guided test outcome assertions and improved selection (22 October 2026)

- Tournament Lab now edits two existing backend assertion fields from the guided UI: `expected_champion_player_id` (optional string) and `expected_played_match_count` (optional nonnegative integer). Empty input writes null, disabling the assertion. Deliberately false expectations are allowed for test diagnostics; no simulation rules, result, seed or Run authority changes.
- Assertion controls preserve independently staged champion/match-count values across applying the other field. Selection and editing changes still preserve source snapshots and keep Session Save explicit.
- Selected Match/Tournament participant and Player competitive week survive local scalar Apply; after shortening a Player scenario, the selected week is clamped to the new available range.
- Focused pure/UI tests exercise bounds, zero, null reset, unsupported source shape, source fidelity, two independently staged assertions and selected-week/participant retention through revision changes.
- Latest successful Fast CI before this addition: `b65dbd35` (199 stable, 62 focused frontend tests, TypeScript and Vite). Reverify current final SHA; genuine HTTP/SQLite/Chromium Lab gates skip Draft and remain required before user merge.

### Existing seed priority editor (22 October 2026)

- Tournament guided mode supports moving existing seeded player IDs one position up or down. This is a pure reorder of the current `seed_order_player_ids` list, not participant creation/deletion, draw mutation, or a seed-authority replacement. It appears only when every listed ID matches one unique existing participant and the list has at least two entries.
- The original player contexts, historical source metadata, match settings, Saved Session and Run remain untouched. Normal backend compatibility inspection remains authoritative.
- Pure/UI tests cover edge positions, unknown/duplicate IDs, reversible swaps, and provenance preservation.

### Independent guided staging and ABA-safe import (22 October 2026)

- Guided fields now retain independently typed but unapplied values when a *different* guided field is explicitly applied and the parent editor revision advances. Previously, keys tied to every revision silently discarded other staged values.
- Switching Session, receiving an externally replaced JSON/source, and applying a reviewed file import reset staged form inputs. Existing variant/player selection is still retained across a normal one-field Apply, and never crosses source replacement.
- In-flight JSON file reads carry a monotonic read ticket. Editor changes and Session/source transitions increment the ticket, so a late read cannot stage an old file even after an A → B → A return to identical text/selection (ABA protection).
- Regression tests cover multiple independently staged fields with parent revision, external source replacement with the same scratch ID, and delayed file read across Session A → B → A. No backend/API/fingerprint modifications.

### Advisory pre-run input preflight (22 October 2026)

- Shared guided scenario authoring now displays **read-only, bilingual (EN/CS), path-specific local preflight** in Match, Tournament and Player Labs, including while the advanced JSON editor is visible.
- Match checks canonical distinct participant IDs, best-of/games-to/win-by/upset variance, modifiers and explicit retirement references. Tournament checks unique participant IDs, participant count 2–128, main draw 2–128, seed-priority references, match format, stop-after round and expected played-match count. Player checks variant IDs/canonical ordering, equal weekly durations 1–61, counts 0–32 and version-specific Health timeline requirements.
- Diagnoses only basic input invariants. No guesswork on sporting realism, seeding validity, backend format authority or Run compatibility. This is **advisory**: no request gating, writes, or new frontend authority; the backend remains final.
- No local warnings for empty scenario (existing empty-state cue) or malformed JSON (existing advanced-editor error). Pure and rendered tests verify both positive and negative cases, EN/CS descriptions, and that review never writes to a Session.
- Exact-head Fast CI, TypeScript build and actual browser/HTTP/SQLite acceptance status must be checked before the user merges; genuine Lab jobs still skip Draft.

### One-step local guided Undo (22 October 2026)

- New bilingual Undo button in Match/Tournament/Player Lab scenario authoring reverts **only the last committed guided Apply** in the current local editor. This is not Save revision history, Run rollback, simulation replay, or a new backend authority.
- The most recent guided operation stores exactly the preceding scenario text and an expected post-edit text + Session identity. A one-step undo clears itself after use. It cannot apply once another editor replacement/source load, manual JSON change, Session switch, remote Session fingerprint update, or editor state revision supersedes that edit.
- Undo also invalidates staged imports and resets independently typed guided fields, preventing partially staged values from contaminating the restored scenario.
- No saved Session mutation or Run write is triggered. Existing explicit Session Save and backend compatibility workflows remain unchanged. Pure/UI regression tests cover historical provenance, previous guided changes, selection/fingerprint changes, scratch replacement, and Match/Tournament/Player isolation.
- Fast CI must pass on this final commit and real HTTP/SQLite/Chromium gates remain required separately before the user merges. Keep the PR Draft.

## Status and merge policy
- This PR is intentionally **Draft** and NOT merge-ready.
- Dedicated genuine Lab API/Chromium acceptance skips Draft PRs. Skipped jobs are not passes.
- Verify latest-head Fast CI / TypeScript and focused frontend tests, then relevant exact-head Ready/manual real API/Chromium acceptance before the owner merges.
- The historical 78 failures in 13 Viewer tests documented in CURRENT_STATE are baseline and may not be hidden or described as passing.
- Complex participants, tournament topology/qualification, Health and career AI still need Advanced JSON or separate canonical contracts. The guided editor is an explicit small subset, not a new schema.
- No backend, shared editor, client, routes, global styles, i18n resources, CI, Master, CURRENT_STATE or ROADMAP modifications.

## Exact-head checks and next work in this SAME PR
- Last confirmed Fast CI success before this additional participant/round work: a11ea995 (199 stable + 56 focused tests, TypeScript/Vite build). New commits require final-head verification.
- GitHub-hosted Fast CI runs focused frontend Vitest and web build. No local node_modules checkout is available in this chat; local TypeScript/build execution was not performed. Hosted job logs are the evidence.
- Verify latest-head CI test/build; a combined-mode invalid JSON duplicate-alert regression was fixed after Fast CI exposed three matching-alert failures. Re-run exact-head tests.
- Real HTTP/SQLite and Chromium Test Lab workflow is skipped automatically on Draft; a required Ready/manual run is still **not executed**. It must pass on the final SHA before owner merge. Draft skips are not green acceptance.
- Continue changes in PR #1633 only. Never merge, never claim success solely from mocked tests or historical head checks.
