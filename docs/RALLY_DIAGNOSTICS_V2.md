# Rally audit diagnostics V2

This is read-only instrumentation, not a new sporting model or a calibration.
It extends `scripts/audit_match_realism.py`; domain code, saved histories and
Master decisions are unchanged. Estimated shots remain abstract model outputs,
not observed racket contacts or a shot-by-shot simulation.

## Measurements

- Trace coverage explicitly reports missing historical control traces.
- Mean estimated shots uses traced rallies as its denominator.
- Opening / natural / hard-cap closure fractions use traced rallies, including
  neutral lets. A closure reason is not a winner/error/let/stroke classification.
- Opening, control and terminal seconds are accumulated separately.
- PATIENT / BALANCED / FAST segment counts, estimated shots and seconds are
  pooled. Seconds per estimated shot is total seconds divided by total shots,
  not an unweighted average of segment ratios. It includes segment overhead;
  it is not directly equivalent to measured inter-contact time in real squash.
- Missing traces or unused pace classes produce null ratios, not fake zeroes.

CSV fields are additive; summary JSON now declares `audit_schema_version: 2`.
The old committed V1 report remains unchanged. Use a new output directory for
each batch: the CLI now refuses to overwrite an existing directory, preserving
earlier evidence even if a previous batch failed halfway through.

## Verification batch

600 complete matches, 100 per existing scenario, seed base 20260908 and the same
match IDs as V1. All original CSV fields except measured execution time match
the first 100 matches of each V1 cohort exactly, including all 600 rally-log
hashes. No engine change or random draw was introduced by instrumentation.

The batch contains 37,700 rallies. No rally reached HARD_SEGMENT_CAP. This
means the cap did not directly terminate any rally in this batch; it does not
prove that the model has a realistic tail or that the cap is universally harmless.

| Cohort | Mean estimated shots per traced rally |
|---|---:|
| equal_84 | 15.354 |
| gap_6 | 15.545 |
| gap_22 | 15.276 |
| attack_retrieve | 15.017 |
| front_counter | 14.810 |
| equal_60 | 16.042 |

The weaker equal pair has both a different shot-count distribution and timing;
the original duration difference cannot simply be called a pace-only effect.
These are descriptive synthetic-cohort observations, not causal estimates or
acceptance thresholds for real squash. The committed JSON contains the full
aggregate measurements for this smaller batch, not a replacement for V1's 3,000.

Reproduce with:

```sh
PYTHONPATH=src python scripts/audit_match_realism.py --samples 100 --workers 4 --output /new/output/directory
```

Next: controlled single-attribute comparisons and a matched real reference
cohort before changing closure probabilities or timing constants. No new
product decision is required to collect these diagnostics.
