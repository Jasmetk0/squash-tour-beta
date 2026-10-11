# Viewer World Tour Finals Result v1

## Purpose

The Viewer Finals Result route must publish the sporting outcome from the same canonical Saved-Revision Tournament Result authority used by ordinary Tournament Detail. It must not read or reconstruct the legacy SimulationRun Finals result payload.

## Authority chain

1. Resolve the selected Viewer Branch through the existing Viewer Product Run context.
2. Read canonical World Tour Finals Race history from the selected Branch Saved Revision.
3. Resolve the latest published Finals event identity from that Saved-Revision publication.
4. Read `viewer_tournament_result.v1` for that exact Finals event.
5. Render only public sporting result data.

If the Finals event identity is not published yet, no Tournament Result query is made.

If the Finals event exists but its canonical Tournament Result is not present in the selected Saved Revision, Viewer reports the result as not published. Live Working Draft completion therefore remains invisible until the normal Save boundary publishes it.

## Public fields

The Finals Result page may expose:

- Viewer Branch identity already exposed by other Viewer read models;
- Finals event ID;
- completed season index and week;
- champion and finalist;
- Qualification winner IDs;
- player result rows;
- match result rows and scorelines;
- links to public player, planned-event and tournament-detail routes.

## Hidden evidence

The page does not expose:

- Tournament Result authority fingerprints;
- point-award or prize-money authority payloads;
- command IDs or retry identity;
- Saved Revision internals;
- source provenance internals;
- legacy Finals technical JSON.

## Failure behavior

- missing Finals publication: explicit empty state;
- missing Finals event identity: explicit empty state and no result query;
- canonical Tournament Result 404: result is not published yet;
- other canonical read failure: surfaced as a read-only Viewer error;
- no fallback to legacy SimulationRun Finals result data.

## Non-goals

This migration does not change Finals qualification, seeding, replacement, tournament gameplay, result calculation, ranking points or prize-money policy. It only changes the Viewer publication source.
