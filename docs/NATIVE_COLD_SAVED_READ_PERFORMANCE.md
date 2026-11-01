# Native cold Saved reads: dependency metadata without full payload decoding

One implementation branch/PR: `perf/native-cold-saved-read-20261031`, [#1679](https://github.com/Jasmetk0/squash-tour-beta/pull/1679).
Only the owner merges; no auto-merge. This is a bounded performance change,
not a pre-alpha, full-season or 50-season release certification.

## Verified starting point and input provenance

GitHub confirmed both #1676 and #1677 merged into `buuk`. The actual base is
`7ad91113d75a5e84cba496fbc8f06bbfbe9bec95`, whose parent includes archive merge
`b32121ae7d1645208c1a7d841f62231c47b171d8`. The reviewed feature heads were not
treated as merges or imported separately. No unmerged parallel Entry work is used.

The original run `41187913306` and artifact `13037844019` were checked through
the authenticated GitHub connection. The artifact remains available, published
size 85,104,092 bytes and published ZIP digest
`96e935648120a55234ad6fe4ecfad716112710b5ef4792fe339e6df16a38be3e`.
Its producing head is `ee4ba68b9c69fda9a3fee0cd92a6301ccce6043f`. These are remote
metadata, not a locally observed ZIP checksum. The connector's workspace transfer
limit is 32 MiB; direct artifact/API and signed-file downloads returned Forbidden.
The original remote ZIP/database was not modified and is not claimed as the local
benchmark input.

As allowed by the task, the unchanged production scenario was recreated:

```sh
timeout --signal=TERM --kill-after=10s 18m .venv/bin/python \
  scripts/native_tour_browser_acceptance.py \
  --root work/cold-saved-baseline-browser --width 80 --offset 80 --players 1000
```

That genuine Chromium/HTTP/SQLite baseline passed in **994.831421225 s**, at the
original 1,080-second command bound. Restart readiness was **106.246577278 s**.
Both Editions, fourteen real matches, explicit Saves, points, physical backend
restart, historical/replay assertions and final W6 ran. This one baseline pass
does not resolve the two earlier timeouts or establish a stable performance margin.

The completed reproduction's files were copied and checksummed before further
work; original copies are read-only. A separate staging copy supplied a consistent
SQLite backup. Every measured write uses a disposable backup of that same input:

| Input | Actual value |
| --- | --- |
| SQLite bytes | 614,948,864 |
| SQLite SHA-256 | `b887654db939cda530a6e317f2cac8267a5fa8226cf0a2bd354ced76f50725c0` |
| Original Saved HEAD | `saved-revision-f139acd4b55244c6bde77a867a7e2354` |
| Baseline production source tree | `7f5e142d2d076ed30157cd7ec5007ab9fb938493` |
| Candidate production source tree | `6e01e153b2b6c6ec41d8005ddc857eb52aa6de43` |
| Candidate code/harness commit | `b00d9b8234780f2c287e93ebd2be1c5c40a1c702` |

Environment: Python 3.11.16; FastAPI 0.142.4; Pydantic 2.13.5; SQLAlchemy 2.1.4;
Uvicorn 0.54.0; Playwright 1.64.1. Linux 6.18.57, glibc 2.41, Intel Xeon Platinum
8573C; 3 visible CPUs but a **2-CPU quota**, **8 GiB cgroup memory limit**.
No dependency or browser/scenario configuration is changed by this PR.

## What the profile established

The first instrumented HTTP cold GET hit the unchanged 120-second transport
bound at 120.111018298 s. It is a failed diagnostic, not a timing sample.
The complete production inspection method was then profiled directly against
another disposable SQLite copy, independently from ordinary HTTP measurements.

The initial direct diagnostic recorded 137.271525247 s cold and 10.707314527 s
warm; a fresh process recorded 136.910197113 s and 11.249936010 s. Its initial
restart assertion failed because the new harness compared Python tuples returned
directly by the service with arrays reloaded from JSON. That failed run is retained.
The harness now compares the complete JSON representation on both sides, including
all identifiers and fields; it neither masks differences nor drops properties.
Those instrumented service durations are not ordinary HTTP performance results.

The completed baseline cold profile contains 38,867,945 function calls:

| Work | Calls | Instrumented cumulative seconds |
| --- | ---: | ---: |
| Full JSON decoding (`json.loads`) | 265 | 54.098 |
| Routing (`is_global_slot_row`) | 39 | 25.459 |
| Dependency reference extraction (`_dependency_references`) | 23 | 14.545 |
| Checkpoint parsing (including nested calls) | 8 | 11.932 |
| Actual MatchEngine simulation | 14 | 3.519 |

These cumulative figures overlap and must not be added. The 23 dependency hint
misses parsed complete actual Saved payloads already needed by the strict Saved
reader. For reference extraction, their population, checkpoint events and rally
trees were immediately discarded: that walk reads only a selected source Branch
ID and whether a Tour component exists. The source graph was freshly authenticated
in its transaction; the redundant work was construction of unrelated JSON trees,
not physical hashing, owner validation or sporting math.

Routing can hand its complete freshly decoded tree to the strict Saved reader.
That existing reuse remains. This change removes the separate dependency-only
materialization; it does not introduce another full-DTO or checkpoint cache.

## Exact change and authority boundary

`_dependency_content` uses the existing Pydantic Core JSON machinery to project
only `content.native_fork_baseline.state.selected_source_branch_id` and the
presence of `content.calendar_tour_authority`. Ignored large subtrees are not
returned as Python population/rally objects. String caching is disabled for the
compiled projection. Unsupported shapes, non-string raw subclasses and parse
failures fall back to the original Python JSON path. Duplicate/escaped keys,
presence versus null, missing fields, non-string Branch IDs and original errors
are covered by differential regressions.

This projection is **dependency routing data only**. It neither replaces the
Saved DTO nor accepts a sporting schema, source owner or declared fingerprint.
Every complete physical field is still reread and hashed before hint lookup.
Actual Run/Branch owners, source HEADs, topology/reachability, strict complete
payload decoding, original hashes, replay/math and pre/post-write transaction
gates remain unchanged. No writer, receipt, Save, RNG, MatchEngine or public clock
logic changes. No source Package or immutable history is modified.

The existing 4,096 compact-reference hint limit and 1 KiB reference ceiling stay
unchanged. All existing exact-value decode caches, two DTO variants, defensive
copies, eviction/oversize behavior and byte budgets stay unchanged. There is no
new retained payload, validation proof, source permission or commit publisher.
An out-of-order commit cannot gain a new path to publish an older HEAD here.

The baseline instrumented cache observation was 51,467,480 input bytes,
100,555,492 reachable Python bytes, 1,232,957,440 process RSS bytes and peak
4,429,292 KiB RSS. These are different measurements. The existing 64 MiB decode
input-byte budget is not a Python heap or process RSS limit.

## Ordinary paired measurement protocol

`scripts/profile_native_cold_saved_read.py` measures actual HTTP cold/warm GET,
Week Transition preview, confirmed execute including independent inspection,
explicit manual Save, the next Saved GET, then cold/warm GET in a fresh OS process.
Complete cold/warm and pre/post-restart JSON representations must match, including
boolean/integer distinctions and signed zero. No field/identifier normalization
is used. Timing mode installs no profiler, call counters or heap traversal.
Cold means a new repository/cache, not flushed OS page caches.

The initial balanced order was **A1, B1, B2, A2, B3, A3, A4, B4**: four ordinary
executions per source tree, each starting from the identical input checksum.
Independent benchmark/profiler/full test jobs do not overlap on this host.
Complete per-case SQLite outputs are backed up and compressed only after all
timed phases and restart finish, to fit the workspace disk quota. Raw times,
errors, actual identifiers, script/input/source hashes and archives are retained.

A2 encountered `SQLite database or disk is full` during Save. The temporary
archive runner used SQLite connection contexts without explicit `close()`, so
deleted disposable database files remained open and occupied the filesystem.
This was a measurement-infrastructure defect. A separate file-descriptor probe
demonstrated that a deleted SQLite file remains open after context exit and is
released by explicit close. The runner now closes its connections before deleting
files; production code and the shared measurement protocol are unchanged.
The original failed A2 DB/WAL/SHM, zero-byte timings report and console are retained
in a raw archive. Five unaltered phase records were recovered from its console.
**A2R** was added immediately after A2 as an explicitly labelled infrastructure
replacement, not a hidden successful retry. Both the failed A2 and A2R remain in
the raw evidence. The phase table distinguishes that failed Save from valid Save
times; transport timeouts remain failed/censored observations as well.

```sh
# Baseline checkout, with the exact same measurement script:
PYTHONPATH=/workspace/squash-cold-baseline/src \
  /workspace/squash-tour-beta/.venv/bin/python scripts/profile_native_cold_saved_read.py \
  --input work/input.db --root work/cold-A1

# Candidate checkout:
.venv/bin/python scripts/profile_native_cold_saved_read.py \
  --input work/native-cold-saved/input.db --root work/cold-B1

# Separate diagnostic; never an ordinary timing sample:
.venv/bin/python scripts/profile_native_cold_saved_read.py \
  --input work/native-cold-saved/input.db --root work/cold-profile-candidate \
  --mode profile --read-only --direct-profile
```

Seconds. Each cell lists every raw observation, then **mean ± sample SD**.
Baseline order in cells: A1/A2R/A3/A4; candidate: B1/B2/B3/B4. `TO` records
the observed timeout duration, not a completed read latency.

| Phase | Baseline raw; mean ± SD | Candidate raw; mean ± SD |
| --- | --- | --- |
| Cold GET | 116.507718, 118.808326, 115.842070, 112.965009; **116.030781 ± 2.406712** | 102.717215, 102.355975, 111.030821, 96.338976; **103.110747 ± 6.036252** |
| Warm GET | 9.364976, 8.959035, 9.115149, 9.572748; **9.252977 ± 0.270922** | 8.700570, 9.778950, 8.604308, 9.710226; **9.198513 ± 0.632399** |
| Week Transition preview | 13.040783, 12.334237, 12.322069, 12.637478; **12.583642 ± 0.337885** | 12.298623, 13.363285, 12.404263, 13.447178; **12.878337 ± 0.610893** |
| Execute + independent inspection | 55.038036, 53.622151, 48.453507, 49.816137; **51.732458 ± 3.104920** | 49.247747, 50.632235, 48.660255, 51.321716; **49.965488 ± 1.225111** |
| Explicit Save | 40.391561, 44.051611, 45.100283, 43.884585; **43.357010 ± 2.048877** | 39.960058, 41.693904, 43.817839, 36.792433; **40.566059 ± 2.969489** |
| Next Saved GET | 8.986284, 8.305187, 10.966108, 11.102960; **9.840135 ± 1.408033** | 9.963256, 10.402733, 9.103432, 9.493862; **9.740821 ± 0.564169** |
| Fresh-process cold GET | TO 120.047720, TO 120.099695, TO 121.345108, TO 120.124802; **not estimable (censored/not reached)** | 116.748763, 114.272397, 113.492083, 112.626804; **114.285011 ± 1.774694** |
| Fresh-process warm GET | -, -, -, -; **not estimable (censored/not reached)** | 11.985301, 10.727363, 9.783119, 9.961359; **10.614285 ± 1.001602** |

The four-pair mean cold GET is **116.030781 → 103.110747 s (11.135% shorter)**.
Candidate cold range is 96.338976–111.030821 s, versus 112.965009–118.808326 s.
The samples describe this one immutable input and host; four pairs do not certify
all Runs or a general latency distribution.

All four baseline post-Save cold restarts hit the unchanged 120-second transport
limit; their actual completed latencies are unknown. All four candidate cycles
completed and compared every Saved DTO field after a fresh OS-process restart.
Candidate restart cold mean is 114.285011 ± 1.774694 s; the slowest was
116.748763 s, leaving only 3.251237 s against that transport bound. Longer histories
and slower hosts remain a performance risk.

Warm/Save/execute observations overlap and individual phases regress in some
pairs. Preview mean rises from 12.583642 to 12.878337 s. The first two candidate
Saved GETs (9.963256/10.402733 s) exceed their paired baseline values
(8.986284/8.305187 s). These are retained, not discarded as noise; no universal
warm or Save speedup is claimed.

The infrastructure-failed A2 additionally recorded cold 113.310077 s, warm
9.646050 s, preview 13.622665 s, execute+inspection 50.966365 s, then a failed
Save at 17.275771 s. Including its successful pre-fault cold observation gives
all-five baseline cold mean 115.486640 s and 10.716% reduction against the
four candidate cold observations. The infrastructure replacement does not hide
that faster baseline observation.


## Completed profiles, retained memory and complete values

The corrected direct-service diagnostics both completed successfully, including
complete JSON equality after a fresh OS-process restart. Their complete Saved W6
DTOs are also byte-identical between baseline and candidate. Instrumented phase
seconds (cold, warm, restart cold, restart warm) were 131.761267, 11.454669,
115.119555, 10.308466 before and 106.291830, 11.170291, 105.893307, 10.873588 after.
These diagnostic durations are not the ordinary A/B sample above.

The cold profiles establish the removed work and retained validation:

| Work | Baseline | Candidate |
| --- | ---: | ---: |
| Full Python JSON decodes | 265 | 242 |
| Dependency-only full Python payload materializations | 23 | 0 |
| Metadata projections | 0 | 23 |
| Dependency extraction cumulative profile seconds | 16.097 | 3.961 |
| Physical dependency signature calls | 48 | 48 |
| Saved revision validation / full Saved content hashes | 23 / 23 | 23 / 23 |
| Checkpoint parser calls, including nested calls | 8 | 8 |
| Complete v13 checkpoint hash counter | 4 | 4 |
| Original Saved evidence parses | 3 | 3 |
| Actual MatchEngine simulation calls | 14 | 14 |
| Defensive decoded-value copy calls | 2 | 2 |

Nothing in this count table substitutes for the physical/source/replay checks.
The JSON projection still scans input syntax; it avoids building unrelated full
Python population/rally trees for dependency metadata.

Post-phase memory from these separate instrumented runs:

| Measurement | Baseline cold / warm | Candidate cold / warm |
| --- | --- | --- |
| Retained decode input bytes | 51,467,480 / 51,467,480 | 51,467,480 / 51,467,480 |
| Reachable cache Python bytes | 100,555,620 / 100,555,620 | 100,555,428 / 100,555,428 |
| Process RSS bytes | 1,227,292,672 / 1,252,249,600 | 1,488,531,456 / 1,581,187,072 |
| Peak process RSS KiB | 4,429,000 | 4,429,700 |

Candidate RSS is higher in these observations; no lower-RSS claim is made.
The retained cache graph is essentially unchanged. RSS/allocator behavior and
larger histories remain limitations, independently from the input-byte ceiling.
No causal attribution of that RSS difference is asserted from two instrumented
processes.

Offline SQLite verification opened the retained consistent archives, ran
`PRAGMA quick_check`, and compared **all fields of the original 23 physical Saved
rows** against the immutable input. All nine outputs, including failed A2,
preserved them exactly. Every primary before-inspection JSON is byte-identical.
The eight successful Saves produced byte-identical **complete Saved payloads**,
including every stored component, without parsing/normalizing away differences.
Their common raw Saved payload SHA-256 is `983cc68f72d406b5234fea28f6222e2cec20ed3a375679abd96028cfd7121fc4`.

Their new revision headers legitimately have different issued IDs, timestamps and
resulting content hashes; complete headers and receipts are retained verbatim in
`complete-value-comparison.json`. A recursive comparison of every inspection DTO
field found exactly one cross-case difference: `/saved_head_revision_id`.
The actual issued IDs are:

| Case | Saved revision ID | Audit event ID |
| --- | --- | --- |
| A1 | `saved-revision-6d9dbaa4279b44b494f6d0ee980751f9` | `revision-audit-event-82762dde9b614a05aa0a3f911cf1ad72` |
| A2R | `saved-revision-81331b12567549cea8f65e0af37a8132` | `revision-audit-event-44e64b6b32e649b1863cfbfe4c5ece36` |
| A3 | `saved-revision-a59757500b6042b88615a3687ea2c56f` | `revision-audit-event-2ee0ebfe96ad4daeb282d8944a9079b6` |
| A4 | `saved-revision-ca4c9234f6414210891c9aa4608107ac` | `revision-audit-event-e2a131cbc44845a2a5a22318c143880b` |
| B1 | `saved-revision-69e975b1a02f419489619a0d328c267d` | `revision-audit-event-365836d711cc46be89eaff97236ea653` |
| B2 | `saved-revision-dddf5b2a05584b0b803409c23b8198d8` | `revision-audit-event-33bf4d240c4145cf9261464798f934a5` |
| B3 | `saved-revision-5c6e261745ea4cb5869897c94303712c` | `revision-audit-event-49727ede3bbe4651bc7865f53f33ead9` |
| B4 | `saved-revision-0d3e6ec63c0d4578bd6eb549553876a3` | `revision-audit-event-de48fd7c090a43ceb6980055f47e1289` |

Failed A2 issued no successful Save receipt and retained the original HEAD
`saved-revision-f139acd4b55244c6bde77a867a7e2354`; its raw DB/WAL archive and
consistent SQLite archive are both retained. No old or newly issued identifiers
were masked, removed or replaced with aliases.

The timing script SHA-256 used in all ordinary pairs and corrected profiles is
`082766511dae3f3b7d5ce22f776c940581ab0047e6b26d3a490c94b6de3cb2c4`.
Raw JSON times, complete DTOs/receipts/differences, profiles, failures, environment
and input/archive checksums are retained with this report. SQLite archives retain
all physical rows, not just sporting fingerprints.

## Local regression and separate adversarial review

The candidate passed **72 focused tests**, including 39 new projection cases and
existing physical snapshot, value cache, type-exact/hash, budget/eviction and
profiling confinement regressions. Another **5,000 deterministic metadata
differential cases** matched the original extractor. The no-full-payload-decode
regression fails on original `buuk` at its actual `json.loads(row[9])` call and
passes on the candidate.

**Six actual HTTP/SQLite cases passed in 237.24 s**, covering changed/rehashed
source rows, concurrency/stale execution, rollback, independent post-write
inspection, complete DTO reuse, exhausted cache budgets, reversed completed Save
handoffs, subsequent continuation and physical SQLite reopen. Existing assertions
and source/math checks were retained. Ruff and `git diff --check` passed.

The distinct final-runtime-diff review at `b00d9b8234780f2c287e93ebd2be1c5c40a1c702`
checked the projection as an untrusted source of
metadata: missing/null/malformed objects; overwritten and escaped duplicate keys;
unknown/subclass input; bool/int and signed-zero fallback; foreign owner/source;
changed actual bytes; unchanged cache limits; failed writes/rollback and reversed
commit completion. The code changes no publication or transaction boundary.
The review found no new runtime authority, mutation or cache-budget bypass.
It specifically verified that the projector consumes raw JSON rather than caller
models, uses no optimistic subclass route, preserves component presence separately
from its value, and cannot supply a Saved/replay DTO. Physical graph digests still
cover every original field before any hint lookup. The 39 focused cases and
5,000 differential cases support those parser boundaries; the existing real
HTTP/SQLite tests independently cover source corruption and transaction failures.
The distinct diagnostic-harness findings and repairs (tuple/array comparison and
archive connection lifetime) are retained above rather than reported as runtime
Saved defects or discarded successful retries.

Tour API/browser workflows now also watch this affected reader. Their original
commands, scenarios, assertions, population and limits are unchanged. Relevant
final-head native API/fork/season/Saved/browser acceptance must actually execute;
Draft skips are not passes. The latest immutable head and hosted result inventory
belong to PR #1679. Full regression, a complete reference season and 50-season
release acceptance remain separate obligations.
