# Viewer Tournament Draw V1

The Viewer exposes a read-only sporting projection of the selected Viewer Branch's
effective canonical Tournament Draw.

## Authority

The endpoint resolves the Product Run's selected Viewer Branch server-side and reads
the current effective Tournament Draw authority. If append-only Draw revisions exist,
the Viewer receives the revised bracket rather than the immutable initial bracket.

## Public projection

`GET /viewer/runs/{product_run_id}/tournaments/{event_id}/draw` exposes:

- Main bracket size and ordered first-round slots;
- Qualification sections and their ordered first-round slots;
- player identities;
- qualifier / Lucky Loser placeholders;
- BYEs;
- seed numbers;
- public entry status for Wild Card / Lucky Loser occupants;
- count of canonical Draw revisions already applied.

It deliberately excludes:

- Draw and Draw Input fingerprints;
- command IDs;
- draw seeds and algorithm version;
- idealized-slot internals;
- seed-protection implementation flags;
- internal node/feed graph identities;
- revision provenance and Admin mutation controls.

The run-scoped Viewer Tournament Detail page renders this projection next to the
canonical Entry Field. Legacy event/result context remains a separate compatibility
surface and is not reclassified as canonical by this slice.
