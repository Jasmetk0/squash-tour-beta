# Native Save decode data: performance and integrity

Baseline: `buuk` `edd237b7a2d5e1d69cf96aafce13799bf428253b`, including merged
#1660. Older candidate/unmerged headings in the state documents are dated
history, not a merge inventory. This work is PR #1662; independent Viewer PR
#1661 and all `web/` files are outside its scope.

## Measured work and implementation

The original coordinator published a complete Saved DTO and then independently
published its v13 checkpoint component. Both retained a defensive checkpoint
copy. The real short HTTP/SQLite profile attributed 0.86s of the first Save and
1.94s of the second Save to four `_copy_decoded_value` calls (instrumented times,
not ordinary request timings). At the second Save the global decode cache
accounted for 7,349,979 input bytes while even the initial lower-bound heap
visitor found 34,080,986 Python bytes. The final visitor also follows dataclass
fields and enum data; the initial number is not a final retained-heap result.
Serialized input length alone is not an observation of retained memory.

The cache now retains one private checkpoint for its complete component key.
A complete-payload adapter retains the original evidence/Tour pair and
that checkpoint key. Two adapters also share an unchanged original evidence
model when its complete component key, Run/Branch and complete typed value
agree. No extra cache or entry is introduced for this shared reference.
A full DTO hit resolves both entries under the existing
repository lock and returns one defensive tuple copy outside the lock. No
adapter keeps an evicted checkpoint alive. The same cache retains at most four
entries and at most two full DTO adapters. Legacy decoders retain their original
two-entry path; there is no additional cache or increased byte ceiling.

The successful Save coordinator publishes both interfaces together after the
existing transaction exit and committed-append proof. It no longer needs the
second checkpoint-copy handoff. A native command reader can consume that full
DTO without reparsing its evidence/Tour. Its cold miss keeps the existing
component decoder rather than populating another full history. A full payload
over budget still hands off a fitting checkpoint; an oversized checkpoint is
strictly decoded without retention. Eviction is always allowed.

For an already retained v13 checkpoint, a type-exact traversal of the entire
model value can establish equality to its previously fingerprint-checked private
value. This avoids adding a redundant full model serialization on Tour-only
handoffs. Boolean/integer/float substitutions and opposite signs of zero are
distinct. The traversal never authorizes equality by object identity; unknown
types take the original fingerprint path. Evidence sharing uses the same
conservative typed-value guard in addition to its complete component key.

## Preserved boundaries

- Keys still hash the **complete actual payload/component**, together with
  Run/Branch. A declared fingerprint, source ID or object identity is insufficient.
- Strict decode/model fingerprint and scope guards remain. Cache values and
  returned nested mutable model data are isolated by the existing defensive
  copier. Only previously supported deeply immutable sporting attribute tuples
  may be shared. No new copier or object-identity authorization is introduced.
- Every reader still enters the actual physical Saved/source/ancestry and
  dependency gates before using decode data. Original live evidence, coupled
  checkpoint/Tour state, sporting replay, post-write checks and hash verification
  remain independently required. The cache contains no permission or proof.
- Rollback and failed/uncertain commit cannot reach the coordinator's publication
  block. Cache insertion order never selects a HEAD. A delayed older committed
  handoff may cause a miss; the current physical HEAD and complete key still
  select the only usable state.
- Sporting outcomes, seeds/RNG, audit, manual Save, immutable history and legacy
  formats are unchanged. The original full captured-DTO reuse assertion remains.

## Reproduction and measurement definitions

`scripts/profile_native_save.py` prepares a real production HTTP/SQLite input
with two drawn overlapping native Editions at W80 Week 4. The measured input
contains 1,000 real players; only eight enter these two four-player Editions.
Each case makes an isolated SQLite backup (including committed WAL contents),
executes actual MatchEngine commands and manual POST Saves, and starts a fresh
Python process for the restart. The entire inspection DTO must equal its saved
pre-restart value. Neither requests nor database operations are mocked.

```sh
python scripts/profile_native_save.py --prepare --players 1000 --width 80 --root work/save-input
python scripts/profile_native_save.py --input work/save-input/run.db --root work/before-1
python scripts/profile_native_save.py --input work/save-input/run.db --root work/after-1
python scripts/profile_native_save.py --input work/save-input/run.db --root work/before-calls --mode calls
python scripts/profile_native_save.py --input work/save-input/run.db --root work/after-calls --mode calls
python scripts/profile_native_save.py --input work/common-played.db --root work/tour-only --mode calls --tour-only
```

