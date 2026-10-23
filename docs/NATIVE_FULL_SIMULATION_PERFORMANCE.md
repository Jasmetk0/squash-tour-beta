# Native Full Simulation history performance

Status: production implementation and local verification completed; final-head hosted
acceptance remains the merge gate. One PR: #1639. This is not a release gate pass.
Base: owner-merged `buuk` `e39d962bb6797960c47c1c659d57be1dc67bba6b`.
Only the owner merges. One implementation branch/PR; no auto-merge.

The baseline runs the existing genuine W52 worker/Save/season acceptance from an
immutable checkout. It preserves a SQLite backup immediately before task Start,
then idle early/middle/late week snapshots. Before/after full runs must start from
that same backup and retain every actual week, sporting assertion and manual Save.
A snapshot profile measures that section only, not end-to-end completion.

Capture total wall time, per-step Save/resume time, SQL count and statement/parameter
bytes, native context time, Saved payload bytes and process peak RSS. Separate
repository-cold from warm context reads; obtain CPU profiles separately so profiler
overhead is not counted as speed evidence. SQL text/parameter volume is not the
volume of query results. Record returned physical-history bytes separately.

The earlier W52/W61/W80 times in the task describe those individual integration
scenarios and are not a benchmark of every Run or the complete product.

The local runtime candidate is `2c134fd85decbf110a9547260280c469d885d939`,
production source tree `4b31268c2fc28c0153c676666105359c8b86c201`. Subsequent
evidence/helper/documentation changes preserve that production tree. Draft-skipped
hosted jobs are not successful acceptance evidence; inspect the final PR head.

## Production changes

- Decode original Saved input projections through a repository-local exact-value
  cache. Each lookup hashes the complete current payload and scope; it retains
  at most two entries and at most 4 MiB of serialized input in total. Parsed model
  memory has additional overhead. Oversized inputs bypass retention. Defensive
  copies prevent callers from mutating retained models. This cache grants no
  owner, lineage, source-head or physical-row authority.
- Reread and hash every physical field using type-tagged, length-delimited UTF-8
  bytes. Reuse only the parsed dependency references for those exact current
  bytes, retaining at most 4,096 compact hints per repository (at most 1 KiB of references each). Actual owners,
  source heads and complete dependency topology are still reauthenticated in each
  new snapshot. Python JSON parsing preserves the verifier's duplicate-key
  semantics; SQLite json_extract would choose a different duplicate value.
  These are ephemeral keys only; persisted content hashes, serialization and
  Saved schemas do not change.
- Replace obsolete physical snapshots instead of retaining every write generation.
  Completed operation proofs follow that same transaction/snapshot. SQLite trace
  invalidation also observes raw driver rollback/savepoints and transaction
  restarts, where `total_changes` alone is insufficient. Reject stale loaded
  source/owner ORM identities before certifying changed physical dependencies.
- Reuse the one decoded runtime inside its root verifier rather than repeatedly
  serializing and reparsing that same input.
- Bound parsed-runtime value retention to eight entries and 8 MiB of serialized
  inputs per operation, using compact digest keys rather than large JSON keys.

The source, horizon, seed, sporting kernels, task lease/fencing, manual boundaries,
commands, receipts and persisted history formats are unchanged. A changed physical
source must still pass the original full verification. No global history cache,
Saved migration, sporting recalibration or timeout increase is introduced.

## Reproduction

Run `scripts/profile_native_full_simulation_scenario.py --root work/before --weeks
52` on the baseline. It invokes the unchanged actual acceptance case and preserves
its genuine pre-Start SQLite input and selected idle weeks. For a comparable
candidate execution use `--root work/after --weeks 52 --input work/before`.
The input copy only replaces fixture construction; every actual worker operation,
manual Save, tournament, point assertion, transition and cold restart still runs.
Use a fresh output directory. The original fixture is never modified.

