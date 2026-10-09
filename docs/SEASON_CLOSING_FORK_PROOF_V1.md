# Canonical Season Closing Ranking — pre-fork proof V1

**Status: pure proof plus ranking replay integration; post-season Saved Revision fork remains blocked.**

A Season Transition is distinct from an ordinary Week Transition. Its
archived Season Closing Ranking belongs to the **completed Week 61**, must use
the outgoing season's policy and published Week-61 predecessor, and may include
Week-61 results that only become ranking-eligible at the next-season boundary.
The result cannot be copied to a different Branch by changing its `branch_id`:
the predecessor ranking, disciplinary-zero provenance and immutable input/archive
hash must all be re-established under the target Branch identity.

`rebind_verified_season_closing_ranking` in
`src/beta_engine/infrastructure/db/season_closing_fork_proof.py` is a pure,
deterministic, **fail-closed preliminary adapter**. It requires:

1. A schema-valid archived source Closing Ranking plus canonical published
   source Week-61 Official Ranking predecessor.
2. The independently reconstructed **target Week-61 predecessor**, with
   identical players, outgoing policy and sporting ranking semantics.
3. Fully resolved original/target roster, result and disciplinary-zero input
   collections for the same Season Closing boundary.
4. **Exact 1:1 provenance maps** of distinct source result and zero
   fingerprints to separately proven target-owned fingerprints; one source
   Tournament fingerprint may be shared by multiple player result rows.
5. A source Closing Ranking recomputed from the supplied frozen inputs and
   **equal to the stored source archive**, including its immutable input hash.
6. A freshly calculated, target-owned archive that preserves player ranks,
   totals and counted sporting results, while changing the branch-bound
   predecessor/input/archive fingerprints.

The caller remains responsible for **independently verifying** that these
target collections originate from installed target-local ranking/zero and
owned tournament authority; a caller-created mapping is *not* sufficient
proof by itself. The later transaction must additionally verify/copy the
season summary, closure marker and binding to the **new** Saved Revision ID,
Season Transition World Event, player sporting/lifecycle/health rollover,
publication history, atomic installation and independent next-season
continuation.

## Focused acceptance

`tests/infrastructure/test_season_closing_fork_proof.py` builds a real
pure Week-61 predecessor with two players, a Week-60 ranked result,
a Week-61 result not eligible until Season-2 Week-1, and an active
disciplinary zero. It tests deterministic replay, target fingerprint
regeneration, repeated source-event provenance, and hostile mutation cases.
It is **not** a Week61-to-Week1 HTTP/SQLite Season Transition acceptance.

The ranking fork planner now invokes `_remap_season_closing_archives` during
replay of the ranking lineage. It resolves each completed Week-61 boundary from
the stored original/target ranking snapshots, frozen player inputs, result-version
history and zero-version history. Every archived Closing Ranking is canonically
recalculated with `rebind_verified_season_closing_ranking`; missing or forged
sources fail closed. The last 2049/50 closure still requires its own
Closing-only-source adapter and remains unsupported.

`tests/infrastructure/test_season_closing_ranking_fork_remap.py` covers
deterministic replay of a Week-61 result first eligible in the following season,
and rejects forged ranking sources and missing Week-61 predecessors.

**This does not enable production post-season Branch creation.** The saved
Season Summary/Closure Marker still requires target revision rebinding. The
atomic ranking fork installer continues to reject Closing archives and
Season Transition World Events, and Week Transition audit remapping remains
event-scoped. Those guards must not be lifted until rollover state, event
provenance, archived closure identity, persistence, rollback and independent
continuation are integrated and tested together. No HTTP/SQLite season-fork,
50-season/realism or pre-alpha release status is implied.

## Cross-Branch Saved Revision closure and SQLite archive install (follow-up)

`rebind_cross_branch_season_closure` rebuilds a target-owned Season Summary,
rule-version envelope and Closure Marker with the newly materialized Saved
Revision identity. It verifies the immutable source component against the
original closing ranking and refuses unknown season-scoped statistic payloads
until they have a real remapping authority. The source revision is never changed.

`install_verified_fork_season_closings` is the SQLite transaction component
for persisting the target archives. It independently recomputes every target
archive against the source/target ranking histories, validates the proposed
archive sequence, requires the real target Week-61 publication, and installs
under a nested savepoint in the caller's outer Branch-fork transaction.
Focused tests use real SQLAlchemy/SQLite persistence, forged data and rollback
after a later injected failure.

**These building blocks are not yet wired to production Run Branch creation.**
That endpoint still rejects Season Closure Saved Revisions and Season Transition
World Events; no guard has been disabled. Full integration must also reconstruct
the Season Transition event's configuration/player/ranking fingerprints from
canonical original and target authority, install its World Event, and recapture
the entire target state together with source-independent continuation.