Run before/after from their respective clean production source checkouts, with
the same script/interpreter and **the exact same prepared input**. When sharing
an editable virtual environment, set `PYTHONPATH` to the selected checkout's
`src`. The script records source commit/tree, input SHA-256, script SHA-256,
interpreter/platform, phases and any production diff; dirty production sources
are rejected. Existing output directories are rejected.

Timing mode installs no instrumentation. Cold means an empty repository decode
cache, not a flushed OS disk cache. Phase times cover real HTTP request(s), not
fixture preparation or process launch. Command phases include preview plus
execution; Save phases include transaction, post-commit handoff and response.
The immediate Saved GET precedes the next command. Restart timings measure the
first and second actual GET in the new process; import/startup is excluded.

Separate `calls` runs count checkpoint/Tour parses, cache canonical JSON calls,
copy calls, checkpoint/evidence roots passed to the defensive copier, Saved
evidence parses and complete checkpoint model hashes. These are scoped
production operation counts, not a count of every JSON conversion in the engine.
Optional `--mode profile` additionally captures cProfile inside the actual HTTP
worker's inspect/preview/execute/Save methods; its times must not be mixed into
the ordinary timing sample.

Memory observations run only with instrumentation. `cache_heap_bytes` traverses
the actual cache's reachable Python objects, deduplicates identities and includes
model dictionaries, field sets, private slots, dataclass fields, enum data and
immutable attribute hints.
It is a reachable graph measurement, not exclusive allocator ownership; shared
immutable data can also be held elsewhere. Current Linux RSS and process peak
RSS are separately recorded. The unchanged 64 MiB ceiling accounts for retained
input bytes, **not a 64 MiB process/heap guarantee**. The adapter charges the
checkpoint once and the rest of the full payload once under that same ceiling.

## Paired results

Production source tree: `64a4208bdc584301cdfbd1e094caaf89bda55d35`.
The final ordinary sample consists of two alternating pairs (A1/B1, B2/A2),
using the same script bytes and the same input SHA-256:
`d1e8c7078664af7125be48cfb58f387791095cdfa01aa990417b0b1bf9e59f0f`.
Both checkouts used Python 3.11.16, Pydantic 2.13.5 and the same Linux execution
environment. No preparation, profile or second acceptance process overlapped
these ordinary timing runs.

Seconds, mean and sample standard deviation; both raw samples are retained:

| Phase | Before: mean ± SD; raw | After: mean ± SD; raw |
| --- | --- | --- |
| Cold GET | 39.495 ± 0.109; 39.418, 39.572 | 40.240 ± 2.442; 38.513, 41.967 |
| Warm GET | 4.059 ± 0.007; 4.064, 4.055 | 4.104 ± 0.285; 3.902, 4.305 |
| First command | 22.499 ± 0.272; 22.307, 22.691 | 23.401 ± 1.202; 22.551, 24.250 |
| Save including handoff | 15.527 ± 0.799; 16.091, 14.962 | 16.397 ± 0.722; 15.886, 16.908 |
| Immediate Saved GET | 4.388 ± 0.094; 4.454, 4.321 | 4.243 ± 0.153; 4.134, 4.351 |
| Next command | 23.893 ± 0.153; 24.001, 23.785 | 24.021 ± 0.699; 23.527, 24.515 |
| Second Save | 16.793 ± 0.817; 16.215, 17.371 | 16.001 ± 1.207; 16.854, 15.148 |
| Process restart cold GET | 48.887 ± 1.875; 50.213, 47.562 | 48.147 ± 1.290; 47.235, 49.059 |
| Restart warm GET | 3.961 ± 0.318; 3.736, 4.186 | 4.133 ± 0.266; 4.321, 3.945 |

The Save → Saved GET → next command → Save sequence averages **60.601s before
and 60.662s after**. This sample does **not demonstrate an elapsed-time speedup**.
The first Save is slower in this sample, the second is shorter, and the available
ranges overlap. Cold restart remains dominated by mandatory physical/source/math
work. Neither runner variation nor code is assigned as the cause of an isolated
slow run. Two pairs are a small sample, not a throughput certification.

The complete persisted checkpoints and accepted-match values are exactly equal
across all four final databases, without normalizing IDs, hashes or fields. The
entire inspection DTO also equals its pre-restart value in every fresh process.

Separate production call observations identify the actual removed work:

| Operation | Before | After |
| --- | --- | --- |
| Checkpoint roots copied during sporting Save | 3 | 2 |
| Checkpoint roots copied during Tour-only Save | 3 | 1 |
| Original evidence roots copied during second Save | 1 | 0 |
| Saved evidence parses during next preview/execution | 3 | 0 |
| Tour parses during next preview/execution | 7 | 4 |
| Checkpoint parses during that sporting command | 2 | 2 |
| Complete checkpoint hashes during first/second Tour-only Save | 2 / 1 | 2 / 1 |
| Cache canonical JSON calls during Save | 2 | 3 |

