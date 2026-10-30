# Viewer Official Ranking history browsing (legacy v1)

## Authority and scope

This frontend-only slice uses the existing read-only GET
/viewer/runs/{product_run_id}/rankings/history, which returns
viewer_official_ranking_history.v1. It does not create a new endpoint,
ranking schema, mutation, Save, simulation command or sports computation.
The exact viewerRankingSnapshotPath(productRunId, week_ordinal) remains
the navigation destination for each original publication.

The response owns each historical season_index, week, canonical week_ordinal,
snapshot_fingerprint, policy_id, best_n and row_count (including valid zero).
Policies are never reconstructed from the present season's defaults.
The legacy RankingWeek projection is 50 seasons of 61 weeks, starting 2000/01.
These are bounds for this specific existing legacy response, NOT universal
limits on new W52/W61/W80 Run calendars or their starting-year/offset choices.
The calendar-native candidate model is not published through this endpoint.

## Source protection and errors

- The route must have matching nonblank Product Run and confirmed Viewer Branch
  identity and a non-loading/non-stale official context before the GET starts.
- The React Query key contains both Product Run and Viewer Branch. The browsing
  child is keyed by their identity, synchronously resetting local filters and
  pagination on source switch. Old-source replies never render in a new scope.
- A response must match both identities, schema, publication count, uniqueness,
  canonical legacy ordinals, public head, fingerprint format and numeric bounds.
  A missing head or malformed/duplicate publication fails closed; no row is
  guessed or silently discarded.
- Empty publication history, empty filtered results and GET/integrity failures
  are distinct. An explicit retry only repeats the GET.

## Browsing and accessibility

- LanguageContext supplies CS/EN titles, labels, statuses, errors, controls
  and accessible names. Opaque policy IDs, fingerprints and URLs remain exact.
- Available season and historical Best N choices derive only from the complete
  returned publication array. Local case-insensitive search matches policy_id
  and ordinal text, NOT players inside snapshots.
- Filter the whole returned history first, then order by canonical ordinal,
  then paginate at 25 rows. First/previous/next/last and a positive integral
  bounded page jump are available with keyboard-accessible native controls.
- Filter/order changes reset to page 1; Run/Branch changes reset all local
  state; CS/EN changes preserve filters and page without changing query identity
  or independently starting a new request.
- Result ranges are exact; zero matching results show 0–0 of 0, never 1/0.

## Verification and limitations

Vitest page tests mock the GET API. Helper tests are pure unit tests.
They are NOT browser/Chromium, real HTTP, Saved-Revision, API or SQLite
integration tests. Test cases address CS/EN, foreign/delayed source responses,
counts and duplicate evidence, zero players, filtering across >25 results,
sort, first/last/empty page, keyboard/invalid jumps, GET retry and exact links.
Do not count skipped Draft jobs as acceptance. The pre-alpha test policy still
requires successful applicable CI/build and any Ready/manual acceptance on
the exact final head before the owner receives a merge-ready handoff.
