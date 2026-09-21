# Pre-alpha performance measurement v1

This is the first measurement layer for Master PAQ-006. It deliberately does **not**
resolve PAQ-006 and does not define an acceptable runtime or memory ceiling.

## Why it exists

The mandatory Master §31.3 acceptance flows are now executable, but a statement such
as "the pre-alpha is fast enough on a normal notebook" needs reproducible evidence
before a threshold can be chosen.

The repository therefore includes:

```bash
python scripts/profile_pre_alpha_acceptance.py
```

By default this runs exactly the two mandatory pre-alpha acceptance flows:

1. Official Run full season -> save/reopen -> Season Transition -> next Season Week 1;
2. empty Run -> two manual players -> one standalone match.

The command prints a JSON `pre_alpha_performance_profile.v1` record. Use
`--output <path>` to persist the same report.

## Measurements

The v1 record contains:

- elapsed wall-clock time for the selected pytest flows;
- current and peak Python heap bytes measured by `tracemalloc`;
- Python version and platform;
- exact pytest node IDs;
- pytest exit code and whether the run passed.

The heap value is **Python-managed traced memory**, not total process RSS. That
distinction is intentional so the metric works on Windows, Linux and macOS without
adding a new dependency. A later PAQ-006 slice may add OS-level RSS measurements if
needed.

## Policy

This profiler is not part of ordinary PR CI. It belongs to explicit internal
release/checkpoint validation and to deliberate performance investigations.

No number produced by this tool is currently a pass/fail threshold. The first useful
baseline should be captured on a representative ordinary notebook, then PAQ-006 can
define a target separately without rewriting historical measurements.
