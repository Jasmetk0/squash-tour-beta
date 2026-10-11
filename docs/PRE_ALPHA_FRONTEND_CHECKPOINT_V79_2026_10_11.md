# Pre-alpha frontend checkpoint v79 — 11 October 2026

## Scope and immutable baseline

Repository `Jasmetk0/squash-tour-beta`, integration branch `buuk`.
Audited HEAD `d1090495f3771e97995b94a6f1d119e7218a816b`, tree `ad0d1549733a5d012afe20dd3854b236c851f1f2`, merge #1383.
Previous Master checkpoint #1375 is reachable in this baseline. All eight new PRs #1376–1383 are merged into buuk. Compared their patches, actual current production files and final feature-HEAD hosted workflow/jobs. This is a focused integration/code review with hosted test evidence; no local full-suite or 50-season release execution is claimed.

## Final-HEAD CI inventory

Skipped irrelevant jobs are not successful runtime tests. Workflow/job conclusions below were inspected on each final feature commit; no failed/pending required run was substituted by an earlier green commit.

| PR | Final feature HEAD | Completed workflows |
| --- | --- | --- |
| [#1376](https://github.com/Jasmetk0/squash-tour-beta/pull/1376) | `7f44a3c3b6101ae6628bff0730832ea446d16055` | [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38153395267): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38153395168): success |
| [#1377](https://github.com/Jasmetk0/squash-tour-beta/pull/1377) | `762e6febc046c44023ba2a021ae47f6a1abde1d1` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38156027302): success; [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38156027292): success |
| [#1378](https://github.com/Jasmetk0/squash-tour-beta/pull/1378) | `f473db33d394e96f2352bfcd3cb8e5066d3cda07` | [Pre-alpha Large Initial Player Cohort Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38156937080): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38156937009): success |
| [#1379](https://github.com/Jasmetk0/squash-tour-beta/pull/1379) | `5fea2e896fc1e81fcd70bb3ab1f2f8c5367090bd` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38161269591): success; [Pre-alpha Large Initial Player Cohort Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38161269626): success; [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38161269620): success |
| [#1380](https://github.com/Jasmetk0/squash-tour-beta/pull/1380) | `a33f2de22845edfcb4ba1027efa4d89cf0be731e` | [Pre-alpha Large Initial Player Cohort Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38162083966): success; [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38162083896): success; [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38162083895): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38162083894): success |
| [#1381](https://github.com/Jasmetk0/squash-tour-beta/pull/1381) | `aa3f9a91cb060ed37e5e2f38c0faef2ec7d359ae` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38164884524): success; [Pre-alpha Large Initial Player Cohort Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38164884529): success; [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38164884561): success |
| [#1382](https://github.com/Jasmetk0/squash-tour-beta/pull/1382) | `6d9c0deba2f8fd14e18e4fe76796699dc2163a1f` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38168686232): success; [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38168686212): success; [Pre-alpha Large Initial Player Cohort Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38168686216): success; [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38168686214): success |
| [#1383](https://github.com/Jasmetk0/squash-tour-beta/pull/1383) | `6a9dfc4e57cfa4105da84f074df0ef32f729d60f` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38169844074): success; [Pre-alpha Large Initial Player Cohort Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38169844073): success |

#1382 changes only concurrency in three browser workflows; Fast CI has successful change detection and irrelevant runtime jobs skipped, plus all three browser workflows successful. It keeps independent workflow_dispatch runs outside PR cancellation. This is CI behavior evidence, not a billing/cost assertion.

## Correct integrated behavior

- #1376 restores the one-pass Keep delta onto actual buuk: the v78 missing-integration finding is resolved.
- #1377 uses separate geographic/travel predicates and options; same-label collision regression is present, while recorded legacy OR semantics and absent-field fingerprint material stay compatible.
- #1378 raises the supported UI first-cohort size to 1,000, reviews all rows through bounded pagination, and rejects duplicate identities. Canonical saved Players readback remains authoritative.
- #1379 authenticates each repeated Keep step through deterministic source replay and fingerprints. Selection changes block adoption until applied; Keep does not become a lifetime lock.
- #1380 validates nine numeric legacy source fields, exact field locks, source provenance and complete server-returned preview. Impossible current/potential/hidden-ceiling or missing-ID edits conflict rather than change silently.
- #1381 stores immutable named Run/Branch-owned proposal snapshots separately from Working Draft/Run Save; verifies checksums/provenance; Open returns the stored cohort without RNG generation. Pending Keep/locks are restored but do not silently become Adopt.
- #1382 groups outdated PR browser runs per workflow/PR; manual runs use a distinct run_id and cancel-in-progress=false.
- #1383 enforces explicit-total, whole-cohort, distinct-country exact quotas, including zero exclusion. Only other eligible countries receive the automatic remainder. Keep counts cannot exceed quotas; impossible remainder/eligibility and malformed quotas fail explicitly. UI verifies whole-cohort exact counts. No quota fields preserves old fingerprint normalization.

## Findings and limitations requiring follow-up

**F79-01 — editable field locks stop at the first Keep pass (product integration gap).**
`RunInitialWorldSetupPanel.tsx` sets fieldEditingEnabled only when keep_from_seed is null; fieldPreviewAction also requires no selected Keep IDs. The backend replays prior requests with the current field_locks, so changing locks cannot simply be pasted into authenticated historical requests: it changes the expected source fingerprint. Supported tested flow is edit before Keep, then preserve that profile. The decided workflow requires continued supported edits after Keep and restored sessions, with explicit coherent precedence/conflict validation. Next PR should introduce a versioned authenticated session-operation representation; preserve old immutable preview/replay paths and never trust arbitrary browser player snapshots.

**F79-02 — stale proposals cannot even be read (partial target fulfillment).**
`read_run_generation_proposal` calls _assert_reviewed_generation_context against stored HEAD/draft/package and refuses any already-created InitialWorld before returning data. This safely blocks stale adoption, but the v78 contract requires warning and explicit new validation rather than loss of inspection. Separate exact nonmutating historical proposal read from current-target adoptability and explicit revalidation. Never automatically regenerate/rewrite the saved proposal. Original Run/Branch ownership must remain strict; this finding does not authorize cross-Run copying or bypassing writable/context guards.

**F79-03 — temporary naming is not implemented.**
`InitialPlayerPoolGenerator._name` still samples given/family names. Decided default is country name + generation serial. New presentation/identity contract must preserve stable player IDs, old snapshot fingerprints and existing/imported names; document counter scope and Keep/branch/retry behavior rather than silently rewriting historical players.

**F79-04 — new v79 selection/Undo/Add targets are pending.**
Inspector has fixed source-model columns and 50-row pagination; current direct Adopt is whole InitialWorld only. No general subset append or undoable bulk command is proven. Action selection must remain distinct from Keep/filter; chosen subset needs its own explicitly validated addition contract and remaining-proposal/duplicate safeguards. Do not implement partial authoritative-world replacement.

**F79-05 — legacy model and broader backlog remain.**
Nine source fields 1–99 are not canonical 57 attributes/OVR 0–200. Numeric ceiling/calibration decisions remain open; unsupported height/weight, advanced grouped constraints, presets, shared older-player development, future-profile activation and general existing-pool additions are not complete. The 17-reroll and 12-proposal limits are documented implementation caps, not newly approved sport rules. Backend field_locks currently caps the list at 2,000 records.

**F79-06 — dated contract documents overstate current restrictions if read alone.**
Earlier docs still say one-pass/no-field-lock/candidate or 1–128. They are historical slice evidence. The active current-state/roadmap and this checkpoint supersede their current-limit claims; later runtime PRs should synchronize touched contract docs rather than delete test/provenance history.

## Evidence boundary

#1383 [backend job](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38169844074/job/114559986878) reports 32 passed / 3676 deselected; frontend jobs report 155 + 33 focused tests and build. [Real large-cohort browser job](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38169844073/job/114560014281) reports `1000-PLAYER BROWSER/SQLITE ACCEPTANCE PASSED`. Its script verifies exactly 20 + 10 fixed country profiles, 970 automatic remainder, complete canonical player inventory after Adopt/Save/ranking and identical identities/order after terminating/restarting the production backend with the same SQLite.

#1381 [saved-player replay browser job](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38164884561/job/114555183201) and actual script verify field editing before two Keep passes, exact saved proposal page reload, 64-player Adopt/Save, ranking, real tournament matches and saved replay after backend restart.

These separate scenarios do not prove all combinations at 1,000 players, evolving locks after Keep, stale-target revalidation, full-season/full-Run acceptance or realism. Broader release gates in docs/PRE_ALPHA_TEST_POLICY.md and Master §31 remain mandatory at release.

## Product consolidation v79

Confirmed decisions since v78 are now canonical in Master §§9.7, 27.21, 31.34 and synchronized constitution/UX/frontend docs. They cover generator columns/bulk session Undo/subset Add; brief World overview; six country tabs and season scrolling; weekly/list calendar; Edition/phase layout; match/replay; simulation console; ranking points side panel. General OPEN mechanics/calibration and deferred animation/Live Ranking are preserved. Qualification/Main switch is only in Draw & Groups; other views use both sections and scroll anchors.

## Next implementation order

1. F79-01 authenticated edit/lock/Keep session integration, including exact saved-proposal restore, focused adversarial tests and production browser roundtrip.
2. F79-02 exact stale-proposal inspection and explicit current-target revalidation, with fail-closed Adopt and no hidden regeneration.
3. F79-03 temporary country+serial names and standalone generator layout/configurable supported columns, preserving canonical data honesty.
4. Bulk selection/edit/diff/session Undo on supported fields; subset Add requires a separate safe generic append/persistence slice rather than an InitialWorld shortcut.
5. Build approved World/country/calendar/Edition/match/replay/ranking pages incrementally on actual authorities; extend missing backend projections where needed.
6. Continue remaining generator/model/season/intake foundations and full pre-alpha release acceptance; this checkpoint is not a declaration of release.

One coherent vertical slice per PR, ordinary base=buuk, user merges. Refresh HEAD/open PRs before each slice and never claim merge readiness before all required final-HEAD checks finish green.
