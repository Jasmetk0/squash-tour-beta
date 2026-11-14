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
- **Content hash over the stored canonical text** (`run_revisions.py::
  stored_canonical_payload_hash_matches`). Writers store `canonical_json(payload)`.
  The canonical envelope is assembled with that stored text as the `payload`
  value; a matching SHA-256 implies the ordinary check passes (the other tokens
  are self-delimiting canonical JSON built here and the structural key
  `,"payload_schema_version":` occurs exactly once after the payload in both
  strings, so the stored text must equal the writer's canonical payload). Any
  mismatch falls back to the ordinary decode-and-reserialize check. 3,000 random
  and adversarial cases plus all real rows of the fixture agree.
- **Scoped cyclic-GC pause** (`cyclic_gc.py`) around the native Tour service reads,
  commands and `save_calendar_tour`. Reference counting still frees everything;
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

__AB__

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

__LONG__

CI: the fast job runs only the exact node id `[w6]` (the former `-k 'not w52'` would
have selected `w61`/`w80`). A separate `long_seasons` matrix job runs `w52`, `w61`,
`w80` by exact node id with a 300-minute job limit; like the other jobs it is skipped
for Draft PRs. The manual full suite excludes the `long_season` marker. The
120-second read transport bound is unchanged.

## Regressions

- `tests/application/test_saved_revision_history.py::test_long_lineage_keeps_proofs_yet_rejects_changed_ancestor_after_success`
  (four corruptions after successful reads of 151 revisions): fails on baseline at the
  decode count, passes on the candidate; a changed payload, summary, declared hash or
  parent edge is rejected after the warm reads.
- `tests/infrastructure/test_native_long_run_read_proofs.py`: digest reuse bound to
  identical actual text, memoized graph equal to the original and invalidated by an
  actual rewrite, a changed actual row rejected inside a warm snapshot, and the GC
  pause (nesting, exceptions, threads, already-disabled collector).

## Limits and next work

- **Every read is still linear in the total bytes of the lineage.** Each Saved
  Revision is a complete snapshot (W52 after two seasons: 126 revisions, 1.59 GB),
  and every read rereads and hashes every ancestor once; a cold process also decodes
  and validates every revision. This is the authority rule (fail closed on any
  changed history), not a cache defect. W52 two seasons, candidate, contended host:
  cold inspect ~98 s (direct measurement), i.e. close to the 120 s transport bound.
  Horizons much beyond two W80 seasons, 50-season Runs and 1,000-player long Runs
  will exceed it. Removing that limit needs an owner decision on storage or proof
  design (for example content-addressed/delta component storage, or a restart
  proof that cannot be forged from inside the same database); it is not attempted
  here.
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
- Next dependency: owner review of this Draft; then, if longer horizons are needed
  before release, a storage/proof decision for Saved history.
