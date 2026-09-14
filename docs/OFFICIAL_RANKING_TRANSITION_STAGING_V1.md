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
The original increment accepted only `none`. Subsequent zero support accepts
resolved zeros and resolves `stored_zeros` through the command runner; see
`RANKING_DISCIPLINARY_ZEROS.md` and `ADMIN_RANKING_PREPARATION_API.md`. Never use
`none` to bypass stored decisions. This staging function itself exposes no API.

The previous candidate is selected by the completed week, so replay of an older
successful request remains verifiable after later weeks have been staged.
Recalculation must match stored content exactly; changed inputs/policy conflict.
The infrastructure store retains scope, read-only, lineage and append guards.
The caller owns the transaction: no independent commit is introduced, and a later
component failure rolls back the newly computed candidate with other writes.

This staging function remains a calculation/storage component, not publication.
The transaction-owning adapter in
`infrastructure/db/authoritative_week_transition.py` is now the sole supported
authoritative publication path for the narrow Week 1→2 slice. Under one SQLite
`BEGIN IMMEDIATE` it revalidates the writable Run/Branch, exact Saved Revision,
authority and owned source fingerprints, stages with this same kernel, publishes
the immutable Official Ranking, advances the scoped clock, and appends a World
Event plus idempotency receipt. Preview executes that production path and always
rolls it back; confirm repeats all reads under the writer lock. Exact command
retry verifies and returns the stored result, while a changed canonical request
conflicts. Saved Revision ranking state V4 captures and restores publications,
clock, events and receipts together with candidates and source evidence.
Confirm requires both the preview's canonical request fingerprint and its
calculated Official Ranking fingerprint. A changed audit reason therefore cannot
be confirmed merely because it happens to calculate the same table. V1 accepts
only an in-season `Week N → Week N+1` boundary; `Week 61 → next-season Week 1`
fails closed because it belongs to the still-unimplemented Season Transition.
Historical exact retry validates its immutable publication and canonical World
Event even after the world head has advanced, while also validating that the
current head points to a real, fingerprint-valid publication.

This does **not** make the legacy week executor authoritative. The frozen
`RankingTransitionAuthority` is still the explicit boundary input for lifecycle
facts that the owned world cannot yet derive. Player development, retirement,
injury, prospect entry, AI, slots, public Viewer consumption, Season Transition,
fork identity remapping and broader tournament shapes remain unsupported; no
no-op sporting default is inferred for them. Production tournament files remain
a legacy producer only after their result/award evidence is explicitly adopted.
See `../CURRENT_STATE.md`.
Legacy simulation and Viewer paths retain their existing behavior.

Real file-backed SQLite tests cover calculated Q+main points, explicit rollover
policy, commit/reload, historical retry/conflict, missing predecessor, future
input rejection and rollback after a subsequent component failure. These are
component integration tests, not full simulation/API acceptance tests.