For section-only profiles run
`scripts/profile_native_full_simulation_context.py --database
work/before/week-26.db --branch <input.json branch> --root work/profile --profile`.
Use the same profiling scripts and disposable input on both source trees. Cold
means a new repository validation/projection cache, not an OS cache flush. Warm
reads use new transactions; `same_snapshot_warm` separately measures one unchanged
transaction. CPU profiles are separate from unprofiled timing records. Fetch
metrics count actual returned text/blob UTF-8 bytes, excluding scalar/protocol
bytes; SQL text/parameter volume is reported separately.

Compare `sporting-history.json` across executions using the shared profiling
scripts. They emit UUID-independent sporting digests: actual generated Save IDs
are aliased by Branch/sequence, and only the explicit schema paths in
`profile_native_full_simulation_evidence.py` mask their derived hash anchors.
The duplicate journal/Tour receipts are excluded from this cross-execution
comparison only. All score, rally, time, stamina, seed, attribute, form, ranking,
development and other history values remain, as do all other configuration and
source hashes. Tests prove the comparator detects changed sport/configuration.
The unchanged acceptance independently verifies actual unnormalized signed logs,
Saved source bytes, exact retry and cold SQLite restart. No runtime or acceptance
assertion uses the normalizer.

## Comparable measured results

Same genuine four-player W52 fixture, initial Saved source, seed, offset, horizon,
operator request and original target. Every week, the real late tournament,
manual Saves and Season Transition executed, followed by a cold database reopen.
The runner had a 2-CPU quota and 8 GiB limit, Python 3.11.16, the same environment
and at most two sustained CPU jobs. These are individual measured executions,
not distribution estimates; brief setup/instrumentation contention remains.

| Complete W52 evidence | Before | After |
| --- | ---: | ---: |
| Execution from reviewed pre-Start source through cold reopen | ~1,589.74 s | 774.04 s |
| Whole script including fixture preparation/copy | 1,632.42 s | 777.68 s |
| Peak process RSS | 1,914,348 KiB | 1,785,864 KiB |
| Final Saved revisions / JSON payload bytes | 63 / 80,909,929 | 63 / 80,909,929 |

The comparable execution speedup is **~2.05×**. Baseline execution time is
reconstructed from the preserved pre-Start manifest/report filesystem timestamps;
the candidate records the same boundary with a monotonic clock. Fixture creation
versus copying is excluded from that ratio. The whole-script numbers are reported
separately because their fixture preparation differs.

| Actual Save/resume cycle reaching an idle week | Before | After |
| --- | ---: | ---: |
| W4 | 5.96 s | 2.41 s |
| W26 | 17.47 s | 7.76 s |
| W50 | 46.68 s | 18.02 s |

The identical phase after the first W3 boundary through the last task read used
40,154 → 37,059 SQL statements, 18,834,700 → 17,762,541 statement bytes and
163,206,807 → 161,528,899 parameter bytes. Faster work naturally requires fewer
unchanged one-second task polls; no polling deadline/cadence or actual operation
was removed. The ordinary row lookups already use the Saved/Branch primary-key
indexes, so adding indexes was not the measured fix.

| Same captured dirty-week context; fresh repository / warm new transaction | Before cold | After cold | Before warm range | After warm range |
| --- | ---: | ---: | ---: | ---: |
| W3 | 2.95 s | 3.10 s | 0.84–0.98 s | 0.17–0.39 s |
| W26 | 9.33 s | 10.50 s | 2.10–2.25 s | 0.90–0.97 s |
| W50 | 27.66 s | 31.28 s | 4.06–4.67 s | 1.46–1.64 s |

At W50 both warm reads issue **120 SQL statements and fetch 118,033,019 text/blob
bytes**. Fresh physical validation is retained. The separate CPU profile attributes
2.920 → 0.084 s to building actual dependency signatures; unchanged original-source
re-decoding previously cost 0.752 s, versus 0.526 s for an isolated cached projection
copy. Profiles include profiler overhead and are not mixed with the timing table.
Actual dirty-suffix replay/`prepare_command` is included in these source contexts.
The same-snapshot second context remains ~0.91 → 1.02 s; repeated ancestry/model
work inside a transaction has not vanished.

