# Paired MatchEngine seed-block audit — scientific diagnostics, not tuning

This experimental harness uses the **real standalone MatchEngine**, producing
genuine rally and timing logs. It never accesses the Run database, branches,
ranking, historical player records or production APIs. It never changes Match
rules. It is complementary to the broad existing
`scripts/audit_match_realism.py` observational distribution scan.

## Design

For every numbered block `i`, derive a reproducible child seed from
`global -> season 1 -> week 1 -> match paired-validation-v1:i:seat`.
For each of two explicit seating orientations (`X` on the left, `Y` on the
left), run three controlled arms with the **same match ID and seed**:

| Arm | X attributes | Y attributes |
|---|---|---|
| `equal` | All seven core attributes 84 | All seven 84 |
| `x_stronger` | All seven 90 | All seven 84 |
| `y_stronger` | All seven 84 | All seven 90 |

Other attributes: synthetic age 27, same neutral country `TST`, fixed
play style and archetype, fixed hidden traits, default BO5/PAR-11 rules and
healthy fresh initial states. The only intended treatment difference within
a seat/block is which side receives the **six-point joint attribute
increase**. This changes seven attributes simultaneously, not one independent
mechanism; it does **not** identify effects of technique, psychology or any
single parameter.

The harness runs every cell **twice** in reversed execution order using a
new `DeterministicRng` each time. It compares full-result canonical SHA-256
digests *and* every captured statistic; any mismatch aborts without emitting a
valid report. Match IDs are intentionally the same across treatment arms to
avoid a hidden identity-dependent RNG change. The same seed is a shared
starting stream, **not** necessarily the same rallies/draws after a change
alters an RNG branch.

## Run

From the repo root after installing the project:

```bash
python tools/validate_match_seed_blocks.py --blocks 8 --root-seed 20261101 --output match-validation.json
python -m pytest -q tests/tools/test_validate_match_seed_blocks.py
```

Output `match_paired_seed_validation.v1` contains every (block, seat, arm)
observation, real winner/rallies/games/timeline seconds, domain rally hash,
full result SHA-256 and fingerprint of the observation array. It also records
three arm-level observed X-win fractions and Wilson intervals, both seating
strata, and matched arm-versus-baseline changes in win, time and rallies
including actual win/loss flips. The output path must not exist: reports are
never silently overwritten. No network service, paid product or additional
dependency is necessary.

Bounded input: 1–500 blocks (six cells and twelve real simulations per
block), nonnegative 63-bit seed. Runtime scales with block count and match
length; do not treat this as a performance acceptance benchmark.

## Draft-inclusive hosted evidence

The separate `.github/workflows/prealpha-match-paired-evidence.yml` runs even
while the PR remains Draft, executes the actual domain tests plus **8 complete
blocks** (48 original real Matches and 48 reversed replay checks), validates
the final observations' SHA-256 and uploads one JSON artifact for 30 days.
A green **Fast CI** alone means the scoped tests passed, not that the full
8-block artifact was generated; inspect both workflows on the exact final
commit. This experiment is deliberately not a pre-alpha release gate.

## Scientific and product limits

- No arbitrary empirical realism threshold, no automatic engine calibration,
  no unexpected rewrites of existing historical snapshots.
- Observed Wilson intervals are simple descriptive bounds; pairing/orientation
  can induce correlations and this report does not provide a formal causal
  confidence interval. There is no guarantee of sample power at 8 blocks.
- The tests show within-revision replay/order repeatability on a *synthetic,
  fresh state*, not cross-version historical compatibility nor Run/SQLite
  integration. For that use actual native Tour, Save/restart and Full Simulation
  acceptance suites.
- This is neither 80 actually played FAX Editions nor 50 completed seasons,
  and it cannot replace those release gates or current qualification geometry
  blockers in #1729/#1732.
- The default 84/90 strengths and synthetic trait values are measurement
  controls, not assertions about real-world player performance. Research R008
  informs the methodology but no provisional research is promoted to canon.

Any unexpected shift across future versions should prompt a review of exact
source revision, effective Match rules, seed hierarchy and logged inputs.
Do not infer a defect solely from an observed outcome difference.
