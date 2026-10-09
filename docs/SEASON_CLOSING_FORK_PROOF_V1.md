# Canonical Season Closing Ranking — pre-fork proof V1

**Status: implemented pure adapter, not integrated Saved Revision fork support.**

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

The existing `RankingRevisionState` remapper and fork installer still
deliberately **reject nonempty season_closing_rankings or Season Transition
World Events**. Those hard guards must remain until all adjoining evidence,
including transactional saved revision closure identity, has dedicated
adapters and full end-to-end acceptance. No 50-season/realism or pre-alpha
release status is implied.
