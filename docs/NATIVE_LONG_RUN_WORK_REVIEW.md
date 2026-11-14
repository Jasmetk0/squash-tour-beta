# Work review / return task for Claude — PR #1803, 14 November 2026

**Decision: REQUEST CHANGES. Do not merge. Radim alone merges.**

Reviewed author HEAD: `84d5af0d829cdd31e97ccb67f3a16652dcb62b39`, against
owner-merged `buuk 320e4766ec8ba78e3de20153b8aaada90585b0cf` (includes #1802).
The reviewed `src/` tree is `04b9341682e548d0dceb8491c6c56872d0a464de`.
This follow-up adds review regressions and this handoff, **no production repairs**.
The new failing tests are intentional blockers, not permission to skip/xfail them.

Radim asked Work to repair small issues but return substantial work to Claude.
This change needs a substantive correction of validation invariants, benchmark
reporting and incomplete acceptance; it is returned as one coherent repair task.
Continue in **the same branch and Draft PR**, preserving useful existing work.

## 1. Blocking regression: a raw-text digest is not a canonical content hash

Locations: `domain/run_revisions.py::stored_canonical_payload_hash_matches` and
`infrastructure/db/repositories.py::_stored_canonical_text_hash_matches` /
`_validate_saved_revision_once`.

The fast path hashes the stored `payload_json` spliced into an envelope and
compares it with the database's declared `content_hash`. Both are untrusted
stored fields. A matching digest does **not** prove that the payload text is
canonical, or that the ordinary `saved_revision_content_hash(decoded_payload)`
would match. The argument in the docstring assumes the digest already came from
an authentic canonical writer, which is precisely what the validator must check.

Real SQLite reproduction:

1. Create an ordinary empty Run and its initial Saved revision.
2. Keep the decoded payload unchanged, but encode it with whitespace, reversed
   key order, or a duplicate key whose last value is the original value.
3. Set `content_hash` to SHA-256 of the envelope containing that raw payload text.
   Assert that this differs from the authoritative canonical content hash.
4. Read history through `RunSavedRevisionHistoryService.list_history`.

**Base rejects with `SavedRevisionHistoryConflictError`; candidate accepts.**
Both cold and previously warmed readers are affected (six failing cases).
This is a demonstrated service/SQLite integrity regression; no external exploit
or sporting-result forgery is claimed.

Repair the validation first, using the existing canonical computation if a safe
equivalent shortcut cannot be proved. Do not merely trust an unchanged declared
hash, a row ID or a writer marker in the same database. Do not repair by rejecting
all noncanonical stored JSON: legacy text with a **valid canonical hash** remains
readable on the base and must stay readable (two positive controls are included).
Correct the docstring, performance document and handoff's soundness claim.

## 2. Blocking regression: dependency graph sharing loses Run scope

Location: `infrastructure/db/native_fork_runtime_state.py::actual_dependency_signature`,
the `dependency_graphs` cache keyed only by `frozenset(visited)`.

Physical row lookup is scoped by `(run_id, revision_id)`. Equal sets of revision
IDs are therefore insufficient to identify the same actual graph. In one real
SQLite snapshot, first calculate the existing `saved` row's graph, then calculate
the same revision ID under a different Run reference. The second lookup should
produce the missing-row graph. Instead, the candidate borrows the first Run's
graph. Reversing the call order also makes a valid owner lookup borrow the
foreign missing-row graph.

The included differential tests compare each memoized answer with the same
function outside the proof scope: **base agrees; candidate disagrees**. This
proves a helper/cache isolation regression, not an established HTTP cross-Run
access exploit. Include Run ownership in every relevant sharing key and audit
closure/encoded-graph/proof reuse for equivalent collisions. Keep snapshot,
write/savepoint invalidation and exact physical-row checks intact.

## 3. Benchmark reporting can pass without any restart responses

Location: `scripts/profile_native_season_archive.py::read_set` and `read`.

`read_set` continues after a transport timeout without populating the values
map. Restart equality is then computed only over the intersection of available
keys. If every response times out, `restart_equal == {}` and
`all(restart_equal.values())` succeeds; the command reports normal completion.
With a subset missing, that subset is silently omitted from the proof.

The included driver test simulates transport timeouts (it is explicitly **not**
a real HTTP integration test). Either fail the invocation or explicitly report
`restart_complete: false` with missing endpoint names. All expected responses
must exist before claiming complete byte equality. Keep censored observations
as diagnostics, never as successful latency samples. Preserve the 120-second
transport bound. Existing raw evidence containing timeouts must remain honestly
labelled; this finding does not invalidate samples that did complete fully.

## 4. Acceptance and CI are still incomplete

- **Newer explicit owner instruction, 14 November 2026:** Sonar is advisory,
  not a mandatory merge condition. A red Sonar result alone does not block
  approval. Assess substantive findings on their merits; the demonstrated
  integrity/Run-isolation defects and required runtime tests below remain
  blockers independently of Sonar. No requirement to make all Sonar checks green
  is part of this return task. The reviewed author's C Security Rating
  (check `132604623677`) remains a recorded observation, not a gate requirement.
- Heavy native/fork/browser gates are Draft skips, not execution evidence.
  Do not launch the expensive matrix until the new quick regressions pass.
- `long_seasons` runs only `w52`, while the manual full suite excludes **every**
  `long_season` test. Thus `w61` and `w80` currently have no executing CI path,
  despite comments/marker text saying each has a dedicated job. Restore truthful
  complete coverage: the full suite must retain them, or explicit actual jobs
  must cover all three. Do not encode the incomplete `{'w52'}` matrix as the
  desired permanent invariant in the CI-policy test.
- W61/W80 two-season restart success has not been demonstrated. The current
  document's 120–125s / 150s figures are **extrapolations**, not completed tests
  proving impossibility. Keep those distinctions explicit. Do not silently
  reduce the assignment to W52 or treat option D as approved by Work/Radim.
- The authored W52 pass at the matching source tree is useful evidence, but Work
  has not independently rerun its 5,111-second scenario. After validation changes,
  old source-tree timing and correctness results cannot certify the repaired head.

## Repair order and boundaries

1. Reproduce the new tests unchanged; fix hash validation and Run-scoped memo
   correctness. Keep valid historical encodings and all exact-byte/source gates.
2. Make benchmark completeness explicit and repair CI selection/claims. Small
   deterministic tests come first, then a real short-clock API/SQLite proof.
3. Audit the other high-risk changes: cold oldest-first validation, promotion
   only after a successful commit, no proof for the new extension revision,
   fork/shared-ancestor reachability, concurrent Save/extension, rollback and
   corruption after successful reads. Add targeted tests where proof is missing.
4. Check the process-wide GC pause under overlapping requests. Current finite
   nesting tests do not establish a memory bound when requests continuously
   overlap and the global active count never reaches zero. Supply bounded-memory
   evidence or choose a narrower safe optimization; do not assume cycles are
   collected merely because `gc.enable()` is eventually called.
5. Re-measure identical immutable inputs against the base and repaired source.
   Record exact source tree, complete/censored reads, memory, CPU and hashes.
   Distinguish authored local proof from actual final-head hosted acceptance.
6. Finish W52/W61/W80 acceptance within the unchanged per-read bound. If a larger
   storage redesign is necessary, describe that as remaining engineering work
   with a concrete backward-compatible proposal. A new storage version must keep
   old Runs/history/bytes valid; do not silently migrate, re-sign, add a trusted
   same-DB proof or change sporting semantics. Do not make Radim choose a technical
   A–D menu before correcting the demonstrated regressions in this PR.
7. Once stable, run the actual relevant Ready/manual gates on the repaired head
   and return the PR to Work with exact results. Radim alone decides merge.

Keep the original scope: deterministic monolith, fixed Run calendar, explicit
Save, immutable Saved history, source provenance, Run/Branch isolation and
unchanged API/DTO/seed/sporting rules. No unrelated Master, ATP, balance or frontend
work. Keep the requested model/effort reporting honest; recommendations are not
performed model switches and no paid upgrade is a prerequisite.

## Independently executed evidence and commands

Local environment: existing workspace Python 3.12 environment, SQLite and actual
production service code. The original focused author tests returned **64 passed**:

```bash
GITHUB_EVENT_NAME=work_review PYTHONPATH=src:.:tests/api python -m pytest \
  tests/infrastructure/test_native_long_run_read_proofs.py \
  tests/application/test_saved_revision_history.py \
  tests/application/test_ci_acceptance_phase_policy.py
```

The new Run/hash review module has **10 cases**: eight blocking regressions plus
two passing legacy-compatibility controls. All ten pass against owner-merged
production source; on the reviewed candidate eight fail and two pass. The base
source tree was checked against `buuk`; test code was held constant. Benchmark
reporting has one additional candidate failure (simulated transport contract).

Run these first on the candidate, then require all eleven cases to pass:

```bash
GITHUB_EVENT_NAME=work_review PYTHONPATH=src:.:tests/api python -m pytest \
  tests/infrastructure/test_native_long_run_work_review.py \
  tests/infrastructure/test_native_long_run_benchmark_review.py -vv
```

For the owner-merged production comparison, Work used a checkout with the same
`src/` tree as `buuk`, putting it first on `PYTHONPATH` and using
`--confcutdir=tests/infrastructure` so the candidate root conftest could not replace
that path. This comparison exercises the actual base implementation, not a mocked
oracle or a bypassed candidate verifier. No browser/full-release/50-season pass
is claimed by this review.
