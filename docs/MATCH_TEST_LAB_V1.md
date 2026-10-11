# Global Match Test Lab V1

Status: implemented diagnostic foundation; global Match/Tournament Lab scope remains incomplete.

## Boundary

The Match Test Lab is a global Admin sandbox outside normal Runs. V1 accepts one
portable immutable `match_test_lab_scenario.v1` containing a complete production
`MatchContext`, one default seed and optional copied-source provenance.

Execution calls the shared production
`beta_engine.domain.matches.match_engine.MatchEngine.simulate` kernel directly.
There is no second Lab-only match simulator.

## Replay and batch diagnostics

- the complete scenario has a canonical SHA-256 fingerprint;
- the submitted request has a separate fingerprint;
- an exact scenario + exact seed replays deterministically;
- up to 100 explicit unique batch seeds may run against the same frozen scenario;
- each result records winner/loser, sets, A-B set scores, rally count, elapsed time,
  termination reason and a canonical result fingerprint;
- pooled diagnostics report wins by player, retirements, average rallies/duration
  and distinct-result count.

No batch result is selected as canonical and no fairness conclusion is inferred.

## Compatibility and safety

The response explicitly reports:

- production kernel path and current protected compatibility label
  `match_engine_v10`;
- whether the scenario is standard BO5-to-11-win-by-2;
- portable/isolated status;
- `run_mutation_performed = false`;
- `run_live_link = false`;
- compatibility warnings.

A `run_snapshot_copy` is data-only provenance. If it lacks a source fingerprint,
V1 warns that source equivalence cannot be proven. The Lab never reads later mutable
state through that reference.

## Admin UI

`/admin/labs/match` exposes the full portable scenario as JSON plus optional
comma-separated batch seeds. This intentionally permits unusual supported
`MatchContext` combinations for diagnostics instead of restricting the Lab to
normal tournament formats.

## Not completed by V1

- built-in GitHub/read-only scenario catalogue;
- persisted editable `New Test Session` copies;
- import from a canonical Saved Revision/player snapshot with verified source
  fingerprint;
- richer compatibility checks against Tournament/Run rules;
- Tournament Test Lab and arbitrary tournament-format scenarios;
- scenario export/library management;
- larger statistical/fairness tooling.

Those follow as separate slices. V1 must not be described as completion of the
global Match/Tournament Lab milestone.
