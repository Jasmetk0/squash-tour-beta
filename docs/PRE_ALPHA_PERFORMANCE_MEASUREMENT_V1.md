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

**Comparing machines.** The same parameters produce different Saved content
under different Python versions and operating systems. On 22 November 2026
the case `--players 8 --width 12 --weeks 1` gave:

| environment | identity digest | nodes |
|---|---|---:|
| Linux, Python 3.11.18 | `5a1d113d…` | 1,407 |
| Linux, Python 3.12.3 | `a0c91271…` | 1,375 |
| Windows Server 2025, Python 3.12.10 | `f3487037…` | 1,397 |

Each environment repeats its own result exactly. On Linux this held in two
runs per version, with `PYTHONHASHSEED` 1 and 2 on 3.12.

A Run built under Python 3.11 opened under 3.12 with an identical inspection,
and the reverse also held.

Master §17.4 and PAQ-127 specify the pre-alpha determinism contract.
They leave exact reproduction between platforms and hardware outside the
automatic guarantee. These measurements use workloads of the same shape.
Use a shared Saved fixture and check output equality when comparing the
same stored state between environments.

The cause and any broader cross-environment requirement remain open.
Radim and Work will agree any change to the product contract before it is
recorded as a decision.

## Linux one-week A/B and CPU diagnosis

Use the same pinned SQLite backup for both commits. Start with a short W6
Run to check the benchmark itself. For a scaling conclusion, repeat at
matched early and late history depths with the same work and hardware.
Each worker executes real Tour requests, including explicit Save, and
checks match and ranking evidence and the complete Saved lineage.

```bash
export BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2
python scripts/profile_native_week_ab.py prepare --database work/week-input.db
sha=$(sha256sum work/week-input.db | cut -d' ' -f1)
python scripts/profile_native_week_ab.py ab --a "$base_commit" --b "$candidate_commit" \
  --input work/week-input.db --sha256 "$sha" --out work/week-timing
python scripts/profile_native_week_ab.py ab --a "$base_commit" --b "$candidate_commit" \
  --input work/week-input.db --sha256 "$sha" --out work/week-cpu --profile-cpu
```

| Evidence | What it measures |
| --- | --- |
| Wall and process CPU, HTTP calls, RSS, DB and WAL | Per request and for the measured week. Counts include the selected workload and separate deliberate retries. Health startup and final lineage checks are outside the timed request set. RSS is sampled at each request boundary, with a separate process high-water mark. DB+WAL uses the largest sampled sum at a single boundary. |
| Logical fetch and OS read counters | SQLite text/BLOB bytes delivered through the instrumented cursor. Linux `/proc/self/io` separately reports bytes returned by read syscalls and storage reads charged to the process. These are whole-process counters, with the client, cache effects and instrumentation included. Their totals have different scopes. |
| CPU utilization | Process CPU divided by elapsed wall time gives mean occupied logical CPUs over the week. The report also records CPU model, process affinity and machine RAM. This does not identify which threads ran in parallel. |
| Optional endpoint CPU profiles | Measure total CPU on the synchronous handler thread. Sample its Python stack every 10 ms of wall time and assign the measured CPU intervals to the top frame. JSON/Pydantic, match modules, Saved storage, replay code, SQL and other work are estimates, with sample counts and unsampled CPU reported. C extension work is attributed to its Python caller. Selected replay and Saved lineage scopes also report inclusive sampled CPU, which can overlap each other and the exclusive groups. HTTP response encoding outside the handler is covered by process timing. Use the separate timing run for throughput and RSS baselines. |
| Component memory | Request RSS covers the whole process. For a separate retained-cache or allocation study use the existing Save memory diagnostic and Python allocation profiler. Those measurements cannot allocate process RSS to individual components. |

For long diagnostics, keep the low-overhead week and Save timeline for
historical comparisons. The legacy giant Save timer stops when response
headers arrive, whereas the short driver also reads and decodes the response.
Use a separate reproduced week for CPU attribution and a retained database
for cold-open or Restore profiling. Task Center polling needs its own scenario.

## Shared-slot week at two history depths — 26 November 2026

`scripts/profile_native_week_ab.py prepare --slot-depth 2|8` builds a W52 Run
(16 players, Saved v2) with 2 or 8 fully played weeks, each one 8-player v2
knockout (7 real MatchEngine matches through three global slots, confirmation,
Week Transition, explicit Saves), then a Saved Draw for the measured week.
Scenarios `slots-d2` / `slots-d8` play the identical measured week: three Next
Slot, confirm-result and Week Transition, each Preview → Execute → GET → Save →
GET. Only the history length differs; the sporting program is the same.

Base `buuk e3ad295`, Linux 4 vCPU container, Python 3.11.18, one process at a
time, `PYTHONHASHSEED=0`, fresh copies of one pinned fixture per depth:

| depth | revisions before | matches before | week wall s | CPU s | peak RSS | max DB+WAL | HTTP calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| d2 | 25 | 14 | 116.8 | 115.3 | 1.35 GiB | 97 MB | 26 |
| d8 | 67 | 56 | 361.5 | 360.3 | 2.97 GiB | 270 MB | 26 |

| per slot (4 matches), s | Preview | Execute | Save |
|---|---|---|---|
| d2 | 1.3 / 1.4 / 1.6 | 9.3 / 8.8 / 9.4 | 5.8 / 4.9 / 5.2 |
| d8 | 3.5 / 4.5 / 4.5 | 26.8 / 27.9 / 27.9 | 15.8 / 15.3 / 15.4 |

SQLite text/BLOB fetched per week: 4.1 GB (d2) and 16.6 GB (d8). The cost grows
roughly linearly with played history although every week has the same 7
matches. MatchEngine is 1.7–2.1 % of request CPU (py-spy, 50 Hz).

Inclusive request CPU (d8 partial run / d2): defensive deep copies of decoded
Saved/live sources 21 % / 20 %; JSON encoding 34 % / 39 % (canonical hashes of
whole checkpoints and payloads, `_value_identity` 7 %); post-write Execute
verification 24 %; recomputing every completed tournament's awards and
sporting fingerprint 7 %; competition replay 7 %; strict checkpoint parse 4–5 %.

Two separable candidates were measured A–B–B–A and are **not** included:

1. Skip the live-row canonical hash in `load_checkpoint` when its stored
   fingerprint column already differs from the Saved value, and reuse the
   component digest inside `native_working_context`: d2 normal 121.2 → 120.7 s,
   retry 123.5 → 124.6 s — within noise.
2. Reuse the operation's own private Saved-source copy in post-write Execute
   verification after a type-exact pristine check: d2 (2 trials) normal median
   115.5 → 115.7 s, CPU 114.4 → 115.0 s, peak RSS 1373 → 1339 MiB. The check
   costs about as much as the skipped copy.

The largest measured cost, the deep copies, overlaps the exact-type copy
experiment #1825; the payload/checkpoint hashing and fetched Saved bytes
overlap the Saved v2 work (#1875 and its predecessors). The next separable
target is the O(history) post-write verification of Execute: it re-decodes,
re-hashes and re-copies the complete live checkpoint after appending one slot.
