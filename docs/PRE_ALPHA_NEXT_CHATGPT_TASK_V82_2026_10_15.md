# Next ChatGPT implementation task — Master v82 (15 October 2026)

Repository: Jasmetk0/squash-tour-beta. Integration branch: buuk. The user merges; never merge PRs. First fresh-fetch current buuk/open PRs and reconcile newer work. Audited base: b63f40387bed75812ae9f9585734a6226b93fda9 after #1488. The v82 documentation PR must be verified before overlapping canon changes; do not duplicate any in-flight implementation.

## Authority and working method

Read AGENTS, complete relevant Master v82 product sections (3.2, 6.1, 6.9–6.12, 31.37), CURRENT_STATE, ROADMAP, the v82 checkpoint and PRE_ALPHA_TEST_POLICY. Preserve the rest of the Master. The old universal 50 × 61 restriction is explicitly superseded; FAX defaults and its 50-season release reference remain. Target status is not runtime evidence.

Implement directly with available ChatGPT tools by default. Ordinary fixes/UI/docs/pure time calculations do not need Codex credits. Use Codex only when a bounded hard compatibility/transaction/recovery task benefits from it. Suggested available model: GPT-6.1 Sol, Medium for a scoped task; consider High for difficult history/concurrency integration. Availability/effort are client-dependent; no automatic Max/Ultra. Official guidance checked 15 October: https://learn.chatgpt.com/docs/models . This is a task recommendation, not a promise of exact usage or universal free access.

Before each PR state the new usable behavior, direct-versus-Codex choice/reason, and concrete implementation prompt (with model/effort if handed off). One coherent functional slice per PR. If credits run out, retain the same branch, PR and last commit; hand off changed files, passed/pending tests and exact next step, then continue directly. No duplicate PR or second implementation. Surface PR for merge only after relevant checks pass on its final HEAD; user owns merge. Report what comes next.

## Immediate small PR — direct ChatGPT

Fix A82-01 in FullSimulationWeekScheduleReview: after an uncertain request is cancelled, fresh intent requires fresh consent even if all proof fields are unchanged. Explicit retry must still send the EXACT frozen Run/Branch/body/command ID. A changed proof/scope/revision must still revoke consent, including change-back. Add unchanged-proof cancellation regression; preserve old cancellation-with-drift, response-loss retry and scope tests. Do not add sport, auto-resume or Save. Keep this small; no new long browser workflow for a component-only fix.

## Main calendar path — start after the small fix

Before editing, inspect actual current callers and propose a short dependency order. Do the inventory inside the implementation task; do not spend a standalone PR or large paid task merely restating this document. Use rg for hard-coded 61/37/26/2000/2049/50, but distinguish unrelated numbers and explicit FAX/PR policy from universal time arithmetic.

1. Central versioned calendar contract and exact conversion/validation: W weeks per year AND season, offset O, start year and horizon. Default Earth=52, FAX=61/O37; empty name-only creation keeps valid defaults. Positive equal-length years, no civil dates/ISO53. Existing mapping signatures with apparent parameters still reject non61; inspect before reusing. Preserve legacy byte/hash/replay behavior via explicit schema-version compatibility, distinguish absent from malformed data. Avoid mutable global defaults or per-page hidden authority.
2. Carry that contract through actual Run persistence/bootstrap/API/Saved Revision reads and authoritative Week/Season/Full Simulation targets. Read immutable historical calendar evidence and current Run configuration from the correct authorities; no local UI-only switch. Lock structural settings when first week starts, with dependency validation before start. Frozen current goals must not grow after horizon extension. Do not expose 52-week sport execution until the touched command paths really support it; report unsupported operations honestly while migrating incrementally.
3. Usable Admin configuration/preview: start year, W, offset, first/last endpoints; last season OR count with mutual conversion; single-year labels for O1, crossing-year otherwise. Run Home/calendar/progress/validators/deep links use actual Run data, never 2000+index. Finish new #1488 CS/EN guidance. Backend validation is authoritative; UI cannot bypass it. Settings may not silently corrupt already prepared players/calendars.
4. Age/generation/annual country source year and long-term development use 1/W elapsed year. Preserve individual traits and existing abstract training/health semantics; do not tune realism or divide every weekly/acute rate blindly. Ranking result default W, existing explicit overrides and first-publication timing unchanged. Entry/penalty durations stated in weeks stay weekly; special PR policy does not get globally rescaled.
5. Explicit horizon extension including Completed, across Branches, without history rewriting, future generation, auto-Save, worker start or terminal-task reopening. New continuation performs formerly unperformed boundary work exactly once. Import preview corrects/skips conflicting dates/dependencies, never clamps/wraps/rescales silently; independent compatible selections remain possible. Use normal protected-source/copy safeguards.

These are dependency areas, not a demand for exactly five PRs or a giant all-at-once rewrite. Choose bounded coherent slices from actual dependencies and update implemented-versus-pending evidence after each one. Direct ChatGPT should handle clear work. If using Codex for hard integration, hand off only the selected slice with exact files/schema/invariants/tests discovered so it does not repeatedly rediscover the whole repository. Preserve default FAX behavior throughout.

## Required verification by impact

- Pure mapping round trips/boundaries for W52/O1, W52/O35, legacy W61/O37 and another valid W; invalid metadata/offset/index inputs fail honestly. Single-year display is not permission to rewrite old stored season IDs.
- Real SQLite/API create/read/Save/reopen and legacy compatibility for persisted-calendar changes. Old Saved payload hashes, ranking/replay and pre-fork ownership stay identical; no current fallback in history.
- Last week -> next season, mapped year boundary, birthday age and annual growth units; point expiry exactly after W valid weeks, explicit week-based rules unchanged. Do not invent final growth coefficients from a test fixture.
- Extension from Completed and from another Branch with no auto-resume/goal growth; stale revision/concurrent mutation, atomic rollback, idempotent retry and original closure preservation.
- CS/EN UI preview/import conflict and no silent writes. Tests must exercise the relevant new public behavior, not mirror implementation mechanically. Run only relevant suites per PR; release-wide gates remain for release. Do not regenerate lockfiles for convenience.

## Preserve and finish genuine sports acceptance

The #1484 same second parent reached Season index1 Week1 and stopped at week_preparation_required after 3 actual games. #1488 only adds navigation. Preserve this acceptance and diagnose the ACTUAL stored blocker before resuming implementation. Once the calendar contract is safe for the path, extend the strongest existing real SQLite/Chromium scenario with a genuinely authored/copied/Saved new-season Calendar, multiple real Tournament Editions and real MatchEngine games to a named concrete next-week goal on the same nonterminal task. A generic awaiting_operator result is not positive success; retain legitimate blocker cases as separate negative tests. Do not manufacture results or interpret missing calendars as empty weeks. Avoid one expensive near-duplicate workflow per tiny extension of the same scenario.

No full-backend, full-season, 1000-player/80-Edition, 50-season, release or realism claim follows from mocks, sparse empty weeks or green unrelated CI. Carry unresolved exact growth curves/coefficients, detailed training/deload, deferred Compare/statistical calibration and pending product decisions unchanged.
