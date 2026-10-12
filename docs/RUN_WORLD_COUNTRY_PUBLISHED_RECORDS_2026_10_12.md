# Country → Records from exact Saved published evidence (2026-10-12)

## Scope and sources
Admin Run World → Country → Records projects **one exact, reachable Saved Revision** of the selected Run/Branch. The backend resolves the revision through the existing Branch history service, checks reachability, and loads Run Calendar, ranking preparation, initial player identities and Run prospect identities using the Saved Revision's **original Branch ID** (shared ancestors supported). A present view passes its immutable Saved HEAD; a historical view passes the selected revision. The World data year is not a simulation year and is never used to infer sports records.

The source of result truth is `resolve_viewer_tournament_history`: `ranking.tournament_sources[].canonical_result` must join to a saved Run-owned Calendar event with matching identity. Merely planned or calendar-`completed` editions are not published tournament results. Duplicate event identities and unmatched canonical results fail closed.

For each published result, both champion and finalist IDs must have fully resolved nationality and display name in **that same Saved Revision** via `resolve_saved_home_player_identities`, batched by 25. Missing identities fail closed (409), instead of dropping results or attributing them to the host country. Prospect source component is from Saved Revision only.

## Display semantics
* `country_titles`: number of canonical published finals won by a player with this country code.
* `country_finalists`: number of published tournament runner-up finishes featuring a player from this country.
* `hosted_published_results`: number of published tournament results where the actual edition `host_country` equals this country code, regardless of winner's nationality.
* `player_results`: published championship finals with this country's champion **or** runner-up.
* `hosted_results`: published championship finals held in this country (may have foreign champion and finalist).
* Totals are **only for published canonical evidence in the selected Saved Revision**, not extrapolated all-time records.

An empty Run with no calendar and no canonical sporting source is a verified empty state. Published sporting source with no matching Calendar, invalid participant identity, foreign Run/Branch, inaccessible Saved Revision or invalid component is unavailable—not an empty record. No computation writes to the Run, no Viewer or mutable planning fallback.

Historical Saved Revision player links are deliberately disabled; only current Saved HEAD may link to current player profiles. Historical **simulation checkpoints** still cannot safely map to Saved Revision and remain blocked. This slice does not claim match-by-match country all-time records, head-to-head statistics, 50-season acceptance, or a separate Viewer Country Records projection.

## Tests
- Pure model: home vs foreign winners, titles and finals vs host records, shared ancestry origin, unplayed edition exclusion, missing national identity and empty source.
- HTTP/SQLite: empty Saved Revision, exact revision identity, foreign revision/Branch fail-closed, invalid country and restart.
- Frontend: source-verified totals and result tables, exact historical revision and no present profile links, no Saved HEAD behavior.
