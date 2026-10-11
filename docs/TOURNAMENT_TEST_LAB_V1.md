# Global Tournament Test Lab V1

Status: implemented classic-knockout foundation for the global isolated Tournament Test Lab.

## Boundary

Tournament Test Lab is available without an active Run. A scenario is portable test data and
never owns, mutates or live-links a Product Run, Branch or Saved Revision.

V1 deliberately separates two questions:

1. **Can this draft execute in the Lab today?**
2. **Would the same draft be compatible with a normal Run tournament boundary?**

An unusual Lab draft may therefore be runnable while still carrying explicit normal-Run
compatibility warnings. A mathematically invalid or not-yet-supported draft remains inspectable,
but produces no draw and no authoritative-looking tournament result.

## Shared production authorities

The V1 executable knockout path reuses:

- `TournamentFormatAuthority` for the effective format contract;
- `TournamentEntryFieldCapacity` and `canonical_classic_seed_count` for classic bracket geometry;
- `TournamentDrawInputAuthority` for frozen draw inputs;
- `TournamentDrawAuthorityBuilder` with `idealized_seed_tiers.v2` for the actual canonical draw;
- production `MatchEngine.simulate` for every played bracket node.

The Lab does not implement a second draw algorithm or a second match simulator.

Synthetic source fingerprints are scoped only to the isolated scenario and bind the pure
authority objects to the scenario fingerprint. They do not claim to be Run persistence.

## Scenario contract

`tournament_test_lab_scenario.v1` contains:

- scenario/display identity;
- an open `format_kind` string so unsupported drafts can still be diagnosed;
- two to 128 complete Match participant contexts;
- Main Draw capacity;
- complete seed-order player permutation;
- draw seed and match seed;
- match format;
- optional `stop_after_round`;
- optional expected champion and played-match-count assertions;
- optional source provenance.

V1 executes only classic knockout. Group, hybrid, Qualification and replacement drafts are not
silently coerced into knockout.

## Compatibility diagnostics

The inspect endpoint returns stable issue codes. V1 currently identifies at least:

- unsupported executable format;
- non-power-of-two classic capacity;
- participant field exceeding capacity;
- seed-order mismatch;
- noncanonical oversized classic capacity;
- nonstandard Match format;
- Run snapshot copy without source fingerprint.

Errors block execution. Warnings allow Lab execution but make `normal_run_compatible=false`.

Example: eight players in a 16-slot bracket can be useful for BYE experiments in the Lab, while
normal Run classic geometry would derive an eight-slot bracket for those eight entrants. The Lab
executes the experiment and explains that difference instead of pretending the draft is ordinary
Run-compatible.

## Step and batch execution

`stop_after_round` executes the canonical draw only through the requested round. The partial
report has no fabricated champion. Champion assertions remain `not_evaluated` until the final
round exists.

Batch mode accepts up to 100 distinct match seeds. One canonical draw is reused across the batch;
only match randomness changes. Each node derives its deterministic seed from the batch match seed
and node identity.

The result reports:

- scenario/request/format/draw-input/draw fingerprints;
- complete canonical draw;
- per-run champion/completion state;
- per-match score, rally count, elapsed time and result fingerprint;
- assertion outcomes;
- aggregate champion counts, completion count, assertion failures and average played matches.

This is suitable for UI use and headless automated agents.

## API

- `GET /admin/labs/tournament/scenarios`
- `POST /admin/labs/tournament/inspect`
- `POST /admin/labs/tournament/run`

Admin UI: `/admin/labs/tournament`.

## Intentionally remaining

V1 is not the complete Tournament Lab milestone. Remaining slices include:

- persistent Tournament Test Sessions / clone / import / export;
- full Qualification topology and progression;
- group and groups+knockout execution;
- withdrawals, replacements, WC/LL and repair windows;
- tournament ranking-point consequences;
- Run → Lab historical tournament snapshot copy;
- Lab → Run editable-draft compatibility bridge;
- finer stepping than round level where useful.

The copied-FAX full-season acceptance track remains separate and is not started by this Lab slice.
