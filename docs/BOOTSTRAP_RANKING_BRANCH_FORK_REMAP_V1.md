# Bootstrap ranking Branch fork remapping v1

## Purpose

A Branch created from a ranking-bearing Saved Revision cannot safely share that revision
as its own head because Official Ranking snapshots, command receipts and fingerprints are
bound to the source Branch identity.

This adapter now supports the safely reconstructible **source-free Official Ranking
history** case: Week 1 bootstrap followed by any consecutive sequence of weekly ranking
commands whose frozen inputs contain no tournament results, corrections, disciplinary
zeros, transition authority, InitialWorld binding, or publication/archive authority.

## Supported source

The source Saved Revision may contain:

- `ranking_preparation`;
- optional shared Run-scoped `run_prospect_source` evidence.

The ranking bundle must start with one Week-1 candidate produced by one stored
`initial_ranking.v1` command. Every later candidate must be the immediately following
week and must have exactly one stored canonical `RankingWeekCommand` receipt.

Every command is revalidated against its frozen manifest, target week, policy and roster.
The chain must contain no tournament result sources, corrections, zero history,
transition authorities, Tournament Ranking Snapshot authorities, Season Closing Ranking
archives, authoritative Week/Season Transition state, or InitialWorld binding.

## Materialized fork root

For a supported ranking-bearing fork, Branch creation no longer points the new Branch
head directly at the source revision.

Instead, in one transaction it:

1. validates the source revision and lineage;
2. rebuilds the Week-1 bootstrap and every later source-free weekly command for the
   target Branch identity;
3. recalculates the complete Official Ranking fingerprint chain in order;
4. installs the remapped multi-week ranking state in target-Branch ranking storage;
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

Any ranking bundle containing historical result sources,
disciplinary-zero history, tournament sources, transition authorities, Week/Season
Transition publication state, Season Closing Ranking, InitialWorld-bound bootstrap
evidence, or other Branch-owned Saved Revision components remains rejected.

Those cases require dedicated remap adapters because their nested fingerprints and
historical authorities are Branch-bound. No generic string replacement is used.

This is a technical ranking identity remapping slice. It does not define new ranking,
discipline, tournament, lifecycle, or Tour-entry policy.


## Stored disciplinary-zero history

The fork adapter also supports result-free histories whose ranking commands use
`stored_zeros`.

Every `RankingZeroVersion` is rebuilt for the target Branch identity. Successor
`previous_fingerprint` links are recalculated against the target zero lineage, and
every stored ranking command is rebound to the remapped zero-version fingerprints.

The adapter verifies that:

- every saved zero version is owned by at least one stored ranking command;
- the frozen ranking manifest's resolved disciplinary-zero set exactly matches the
  source zero history at that week;
- only `none` or `stored_zeros` discipline is accepted;
- manually injected `resolved_zeros` history is not silently adopted.

The target can append later zero corrections independently after the fork. Source zero
history remains immutable and unchanged.

Tournament/correction result history and authority-backed transition/publication state
remain outside this adapter.


## Result-version and correction history

The fork adapter also supports branch-owned `RankingResultVersion` histories when
`tournament_sources` is empty.

Every result version is rebuilt for the target Branch identity. Correction
`previous_fingerprint` links are recalculated against the target result lineage.
Stored weekly command corrections are rebound to the remapped result-version
fingerprints before command and ranking fingerprints are recalculated.

At every ranking week the source Saved Revision's frozen result manifest must exactly
match resolution of its saved result-version history. The target manifest is then built
from resolution of the remapped target result history.

The immutable `OfficialRankingResult.source_fingerprint` sporting provenance is kept
unchanged: the fork shares the same historical sporting result evidence while owning a
new Branch-scoped version chain.

`OwnedTournamentRankingSource` and canonical tournament authorities remain outside
this adapter and continue to fail closed.
