# Official Ranking transition staging V1

The application function `stage_official_ranking_transition` connects the pure
calculator with the candidate store. It requires the stored completed-week
candidate and stages exactly the following week's candidate. Explicit bootstrap
remains separate. Week 61 rollover requires an explicit target-season policy;
this component does not activate the season or advance its clock.

The caller supplies the complete historically resolved roster (including stored
tie-break tokens) and result set, not only the previous snapshot's Best N rows.
It must resolve Ranked status, retirement, corrections and original first
publication before calling. Future completed results and future publication
inputs are rejected. These checks cannot prove source completeness or provenance.
Discipline must be explicitly `none`; this is an internal supported-scope claim,
not a public bypass for sanctions. No API is exposed by this increment.

The previous candidate is selected by the completed week, so replay of an older
successful request remains verifiable after later weeks have been staged.
Recalculation must match stored content exactly; changed inputs/policy conflict.
The infrastructure store retains scope, read-only, lineage and append guards.
The caller owns the transaction: no independent commit is introduced, and a later
component failure rolls back the newly computed candidate with other writes.

This is an integrated calculation/storage component, not public Official Ranking
publication. Production source resolution, command/revision anchoring, fork
ancestry, discipline and wiring into the full Week/Season Transition remain.
Legacy simulation and Viewer paths retain their existing behavior.

Real file-backed SQLite tests cover calculated Q+main points, explicit rollover
policy, commit/reload, historical retry/conflict, missing predecessor, future
input rejection and rollback after a subsequent component failure. These are
component integration tests, not full simulation/API acceptance tests.
