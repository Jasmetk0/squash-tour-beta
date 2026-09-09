# Official Ranking result history V1

`official_ranking_result_versions` stores immutable resolved Edition/player result
versions scoped to a product Run and Branch. Each version includes its effective
publication week, full result provenance, payload fingerprint and predecessor
fingerprint. Table creation uses the existing schema bootstrap.

`OfficialRankingResultStore.append` validates identity, chronology, lineage and
read-only flags, then flushes without committing. Exact retries are reads;
conflicting versions cannot overwrite history. Initial versions become effective
at their explicitly supplied first-publication week. Corrections must be later
than their predecessor and preserve original completion, first publication and
validity. This increment supports award/Ranked-status corrections; correcting
original timing/validity requires a separate explicit history workflow.

New source writes at or before the latest staged ranking candidate are rejected.
A later correction must have a later effective boundary. This prevents silently
changing inputs to an already calculated historical week through this adapter.
It does not infer the actual first-publication week from a wall clock or a
calendar schedule, and candidate staging is not public publication.

`resolve` validates local per-result lineages and returns the latest effective
version for each Edition/player at the requested week, in canonical identity
order. Future corrections do not replace earlier knowledge. Expired and
non-Best-N results are retained; the existing calculator handles eligibility and
selection without losing reserve results. Missing ancestors, changed identities
and invalid payload/fingerprints fail closed. As with candidate storage, there
is no independent terminal-head manifest: tail deletion or coordinated database
rewrites are outside local hash-chain detection. A future corrupt record can
block a historical read because the complete local lineage is checked.

`stage_official_ranking_from_history` loads these persisted results before using
the application staging component from #693. The caller still supplies the
historically resolved roster, tokens and policy, explicitly confirms the
supported discipline scope, and owns a single transaction for both stores and
all other transition writes. No independent commit is introduced.

Concurrency requires one serialized writer for a branch. On a database uniqueness
or locking conflict, roll back and retry the whole transaction. This increment
does not introduce a branch lock or promise atomicity across different Sessions.
Fork scopes fail closed until shared source ancestry is implemented.

## Verification and remaining integration

File-backed SQLite tests exercise persisted source reload into the real ranking
calculator/candidate store, season rollover, later corrections, historical retries,
expiry at the original boundary, source and candidate rollback with another write,
corrupt storage rejection, identity isolation, read-only/fork guards, conflicts,
missing predecessors and backdating. Schema bootstrap tests cover the new table.

This is an internal source store and its ranking consumer, not an import of the
legacy JSON awards. It cannot prove that supplied sources are complete or truly
authoritative. Production tournament ingestion, historical publication resolution,
roster/token/policy resolution, discipline, revision/restore/export anchors, fork
ancestry and complete Week/Season Transition/API/Viewer integration remain.
No legacy player totals, sporting rules or simulation calibration are changed.