The W50 progress read remains ~0.28 → 0.29 s, 16 SQL statements and 6,215,363
text/blob bytes. In the complete candidate run 221 task projections used 53.52 s
of thread CPU (73.05 s aggregate wall time); two task-heartbeat callbacks used
0.012 s CPU. Invocation lease renewal/fencing remains separate and unchanged.
Progress reads still cost measurable CPU, but eliminating heartbeats would not
address the measured bottleneck. No control/read semantics were relaxed.

### Sporting and history equivalence

Both original task-source and physical-origin Saved rows (including their stored
payloads, hashes, identities, calendar and timestamps) are byte-for-byte unchanged
from the shared pre-Start backup. The reviewed command is identical.
All **55 reachable native Saved states** have equal normalized sporting digests,
including full rally/time/stamina values, development, Form, ranking and points.
Of those states, 51 also have equal raw sport digests. The four states after the
late tournament differ in generated Save IDs and their derived match-log/ranking
hash anchors; the explicit comparator reports that boundary instead of claiming
raw hash equality. The real three-match tournament and 220 prepared points, with
a 100-point champion, passed the unchanged production assertions in both runs.

### Remaining scaling limits

The work does **not** make history cost flat. W4→W50 cycle cost still rises about
7.5× (baseline 7.8×), with substantially lower absolute times. Complete immutable
snapshots/journals grow with history, and every new snapshot still reads/hashes the
actual dependency bytes. Cold W50 context is ~13% slower here, despite the warm
speedup; a cold repository still performs full trusted ancestry/source and weekly
replay/model validation, and bounded parsed retention can require re-decoding.
Its cold CPU profile spends ~28.9 of 33.6 profiled seconds in root verification,
including 48 historical root validations. One-pass cold verification and storage
amplification remain separate engineering work; no format migration was justified
or smuggled into this change. Larger populations, arbitrary Runs and a complete
50-season product runtime are not extrapolated from these fixtures.

## Local verification and final-head gate

- 65 focused format, source/snapshot/cache/equivalence contracts: passed, 2.51 s.
- Five real HTTP/SQLite native target, final Run closure/late rollback, uncertain
  commit/recovery/concurrent-stale worker, seasonal approval/pause/restart and
  fork/horizon/restore controls: passed, 346.44 s on the preceding runtime candidate.
  They are required again by the final-head native controls job.
- Frozen production-tree W52 worker/points/all weeks/Season Save/cold restart:
  passed, 777.68 s including the fixture copy.
- Genuine Chromium native Full Simulation, three matches/points, separate
  approvals, manual final Save and physical SQLite reopen: passed, ~281 s
  from fresh log creation to the completed evidence artifact.
- Changed helper/runtime lint, byte-compilation and `git diff --check`: passed.

The final PR must actually pass Fast CI, CodeQL, the full native task W52/W61/W80
and short matrix/control/browser gates, relevant native Tour API/browser gates
and Saved Branch integrity/continuation gates on its latest head. Their hosted
results/durations are maintained in the PR/check artifacts; a Draft skip is never
a pass. The original full native Tour/season boundaries remain required according
to the existing repository policy; no negative check or timeout was removed.

## Distinct adversarial pass

The separate pass traced cache ownership, exact-byte input keys, new SQLite
snapshots, pending ORM work, direct SQL/driver writes, external commits, rollback
and savepoints, raw-driver calls from a different Python context, stale loaded
source/owner identities, source-head movement and cache retention. It found and
fixed the raw-driver rollback generation gap and the differing duplicate-key
semantics of SQLite JSON extraction. Negative regressions retain malformed and
rehashed sources, owner mismatch, bounded retention and caller mutation isolation.
Existing actual fork/restore/horizon/restart and uncertain-commit tests remain the
authority for those complete workflows. The Master, sporting rules, final-week
Edition limitation, reserved Lab/Packages frontend and known Viewer debt are untouched.
