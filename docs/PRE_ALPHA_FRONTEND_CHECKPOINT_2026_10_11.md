# Pre-alpha frontend checkpoint — 11 October 2026

Implementation evidence and review guidance, not new product authority or a release declaration.

## Immutable baseline and scope

- Repository: Jasmetk0/squash-tour-beta, integration branch buuk.
- Inspected base: `1f6bc2f1cfbf42e0b26b4dcb557864d2600e4ad3`, merge #1358 at 2026-10-11T09:04:54Z.
- Documentation #1347 is merged; ten implementation/test PRs #1348–1352 and #1354–1358 are merged.
- #1353 was closed unmerged as a duplicate of #1352. It must not be counted as an additional shipped feature.
- This review fetched PR metadata, changed-file inventories/patches and focused current shell, navigation, Home, read-model/router, player-history/replay and browser-acceptance sources.
- Hosted workflow records were checked against each exact final feature HEAD. All returned final-head runs below completed successfully.
- The latest #1358 browser job steps and log were inspected, including `SAVED PLAYER REPLAY BROWSER ACCEPTANCE PASSED`.
- No new local runtime, full regression/release gate or new visual screenshot assessment was performed in this documentation review. Hosted browser evidence is attributed to the existing CI runs.

## PR inventory and exact-head CI

