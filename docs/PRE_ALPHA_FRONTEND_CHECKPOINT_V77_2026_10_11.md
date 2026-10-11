# Frontend checkpoint v77 — 11 October 2026

This is a scoped code/CI review, not an internal release declaration or full test-suite run.
Product authority: Master v77. Branch reviewed: `buuk`, commit
`9fb8c519b203d91fbd35d9981090c79fd474143a`, after merge #1365.
No open PR was returned by the baseline inventory.

## Review method and evidence limits

Read all six PR patches, their final feature-head CI summaries, current routing,
Runs/catalog/World apply code, Run/Branch guard and Players read contracts.
Read production Chromium/FastAPI/SQLite browser logs for #1362 and #1365.
The review did not rerun local runtime tests, inspect rendered screenshots or run
the full release gates. Green hosted checks prove their exercised scope only.
Earlier #1358 saved replay/fork/restart evidence remains dated evidence; this
checkpoint does not newly prove divergent evolution or full season continuity.

## New merged PRs

| PR | Final feature head | Correct implemented scope | Remaining boundary | Successful final-head workflows |
| --- | --- | --- | --- | --- |
| #1360 | `16ef1772c1a19cad079a45e76c3cd054aabfa232` | Canonical Runs inventory, lazy Branch/time expansion, exact Admin deep links; separate legacy diagnostic; sidebar persistence and CZ/EN submenu corrections. | Quick-open policy remains open; legacy pages are not made Branch-aware by shell context alone. | Fast CI 38128612199; Shell Browser 38128612182. |
| #1361 | `5c0a45fc52d85d8c454a5ae3b48f2cdb77c07d2c` | Source-backed World/Countries categories, deduplicated inventory, actual World Overview/Contents/Validation. | Only World sources are inventoried. Other existing competition source types require adapters; Player/Hybrid schema is not invented. | Fast CI 38129519855; Shell Browser 38129519866. |
| #1362 | `843764b193468e2bf047833f3969753c50ab88a9` | Selective World entity apply, server-owned diff and dependencies; review binds source/state/HEAD/draft/selection; confirm stages draft, manual Save creates revision. | Entity-level selection, not arbitrary field selection. Global Apply lacks an unsaved-target safeguard; create-Run entry does not preserve an automatic return flow. | Fast CI 38131090635; Shell Browser 38131090597. |
| #1363 | `85fe536b2585a423e1c2931ba432cf2029c47baf` | Replay cursor reset when authoritative match/scope changes. | Does not implement new player tabs, attributes editor or historical player projection. | Fast CI 38131660706; Saved Replay Browser 38131660709. |
| #1364 | `cd709f279747a4483defa143f1da9cd22cce209c` | Evidence-based local edits plus matching backend dirty draft; read-only filters and clean Run exits avoid false prompts. | DOM-based form tracking still is not a complete router-level dirty-state contract. | Fast CI 38132359428; Shell Browser 38132359472; Saved Replay Browser 38132359504. |
| #1365 | `5d3e3f3d1c6c944322fc22d807a09301063b9f1f` | Provider guards imperative selectBranch; Run selector and Simulation open action use same guard; approved native Branch link avoids duplicate prompt. | Denied deep link leaves URL/selection mismatch; invalid link clears selection before safeguard. Other programmatic/history navigation is not comprehensively guarded. | Fast CI 38133066957; Shell Browser 38133066997. |

Each listed workflow was returned as completed/success at review time on that exact
feature head. All six PRs were already merged; this is not a new merge approval.

Latest Shell Browser log reports neutral startup, all three Labs without Run,
Run creation, correct 50/61 Home, Branch selection surviving reload without
Viewer-pointer change, sidebar preferences, clean exit with no warning,
cancel/approve Branch dropdown and selective Save of one real World entity,
with no browser errors. The browser test selects a whole entity, not one field.

## Findings to address

### F1 — URL and selected Branch disagree after rejecting a deep link

`web/src/admin/AdminBranchContext.tsx` checks a requested query Branch in an effect.
When the user declines the transition, it returns without restoring the old URL.
The new `AdminBranchContext.test.tsx` explicitly expects `?branch=a-other` while
the selected Branch remains `a-viewer`. A reload then treats the URL as initial
selection, creating a route to a Branch that the user just declined. This is a
code/test-confirmed mismatch; no new browser reproduction was run in this review.

Additionally, the invalid requested-Branch path deletes selection before reaching
the safeguard. Keep the invalid-link error/fail-closed behavior, but protect the
current draft/form and do not silently replace the URL's context with another
Branch. Fix navigation before context changes; rejected transitions must preserve
URL, selected Branch and inputs together.

### F2 — Incomplete navigation and global Apply draft protection

`RunNavigationSafeguard` handles native links and beforeunload; scoped imperative
call sites consult the guard. It does not block all router `navigate` calls or
browser back/forward. Global `WorldPackageApplyPage` is outside this Run component
and can stage an unsaved draft for its explicit target Run/Branch. Navigation or
target selection clears local `pendingSave` without an equivalent safeguard.
This does not establish persisted data loss: the backend Working Draft remains.
It does establish an unprotected user workflow and loss of the local Save context.
Cover local review state, target draft, cancellation, failed/stale Save and
recovery. Do not protect read-only search/filter changes as if they were edits.

### F3 — Canonical Players list/profile are not one coherent data source

`PlayersPage.tsx` calls `listRunPlayers(runId, ...)` and `getRunPlayerDetail(runId, ...)`
with keys that omit Branch, Saved Revision and time. It shows a selected Branch
label next to these Run-level results. The newer `/people/:playerId` saved profile
does validate Run/Branch/head/player and rejects historical mode; this safer
profile does not repair the Explorer. Build a canonical read projection/table and
use it for navigation to the canonical profile; retain legacy diagnostics under
an explicit boundary. No today's values under historical time or borrowed legacy
identity/attributes when a selected snapshot lacks them.

### F4 — Partial feature completion is honestly exposed, but still incomplete

`catalogFromWorlds` only inventories World sources; Countries is valid owned
content. Empty Player/Hybrid categories are honest, not their implementation.
Existing Category/Series/Calendar/Setup registries need actual inventory/detail
adapters when ready. A reference is not contained data.
World Apply selects entire package entities and shows JSON-level before/after;
the approved field-level partial-change target is not delivered. A later slice
must validate and fingerprint a supported field patch and preserve unselected
fields, or keep that action explicitly unavailable. Do not claim arbitrary
partial selection complete based on entity checkbox tests.

## Next coherent work

1. Repair navigation consistency and global Apply safeguards with focused unit
   regressions and real browser cancel/accept/back/forward/Save cases.
2. Build canonical Branch/revision/time-scoped Players inventory and three-tab
   profile over real available fields, reusing saved ranking/results/replay.
   Unsupported historic/attribute slices are explicit; missing is not zero/NR.
3. Connect a first unified Generate preview/confirm vertical slice to existing
   generation kernels and canonical Run snapshots. Keep preview side-effect-free,
   bind commit to exact context/input/seed/model, preserve lock/provenance and
   manual Save. Use explicit fully specified batches while remainder and group
   overlaps are open. Do not retune talent or invent Player Package serialization.
4. Extend supported conditions, preview edits/Keep and summaries in separate PRs;
   add World country/intake editors after the canonical ownership boundary exists.

Refresh `buuk` and open PRs before each new slice; parallel chats may have already
implemented it. User owns merge. Update current-state evidence, not product canon
from implementation choices. Required latest-head checks must be green before
sharing a PR as a merge action. Full regression/release gates are still required
at the actual internal-release boundary.
