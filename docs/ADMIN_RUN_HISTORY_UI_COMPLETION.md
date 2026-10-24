# Admin Run history UI — CS/EN read-only completion ledger

**Scope:** PR #1641, feature branch `feat/admin-run-history-csen-readonly-20261024`, against the independently verified `buuk` starting point `e39d962bb6797960c47c1c659d57be1dc67bba6b`. **Status: Draft — CI on the final HEAD is required before merge.** The owner alone merges.

## Source authority and safety boundary

The eight edited Run-scoped pages consume the existing **legacy SimulationRun** endpoints (`/runs/:runId/...`) through existing API clients: run details/status/source/lineage, activity, persisted events, ranking/race snapshots, Finals read DTOs, and rollover read DTOs. They are **not** Product Run Saved Revision, Branch sporting truth, World Event Log, public news, notification, audit, or new Full Simulation Saved-history verification. The presentation now states this distinction rather than silently implying canonical Product Run authority. The separate native work in #1639 and Test Labs/Packages work in #1640 is untouched.

UI changes do not alter request payloads, query keys, API/types, URL parameter meaning, saved values, ranking/points/rules, timestamp conversions, simulation/DB behavior, role gates, Viewer availability or server/task workflows. Refresh buttons invoke the preexisting TanStack Query `refetch` operations only. Scope validation is performed locally when the existing response exposes an identity; no missing server identity is inferred. Raw payloads and server error messages retain their original data.

The snapshot list/detail DTOs expose a sequence, kind, optional source event ID and payload **but no trusted timestamp**. Consequently the UI labels them saved historical snapshots and explicitly says that the actual save time cannot be displayed from this endpoint; it does **not** manufacture a date or label them as the live ranking. An unavailable resource or 404 is not evidence that it never existed in another history. Event existence does not imply that `tournament_result` is stored.

## Review checklist — 26 user requirements

| # | Status | What changed / what was already correct |
|---|---|---|
| 1 | Implemented | Run diagnostics headings, summaries, metadata, navigation and available statuses localize via the scoped dictionary. |
| 2 | Implemented | Per-query loading/error states remain independent; a failed Finals, status, source or history query does not block unrelated correctly scoped sections. |
| 3 | Preserved | #1638 chooses most recent saved event with a result and snapshots by **persisted sequence**, not array position. Existing regression assertions retained. |
| 4 | Preserved + localized | Existing wrong-Run, cross-season and inconsistent-progress suppression remains; actionable warnings are now CS/EN. |
| 5 | Implemented | Artifact status describes loaded, missing, unavailable and failed reads without asserting an absent historical record never existed. |
| 6 | Implemented | Activity summary, existing filters, known technical kinds, record details and link labels localize. Stored user labels and IDs are not translated. |
| 7 | Preserved | Activity remains a technical source feed with separately conditional bridge links, not a World Event Log or public news stream. |
| 8 | Implemented | A genuinely empty returned history differs from a nonempty history filtered to zero; reset affects only local filters. |
| 9 | Implemented | Counters are explicitly described as loaded/returned items; the UI makes no claim that these are complete Product Run history counts. |
| 10 | Implemented | Events list, selected details, filter labels and stored-versus-planned context localize. |
| 11 | Implemented | A saved event with `tournament_result: null` is marked as having no evidenced result; a stored result is not computed or inferred. |
| 12 | Preserved + guarded | Selection/filters remain during CS/EN toggles; data are re-scoped by Run query key and mismatched list/detail identities are rejected when provided. |
| 13 | Implemented | Ranking and Race list modes, filters, metadata and navigation share scoped translations; mode identifiers remain unchanged. |
| 14 | Implemented within API limits | Both modes are explicitly **historical**; no unexposed timestamp, current ranking, or new Saved authority is guessed. |
| 15 | Implemented | Snapshot detail labels and related source/other snapshot navigation localize; raw payload untouched. |
| 16 | Preserved + guarded | Links retain exact Run/snapshot/event references and URL encoding. A missing ordered-plan source no longer receives a guessed planned-detail link; foreign list identities are ignored. |
| 17 | Implemented | Finals qualification detail, source season/week, group and qualified-player information localize; counts come only from arrays present in returned records. |
| 18 | Implemented | Finals result detail displays stored response only and retains missing-result 404; qualifying alone does not synthesize a result. |
| 19 | Implemented | Stored rollover target/from season, metadata summaries and inspect-only navigation localize. |
| 20 | Implemented | Player transition/next-season lists and player ID filter localize; source values and calculations remain unchanged. |
| 21 | Implemented with source limitations | Loading/error/not found/true-empty/filter-empty states are separated for the relevant read DTOs; missing payload authority is not faked. |
| 22 | Implemented | Explicit read-only refresh for each applicable primary view or read collection uses its existing `refetch`; no simulation or mutation is wired. |
| 23 | Preserved + corrected | `??` prevents valid 0/false being replaced by fallback text; a failed/mismatched rollover read is **unavailable**, not a displayed count of zero. |
| 24 | Partially implemented | Filter controls use labels, targeted errors use `role=alert`, and refresh/reset have readable button text. Shared `RunScopedUi`, global responsive wrappers, and global accessibility contracts are explicitly untouched. |
| 25 | Implemented + tested | Independent live-language tests exercise an open selection/filter and a pending read: language changes do not initiate new API requests or writes. |
| 26 | Implemented, verification gate still open | Existing scoped regressions are retained, live CS/EN/read-only tests added. Exact-head automated test and TypeScript/Vite build results must be recorded from CI, not assumed from earlier commits. |

