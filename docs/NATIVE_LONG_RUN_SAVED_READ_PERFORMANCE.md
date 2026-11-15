# Long native Runs: Saved/season reads and two full seasons on W52, W61, W80

Claude Draft PR on branch `claude/ecstatic-davinci-qpie07`, based on verified `buuk`
`342b826d20b43055f5e1117bab8d58176259360c` (#1801 merged). Owner merges; no
auto-merge. This is a bounded performance and acceptance-evidence change, not a
50-season or full pre-alpha release certification.

## What was measured first

All measurements use the production FastAPI app over real HTTP and SQLite, with
inputs produced by the unchanged production scenario of
`tests/api/test_native_season_archive_wide.py` (8 players, two overlapping
four-player ranked Editions per season, real MatchEngine matches, confirmed
results, a Week Transition for every week, both Season Transitions and an explicit
Save after every operation). `scripts/profile_native_season_archive.py build` plays
the scenario on baseline `342b826` and keeps a consistent SQLite backup after each
closed season; `read` copies one immutable input (opened read-only) and measures it
in a fresh OS process. Profiling (`--profile`) is a separate run and never a timing
sample.

Authentic inputs (built on baseline `342b826`, source tree `33f8878c027e`; SQLite
SHA-256 of the consistent backup; "Saved bytes" is the sum of `payload_json`):

| Input | Saved revisions | Saved bytes | Largest revision | SQLite SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `w6-after-season1.db` | 34 | 216,992,108 | 13,207,485 | `fec1ce94cf46aeddf0568c356b26bf53b924d9dc9a6655caa07c69a0b3594fc5` |
| `w52-after-season0.db` | 66 | 532,168,842 | 11,986,428 | `a56bcf816916c6d54e8b9b94304b3ed2a641e1cdd0637d2a6c48ee17148d3b14` |
| `w52-after-season1.db` | 126 | 1,591,301,520 | 20,675,101 | `ba8b0e5288a24bc5eba59172eaa03eaa14929d37edb5a08d8febfcb1b7326d23` |
| `w61-after-season0.db` | 75 | 637,359,629 | — | `45085464a89d4cb07b357dd05abbe3f21d6cc093457984bc8c4c994d26632eb4` |
| `w80-after-season0.db` | 94 | 890,588,975 | — | `8d4ebd5c66d99f387867365ca5468347fbe4947a98e321f143b6341c160f0b93` |

The baseline W52 build played both seasons in 8,089 s (contended host). The
baseline W61/W80 builds were stopped after their first closed season to free the
host; their per-request logs are retained. Baseline wide W6 test: 782 s.

Environment: Python 3.11.18, FastAPI 0.162.7, Pydantic 2.14.3, SQLAlchemy 2.1.8,
Uvicorn 0.54.0; Linux 6.18, Intel Xeon @ 2.10 GHz, 4 vCPU, 15 GiB RAM. Builds and
long tests ran concurrently on this host, so their wall times are contended; the
A/B read pairs below were run in a balanced order on identical input copies.

Each Saved Revision stores the complete Run state (2.3 MB at the first Tour Save,
~89 KB more per week, ~2.5 MB more per played global slot). Every read re-authenticates
the complete lineage from its physical bytes. The per-read work therefore grows with
the *sum of all revision sizes* (W52 after one season: 66 revisions, 532 MB) and a
long Run's total work grows quadratically with the number of weeks.

## Dominant costs found (profiles and direct counters)

1. **First-in-first-out proof eviction above 128 revisions.** The repository's
   metadata-only validation proofs were bounded to 128 entries in insertion order.
   Every read walks the lineage from HEAD to the root, so a lineage longer than the
   bound evicted each proof just before the next walk needed it. Measured on 151
   ordinary Saved revisions: baseline re-decoded **55–58 revisions on every read**,
   the candidate **1** (the HEAD). Two W52 seasons reach ~140 revisions, W61 ~155,
   W80 ~200.
2. **The same multi-megabyte text hashed 3–4 times per revision per read.** Routing,
   the validation signature and the actual dependency graph each re-encoded and
   SHA-256-hashed every `payload_json`. W6 after two seasons: 268 MB hashed for 72 MB
   of Saved text per warm read.
3. **Quadratic dependency graph construction.** Every Tour revision's dependency graph
   contains its Branch HEAD and hence the whole lineage; each revision rebuilt,
   sorted and canonically encoded that complete graph. W52 after one season: 27,717
   row visits for seven lineage walks.
4. **Cyclic garbage collection.** Reads decode/copy millions of acyclic objects; the
   generational collector repeatedly traversed them. Disabling it for a whole read
   (diagnostic only) changed W52 cold 49.6 → 38.2 s and warm 4.2 → 3.3 s.
5. Remaining, not changed: defensive deep copies of the decoded HEAD checkpoint
   (~23 % of a weekly cycle), the opening-knockout evidence parse, rereading every
   ancestor's bytes once per read, and the cold path's recursive validation (below).

Separate profiled runs (`--profile`, candidate unless noted; instrumented seconds are
not timing samples):

- W52 after one season, baseline cold inspect: `json.loads` 17.4 s (14.6 s of it the
  routing decode of each revision), canonical re-encoding 15.5 s, component
  validation 16.6 s; peak RSS 3.1 GB for 532 MB of Saved text.
- The cold validation nests: HEAD validates its parent inside its own source gate,
  which validates its parent, and so on — depth 59 at W52 after one season, about
  3 Python frames per level (the default recursion limit of 1,000 would be reached
  near 300 revisions). Every level keeps its decoded payload alive.
- W52 after one season, weekly cycle (preview, execute, draft read, Save): deep
  copies of the decoded checkpoint 10.5 s, lineage walks 11.4 s for seven walks of
  which the dependency graph 7.3 s (27,717 row visits).
- W80 after one season after the first changes: 1,735 row visits for seven walks;
  each walk still reads and hashes every ancestor once (~1.8 s per walk at 891 MB).

## Changes (no public API/DTO, schema, Saved byte, seed or sporting change)

- **LRU validation proofs, bound 4,096** (`repositories.py`). Same keys: all row
  metadata plus SHA-256 of the exact stored payload and change summary. Only the
  eviction order and bound change; entries remain metadata only.
- **One digest per physical text per read snapshot** (`exact_text_digest.py`).
  The actual row read by the dependency gate stores its digest in the snapshot's
  existing physical-row cache. Another gate reuses it only for the same `str`
  object or a byte-for-byte equal one (`==`); any other text is hashed on its own.
  Nothing extra is kept alive; the memo dies with the snapshot.
- **Dependency closure memo per read snapshot** (`native_fork_runtime_state.py`).
  Corrected after Work's review: shared sorted graphs are keyed by **(Run, node
  set)**; an earlier head keyed them by the revision-ID set alone and could return
  another Run's graph for the same IDs (helper-level isolation defect, regression
  in `test_native_long_run_work_review.py`).
  Inside one unchanged SQLite snapshot every row/owner/digest is fixed, so the
  complete walk from a node is fixed: a later walk merges it instead of re-expanding
  it, and identical node sets share their sorted graph and canonical JSON. The proof
  key is still SHA-256 of exactly `canonical_json(signature)` (the array encoding is
  assembled from the same element encodings). Any own write, savepoint rollback or
  new transaction creates a new snapshot and discards the memo with the rows.
  A differential check on every revision of real inputs found identical signatures
  and proof keys.
