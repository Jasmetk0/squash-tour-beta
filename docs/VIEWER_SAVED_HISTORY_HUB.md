# Viewer saved publication history hub — CS/EN and source safety

## Scope

This bounded slice improves top-level `/viewer/history` without changing
Saved Revision read models, routes, shared i18n, mutations or domain rules.
The hub displays a single coherent, read-only summary from the existing
`getViewerTournamentHistory`, `listViewerOfficialRankingHistory` and
`getViewerFinalsRace` GETs. Before issuing those requests it resolves the
current saved Product Run / Viewer Branch via the existing
`useViewerOfficialRunContext`. The API's `official_branch_id` is legacy
technical terminology, not a privileged branch in the product.

### Source fences

All three history query keys contain the **selected Product Run ID and
confirmed Viewer Branch ID**. A keyed child is unmounted during a pending
context refresh or on any source switch; an older GET result cannot be
displayed under a new source. The hub rejects missing or foreign
Run/Branch identities, incorrect schema names, duplicate tournament IDs,
mismatched tournament/publication counts, invalid ranking publication
ordinals/fingerprints, duplicate ranking publication ordinals and
duplicate Finals Race target seasons, wrong latest Race marker or wrong
publication source. A failure in **any** source hides the entire composite
summary rather than mixing two branches or showing a misleading partial
count. Only explicit GET retries are exposed.

Legacy `viewer_official_ranking_history.v1` and
`viewer_finals_race_history.v1` both use legacy W61 / 50-season bounds.
Those fields are validated only for these existing versioned projections.
The current Master permits W52, W61 and W80 Run-specific calendars, whose
future canonical read models must get their own versioned contracts.

### Published information, not inferred history

The summary contains scheduled tournament count, **actually published**
tournament result count, published Official Ranking count and published
Finals Race season count. Latest published tournament is selected among
actual `result_published` entries only (not latest scheduled event).
Latest Official Ranking is selected by maximum published ordinal, not
response ordering. The latest Race season uses its validated
`latest_target_season_index` and links to the existing run-scoped Race
browser. Links use the established route builders for tournament detail
and ranking snapshot and the already-existing full archive pages.

The page does not expose unpublished rankings, infer results from future
calendar events or merge histories across Branches. If none of the three
sources has a publication, it reports an explicit empty state while
keeping navigation.

### Presentation and acceptance

CS/EN labels, statuses, navigation names and error copy are local to this
page using LanguageContext. IDs, historic season/ordinal, event names and
policy IDs stay authoritative source values. Errors and conflicting
histories are distinct; backend internal error strings are not echoed in
this public read-only summary. Switching language preserves the current
source and cached read queries.

Colocated pure-validation Vitest tests and mocked GET React tests cover
wrong/corrupt sources, empty cases, latest links, failed endpoints,
Run/Branch switching, delayed old replies, and CS/EN. They are **not**
a real HTTP/SQLite/Chromium acceptance result. Require matching final
commit Fast CI, changed frontend tests, TypeScript/Vite build, CodeQL
and SonarCloud, as well as any relevant Ready/manual gates; skipped
unrelated jobs are not passes. Only the repository owner merges.