**Legend:** Implemented = this PR adds display-only behavior; Preserved = already correct and intentionally not rewritten; Partially implemented = remaining work crosses an explicit source/shared-component boundary; verification evidence is independent of this checklist.

## Files and explicit exclusions

Only the eight named pages, their colocated frontend tests plus `RunHistoryLocale.test.tsx`, the local `runHistoryText.ts` translation helper, and this document are in scope.

No changes to BootstrapLineagePage, FinalsPage, RolloverPage, `RunScopedUi`, the global language context, clients/query keys/contracts, backend, Master/AGENTS/CURRENT_STATE/ROADMAP, unrelated packages/labs, dependencies, workflows, or acceptance scripts.

## Follow-up review hardening — 24 October 2026

A separate follow-up to the same **Draft PR #1641** closes additional practical gaps found after the initial green frontend run. It adds no new files beyond the permitted page/test/helper/handoff scope.

- **Run diagnostics:** remaining recent-event statuses, sequence labels, quick-inspection link captions and list accessibility names now use the same scoped CS/EN display strings. Stored sequences, link targets and #1638 latest-by-sequence decisions are unchanged.
- **Snapshots:** list filters and accessibility labels now localize; a failed or mismatched planned/persisted source read is **unavailable**, not evidence of a missing historical relation. The sibling-history link describes its actual **unfiltered mode-list destination** instead of falsely promising a prefiltered result.
- **Snapshot detail:** previous/next endpoints retain their original server-provided order when a valid index exists, while a missing/failed/foreign index or direct detail omitted from an index cannot be presented as the start/end of history. Related snapshot metadata is explicitly unavailable when its independent read fails. Invalid and missing-sequence explanations now localize.
- **Activity:** a technical admin record without an evidenced planned-event relation no longer exposes a guessed planned detail link. Failed context reads are not described as absent records. The bridge count measures actionable links, not explanatory placeholder rows; original technical event names and identities remain untouched.
- **Event detail:** same event ID is insufficient if the stored event sequence, season or week explicitly contradicts the selected record. Such a detail's raw payload is hidden without hiding the rest of the list.
- **Rollover detail:** the manual read-only retry is disabled for invalid target-season URL parameters, avoiding unsupported refetches.
- **Regression evidence added:** English and live CS/EN scenarios cover unavailable snapshot index boundaries and preserved backend navigation order, snapshot filters during a language switch, missing/failed admin planned-event links, mismatched event sequences/season/week, and invalid rollover retry. No old #1638 assertions were removed.

These are presentation-level, existing-endpoint changes only. A fresh final-HEAD frontend test/build run is required to validate this follow-up independently of the earlier 309 passing tests.

## Follow-up hardening — cross-season provenance

The existing legacy SimulationRun history endpoints are **not** a canonical multi-season Product Run event log. Consequently, a matching `event_id` or `source_event_id` is not, by itself, proof that a stored historical entry belongs to the currently opened season plan.