- **Cold lineage order** (`repositories.py::_prevalidate_cold_global_lineage`). Only
  when HEAD is not yet proven: HEAD's single complete component replay runs first
  (exactly the replay HEAD's own validation runs first; it only records evidence),
  then the contiguous unproven ancestors are validated oldest first by the ordinary
  validator, then the ordinary HEAD-to-root walk runs unchanged. Each child now
  finds its parent's completed proof, so validations no longer nest (depth 59 → 2)
  and each decoded payload is released before the next. Any error in this pass is
  discarded and the ordinary walk raises its original error in its original order.
- **Replay evidence covers the lineage** (`calendar_native_competition.py`): the
  per-walk evidence maps grow from 128 to 4,096 entries (hashes and frozen states
  that share receipts/events with the replay). With 128, ancestors older than 128
  states replayed the whole history again.
- **No unused parent prefix**: when the declared component identity is already
  in this walk's replay evidence, the parent's sources are not decoded/copied for
  a prefix that the component check would not use. If the actual values differ,
  the component check replays from the root without a prefix (same verdict).
- **Retracted (Work review, 14 November 2026): content hash over the stored
  text.** An earlier head accepted a revision when SHA-256 of the stored payload
  text spliced into the envelope equalled the declared `content_hash`. That is not
  a proof: both values are untrusted stored fields, so noncanonical text with a
  hash computed over it was accepted where the base rejects it. My argument assumed
  an honest writer, which is exactly what the validator must check, and my
  3,000-case test only ever used honest hashes. The shortcut and those tests are
  removed; the ordinary canonical computation runs again (Work's six regressions
  pass; valid noncanonical legacy text stays readable). Measurements of heads
  before `aac8f8d` include that shortcut and are labelled as such below.
- **Horizon-extension review** (`run_calendar_extension_commit.py`). It validated
  the lineage with every payload materialized and then discarded the result,
  although the following state read validates the same lineage through the same
  gates; that first walk is now metadata-only (HEAD's payload is still read). Its
  live capture now gets the HEAD authenticated in the same transaction as the
  Tour prefix, exactly as the Save coordinator does, so only origins newer than
  HEAD are folded again; the captured live aggregate is still replayed and must
  equal the Saved content exactly. W52 after two seasons, warm, contended host:
  132–138 s → 34–39 s, identical result (`can_save` true, no blockers). The first
  two-season W52 run on the previous head failed exactly here (transport timeout
  after every sporting assertion had passed).
- **Extension Save re-keys authenticated ancestor proofs** (`run_calendar_extension_commit.py`,
  `native_fork_runtime_state.py::remember_committed_ancestor_proofs`). The complete
  actual dependency graph of each native HEAD is taken before the append and
  again after it; `assert_global_save_append` must find exactly the one appended
  revision and the HEAD advance. Only after commit are the OLD revisions' proofs
  re-keyed to the new graph (as the ordinary Save coordinator does). No HEAD proof
  is recorded: the new extension revision is fully validated by the next read
  (regression: it enters the validation cache only through the exact-byte
  validator; a re-hashed change to it or to an old ancestor is rejected). First
  read after the extension, W52 after two seasons: 69–73 s → 13 s. The second
  two-season W52 run on the previous head failed exactly here.
- **Scoped cyclic-GC pause** (`cyclic_gc.py`) around the native Tour service reads,
  commands and `save_calendar_tour`. Bounded after Work's review: overlapping
  operations could keep the process-wide count above zero forever, so whenever an
  operation starts or ends after 30 s of continuous pause a full `gc.collect()`
  runs (regression: cyclic garbage is collected while another operation stays
  paused). Reference counting still frees everything;
  cycles are collected after the outermost operation. Reference counted across
  threads; an already disabled collector stays disabled.

Not changed: physical rereading of every ancestor, owners, topology/reachability,
source HEADs, strict decoding, component replay/evidence matching, Save receipts,
transaction gates, the 120-second transport bound and every existing cache budget.

Rejected after measurement (reverted, not shipped):

- validating ancestors oldest first *before* HEAD's replay: depth 1 but W6 cold
  188 s instead of ~34 s, because each ancestor then replayed the whole history;
- keeping loaded ORM rows referenced during the cold pass: 242 → 201 row loads and
  ~2 s faster at W52/one season, but peak RSS 1.0 → 1.8 GB.

## Before/after (identical input copies, balanced order A1 B1 B2 A2)

**Superseded candidate source.** The candidate runs in this section (`046ebca`,
`c630357`, `bbef6da`) predate Work's review: they include the retracted stored-text
hash shortcut and the unscoped graph key. They remain raw evidence of those heads,
not of the repaired source; the repaired head is re-measured in
"Re-measurement of the repaired head" below.

Raw records, environment, input/output digests and memory of every case (including the
failed baseline W52 two-season case and a superseded intermediate `27df2b1` case) are in
`docs/evidence/native-long-run-reads-20261114.json`. Reproduce one case with
`python scripts/profile_native_season_archive.py read --input <input.db> --root <new dir> --seasons 2`
from each checkout (`build --width 52 --root <dir>` creates the inputs).

All pairs: fresh OS process per phase start, identical copies of the immutable input, measurement script identical in both trees (SHA-256 recorded per run), host shared with up to three long tests. Mean ± sample SD over every raw observation; `TO` is a read censored at the 120 s transport bound, never a latency.

### W6 after two seasons (34 revisions, 217 MB)

Runs: A1 `342b826d20`, A2 `342b826d20`, B1 `c63035748e`, B2 `c63035748e`

| Phase / read (s) | Baseline A1, A2 | Candidate B1, B2 |
| --- | --- | --- |
| cold / tour | 32.32, 33.11; **32.72 ± 0.56** | 23.06, 20.04; **21.55 ± 2.14** |
| cold / archive | 2.39, 2.78; **2.58 ± 0.27** | 2.51, 2.15; **2.33 ± 0.25** |
| warm / tour | 4.28, 3.91, 4.28, 3.63; **4.02 ± 0.31** | 2.98, 2.99, 2.36, 2.47; **2.70 ± 0.33** |
| warm / archive | 2.68, 2.33, 3.05, 2.62; **2.67 ± 0.29** | 1.88, 1.97, 1.78, 1.79; **1.86 ± 0.09** |
| warm / season0 | 2.45, 3.20, 2.44, 3.21; **2.83 ± 0.44** | 1.93, 2.34, 1.77, 1.66; **1.93 ± 0.30** |
| write / preview | 4.26, 4.65; **4.46 ± 0.28** | 3.03, 2.87; **2.95 ± 0.11** |
| write / execute | 13.57, 15.08; **14.33 ± 1.06** | 10.31, 8.58; **9.44 ± 1.22** |
| write / save | 9.29, 10.88; **10.09 ± 1.12** | 6.56, 6.14; **6.35 ± 0.30** |
| after_save / tour | 4.01, 4.23; **4.12 ± 0.15** | 2.44, 2.40; **2.42 ± 0.04** |
| after_save / archive | 3.04, 3.44; **3.24 ± 0.28** | 1.60, 1.55; **1.58 ± 0.03** |
| restart_cold / tour | 32.68, 32.91; **32.80 ± 0.17** | 21.02, 22.21; **21.61 ± 0.84** |
| restart_cold / archive | 3.30, 3.06; **3.18 ± 0.17** | 2.45, 2.27; **2.36 ± 0.13** |

Server peak RSS (GiB, VmHWM): A1 1.49, A2 1.49, B1 0.92, B2 0.91. Restart byte-equal: A1, A2, B1, B2. Cold responses byte-identical across all runs with digests: yes.

### W52 after one season (66 revisions, 532 MB) — candidate at the intermediate head `046ebca` (before the stored-text content hash and evidence probe)

Runs: A1 `342b826d20`, A2 `342b826d20`, B1 `046ebca6a9`, B2 `046ebca6a9`

| Phase / read (s) | Baseline A1, A2 | Candidate B1, B2 |
| --- | --- | --- |
| cold / tour | 49.12, 49.05; **49.09 ± 0.05** | 38.85, 39.01; **38.93 ± 0.11** |
| cold / archive | 3.57, 3.85; **3.71 ± 0.19** | 2.27, 2.33; **2.30 ± 0.04** |
| warm / tour | 4.36, 4.22, 4.03, 4.01; **4.15 ± 0.17** | 2.63, 2.78, 2.67, 2.80; **2.72 ± 0.08** |
| warm / archive | 3.43, 3.40, 3.74, 3.91; **3.62 ± 0.24** | 2.24, 2.24, 2.20, 2.32; **2.25 ± 0.05** |
| warm / season0 | 3.34, 3.84, 3.37, 3.40; **3.49 ± 0.23** | 2.24, 2.13, 2.32, 2.18; **2.22 ± 0.08** |
| write / preview | 4.34, 4.53; **4.43 ± 0.13** | 3.13, 2.85; **2.99 ± 0.19** |
| write / execute | 12.13, 13.25; **12.69 ± 0.79** | 8.21, 7.97; **8.09 ± 0.17** |
| write / save | 11.85, 11.70; **11.77 ± 0.11** | 8.14, 7.98; **8.06 ± 0.11** |
| after_save / tour | 3.86, 4.32; **4.09 ± 0.33** | 2.42, 2.49; **2.46 ± 0.05** |
| after_save / archive | 3.69, 3.41; **3.55 ± 0.19** | 1.92, 1.96; **1.94 ± 0.03** |
| restart_cold / tour | 48.31, 49.58; **48.94 ± 0.90** | 37.79, 39.72; **38.76 ± 1.37** |
| restart_cold / archive | 3.44, 3.60; **3.52 ± 0.11** | 2.42, 2.53; **2.47 ± 0.08** |

Server peak RSS (GiB, VmHWM): A1 3.17, A2 3.17, B1 1.19, B2 1.18. Restart byte-equal: A1, A2, B1, B2.

### W80 after one season (94 revisions, 891 MB)

Runs: A1 `342b826d20`, A2 `342b826d20`, B1 `c63035748e`, B2 `c63035748e`

| Phase / read (s) | Baseline A1, A2 | Candidate B1, B2 |
| --- | --- | --- |
| cold / tour | 87.51, 85.27; **86.39 ± 1.58** | 48.17, 46.44; **47.30 ± 1.22** |
| cold / archive | 6.24, 5.62; **5.93 ± 0.44** | 3.42, 3.58; **3.50 ± 0.11** |
| warm / tour | 6.75, 6.14, 6.10, 6.62; **6.40 ± 0.33** | 3.72, 3.66, 4.02, 4.12; **3.88 ± 0.22** |
| warm / archive | 5.91, 5.53, 5.44, 5.65; **5.63 ± 0.20** | 3.43, 3.55, 3.43, 3.20; **3.40 ± 0.14** |
| warm / season0 | 5.62, 5.11, 5.26, 5.85; **5.46 ± 0.34** | 3.41, 3.63, 3.51, 3.38; **3.48 ± 0.11** |
| write / preview | 6.57, 6.76; **6.66 ± 0.14** | 4.35, 4.51; **4.43 ± 0.12** |
| write / execute | 17.90, 19.51; **18.70 ± 1.14** | 11.22, 11.16; **11.19 ± 0.04** |
| write / save | 18.04, 18.66; **18.35 ± 0.44** | 11.79, 11.50; **11.65 ± 0.20** |
| after_save / tour | 6.21, 6.78; **6.50 ± 0.40** | 3.87, 3.78; **3.82 ± 0.07** |
| after_save / archive | 5.66, 5.30; **5.48 ± 0.25** | 2.89, 2.73; **2.81 ± 0.11** |
| restart_cold / tour | 85.01, 98.35; **91.68 ± 9.43** | 46.65, 45.83; **46.24 ± 0.58** |
| restart_cold / archive | 6.20, 6.18; **6.19 ± 0.01** | 3.45, 3.54; **3.50 ± 0.07** |

Server peak RSS (GiB, VmHWM): A1 5.22, A2 5.22, B1 1.59, B2 1.60. Restart byte-equal: A1, A2, B1, B2. Cold responses byte-identical across all runs with digests: yes.

### W52 after two seasons (126 revisions, 1.59 GB)

Runs: A1 baseline `342b826` (A2 not run: it would again exhaust host memory next to the long tests), B1/B2 `bbef6da` (same source tree as `c630357`)

| Phase / read (s) | Baseline A1, A2 | Candidate B1, B2 |
| --- | --- | --- |
| cold / tour | TO 120; censored | 82.09, 86.09; **84.09 ± 2.83** |
| cold / archive | TO 68; censored | 5.32, 5.83; **5.58 ± 0.36** |
| warm / tour | server gone (OOM-killed) | 5.95, 6.14, 6.59, 6.50; **6.30 ± 0.30** |
| warm / archive | server gone (OOM-killed) | 5.29, 5.49, 5.31, 5.75; **5.46 ± 0.21** |
| warm / season0 | server gone (OOM-killed) | 5.07, 5.47, 5.43, 5.76; **5.43 ± 0.29** |
| write / preview | — | 6.28, 7.02; **6.65 ± 0.52** |
| write / execute | — | 17.92, 17.98; **17.95 ± 0.04** |
| write / save | — | 18.61, 19.90; **19.26 ± 0.91** |
| after_save / tour | — | 5.70, 6.78; **6.24 ± 0.76** |
| after_save / archive | — | 4.96, 5.36; **5.16 ± 0.28** |
| restart_cold / tour | — | 92.40, 88.75; **90.57 ± 2.58** |
| restart_cold / archive | — | 5.51, 6.25; **5.88 ± 0.52** |

Server peak RSS (GiB, VmHWM): baseline A1 server killed by the kernel OOM killer at 10.8 GB anon RSS (cgroup limit 15 GiB shared with the long tests); B1 2.50, B2 3.56. Restart byte-equal: B1, B2. Cold responses byte-identical across all runs with digests: yes.


## Re-measurement of the repaired head

Identical immutable input copies, balanced order A1 B1 B2 A2, idle 4-vCPU host (no other jobs), baseline `buuk 320e476` (`src/` `33f8878c`, unchanged since `342b826`) vs the repaired head (`src/` `0d611805`), same measurement script (SHA-256 in the evidence file). Mean ± sample SD over all raw observations; `TO 120` is a read censored at the unchanged 120 s transport bound, never a latency; a later read waiting for the same single-flight validation shows when it ended. CPU is the server process's user+system time for the whole case.

### W80 after one season (94 revisions, 891 MB)

Runs (commit, `src/` tree): A1 `320e4766ec` `33f8878c02`; A2 `320e4766ec` `33f8878c02`; B1 `bcb8dfbbcb` `0d61180512`; B2 `bcb8dfbbcb` `0d61180512`

| Phase / read (s) | Baseline A1, A2 | Repaired B1, B2 |
| --- | --- | --- |
| cold / tour | 79.40, 76.64; **78.02 ± 1.95** | 48.94, 50.59; **49.76 ± 1.17** |
| cold / archive | 4.81, 4.91; **4.86 ± 0.07** | 3.34, 3.36; **3.35 ± 0.01** |
| cold / season0 | 5.06, 5.24; **5.15 ± 0.13** | 2.97, 3.54; **3.25 ± 0.40** |
| warm / tour | 5.66, 5.69, 5.50, 5.73; **5.64 ± 0.10** | 3.78, 3.84, 3.53, 3.59; **3.68 ± 0.15** |
| warm / archive | 5.25, 4.95, 4.78, 4.87; **4.96 ± 0.21** | 3.20, 3.35, 3.67, 3.41; **3.41 ± 0.19** |
| write / preview | 6.43, 5.97; **6.20 ± 0.32** | 4.05, 4.25; **4.15 ± 0.14** |
| write / execute | 15.80, 16.51; **16.15 ± 0.50** | 10.01, 10.48; **10.24 ± 0.33** |
| write / save | 16.17, 17.34; **16.75 ± 0.83** | 11.09, 12.02; **11.55 ± 0.66** |
| after_save / tour | 5.89, 6.33; **6.11 ± 0.31** | 3.75, 3.78; **3.76 ± 0.03** |
| after_save / archive | 4.20, 4.28; **4.24 ± 0.06** | 2.86, 3.16; **3.01 ± 0.22** |
| restart_cold / tour | 79.06, 80.64; **79.85 ± 1.12** | 51.18, 50.33; **50.76 ± 0.60** |
| restart_cold / archive | 5.63, 5.33; **5.48 ± 0.21** | 3.59, 3.48; **3.53 ± 0.08** |

A1: peak RSS 5.22 GiB, server CPU 191 s, restart_complete True; A2: peak RSS 5.21 GiB, server CPU 188 s, restart_complete True; B1: peak RSS 1.61 GiB, server CPU 123 s, restart_complete True; B2: peak RSS 1.57 GiB, server CPU 127 s, restart_complete True.
Cold responses present in every run (archive, season0, tour) byte-identical across baseline and repaired: yes.

### W52 after two seasons (126 revisions, 1.59 GB)

Runs (commit, `src/` tree): A1 `320e4766ec` `33f8878c02`; A2 `320e4766ec` `33f8878c02`; B1 `bcb8dfbbcb` `0d61180512`; B2 `bcb8dfbbcb` `0d61180512`

| Phase / read (s) | Baseline A1, A2 | Repaired B1, B2 |
| --- | --- | --- |
| cold / tour | TO 120, TO 120; censored | 86.67, 85.34; **86.00 ± 0.94** |
| cold / archive | 89.15, 98.15; **93.65 ± 6.36** | 5.06, 5.01; **5.04 ± 0.03** |
| cold / season0 | 9.04, 8.68; **8.86 ± 0.26** | 5.35, 4.96; **5.15 ± 0.27** |
| warm / tour | 10.24, 9.99, 9.81, 9.98; **10.00 ± 0.18** | 6.06, 5.87, 6.38, 5.85; **6.04 ± 0.24** |
| warm / archive | 8.62, 9.01, 8.27, 7.97; **8.47 ± 0.45** | 5.24, 5.14, 5.06, 5.27; **5.18 ± 0.09** |
| write / preview | 10.57, 10.39; **10.48 ± 0.13** | 6.13, 6.55; **6.34 ± 0.29** |
| write / execute | 28.20, 29.27; **28.74 ± 0.76** | 15.55, 16.66; **16.11 ± 0.79** |
| write / save | 29.30, 28.45; **28.87 ± 0.60** | 18.28, 17.78; **18.03 ± 0.35** |
| after_save / tour | 9.88, 10.06; **9.97 ± 0.13** | 5.29, 5.68; **5.48 ± 0.28** |
| after_save / archive | 8.62, 8.18; **8.40 ± 0.31** | 4.81, 4.63; **4.72 ± 0.13** |
| restart_cold / tour | TO 120, TO 120; censored | 87.20, 91.79; **89.50 ± 3.24** |
| restart_cold / archive | 118.15, 83.56; **100.85 ± 24.46** | 5.23, 5.20; **5.22 ± 0.02** |

A1: peak RSS 11.86 GiB, server CPU 513 s, restart_complete False; A2: peak RSS 10.07 GiB, server CPU 511 s, restart_complete False; B1: peak RSS 2.49 GiB, server CPU 258 s, restart_complete True; B2: peak RSS 2.49 GiB, server CPU 260 s, restart_complete True.
Cold responses present in every run (archive, season0, season0_vs_1, season1, season1_vs_0) byte-identical across baseline and repaired: yes.

On the W52 two-season input the baseline cannot complete a cold read within the bound (validation ends ~210–240 s after start, 10–12 GiB peak); the repaired head completes every read (restart_complete true) at 86–92 s with 2.5 GiB. This is the only input where the repaired head was measured on two complete seasons in the A/B protocol; the W61/W80 two-season results are the actual final-DB measurements in the next section.

Raw records: `docs/evidence/native-long-run-reads-20261115-repaired.json`.

## Two full seasons on W52, W61 and W80

`test_two_closed_seasons_archive_compare_extend_and_restart` is parametrized
`w6`, `w52`, `w61`, `w80`. Each Run has its own immutable clock (W61 Season Week 1 =
Year Week 37). The test records the Saved clock after every executed week and
requires exactly every week 1..W of both seasons followed by both W → Week 1 Season
Transitions; two real Editions per season are played through `next-slot` (MatchEngine)
and confirmed; every operation ends in an explicit Save. It checks the archive, the
point doubling in season 2, both comparison directions, non-overwriting of both
closed seasons after a horizon extension, and byte-equal archive/summaries/comparisons
after a cold process restart. No result is inserted by hand, no week is skipped and
the sporting simulation is not shortened.

Local runs on this host (each a real HTTP/SQLite pytest process; see the commit for
each head). Earlier runs are reported because each found a real limit:

| Run | Head | Result |
| --- | --- | --- |
| W6 | `c630357` and earlier | PASSED (601 s, contended host) |
| W52/W61/W80 #1 | `046ebca` | stopped by me (code changed mid-run) |
| W52/W61/W80 #2 | `c630357` | infrastructure failure: session disk allowance exhausted by my own measurement copies (500 on every server) |
| W52 #3 | `c630357` | every week of both seasons, both Season Transitions, archive, both comparisons and point doubling **passed**; horizon-extension review exceeded 120 s → fixed in `8c051d9` |
| W52 #4 | `e3f9b03` | all of the above and the extension Save **passed**; first read after the extension exceeded 120 s → fixed in `e3f9b03`→`a3855c7` (proof re-keying, boundary replay) |
| W52 #5 | `a3855c7` (same `src/` and test tree as the final head) | **PASSED**, 5,111 s, run alone: every week of both seasons, both Season Transitions, real MatchEngine Editions, points, explicit Saves, archive, both comparison directions, extension without rewriting closed seasons, cold restart with byte-equal reads |
| W52/W61/W80 #6 | repaired head (`src/` `0d611805`), three tests in parallel | each clock: every week of both seasons, both Season Transitions, Editions, points, Saves, archive, both comparisons and the extension **passed**; each **failed** at the first read after the cold restart (120 s transport timeout). W52 5,111 s, W61 6,726 s, W80 10,175 s |
| Hosted (GitHub, `workflow_dispatch` run 43665809817, `bcb8dfb`) | repaired head | `long_seasons/w52` **success** (job 132664784403, 71 min); `long_seasons/w61` **failure** at the first read after the cold restart, everything before it passed (job 132664784409, test 6,026 s); `long_seasons/w80` **failure** at the same point, the first read after the cold restart (`test_native_season_archive_wide.py:193`), everything before it passed (job 132664784228, test 12,117 s) |
| W52 #7 | repaired head (`src/` `0d611805`), run alone | **PASSED**, 4,982 s: every week of both seasons, both Season Transitions, Editions, points, Saves, archive, both comparisons, extension and cold restart with byte-equal reads |

Measured cold restart (fresh process, idle host unless noted) on authentic inputs:

| Input | Revisions | Saved bytes | Cold inspect |
| --- | ---: | ---: | ---: |
| W52 after two seasons + extension (final test DB of run #4) | 127 | 1.61 GB | 96.5 s |
| W80 in season 2 (133 revisions, before extension) | 133 | 1.63 GB | 80.1 s |
| Same W52 input, repaired head (no stored-text shortcut) | 127 | 1.61 GB | 109.1 s |
| W61 two seasons + extension (final DB of run #6), W80 test running alongside | 145 | 2.02 GB | **~191 s**: `inspect` censored at 120 s; the next read completed 70.8 s later after the same single-flight validation (`restart_complete: false`) |
| W80 two seasons + extension (final DB of run #6), W52 test running alongside | 183 | 2.80 GB | **~260 s**: `inspect` and `archive` both censored at 120 s; `season0` then completed in 19.5 s (`restart_complete: false`) |

The 96.5 s and 80.1 s rows were measured on a head that still contained the
retracted content-hash shortcut. The W61/W80 two-season numbers in an earlier
version of this document were extrapolations, not completed tests; they are
replaced by the actual run #6 results above. The 120 s bound is unchanged.

CI: the fast job runs only the exact node id `[w6]` (the former `-k 'not w52'` would
have selected `w61`/`w80`). A separate `long_seasons` job runs `w52`, `w61` and `w80` by exact node id with a
300-minute job limit (skipped for Draft PRs like the other heavy jobs). The manual
full suite excludes the `long_season` marker because that job executes every long
clock; the CI-policy test derives the required clocks from the test parametrization. The
120-second read transport bound is unchanged.

## Continuation, 15 November: cold restart of two full seasons (Work's follow-up)

Work's follow-up (`docs/NATIVE_LONG_RUN_WORK_REVIEW.md`, 15 November) kept the
repairs, added the GC-lock fix and asked for the W61/W80 cold-restart blocker to be
fixed before broader engine work. Profiles of a cold read of the actual final W61
DB (the run #6 failure input) showed the time was not in SQLite but in Python work
proportional to every revision's full snapshot:

| W61 cold read (cProfile, 207 s) | Share |
| --- | ---: |
| two complete component replays (HEAD; newest revision below the extension) | 80 s |
| re-encoding every decoded revision for its content hash | 30 s |
| origin checks, replay-evidence fingerprints, dependency signatures, routing decode | 18–20 s each |

Changes (each behind an equality check against the original computation):

1. **Proven canonical text** (`canonical_text.py`). The content hash is defined over
   `canonical_json(json.loads(text))`. `verify_canonical_text` now *proves* that the
   exact stored characters already are that encoding: a segment is accepted only if it
   is byte-identical to a segment of an earlier text this module proved (held as the
   actual string), or if it is decoded and re-encoded to the same characters; container
   syntax, key encoding, strictly ascending keys (no duplicates) and separators are
   checked. Only then are the content hash, the replay-evidence component hashes, the
   replayed-Tour lookup and the dependency references computed over those exact bytes.
   Non-canonical text keeps the ordinary path. This is the sound form of the removed
   shortcut: that one *assumed* canonical text; this one proves it every time. Proof
   objects are unforgeable (only the module constructs them).
2. **Replay** (`replay_scope.py`, active only inside the private replay scope): the
   growing Tour fingerprint reuses per-element encodings of identical immutable
   receipts/rankings/transitions; lifecycle and health-transition fingerprints are
   memoized per frozen object; a passed health step is not re-checked for the same
   objects; birth-history steps of an identical prefix are reused only for the same
   state objects, source object, world and ordered relevant submissions (week ≤ the
   predecessor week, exactly what `advance_calendar_lifecycle` reads; every
   submission's foreign check still runs). Live commands (no replay scope) are
   unchanged.
3. **Replay evidence per binding**: an extension changes only the Run calendar, so the
   boundary replay overwrote HEAD's evidence and HEAD then decoded its parent for an
   incremental replay. Evidence keeps up to four distinct replayed input sets per
   identity; a reader must match one exactly.

Equality evidence on the actual inputs: all 145 W61 content hashes and 139 replay
input hashes equal the ordinary computation; 290 incremental Tour fingerprints, 121
birth histories and 121 health histories equal a fresh computation during a real
replay; 179/183 W80 dependency-reference sets equal the original parser (4 small rows
keep it). Random and adversarial tests (`test_canonical_text_proofs.py`, 3,000 random
values × 16 non-canonical edits, 1,500 random parent/child references with descent,
forged references) and real SQLite/API tests (`test_native_long_run_text_proofs.py`:
cross-checks during a real cold read, byte-identical response with proofs disabled,
canonically rewritten + re-hashed ancestors rejected cold and after a warm read,
whitespace respelling keeps the ordinary verdict) pass.

First HTTP read after a cold server start, identical final DBs of run #6 (fresh copy
per run, idle 4-vCPU host), base `7ef4b3a` (Work's head, `src/` with Work's GC fix) vs
candidate `29ca584`:

| Input | Base | Candidate | Response |
| --- | ---: | ---: | --- |
| W61 two seasons + extension (145 revisions, 2.02 GB) | 152.1 s | 84.0 s (78.1 s on a warm page cache) | byte-identical (`7c6b8150…`) |
| W80 two seasons + extension (183 revisions, 2.80 GB) | 225.6 s | 111.0, 109.3, 108.0 s (103–105 s on a warm page cache) | byte-identical (`e71b6145…`) |

Peak server RSS: W61 3.1 GB, W80 4.0 GB (unchanged from the base). The W80 HEAD
component replay alone went from 31.5 s to 20.8 s.

**Not yet shown:** the complete W52/W61/W80 two-season acceptance on this head
(`workflow_dispatch` run 43713955097, `long_seasons` matrix, started 15 November
12:27 UTC; result recorded when finished). W80 locally is under 120 s but without a
wide margin; hosted runners ran W52 about 15% faster than this host. An experiment
that shared byte-identical text objects across the read caches raised W80 peak memory
to 5.1 GB without a speedup and was reverted.

Known difference: the content hash is computed over the stored text the payload was
decoded from. If a later validator mutated the decoded payload in place (a code bug;
none is known), the original order would have reported an integrity failure; the
candidate validates the stored bytes.

## Regressions

- `tests/application/test_saved_revision_history.py::test_long_lineage_keeps_proofs_yet_rejects_changed_ancestor_after_success`
  (four corruptions after successful reads of 151 revisions): fails on baseline at the
  decode count, passes on the candidate; a changed payload, summary, declared hash or
  parent edge is rejected after the warm reads.
- `tests/infrastructure/test_native_long_run_read_proofs.py`: digest reuse bound to
  identical actual text, memoized graph equal to the original and invalidated by an
  actual rewrite, a changed actual row rejected inside a warm snapshot, and the GC
  pause (nesting, exceptions, threads, already-disabled collector, bounded under
  continuous overlap).
- Work's review regressions `tests/infrastructure/test_native_long_run_work_review.py`
  (noncanonical stored text with a stored-text hash rejected cold and warm, valid
  legacy text readable, Run-scoped dependency graphs) and
  `test_native_long_run_benchmark_review.py`, plus
  `test_native_long_run_benchmark_contract.py` (complete vs censored restart).
- `tests/api/test_native_long_run_cold_lineage.py`: flat cold depth with identical
  results, changed ancestors rejected cold/warm/after extension, the new extension
  revision validated by the next read, boundary replay count, and a failed
  extension Save (after its append proof) that promotes nothing.

## Limits and next work

- **Every read is still linear in the total bytes of the lineage.** Each Saved
  Revision is a complete snapshot (W52 after two seasons: 126 revisions, 1.59 GB),
  and every read rereads and hashes every ancestor once; a cold process also decodes
  and validates every revision. This is the authority rule (fail closed on any
  changed history), not a cache defect. W52 two seasons + extension, repaired head,
  idle host: cold inspect 109 s, close to the 120 s transport bound. 50-season and
  1,000-player long Runs will exceed it. The structural fix is the
  backward-compatible content-addressed component storage in
  `docs/NATIVE_SAVED_COMPONENT_STORAGE_PROPOSAL.md` (remaining engineering work,
  not attempted here).
- Cold validation depth is now ~2, but the *warm* single-revision paths are
  unchanged; the per-walk replay-evidence bound (4,096) and the proof bound (4,096)
  are sized for lineages up to a few thousand revisions; the dependency-proof
  bound (256 per repository) is unchanged and exceeded by lineages longer than 256.
- Remaining dominant costs: defensive deep copies of the decoded HEAD checkpoint,
  JSON decoding of every revision on a cold start, replay fingerprints and
  ancestor rereads. Memory: server peak ~1.1–1.6 GB at one season, ~2.3 GB for the
  W52 two-season cold read (baseline was OOM-killed on that input on this host).
- Timings are from one 4-vCPU host with concurrent jobs; GitHub runners differ.
  No browser, frontend or 1,000-player scenario was run for this change.
- Next dependency: Work's re-review of the repaired head; then the storage proposal
  as its own task.
