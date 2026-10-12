# Country Match Records — canonical played Saved results (2026-10-12)

## Independent backend functional slice
Read-only endpoint:

`GET /admin/runs/{run_id}/branches/{branch_id}/country-match-records/{country_code}?revision_id={exact_reachable_revision}&offset=0&limit=25`

This standalone implementation is independent of Country Records frontend PR #1410. After that PR is merged, a separate frontend slice can connect its Country Records tab to this validated match source without merging concurrent files.

## Authority
The existing Saved Revision history service validates exact Run/Branch reachability, including shared ancestral revisions. All package, ranking and player-identity components are loaded only from the selected immutable revision under its original Branch ownership. There is **no** current Saved HEAD substitution, live match state, Viewer selection, or unplayed Calendar-only fallback.

The stored canonical Tournament Result must match a saved Calendar event's Run/Branch/Event/Season/Week. Each match has a canonical winner, loser and scoreline. A BYE/no-opponent entry is not a played match; walkover scorelines are classified separately using the existing saved player-match detector. Same-nationality matches correctly count one national win and one national loss; host-country match totals are independent of player nationality. All winning/losing player IDs must resolve to verified Saved Revision national identities; missing identities fail with 409 rather than being dropped or silently assigned a nationality.

Return counts for played/walkover games of the selected country plus independent hosted counts. The rows show a bounded 1–50 page of verified national match appearances, ordered from latest evidence first, including season, week, event, round, nationalities and original scoreline. The response distinguishes empty Saved Calendar from published matches; it is not a claim about whole-world historical matches outside this revision.

## Verification and gaps
- Pure deterministic critical tests for played/walkover/BYE, separate host and nationality, pagination, shared historical origin, duplicated/foreign/missing identities, no source.
- Real FastAPI/SQLite empty revision and foreign/unreachable revision checks, restart read consistency.
- Scoped Fast CI backend tests required for merge readiness.
- Not yet wired into the Country Records browser. No unverified 50-season or browser result claims.
