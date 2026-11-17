# Next Claude implementation boundary — unified Saved v2, 17 November 2026

Work is integrating #1803/#1809/#1810/#1814/#1819 in
`fix/performance-integration-20261117`; Radim alone merges. Do not concurrently
edit its persistence, native runtime or Tour files. First fetch current `buuk`,
read the integration PR and this file, and establish the actual merged base.
If the integration is still pending, disclose that dependency and prepare the
isolated storage/fixture design in the existing prototype; do not start a second
competing production writer. Once the integration is owner-merged, Claude owns
one production v2 implementation; Work owns independent review and integration.

## Prompt for the next Claude Code session

Implement **one production Saved v2 storage path** in
`Jasmetk0/squash-tour-beta`, based on the unified architecture proposed in PR
#1823 (`docs/SAVED_V2_UNIFIED_ARCHITECTURE_ADR_2026_11_16.md`). Read its actual
current contents and the existing #1805 generic Merkle DAG, #1811 native stream
and #1821 original-Tour experiments before coding. Do not merge three competing
formats or infer that prototypes are already used by production. Reuse their
demonstrated algorithms and adversarial fixtures in one implementation.

Target the measured problem: the #1820 five-season/1,000-player plan failed at
the first season's W8 manual Save (120-second request timeout), with about 1.85 GB
of SQLite and 5.15 GiB peak RSS. Passing short-clock tests does not establish
long-world scalability. Work has already consolidated the v1 optimizations;
do not reimplement them or expand this task into sporting calibration.

Before editing, state the available model/effort you recommend for this task and
why; distinguish a recommendation from an actually selectable/running setting.
Use a single Draft PR for a coherent usable slice. Continue through necessary
implementation, failures and repairs; report concrete product ambiguity only
when it actually blocks work. Sonar is advisory. Never merge or close predecessor
PRs on your own. No model/budget claim without measured evidence.

### Implementation and trust boundary

1. Preserve existing v1 readers, stored bytes, hashes, seeds and API behavior.
   Add an explicit versioned opt-in writer for new Runs. No automatic migration,
   re-signing, reinterpretation or dependence on today's defaults for old history.
2. Use one Run-scoped content-addressed representation with authenticated
   parent/child structure and explicit revision/root ownership. A digest alone
   does not grant foreign-Run or unreachable-Branch access. Historical and shared
   pre-fork ancestry must remain readable through the same legitimate context.
3. Share unchanged components/history; write changed paths incrementally. True
   prefix appends may use the fast path, but legitimate replacement/deletion,
   rankings correction, Edition updates and Restore need a correct copy-on-write
   fallback. Never silently force append-only semantics onto editable data.
4. Avoid decoding, deep-copying and serializing the entire old aggregate before
   every incremental write; otherwise smaller SQL rows merely hide the same CPU
   and peak-RAM problem. Keep sporting replay and actual evidence intact.
5. The physical read must independently authenticate the actual node bytes,
   envelope, graph closure, identities and sources in its current transaction.
   A proof persisted beside the data is not an independent trust root. Keep
   cold/warm tamper rejection, cycle/missing-node checks and bounded caches.
6. Make root/node insertion, explicit Save, draft cleaning and Viewer selection
   atomic; preserve exact retry, rollback, crash recovery and concurrent stale
   writer rejection. Shared node lifetime must respect every reachable revision
   and fork. Garbage collection is not a prerequisite; do not delete reachable
   history to produce a favorable file-size measurement.

### Required evidence and useful order

- First exact logical/hash compatibility and a small real HTTP/SQLite Save →
  restart → read → fork → Restore flow, not only an isolated Merkle unit test.
- Exercise original Tour, native fork and shared ancestry; Unicode, absent/null,
  genuine append, changed historical element and fallback paths. Use frozen
  authentic inputs and actual MatchEngine evidence, not fabricated sporting data.
- Reject tampered root/child/ancestor, foreign Run, unreachable sibling revision,
  missing nodes, forged sizes/edges, partial commit and stale concurrent Save.
  Corruption tests must use a new physical read after a successful warm read too.
- Compare the same authentic W12 database/workload on pinned baseline and
  candidate, alternating order and repeating samples. Record full-state/sporting
  equality, real request wall times, CPU separately, Save/read costs, physical
  SQLite/WAL sizes and peak/current RSS. Node JSON size alone is not file size.
