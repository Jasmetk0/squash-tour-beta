# Viewer current Official Ranking – canonical top-level read-only preview

## Source contract

The top-level `/viewer/rankings` page now uses two existing GET operations:

1. `GET /viewer/runs/{product_run_id}/official-context` resolves the
   saved Product Run's current Viewer Branch, represented by legacy API
   field `official_branch_id` (this is not a privileged product Branch).
2. Only after a matched context is available,
   `GET /viewer/runs/{product_run_id}/rankings/current` reads its actual
   `viewer_official_ranking.v1` publication. No client-controlled
   Branch parameter or new backend endpoint is introduced.

React Query keys separately scope context to Product Run and publication to
**both** Product Run and Viewer Branch. When the active Run changes, or a
fresh context GET reports a different saved Viewer Branch, the keyed publication
child remounts and cannot show any previous source response. Pending context
refreshes do not temporarily display older cached publication data.

The UI rejects mismatched Product Run / Viewer Branch, unknown schema, invalid
legacy publication ordinal/clock, fingerprint, counts, duplicate players,
noncontiguous ranks, invalid points and rows out of descending point order.
Malformed evidence fails closed. The source remains authoritative; the UI does
not infer or repair sporting outcomes or compute new rankings.

**Calendar boundary:** The ordinal consistency check here is for the
currently shipped `viewer_official_ranking.v1` legacy RankingWeek read model
(50 × W61, starting in 2000). It is **not** a universal cap on new W52/W61/W80
Run calendars. Future calendar-native publication models need a distinct typed
contract, not an implicit reinterpretation of old signed snapshots.

## CS/EN preview and navigation

The page uses the existing LanguageContext and a local paired CS/EN copy.
Actual IDs, fingerprint, policy ID, historical Best N, rank, player ID and points
are never translated or replaced with current defaults. It shows the first ten
actual rows in the saved server order, and distinguishes valid zero players
from unavailable or corrupt GETs. Player-ID links use the existing Viewer
career route; current profile pages must not be mistaken for reconstructed
historical profile values.

Neither this read model nor its endpoint contains resolved player names,
countries, movement, point breakdowns or counted tournament items. The table
therefore shows only rank, player ID and points; no invented placeholder
movements or implied results. Links point to the complete saved publication
history and the **exact current publication** by canonical week ordinal.
The page deliberately no longer embeds the generic top-level Viewer shell's
unrelated manually selected 61-week time-machine hint as if it were this
publication's effective clock.

Changing language does not alter query keys or trigger a new request. Explicit
retry reruns only the failed GET. Product Run selection is performed elsewhere,
and no Save, mutation or simulation operation is exposed.

## Tests and limitations

Colocated Vitest component tests use mocked GET API calls, including delayed
old-source replies, context-vs-publication identity, invalid evidence,
source switch, zero players, CS/EN stability, safe links and GET retry.
Helper tests exercise pure source and row validation. These are **not**
real browser/Chromium, HTTP, publication backend or SQLite integration tests.
Final-head frontend baseline, focused tests, TypeScript/Vite build, CodeQL and
SonarCloud are required. Never treat Draft skips or unrelated skipped jobs as
integration acceptance; complete internal-release gates remain separate.