| PR | Change | Feature HEAD | Hosted final-head checks |
| --- | --- | --- | --- |
| [#1348](https://github.com/Jasmetk0/squash-tour-beta/pull/1348) | Build pre-alpha dark Admin shell, global Home and scoped navigation | `6c65a33b` | [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38071348018): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38071348028): success |
| [#1349](https://github.com/Jasmetk0/squash-tour-beta/pull/1349) | Build canonical pre-alpha Run Home with 50/61 timeline and attention panels | `49f1f22a` | [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38072293983): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38072293860): success |
| [#1350](https://github.com/Jasmetk0/squash-tour-beta/pull/1350) | Add Branch-owned saved Calendar and published results to Run Home | `e509a58c` | [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38073054448): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38073054408): success |
| [#1351](https://github.com/Jasmetk0/squash-tour-beta/pull/1351) | Show real saved weekly ranking movement on canonical Run Home | `29d7292f` | [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38073836155): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38073836072): success |
| [#1352](https://github.com/Jasmetk0/squash-tour-beta/pull/1352) | Show Saved Revision player names and branch-safe canonical player identity details | `27fce99e` | [Pre-alpha Shell Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38074720334): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38074720324): success |
| [#1354](https://github.com/Jasmetk0/squash-tour-beta/pull/1354) | Show Branch-owned saved Official Ranking and tournament finishes on Admin player profiles | `c092b8ef` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38090174516): success |
| [#1355](https://github.com/Jasmetk0/squash-tour-beta/pull/1355) | Add canonical Saved Revision player match history with W/L and season filters | `c0a46d89` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38090673332): success |
| [#1356](https://github.com/Jasmetk0/squash-tour-beta/pull/1356) | Open canonical saved player match details and replay verified archived rallies | `44fddcdc` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38123580306): success |
| [#1357](https://github.com/Jasmetk0/squash-tour-beta/pull/1357) | Exercise saved player replay in real Chromium tournament Save and restart | `7725254a` | [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38124823891): success; [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38124823797): success |
| [#1358](https://github.com/Jasmetk0/squash-tour-beta/pull/1358) | Test atomically forked Branch saved match replays in Chromium and after restart | `f2fe1299` | [Pre-alpha Saved Player Replay Browser](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38125740716): success; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/38125740718): success |

## Alignment with the assigned frontend work

The first two assigned slices are implemented within explicitly bounded scope:
- #1348: dark Admin, no pre-alpha mode/theme selector, neutral global Home using actual Product Run/World Package registries, scope-sensitive navigation, independent global Labs, persistent shell language.
- #1349: Run Home identity, partial Working Draft status, 50-season/61-week indicators, supported simulation/revision signals, honest unavailable/empty handling and checkpoint-metadata-only historical boundary.
- #1350–1352: real Saved Calendar/published tournament results, weekly published ranking deltas, Saved HEAD player names and canonical player links.

The later profile/history/replay PRs extend those real result links in a useful direction; they do not constitute completion of all detailed frontend design:
- #1354–1356: selected-Branch Saved HEAD player identity/rank/finishes, paged completed canonical tournament match history, and replay from validated archived rallies.
- #1357: real Chromium + production FastAPI/SQLite tournament, Save, archived replay pagination, backend restart and preserved evidence.
- #1358: materialized canonical Saved Revision fork, unchanged source, target-owned equivalent replay, actual Admin Branch selection and equality after restart.
- #1358 does not prove post-fork divergent simulation. Player historical checkpoint profiles/replays are explicitly unsupported. Standalone/live matches and a complete career/development editor are not included.

## Concrete unfinished frontend work and corrections

1. **Runs remains a migration surface.** `web/src/pages/RunsPage.tsx` mixes a compact canonical list with a large legacy Simulation Run browser and legacy filters. It has no newly approved compact Branch expansion, and most content remains English. Build the canonical pre-alpha Runs screen; preserve older tools behind a clearly separate migration/diagnostic entry where needed, not as competing default worlds.
2. **Packages is a scaffold.** `PackagesHomePage.tsx` has World, category/calendar source links and an honest Player Package unavailable state. It lacks complete supported category lists, All packages deduplication, hybrid membership, the three detail tabs and selection/before-after apply workflow. Today's approvals are new target decisions; their absence is not a retroactive failure of #1348.
3. **Sidebar preferences are not persisted.** `AdminNavigation.tsx` initializes collapse/pin with component useState and no durable preference. Persist the approved preference and verify reload plus hover without content displacement.
4. **Category indication misses canonical player routes.** Run Players uses `/players`, while profiles/replays use `/people/...`. Current isItemActive logic does not map that canonical route family to Players. Add an explicit route-category mapping without relabeling legacy data as canonical.
5. **Submenu translation is incomplete.** Top-level items call t(); child links render child.label directly. Translate the supported submenu labels in both languages.
6. **Navigation protection is deliberately conservative, not complete.** RunNavigationSafeguard treats any main input/select change as a form edit, including read-only filters, and does not reset its edit flag on an authoritative Save. It always asks when a link exits the Run. Do not call this full dirty-state recovery. Integrate explicit dirty signals progressively; verify clean inspection, unsaved forms, Save/cancel and programmatic context switches.
7. **Match replay cursor lifetime needs regression coverage.** SavedPlayerMatchDetailPage index is component state and is not explicitly reset when Run/Branch/Saved HEAD/player/event/match scope changes. A shorter second replay can retain an out-of-range cursor. Add a targeted scope-change test and reset behavior in a focused fix; current scope checks prevent borrowing foreign data. The career panel already has a Branch/HEAD/player key that resets its page/filter on that scope change; do not falsely report it as missing.
8. **Home status is intentionally partial.** Working Draft indicator covers Viewer Branch selection, not every editor. Broader health/talent/world-event feeds and arbitrary historical detail are unfinished. Global search/Ctrl+K and cross-page task/notification surfaces also remain target work; existing shell does not prove them complete.

## Next coherent implementation slices

1. Canonical Runs with wide rows, compact Branch expansion and explicit correct target-Branch opening; fix related sidebar persistence, category mapping and submenu language.
2. Supported Packages category hub/lists, All packages and Overview/Contents/Validation details using real source metadata.
3. Actual selective preview/apply of an already supported Package type, with concrete old/new values, selected/excluded changes, exact target/source-version binding, stale preview rejection, manual Save and persistence/restart/isolation tests.

Keep Player/hybrid payload, identity mapping and unresolved conflict mechanics open. Do not fabricate content or implement a new serialization schema merely to fill the UI.
User-controlled merge remains required; implementation chats must read the actual newest buuk before starting each PR.