- Then W52 and a progressively larger 1,000-player workload. Demonstrate the
  growth slope across successive saves/weeks; do not launch the whole five-season
  giant fixture after every tiny patch. Keep W61/W80 compatibility and unchanged
  production timeout bounds; short-clock coverage supplements wide calendars.
- Hand Work exact stable SHA, base/dependencies, changed files and executed
  evidence. Describe remaining unsupported paths honestly. No fixed speedup or
  pre-alpha completion claim from prototype ratios or skipped CI.

The ordinary ChatGPT contributor may independently consolidate benchmark output
and cheap test-harness checks. It must not edit the production writer, schema,
native runtime or these same fixtures while Claude owns them.

---

# Review handoff for Work — long native Saved reads (Draft #1803)

**Update, 15 November (continuation after Work's follow-up).** Work's GC-lock fix is
kept. The cold-restart blocker is addressed without a new storage format: proven
canonical stored text (`canonical_text.py`) replaces re-encoding for the content hash
and component hashes, and the replay is made linear inside its private scope
(`replay_scope.py`). Actual first HTTP read after a cold start on the run #6 final
DBs: W61 152 s → 84 s, W80 226 s → 108–111 s, byte-identical responses. Review
priority, highest first:

| Risk | File / function | What must still hold |
| --- | --- | --- |
| High | `canonical_text.py::verify_canonical_text` | Verdict == `canonical_json(json.loads(t)) == t` for every text; references only byte-compared, unforgeable |
| High | `repositories.py::_saved_revision_model_content_hash` | Same hash as the ordinary computation; non-canonical text takes the ordinary path |
| High | `calendar_native_birth_replay.py::_reusable_birth_steps` | A step reused only for identical objects and identical ordered relevant submissions |
| Medium | `calendar_native_competition.py` evidence per binding, `_proven_hash`, `_raw_global_inputs` | Actual inputs must equal one replayed set exactly |
| Medium | `native_fork_runtime_state.py::_proven_dependency_branches` | Same Branch set as the original projection parser |
| Low | `calendar_global_slots.py::_incremental_tour_fingerprint`, lifecycle/health fingerprint memo | Same canonical hash; scope-only, identity-keyed |

The storage proposal remains valid for growth beyond two seasons (bytes still grow
quadratically); it is not needed for this blocker. Details and evidence:
`docs/NATIVE_LONG_RUN_SAVED_READ_PERFORMANCE.md`, section "Continuation, 15 November".

**Update after Work's REQUEST CHANGES (`docs/NATIVE_LONG_RUN_WORK_REVIEW.md`).** The
three demonstrated defects are repaired in this branch: the stored-text content-hash
shortcut is removed (ordinary canonical check), shared dependency graphs are keyed by
(Run, node set), and the benchmark reports completeness and fails on any missing
restart read. The GC pause is bounded under continuous overlap, `long_seasons` covers
w52/w61/w80 again, and a rollback test shows a failed extension Save promotes no
proof. Statements below that relied on the shortcut are corrected; the decision
section is replaced by an engineering proposal
(`docs/NATIVE_SAVED_COMPONENT_STORAGE_PROPOSAL.md`). Final-head results are in the
PR description.

Prepared by Claude on 14 November 2026 for Work's independent review and for the
owner's storage decision. Radim alone merges. This file selects review work; the
measurements, raw evidence and full limits are in
`docs/NATIVE_LONG_RUN_SAVED_READ_PERFORMANCE.md` and
`docs/evidence/native-long-run-reads-20261114.json`.

## Exact state

- PR: Draft #1803, branch `claude/ecstatic-davinci-qpie07`, base `buuk 320e476`
  (#1802). Linear commits on that base only; no stacked PRs.
- Reviewed source tree: `src/` tree `04b9341682e5` = the tree of `a3855c7` on which
  the passing W52 two-season test ran. Later commits change only CI, docs and tests.
- Not merged, no auto-merge. Draft skips the heavy CI jobs (`long_seasons`, browser);
  to run them: mark Ready or dispatch "Native career season and follow acceptance".

## What changed, ordered by review risk

| Risk | File / function | Change | What must still hold |
| --- | --- | --- | --- |
| High | `repositories.py::_prevalidate_cold_global_lineage`, `_prevalidate_oldest_first*` | Cold HEAD only: HEAD component replay, then the newest revision below each horizon extension, then unproven ancestors oldest first via the ordinary validator | Same gates per revision; proofs only after own full validation; any error → ordinary HEAD-first walk raises the original error |
| High | `run_calendar_extension_commit.py::_verified_ancestor_appends`, `native_fork_runtime_state.py::remember_committed_ancestor_proofs` | After commit, re-key dependency proofs of OLD revisions when `assert_global_save_append` shows only this append + HEAD advance | The NEW extension revision gets no proof (no HEAD proof is written); any other graph change promotes nothing |
| Medium | `run_calendar_extension_commit.py` review | First lineage pass metadata-only; live capture uses the HEAD authenticated in this transaction as Tour prefix (Save-coordinator pattern) | Captured aggregate still replayed and compared exactly with Saved content |
| Medium | `repositories.py` cold path `already_replayed` | Parent prefix not decoded when the declared identity is already in replay evidence | If actual values differ, the component check replays from root (same verdict) |
| Medium | `native_fork_runtime_state.py::actual_dependency_signature`, `_dependency_proof_key` | Per-snapshot closure memo; shared sorted graph (keyed by Run + node set) and canonical JSON | Signature/proof key identical to the original algorithm, including for another Run's equal revision IDs |
| Low | `exact_text_digest.py` | Digest reuse only for the same/byte-equal text held by the snapshot's actual-row cache | Different, stale or tampered text is hashed separately |
| Low | `repositories.py` validation proofs | LRU, bound 4,096 (was FIFO 128) | Keys unchanged (all metadata + SHA-256 of exact bytes); metadata only |
| Low | `calendar_native_competition.py` | Replay evidence bound 128 → 4,096 | Values still matched against every ancestor's actual values |
| Low | `cyclic_gc.py` + decorators | Cyclic GC paused during native Tour reads/commands/Save; full collection after 30 s of continuous pause | Process-wide, ref-counted, restores the previous state; bounded under continuous overlap |

## Suggested adversarial checks

1. Tamper an ancestor (payload, summary, declared hash, parent edge, re-hashed
   component) after a successful warm read, after a cold read and after an extension;
   every case must 409. Existing: `test_long_lineage_keeps_proofs_yet_rejects_changed_ancestor_after_success`,
   `test_native_long_run_cold_lineage.py`, `test_native_long_run_read_proofs.py`.
2. Confirm the new extension revision is never treated as proven before its own
   validation (`test_extension_revision_is_fully_validated_by_the_next_read`).
3. (Resolved by removal) the stored-text hash shortcut; Work's six regressions now
   pass and valid noncanonical legacy text stays readable.
4. Concurrency: two extension Saves / Save during a cold read; promotion must only
   follow a committed, exactly-appended graph.
5. Forks and shared pre-fork ancestry (`test_native_fork_*`, Saved Branch review).
6. Check that nothing changed in sporting outputs: cold responses of baseline and
   candidate are byte-identical on W6/W80 inputs (digests in the evidence file).

## Results to re-check (actual commands)

```bash
PYTHONPATH=src:.:tests/api python -m pytest -q tests/infrastructure/test_native_long_run_read_proofs.py tests/application/test_saved_revision_history.py tests/application/test_ci_acceptance_phase_policy.py
```

```bash
GLOBAL_SLOT_CALENDAR=6 PYTHONPATH=src:.:tests/api python -m pytest -q tests/api/test_native_long_run_cold_lineage.py tests/api/test_calendar_sporting_horizon_extension.py
```

```bash
PYTHONPATH=src:.:tests/api python -m pytest -vv 'tests/api/test_native_season_archive_wide.py::test_two_closed_seasons_archive_compare_extend_and_restart[w52]'
```

The last one is long (~1.5 h on a 4-vCPU host). Locally it PASSED in 5,111 s;
`[w6]` passed earlier. Pre-existing failures identical on baseline: four ranking
restore/remap tests and a `PYTHONPATH` collection error of
`test_run_entry_decision_slots.py` (passes with `tests/application` on the path).

## Remaining engineering work (not an owner menu)

Each Saved Revision stores the complete Run state, so reads are linear in the total
bytes of the lineage and a cold process re-validates every revision. Whether two
full W61/W80 seasons fit the unchanged 120 s bound on the repaired head is reported
from actual completed runs in the PR description, not extrapolated. The structural
fix is the backward-compatible content-addressed component storage described in
`docs/NATIVE_SAVED_COMPONENT_STORAGE_PROPOSAL.md` (new writer version only; no
migration, re-signing, same-database proof or sporting change).
