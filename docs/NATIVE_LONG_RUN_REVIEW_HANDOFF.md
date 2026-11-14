# Review handoff for Work — long native Saved reads (Draft #1803)

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
| High | `run_revisions.py::stored_canonical_payload_hash_matches` | Content hash over the stored canonical text spliced into the canonical envelope | `True` must imply the ordinary check passes (argument in docstring); `False` always runs the ordinary check |
| Medium | `run_calendar_extension_commit.py` review | First lineage pass metadata-only; live capture uses the HEAD authenticated in this transaction as Tour prefix (Save-coordinator pattern) | Captured aggregate still replayed and compared exactly with Saved content |
| Medium | `repositories.py` cold path `already_replayed` | Parent prefix not decoded when the declared identity is already in replay evidence | If actual values differ, the component check replays from root (same verdict) |
| Medium | `native_fork_runtime_state.py::actual_dependency_signature`, `_dependency_proof_key` | Per-snapshot closure memo; shared sorted graph and canonical JSON | Signature/proof key identical to the original algorithm (differential check on real rows) |
| Low | `exact_text_digest.py` | Digest reuse only for the same/byte-equal text held by the snapshot's actual-row cache | Different, stale or tampered text is hashed separately |
| Low | `repositories.py` validation proofs | LRU, bound 4,096 (was FIFO 128) | Keys unchanged (all metadata + SHA-256 of exact bytes); metadata only |
| Low | `calendar_native_competition.py` | Replay evidence bound 128 → 4,096 | Values still matched against every ancestor's actual values |
| Low | `cyclic_gc.py` + decorators | Cyclic GC paused during native Tour reads/commands/Save | Process-wide, ref-counted, restores the previous state |

## Suggested adversarial checks

1. Tamper an ancestor (payload, summary, declared hash, parent edge, re-hashed
   component) after a successful warm read, after a cold read and after an extension;
   every case must 409. Existing: `test_long_lineage_keeps_proofs_yet_rejects_changed_ancestor_after_success`,
   `test_native_long_run_cold_lineage.py`, `test_native_long_run_read_proofs.py`.
2. Confirm the new extension revision is never treated as proven before its own
   validation (`test_extension_revision_is_fully_validated_by_the_next_read`).
3. Try to break the stored-text hash argument: non-canonical text, duplicated keys,
   text that tries to absorb the following envelope key, changed metadata.
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

## Open decision for Work + owner (not decided by Claude)

Two complete W61/W80 seasons cannot pass their cold restart within the unchanged
120 s read bound: every Saved Revision stores the complete Run state and a cold start
re-validates all of it (W80 at 133 revisions: 80 s idle; two seasons + extension
≈ 150 s; W61 ≈ 120–125 s). The Master's mandatory 50-season FAX release test
(31.28 / PAQ-001) is unreachable with this storage: data and validation grow
quadratically with weeks.

| Option | Effect | Cost / risk |
| --- | --- | --- |
| A. Background verification after start | Reads during warm-up return an explicit "verifying (n %)" state instead of a timeout; same rules | Small; does not fix growth or slower weeks; needs a UX decision |
| B. Signed validation proof outside the DB | Restart ≈ hashing only | Moves the trust boundary to a local key; growth unsolved; Claude does not recommend |
| C. Saved storage without full snapshots (shared immutable components, revisions reference them) | Validation/data proportional to actual change; scales toward 50 seasons | Largest; new schema version, old Runs keep their format; separate task |
| D. Document only (this PR) | W52 proven; W61/W80 open | None now |

Claude's recommendation: D for this PR, C as the next task (A only as an interim UX
fix if wanted). Work and the owner decide.
