# Viewer Official Ranking V1

Viewer now has a canonical read-only Official Ranking projection for the selected
Viewer Branch of a Product Run.

## Authority

The read model resolves the Product Run's selected Viewer Branch, then reads the
Branch-owned `AuthoritativeWorldState`. Only the `PublishedOfficialRanking` at
that world's exact `current_ordinal` is eligible for Viewer output.

The stored publication is accepted only when:

- Run and Branch scope match the selected Viewer Branch;
- publication week equals the public world head;
- publication fingerprint equals the world's ranking fingerprint;
- the stored Official Ranking payload validates against that trusted fingerprint.

A later publication already present in persistence is ignored until the authoritative
world head advances to it. This is the no-future-leak boundary.

## Public projection

`GET /viewer/runs/{product_run_id}/rankings/current` exposes only:

- Product Run and Viewer Branch identity;
- current season/week and immutable publication fingerprint;
- effective policy id / Best N;
- ordered public rows: rank, player id and points.

It does not expose ranking input manifests, disciplinary evidence internals, Working
Draft state, unpublished candidates or future publications.

The top-level MSA Rankings Viewer page uses this endpoint for its current Top 10
preview. Legacy ranking snapshot pages remain available as compatibility/history
surfaces; migrating their complete historical timeline to the canonical Branch-owned
publication chain is a separate follow-up.


## Historical publication timeline

The run-scoped Viewer ranking routes now use the same canonical Branch-owned publication chain. `GET /viewer/runs/{product_run_id}/rankings/history` lists only validated publications at or before the selected Viewer Branch public world head, newest first. `GET /viewer/runs/{product_run_id}/rankings/history/{week_ordinal}` reads one exact historical publication and rejects any requested ordinal beyond the public head. The existing Viewer URLs `/viewer/runs/:runId/rankings` and `/viewer/runs/:runId/rankings/:snapshotSequence` are retained for navigation compatibility, but the trailing identity now resolves canonical ranking week ordinal rather than a legacy SimulationRun snapshot sequence.
