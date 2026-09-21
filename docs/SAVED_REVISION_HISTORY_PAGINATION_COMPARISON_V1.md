# Saved Revision history pagination and comparison v1

Saved Revision history remains a read-only projection of the complete validated lineage.
This slice makes that projection usable for long-running Runs without changing history
semantics or introducing a mutation path.

## Stable history pagination

The history endpoint accepts:

- `limit` (1..200, default 50);
- `before_sequence` as an exclusive cursor.

Without a cursor, the server returns the newest window of reachable revisions, ordered
oldest-to-newest inside that page. If older reachable history exists, the response
returns `has_more_older=true` and `next_before_sequence` equal to the first sequence
in the current page.

Using an exclusive sequence cursor makes older-page traversal stable when a new Saved
Revision is appended to the Branch head between requests. Pages never need to reinterpret
their cursor against a new total offset.

Every page is still derived from the fully validated reachable lineage, including shared
pre-fork ancestry. Pagination does not bypass content-hash, parent, cycle or shared-origin
validation.

## Read-only comparison

`GET .../saved-revisions/compare?from_revision_id=...&to_revision_id=...` compares two
Saved Revisions only if both are reachable from the selected Branch head.

The comparison returns:

- the two validated revision identities;
- changed top-level Run metadata fields;
- changed top-level Branch metadata fields;
- every Saved Revision `content` component classified as
  `added`, `removed`, `changed` or `unchanged`;
- deterministic SHA-256 fingerprints for the before/after component JSON where present.

The comparison deliberately does not interpret sporting meaning or invent domain-specific
diff policy. It is a generic persistence/history inspection tool.

## UI

Saved Revision History loads the newest page first and exposes **Load older revisions**
when more history exists. Loaded pages are combined into one chronological list.

After opening a revision, Admin may choose another loaded revision as the comparison
source. Comparison is read-only and does not create a Branch, checkpoint, draft, restore
or audit event.

This is the pagination/general-comparison follow-up described in ROADMAP section 11.
