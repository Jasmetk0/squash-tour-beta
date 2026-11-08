# Compare two Run storage observations (no new acceptance gate)

Use existing `scripts/profile_run_storage.py` against each SQLite sample, then
compare the JSON reports **offline**. The comparator reads reports, never DBs or
GitHub, and cannot trigger Save, delete archives or modify Runs.

```powershell
python scripts/profile_run_storage.py --database old.db --run-id <same-run-id> --label before --output before.json
python scripts/profile_run_storage.py --database new.db --run-id <same-run-id> --label after --output after.json
python scripts/compare_run_storage_profiles.py before.json after.json --output change.json
python -m pytest -q tests/tools/test_compare_run_storage_profiles.py
```

The new `run_storage_profile_comparison.v1` contains before/after, integer delta
and percent change for comparable physical sizes, whole-DB SQLite page metrics,
scoped table counts and Saved Revision owner aggregates. A zero denominator is
`percent_change: null`. Added/removed branches are listed as identity changes,
not silently treated as zero-baseline owner data. Missing WAL/SHM or tables remain
**unavailable** rather than being assigned zero bytes/rows. Different Run scope
IDs or malformed input fail closed. Output creation is exclusive: existing
files, including original input files, are not overwritten.

## Important interpretation limits

* DB/WAL/SHM and SQLite pages always describe the **whole database**; only table
  metrics explicitly marked `selected_run` and selected-owner aggregates refer
  to the chosen Run. Do not allocate whole-DB growth to a single Run.
* The existing profiler samples physical file size **after** its logical SQLite
  snapshot; different file sizes are neither simultaneous nor proof of leakage.
* Owner aggregation is not a HEAD lineage integrity check. Report values are
  evidence for investigations, not an automatic performance budget or a release
  pass/fail decision. Test runs may use distinct paths, hardware, data and states.
* This tool is read-only and intentionally does not certify SQLite integrity,
  Source identity, deterministic sporting replay, or the 1,000-player/50-season gate.
