# Viewer World Tour Finals Result — scoped publication boundary

## Scope

This frontend-only, read-only repair covers public Finals Summary,
Qualification and Result routes and their mocked contract tests. It neither recalculates
race standings nor changes API contracts, saved history, Admin or simulation.

## Display authority

- All three Finals pages validate that the canonical Finals Race history belongs
  to the requested Product Run, a non-empty Viewer Branch and nested publications
  owned by that same context. Foreign participant rows are never displayed.
- A Finals event ID is not alone public authority. The route only requests
  Tournament Result when its selected Finals publication explicitly says
  `selection_published: true` and supplies that event ID.
- The returned Tournament Result must match the current Product Run, selected
  Viewer Branch and exact published Finals event. Missing structural result
  arrays or foreign identity is an error, not a match/participant table.
- Query identities include Product Run, Viewer Branch and event ID, avoiding
  reuse of a prior Branch's cached Finals result under a changed selection.
- An unpublished event does not expose its ID in Source links, Finals Summary
  or Qualification metadata. A 404 still
  means the completed result is not published yet; network errors remain errors.

## Evidence and limits

Focused Vitest tests use mocked public API responses to cover identity
mismatches, unpublished event ID across three pages and malformed result body, alongside
existing published/unpublished/404 behavior. They do not prove end-to-end
backend/SQLite publication or browser operation. No changes are made to
Viewer selection, Race computation, authentication or backend integrity.
