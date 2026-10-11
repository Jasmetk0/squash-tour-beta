# Viewer Canonical People v1

## Purpose

\`viewer_players.v1\` and \`viewer_countries.v1\` publish current read-only player/country state from the selected Viewer Branch Saved Revision.

They do not read the legacy SimulationRun player registry.

## Authority

The projection joins only Saved Revision-owned components:

- Initial World for initial player identity/name/country;
- player lifecycle history for the current public roster, age, active/retired status and Tour-entry boundary;
- player sporting history for current OVR, potential OVR, form, sharpness and fatigue;
- Run prospect source snapshot for identity/name/country of later generated players.

The latest lifecycle and sporting states must represent the same public week.

## Fail-closed rules

The projection is unavailable when:

- Initial World, lifecycle or sporting components are missing;
- Saved component scope differs from the Viewer Product Run/Branch;
- latest lifecycle and sporting weeks differ;
- an active lifecycle player has no sporting record;
- a current player cannot be resolved to either Initial World or saved prospect identity;
- Initial World and prospect source duplicate the same player identity.

## Public fields

Players expose:

- canonical player ID;
- display name;
- country code;
- current age and active/retired status;
- Tour-entry season/week when applicable;
- current OVR and potential OVR;
- current form, match sharpness and long-term fatigue;
- coarse identity source (\`initial_world\` or \`run_prospect\`).

Internal fingerprints, RNG seeds, tie-break tokens/provenance, generation fingerprints and hidden traits are not published.

Countries aggregate the canonical player projection by country code and expose player counts, active/retired counts, average current OVR and top-player identity.

## Endpoints

- \`GET /viewer/runs/{product_run_id}/players\`
- \`GET /viewer/runs/{product_run_id}/countries\`

Working Draft or live legacy player mutations are invisible until captured by the selected Viewer Branch Saved Revision.
