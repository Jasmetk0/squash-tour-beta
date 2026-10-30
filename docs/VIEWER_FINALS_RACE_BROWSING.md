# Viewer Race to Finals — saved publication browser (CS/EN)

## Canonical read-only boundary

Both existing entrypoints — top-level `/viewer/rankings/race` and
run-scoped `/viewer/runs/:runId/race` — use the existing
`GET /viewer/runs/{product_run_id}/finals/race` read model
(`viewer_finals_race_history.v1`). The top-level view first resolves
`getViewerOfficialRunContext(product_run_id)`; the run-scoped view
uses its already resolved Viewer Product Run route context.

`official_branch_id` is the **legacy technical field** selecting the saved
Viewer Branch, not a privileged Main/Official sporting branch. A race GET
runs only for a valid, matching Run/Viewer Branch context. Its React Query key
includes both IDs, and a keyed child resets all local selections when either
source changes. A pending context refresh conceals old publication data.
All failed reads can only be retried with GET; no Save/simulation/mutations.

## Validity constraints

The frontend checks the exact history/publication V1 schema, parent and child
Run/Branch identity, unique target seasons, correct latest-season marker,
target/cutoff clock, Best N, ordered unique player IDs/ranks, integer
nonnegative scores, each row's counted-result count, exact Race-points sum,
bounded counted results, and distinct published Finals seeds.

The existing V1 Saved Revision read-model from
`src/beta_engine/application/viewer_finals_race_read_model.py` is the
authority. Invalid or foreign payloads fail closed; the frontend never
repairs, sorts or recomputes any player's published rank or result.
The frontend **may reorder the seasonal publication menu** newest-first
without changing source sporting data: it derives the latest by the
authoritative target season rather than trusting the API list position.

The legacy V1 race model has 50 seasons × W61 with target-season cutoff.
Those checks are specific to that endpoint; they do not limit the later
calendar-native W52/W61/W80 Run model. Future schema needs its own versioned
adapter, not a reinterpretation of this source.

## Browsing and UI

The user can choose any saved target season from a selector or season list.
All statuses/labels/ARIA text are in CS/EN via LanguageContext, but
`player_id`, `event_id`, ranking values, points and qualification source
come only from the chosen saved publication. A season switch resets search
and pagination. Case-insensitive player-ID search filters the **complete
chosen season**, preserving its published order and rank numbers. Results
are locally paginated in 50-player pages; first/previous/next/last and a
validated exact page jump support keyboard use. Language switching keeps
the chosen season, query and page.

Each player row shows counted tournaments and each authoritative counted
event with its saved target-season/week and awarded Race points. The
distinct statuses before selection, excluded, Race-qualified and direct
entry are preserved. The current Finals participation is sourced from
the backend effective participant state (which may include accepted
replacements); it is not inferred from an initial bracket.

Valid zero publications, a zero-player publication, no local search
matches, failed GET and invalid/falsified payload have distinct states.
Nothing exposes private selection or Race fingerprints, tie-break
tokens, source audit or unpublished Working Draft state.

## Verification boundaries

Pure validation Vitest and mocked-GET React tests cover identity, duplicate
seasons, counted-result arithmetic, pending and selected statuses,
older seasons, pagination, language switch, out-of-order API history,
late old-Run responses and Branch changes. They are **not**
real Chromium/HTTP/SQLite integration. The scoped final-head PR CI gates
and later release/checkpoint acceptance remain mandatory.
