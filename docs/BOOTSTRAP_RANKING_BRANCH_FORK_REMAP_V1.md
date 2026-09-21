# Bootstrap ranking Branch fork remapping v1

## Purpose

A Branch created from a ranking-bearing Saved Revision cannot safely share that revision
as its own head because Official Ranking snapshots, command receipts and fingerprints are
bound to the source Branch identity.

This slice removes the blanket rejection for the first safely reconstructible case:
**bootstrap-only Official Ranking history**.

## Supported source

The source Saved Revision may contain:

- `ranking_preparation`;
- optional shared Run-scoped `run_prospect_source` evidence.

The ranking bundle must contain exactly one Week-1 candidate produced by one stored
`initial_ranking.v1` command. It must have no tournament result sources, zero history,
transition authorities, Tournament Ranking Snapshot authorities, Season Closing
Ranking archives, authoritative Week/Season Transition state, or InitialWorld binding.

The stored bootstrap command must exactly match the frozen manifest, policy and target
week. This is verified before any write.

## Materialized fork root

For a supported ranking-bearing fork, Branch creation no longer points the new Branch
head directly at the source revision.

Instead, in one transaction it:

1. validates the source revision and lineage;
2. rebuilds the bootstrap command for the target Branch identity;
3. recalculates the Week-1 Official Ranking snapshot and request fingerprint;
4. installs the remapped ranking state in target-Branch ranking storage;
5. creates a new target-owned `branch_fork_materialized` Saved Revision whose parent
   is the selected source Saved Revision;
6. bases the new clean Working Draft on that new fork-root revision.

The original source revision remains immutable and reachable as shared ancestry through
`forked_from_saved_revision_id`.

## Divergence

After the fork, source and target ranking histories are independent. The target Branch
can prepare and Save Week 2 while the source Branch remains on its original Week-1
ranking history.

## Fail-closed boundaries

Multi-week ranking history and any ranking bundle containing historical result sources,
disciplinary-zero history, tournament sources, transition authorities, Week/Season
Transition publication state, Season Closing Ranking, InitialWorld-bound bootstrap
evidence, or other Branch-owned Saved Revision components remains rejected.

Those cases require dedicated remap adapters because their nested fingerprints and
historical authorities are Branch-bound. No generic string replacement is used.

This is a technical ranking identity remapping slice. It does not define new ranking,
discipline, tournament, lifecycle, or Tour-entry policy.
