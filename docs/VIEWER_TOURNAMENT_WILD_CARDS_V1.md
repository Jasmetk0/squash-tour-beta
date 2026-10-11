# Viewer Tournament Wild Cards V1

Viewer Wild Card output is derived only from persisted definitive WC/RWC assignment
authority on the selected Viewer Branch.

## Public boundary

`GET /viewer/runs/{product_run_id}/tournaments/{event_id}/wild-cards` exposes:

- Wild Card slot number;
- assigned player identity;
- whether the definitive assignment came from the original WC nomination or Reserve WC;
- Reserve WC ordinal when applicable.

It deliberately excludes:

- WC review command IDs;
- Entry Field / WC authority fingerprints;
- decision week and global Simulation Slot ordinal;
- Admin operator/audit reason;
- provenance strings;
- first Tour-entry trigger fingerprints and arbitration details;
- preliminary nominations, unavailable lists and unfilled WC slots.

An event with no definitive assignments returns an empty public collection rather than
falling back to legacy wildcard actions or Admin preview state.