- **Events:** plan joins now require consistent Run/season-state headers, season-matching planned entries and (when supplied) a matching persisted event season. A stored earlier-season event stays browsable, but does not link to the current season's plan/week using a reused event ID.
- **Activity:** derived week context checks season identity in the persisted and planned source indexes. Admin plan links and current-week bridges require an evidenced current-season relation. Seasonless admin records can still obtain a week bridge from a matching source record.
- **Snapshot list and detail:** planned context requires consistent Run/season-state headers. If persisted source and planned source disagree on season, the list doesn't join them; the dedicated detail warns and suppresses mismatched planned/week links. Historic payloads and valid persisted-source inspection remain available.
- **No schema/endpoint changes:** these guards use only already-returned Run, season-state and event history fields. A snapshot without a source season cannot independently prove a Saved Revision; no absent timestamp is fabricated.
- **Regression cases:** stale Run season-state, reused event ID with a different stored season, historic snapshots, seasonless admin source context and dedicated snapshot detail are covered by colocated tests. Existing ordering, URL and read-only behavior are retained.

## Follow-up hardening — independently loaded Finals and rollover records

The Finals summary, the per-artifact detail, and rollover records are loaded from **independent legacy read endpoints**. An agreeing outer Run/season ID does not prove that the artifact payloads refer to the same source observation.

- **Finals qualification:** when both summary and qualification detail are present, explicit `source_as_of_season` or `source_as_of_week` conflicts suppress the independently fetched detail and display a CS/EN warning. Missing source fields in an older summary are not treated as contradictory. When the summary is genuinely unavailable, a valid standalone detail remains visible.
- **Finals result:** additionally compares `event_id`, `source_as_of_season`, and `source_as_of_week` across summary and direct result. Conflicting payloads are hidden without fabricating a winner, runner-up, or result; a valid result may still be independently displayed when the summary request fails.
- **Cross-links during a pending/failed Finals summary:** navigation captions no longer claim the complementary result/qualification does not exist when the summary is simply loading, failing, or rejected as foreign. Those cases show `Waiting for Finals summary` or `... cannot be verified ...` in CS/EN; an actually loaded summary with no complementary artifact retains the original truthful absent-state label.
- **Rollover transition / next-season player rows:** verify every explicit row-level Run ID, `to_season`, and (only when an independently valid rollover summary exists) `from_season`. A foreign row invalidates **only its own collection**, not the independently valid sibling collection or stored summary. Unspecified optional row provenance is not itself evidence of a conflict; accepted legacy fixture formats remain displayable.
- **Regression coverage:** mismatched source dates, Finals result event IDs, cross-season rollover rows and independently unavailable summaries, including valid zero-valued data, are covered in the existing colocated tests.

No backend endpoints, shared API types, query keys, simulation controls, router, global i18n, or cross-PR files were touched. Exact-head CI evidence must include the stable baseline, changed test suites, and TypeScript + Vite production build.

## Follow-up — delayed query updates and plan indices

- **Stored event plan positions:** the ordered season plan is an array internally indexed from zero, but the UI now consistently presents **position 1 for the first event**. This matches the existing Activity/Snapshots conventions and does not reorder or mutate server data. A regression checks the first two positions.
- **Seasonless activity source ambiguity:** if a technical/event/snapshot activity does not carry a season and the matching persisted event and current season plan explicitly disagree about the same `event_id`, neither source is used to infer a week or build a planned/current-week/persisted-detail bridge. An explicit CS/EN alert explains why navigation is unavailable; any independent snapshot detail remains inspectable. Activities with an explicit disambiguating season keep their existing valid links. Colocated regression cases cover all three activity kinds.
- **Rollover source revalidation:** a completed player/transitions read can become invalid when its separately loaded rollover summary later reveals a different source season, and can become valid again after a read-only refresh. The filtered payload memoization now depends on the **validated** transition/player arrays, not only the raw query responses. This prevents a previously filtered empty list from remaining falsely empty when independent source evidence changes.
- **Regression:** one test deliberately resolves the rollover summary later than the unchanged player responses, changes the active player filter while the source is invalid, and then revalidates the same data through the existing read-only refresh. The original zero-valued player state remains intact.

No query keys, API calls, mutation endpoints, global components, or native Product Run history implementation were modified.

## Follow-up — failed refresh versus cached history evidence