The additional canonical call binds the shared evidence to its complete actual
component. Physical decode/hash work is not removed. The model-value guard avoids
the extra model hashes introduced by the initial adapter prototype, while keeping
the original model fingerprint contract. Successful copy/data reuse is a concrete
benefit; it is not presented as a whole-browser speed claim.

Final corrected heap/RSS observations and the complete final-head run inventory
are recorded with the exact head in PR #1662. Input-byte accounting, reachable
heap and process RSS are separate metrics; allocator retention and other existing
repository caches can prevent a lower model graph from reducing process RSS.

Three earlier exploratory pairs used an earlier adapter source tree
`3c343296f7072882c2f6b75e7d9e550f306c7889`; their apparent improvement is not
reported as a result for the final implementation. They demonstrated why repeated
samples and preserving the two-source DTO contract were necessary. Their raw
data remains in the task workspace alongside the final samples.

## Validation and distinct adversarial review

The focused cache/dependency/domain/measurement suite passes **58 tests**.
An earlier implementation passed nine real HTTP/SQLite cases (528.86s), including
partial/nested forks, actual final replay, concurrent/stale/retry/rollback,
rehashed source, metadata history and strict version-directed equivalence.
After preserving two-source reuse and sharing evidence, five focused real
HTTP/SQLite cases passed (157.32s), including immediate handoff, exhausted budget,
failed/late-write Save, full DTO equivalence and a subsequent Tour-only Save.
Those local runs are preflight evidence; the final-head hosted native
API/fork/group/worker/season/browser inventory in PR #1662 is the merge gate.
Draft skips are never executed passes. The original complete captured-DTO
regression and every physical/source/math assertion remain present.

A distinct adversarial pass found and resolved two problems in the initial
candidate rather than merely confirming the design:

- A single full DTO adapter made two alternating sources decode six times
  rather than twice. The new regression passes on original `buuk`, fails on the
  initial candidate and passes after restoring two adapters under the same four
  entries. No old full-DTO regression was deleted or weakened.
- Ordinary Python/Pydantic equality conflates booleans, integers and floats,
  and ignores the sign of zero. Model-hash reuse now compares complete typed
  values, distinguishes signed zero and conservatively falls back for unknown
  types. Tests explicitly demonstrate those equal-Python/different-JSON cases.

The pass also checked that rollback/uncertain transaction exit cannot reach
publication; reversed publication of two genuinely committed Saves cannot
select an older HEAD; component eviction removes dependent adapters; shared
evidence stays charged inside the existing budget; complete changed/rehashed
values and foreign scope cannot reuse an entry; and nested mutations of returned
CP/evidence/Tour models cannot modify cache data or immutable history. Both the
whole DTO and component paths compare to the complete strict decoded value.
Real process restart compares the entire inspection, not just fingerprints.

The hosted Sonar review additionally identified ambiguous restart CLI arguments,
unconfined measurement output paths and direct floating-point comparison. The
harness now resolves and confines inputs beneath the checkout's `work/` tree
(including symlink/traversal rejection), restricts output to an allowlisted
`work/<case-name>` leaf, and starts restart with multiprocessing `spawn`.
Restart parameters are Python data; no user-controlled subprocess command is
constructed. The new interpreter preserves the selected virtualenv. Profile
filenames use only fixed prefixes and numeric indices. Exact float comparison
uses hexadecimal representations and rejects NaN; signed-zero and typed-value
semantics are unchanged. Focused regressions cover these boundaries. Ordinary
timing samples above predate this equivalent float-comparison spelling; they
remain observations of their explicitly recorded source tree, not a timing
claim for a later revision.

An intermediate attempt resolved the virtualenv interpreter symlink and the
restart correctly failed because the underlying interpreter lacked pytest.
That failed sample is retained and is not a successful restart observation.
The spawn correction is verified with the real HTTP/SQLite scenario before
publishing the next candidate.

One diagnostic invocation used an older script against an already-played input
and correctly received 409 for a reused command ID with different payload. It
is excluded from paired results. The harness now namespaces Tour-only command
IDs; the rejected attempt and exploratory samples are retained in the workspace.
No production check, assertion, population or timeout was weakened to obtain a
pass, and no failed acceptance was retried merely to obtain green.

Remaining limits: the two-pair sample does not establish elapsed-time speedup;
cold physical/source/math verification remains expensive; input-byte budget is
not a process memory cap; multiple different CP/Tour values and allocator slack
still consume memory; full envelope/checkpoint oversize and eviction legitimately
take the strict decoder. This is not full pre-alpha or 50-season certification.
Owner alone merges; no auto-merge is enabled.
