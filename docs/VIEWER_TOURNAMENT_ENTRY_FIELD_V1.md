# Viewer Tournament Entry Field V1

The Viewer now has a read-only projection of the selected Viewer Branch's canonical
Tournament Entry Field for one event.

## Authority

The endpoint resolves the Product Run's selected Viewer Branch through the existing
Viewer Run context and then reads the Branch-owned canonical Tournament Entry Field.
It never accepts a Branch id from the Viewer caller.

## Public projection

`GET /viewer/runs/{product_run_id}/tournaments/{event_id}/entry-field` exposes:

- current field version and mode;
- Main capacity, active Main entrant count and effective BYE count;
- direct Main entrants;
- Qualification entrants;
- below-cut alternates;
- withdrawn players.

It deliberately excludes:

- field and predecessor fingerprints;
- frozen application payloads and request identities;
- internal bracket diagnostics;
- Admin lock / mutation metadata;
- Tournament Ranking Snapshot authority internals.

The run-scoped Viewer Tournament Detail page consumes this projection alongside its
existing compatibility event/result context. The broader tournament page still has
legacy event/result dependencies; this slice only makes Entry Field state Branch-owned
and Viewer-safe.
