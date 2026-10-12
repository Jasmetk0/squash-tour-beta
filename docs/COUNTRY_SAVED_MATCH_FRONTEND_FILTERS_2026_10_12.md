# Country Records — Saved match filters and frontend integration (2026-10-12)

## Functional slice
Run → World → Country → **Records** now combines the independently published-tournament Country Records read model (#1410) with the exact-Saved-match backend (#1411).

The existing published titles, runner-up and hosted-result figures remain unchanged. A new independently guarded **Country match records** section displays on-court national wins/losses, separate national walkover wins/losses, hosted played matches, verified participants, exact scorelines, a safe present-time match-detail link and 25-row paging.

### Server-side filters (before paging)
- `season_index`: optional 0–49, corresponds to Run seasons 2000/01–2049/50.
- `result_kind`: `all | played | walkover`.
- `outcome`: `all | win | loss`, from **this country's player's perspective**. A national derby appears in both the win and loss filters.
- `offset` / `limit`: bounded. Each request returns the verified global Saved Revision national and hosting counters, `available_seasons` from national participant matches, `country_match_count` unfiltered, and `filtered_match_count` after server filters. `has_more` and rows are based on the filtered set only.

Never filter only a returned page: that silently misses records beyond 25. The backend validates every published tournament, source scope, score, participant and Saved nationality before filtering. BYE and non-public events are excluded; saved walkovers are not on-court played wins. In a same-nationality match, count one country's win and one loss. Host identity is independent of player nationality.

### Historical safety
The selected Run, Branch, country and exact Saved Revision are all inputs to the query and cache key. A selected historical Saved Revision reads its original Branch owner, including reachable shared pre-fork ancestry. No current Saved HEAD, live Run packages, Viewer content or future simulation checkpoint is substituted. Present-time player/match links are disabled on historical selection. Changing the selected Run/Branch/Revision remounts filter state; changing a filter resets paging. Season options persist while the filtered fetch is in flight.

No authoritative Saved Revision = no match request. Invalid response scope, filters, national identity or unreachable revision = explicit error, not invented zero. An **empty valid Saved Revision** still truthfully shows zero matches.

### Verification
- Backend deterministic filter vs paginated slice, global counters, missing seasons, won/lost/walkover and invalid parameters.
- HTTP/SQLite 422 query rejection, immutable Saved Revision identity, persistence/restart.
- Frontend component tests for controls/query arguments and pagination, historical link safety, missing HEAD and errors.
- Backend and frontend CI on exact PR head. This is **not** a claim of full 50-season test coverage or an actual browser end-to-end path specifically opening the Records tab.

Future deeper features: stage/rally records, per-player aggregates, event-season drill-down, and a 50-season performance test of the immutable read model.
