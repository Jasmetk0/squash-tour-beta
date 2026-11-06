# Verified Saved Tour calendar export (CS/EN) — 2026-11-01

## User-visible feature

The existing Admin Saved Tour Calendar can export its exact immutable, scoped
season calendar for spreadsheet inspection and evidence handoff:

- **Whole Saved season** (default): all already verified Editions of the
  selected Season in canonical saved order, independent of current UI filters.
- **Current filters + focused week**: only the records shown by the existing
  saved-calendar filter rules, including Tour, category, country, name/ID,
  publication flag, published champion/finalist ID and optional exact week.
  Merely choosing the *compact weeks* display does not discard other weeks.
- **JSON**: a versioned `saved_tour_calendar_export.v1` envelope with
  actual Run ID, selected Branch, original source Branch of a reachable Saved
  Revision, exact saved revision ID, season identity, complete saved Edition
  count, selection filters, exported row count, publication count and edition
  fields. An empty Saved season can be exported as JSON with its source proof.
- **CSV**: RFC4180-quoted columns suitable for spreadsheets, with Run/Branch/
  original source Branch/Saved Revision/Season identity repeated on each data
  row. CSV is disabled for zero rows because header-only CSV cannot retain
  the immutable source identity. Text beginning with spreadsheet formula
  prefixes, including leading whitespace, is prefixed with an apostrophe.
  A UTF-8 BOM supports Czech Excel import. Generated filenames are sanitized;
  the source identity **inside** each export is not changed.

The buttons only appear when the already-existing current query has a
validated `run_saved_tour_calendar.v1` response for the correct Run/Branch/
Saved Revision/Season and is not being refetched. The download handler checks
that same immutable source *again* on the explicit user click.

## Authority / safety

The UI makes **no new backend request** and neither modifies a Working Draft
nor writes a Saved revision. The established
`validSavedTourCalendar` production validation and
`filterSavedTourEvents` projection are used directly. No invented events,
cross-Branch projections, future HEAD fallbacks, simulated match results,
result-publication inference, missing champion guesses or new sporting rules.

The JSON export counts only `result_published: true` events as published
finals, and does not claim that an unpublished Edition was never played.
It includes only the limited existing Saved Tour Calendar fields; it is
*not* the entire match/rally archive or a regulatory audit certificate.

## Scope and tests

Changes stay inside the Saved Tour Calendar Admin screen, one new pure export
serializer, one new lightweight CS/EN control component and focused tests.
The previous Saved Tour calendar filtering/deep link/validation tests remain
mandatory. No changes to backend, Viewer, source Packages, native MatchEngine,
Windows preview, ranking or the canonical Master.

Tests cover: exact source and season identity, filters/focused week vs whole
season, publication semantics, foreign Run/Branch/head rejection, tampered
counts/duplicate editions, JSON for empty history, disabled empty CSV, CSV
escaping and spreadsheet-injection strings, filename path sanitization,
CS/EN, user gesture-only downloads and object-URL revocation.

This is convenience for **already Saved** calendar records, not evidence of a
complete 80-Edition FAX season or 50-season full simulation. The current
`docs/PRE_ALPHA_TEST_POLICY.md` release gate and additional real
HTTP/SQLite/Chromium tests remain separate. No automatic merge.
