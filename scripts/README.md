# Scripts

Operational and developer helper scripts will live here.

- `countries_tabular_tool.py`: CSV <-> canonical JSON bridge for country dataset authoring.

## Pre-alpha acceptance profiler

Run `python scripts/profile_pre_alpha_acceptance.py` to measure the two mandatory
Master §31.3 acceptance flows. Use `--output <file.json>` to retain the versioned
measurement report. This is a measurement tool, not a performance pass/fail gate.