The read-only screens use React Query, which may retain a previous successful `data` value when a later manual `refetch()` fails. Presenting that cached response next to an error as if it were the outcome of the latest read is misleading.

- **Activity, events and snapshot history lists:** after a failed source read, the list and the selected record derived from it are no longer displayed as current; a successful retry restores them. Selected URLs and backend ordering/identity contracts remain unchanged. Event payload from an independently failed detail read is likewise suppressed.
- **Dedicated snapshot detail:** a failed detail refresh removes the stale summary/source/payload while preserving independent history navigation and its error explanation. A successful retry restores the same payload, including valid zero values. Independently refreshed history indices and sibling lists are guarded too: failed index/sibling reads cannot leave cached neighbor/related-snapshot links displayed as verified.
- **Finals qualification/result and rollover:** each independently failed artifact read hides only its own cached data. A still-valid complementary resource remains available; previously observed provenance comparisons continue to apply when both resources are healthy.
- **Run diagnostics:** Run, status, Finals, rollover, lineage, source and historical artifact evidence now excludes resources whose latest request failed. Cached 'latest event' links and numeric fallback counts cannot survive a failed event read as if verified; unrelated ranking/Run evidence remains visible.
- **Regression tests:** explicitly exercise successful read → failed manual refresh → successful recovery for activity, events, ranking snapshots, direct snapshot detail, Finals qualification/result, rollover transitions and diagnostics. Tests preserve independent sibling data and show no writes.

These guards do not alter the React Query client, shared components, global retry policy, backend endpoints, or native Product Run saved-history authority. They intentionally distinguish a successful historical read from stale cached data after a failed read, not certify end-to-end browser or backend behavior.

## Follow-up — event IDs reused across seasons

Legacy persisted event IDs may recur in more than one season. A read-only event timeline must distinguish these records using the **persisted `event_sequence`**, not only the `event_id`.

- Timeline row keys and selected-row state now use event sequence; different records with a reused ID are independently selectable rather than accidentally sharing React keys or both appearing selected.
- Deep links support the scoped `selectedEventSequence` alongside `selectedEventId`, with strict positive-safe-integer parsing. Existing bookmarks containing only `selectedEventId` continue to open the first matching persisted event in API order.
- The existing direct detail endpoint is addressed by `event_id` alone, so a duplicate ID is **not** a safe dedicated-detail URL. Such links are unavailable with explicit CS/EN explanation, while the selected persisted record's own metadata and planned/current-week links continue to follow their independent season checks.
- For duplicate IDs, a fetched ID-only detail payload is displayed **only when it explicitly contains a matching valid `event_sequence`**. An absent or conflicting sequence cannot prove the payload belongs to the selected row. The detail query also includes the selected sequence in its client cache key to avoid reusing same-ID details between distinct records.
- Regression tests cover duplicate IDs across seasons, selected-row accessibility, explicit sequence links, legacy bookmarks, malformed sequence parameters, direct-link suppression, detail isolation, and independent API requests after switching rows.

This is a frontend provenance safeguard, not a change to the backend event model, URLs of the dedicated ID-only endpoint, or canonical Product Run saved-history authority.

## Verification plan and evidence

- Retained English historical regressions explicitly select English inside their test mocks; they do not weaken or delete legacy sequence/progress mismatch assertions.
- Added integrated tests with a real `LanguageProvider` for toggling during a pending read, preserving active filters and selection, differentiating missing results from stored zeros, rejecting foreign Run activity, read-only manual refresh, and snapshot historical provenance.
- Final gate: GitHub **Fast CI**, including stable critical baseline, changed/colocated Vitest suites, and TypeScript + Vite production build, all passing on the **same final SHA**. Draft-skipped workflows count neither as executed nor as passed. A full backend/simulation matrix is intentionally not run for this display-only scope.

**Important limitations / review questions:** these legacy endpoints do not supply an authenticated Product Run Saved Revision scope or an actual snapshot timestamp. A detail DTO without its own Run ID can be validated against the specific requested event/sequence but cannot independently prove the owning Run. Some test fixtures deliberately omit optional identity metadata; guards activate when the real DTO actually provides it. The existing shared UI and large-table responsiveness have not been redesigned in this PR. Product Run native history should be reviewed separately with #1639, not inferred from these legacy views.
