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

## Reference PC procedure (Windows, 4 cores, 8 GB RAM, SSD) — 22 November 2026

Master 31.41 names this machine as the first local performance reference. It
asks for the exact hardware and configuration, the number of players and
tournaments, the time of an ordinary week, of a Save and of the first open
after a restart, the peak RAM and the stored data size, both early and later in
a long Run. Measured numbers and release thresholds are kept separate. These
commands produce no threshold.

`scripts/measure_saved_v2_growth.py` and `scripts/measure_cold_tour_read.py`
now run unchanged on Windows as well as on Linux and macOS
(`scripts/process_measurement.py`):

- **Memory:** current/peak memory per request uses the Windows working set
  (`K32GetProcessMemoryInfo`); Linux and macOS use RSS. The keys stay
  `VmRSS`/`VmHWM`.
- **Report:** every report records the machine (CPU model, logical CPUs,
  total physical memory, OS, Python) without host or user names.
- **Linux restart peak:** this is now the restart process's own `VmHWM`.
  `ru_maxrss` also carried the parent's peak across the spawn, so older
  restart peaks were too high.

From a checkout with the locked Windows dependencies installed, in PowerShell:

```powershell
# One Run built through production HTTP/SQLite with explicit Saves: early part
python scripts/measure_saved_v2_growth.py case --storage saved_v2 --players 1000 --width 52 --weeks 4 `
  --root work/ref-early --hardware-note "SSD model, power plan, on AC power"
# A longer Run of the same shape: later part of the season
python scripts/measure_saved_v2_growth.py case --storage saved_v2 --players 1000 --width 52 `
  --root work/ref-season --hardware-note "SSD model, power plan, on AC power"
python scripts/measure_saved_v2_growth.py compare work/ref-early work/ref-season
```

**What `requests.jsonl` and `summary.json` record:**

- **Per request:** each week's requests (wall and CPU time, current and peak
  memory) and each explicit Save with the SQLite and WAL sizes.
- **Restart:** a separate process performs the first Tour read and a warm
  read. It checks their equality with the state before the restart and
  records its own peak.
- **Logical sizes:** revisions, nodes and stored bytes.

The disk type, the power plan and anything else the script cannot detect go
into `--hardware-note`. A retained long Saved fixture can also be measured
directly. With its metadata JSON (`sha256`, `expected_inspection`), for
example the W9 artifact `pr1828-one-shot-w9-44612526515`:

```powershell
python scripts/measure_cold_tour_read.py before-restart.sqlite before-restart.json work/ref-cold-w9.json
```

Run cases one at a time on an otherwise idle machine, and repeat each at
least twice.
