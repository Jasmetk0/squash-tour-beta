# Browser-local pinned views of exact Saved Editions — 2026-11-01

## User value

An Admin studying dozens of Editions across 50 potential seasons needs to
return to a specific authenticated Saved Edition, tab and published-result
search without manually reconstructing the original Run/Branch/revision
navigation. The existing Saved Edition detail page now provides a small CS/EN
pinned-view panel **only after** its canonical
`run_saved_tour_edition.v1` response passes the established exact-source
validation and is not refetching.

A user may name and explicitly pin the current tab, exact Saved Revision,
Run, Branch, Season, Edition and (on the Results tab only) published-match
search. Re-pinning the same exact view renames the existing entry instead of
duplicating it. Pinned views within the current selected Run and Branch may
reference older Saved Revisions; clicking one rebuilds the original internal
Admin route from individually validated fields. It makes the *normal existing
backend Saved Edition request*, which separately rejects a foreign, deleted
or unreachable revision. It never substitutes today's HEAD, silently
resolves stale links or pretends unpublished Results were played.

## Durability / authority boundary

- **Local browser only:** `localStorage` scoped key
  `squash-saved-edition-shortcuts.v1`; this is not canonical Saved Views,
  Cloud sync, a Saved Revision mutation, an export/import bundle, a persisted
  user preference in the backend, or an authoritative world event.
- 24 explicit shortcuts maximum, no automatic eviction. A full store refuses
  new entries; an existing identical view can be renamed in place.
- A corrupted JSON blob, duplicate ID, unknown schema/tab, out-of-range
  season, empty/oversized identity and oversized match search is ignored,
  never interpreted as a URL. Serialized writes validate again and fail
  atomically; blocked browser storage results in an explicit error.
- The internal route is always built from encoded
  `/admin/runs/{run}/tour/calendar/{edition}` and an allowlisted query
  with exact Branch/Revision/Season/Tab/optional match search. The storage
  never contains an arbitrary URL, JS URI, relative redirect or protocol.
- The panel excludes shortcuts of other Run/Branch identities and supports
  cross-tab storage changes. Deletion applies only to a matching saved
  shortcut from the currently selected Run and Branch.
- `localStorage` is best-effort on this single desktop browser. Backups,
  browser-profile deletion or reinstall may lose shortcuts. No migration or
  cloud-import behavior is claimed.
- No MatchEngine, ranking, official year, tournament eligibility, Saved
  Revision or Player identity changes. Original Saved Edition read validation
  remains the exclusive source of result authority.

## Tests and review

Pure tests cover source identity and URL encoding, exact old-revision
deep links, corruption/duplicates, capacity, view deduplication and foreign
scope isolation. React tests cover explicit user clicks, re-mount persistence,
CS/EN, rename/remove, cross-tab updates, quota errors and inability to
silently discard an old bookmark. Existing Saved Tour Edition page tests
and frontend production build remain mandatory on this Draft branch.

This UX slice deliberately avoids open PR #1721's Saved Calendar page and
#1720's Tour operator queue, and has no overlap with Codex/Jules backend
and scientific research PRs. The original Master requirement for complete
durable Saved Views and notification watchlists remains open; do not count
browser shortcuts as closing it. Owner handles all merges.
