# Native fork Saved append: omit a replaced subtree from defensive copy

**Date:** 16 November 2026  
**Base:** `buuk` `320e4766ec8ba78e3de20153b8aaada90585b0cf`  
**Scope:** `src/beta_engine/application/native_fork_runtime_service.py` only. This is the **native fork v2** append path, not the older v1 Saved reader or the MatchEngine.

## Why this copy is unnecessary

`NativeForkRuntimeService._append` historically deep-copied `payload or previous.payload`, then **unconditionally replaced** `payload["content"][KEY]` with `component(runtime)`. `KEY` names the previous complete `native_fork_runtime` subtree. An expensive traversal of that discarded tree cannot contribute to the new Saved JSON bytes.

The change creates a temporary dictionary containing every source field **except the discarded native runtime**, and deep-copies that whole reduced dictionary. It then executes the existing calendar, runtime replacement, content-hash, canonical JSON, SQLite insertion, audit, state updates and validated post-write read **unchanged**. No value surviving into the Save is shallow-copied or aliased to the source. All generic/unknown root and content fields except that one explicitly replaced key survive with their original values. The retained source remains immutable to the writer.

This is intentionally **not** the unsafe optimization of sharing mutable models between consumers: all retained nested `dict`/`list` values are still defensively deep-copied, and the produced Saved payload crosses canonical JSON into SQLite.

## Candidate comparison and limitations

A small independent Python 3.13 local replica of the exact `deepcopy`/replacement/canonical-serialization structure was measured on a synthetic ~1.6 MB source containing 1,000 player-shaped records with 57 numeric attributes, health entries and historical data. A corrected 10-pair interleaved A/B/B/A measurement with the **exact reduced-dictionary deep-copy algorithm** gave **52.4 ms** baseline versus **12.7 ms** candidate median (Python 3.13.5). That is **4.1× faster in this isolated copy + serialization operation**, **not** a production Save, W6 season or 50-season result. Canonical output was byte-for-byte identical. A separate instrumented trial showed peak Python allocations (tracemalloc) of **5.95 MB** versus **1.70 MB**; this is not process peak RSS nor the complete Save memory cost. An earlier uncorrected ~65/~13 ms exploratory estimate was superseded by this exact-code measurement. Workload composition, actual component generation, hash validation, SQLite and full replay are absent from this isolated sample. No whole-season improvement or RAM reduction is claimed.

For repeatable source-tree measurement:

```bash
PYTHONPATH=src python scripts/benchmark_native_fork_append_copy.py --players 1000 --repeats 8
PYTHONPATH=src python scripts/benchmark_native_fork_append_copy.py --database work/actual-native-v2-run.db --run-id RUN --branch-id BRANCH --repeats 8
```

The second option requires a real **previously prepared native v2** SQLite fixture, reads it in read-only mode and does not modify its Saved rows. This input is for *timing only* and is not itself a substitute for an authenticated production Saved read. The script performs paired A/B/B/A measurements, verifies **byte-identical canonical JSON**, and reports memory separately. For real end-to-end performance, use the existing `scripts/profile_native_save.py` / native Full Simulation acceptance against independent copies of the same SQLite input, and compare the identical historical sporting facts.

## Actual native-v2 SQLite Save/Restore A/B (Fast CI, Python 3.11)

Added `tests/api/test_native_fork_append_sqlite_equivalence.py`, a **real integration test**, on commit `a7caebcd82e06bc74c00d51e2f4cb2ea5326d12f`. It creates a normal signed Run through production HTTP endpoints, installs a real native v2 fork, advances one real working transition, then takes a consistent `sqlite3.Connection.backup` before the Save. Four cloned SQLite inputs execute A/B/B/A. A monkeypatch changes **only the copy function** from the reduced tree to the original `deepcopy(source)`; both variants run the same production Save/Restore services, content hashes, original-row validation, real SQLAlchemy inserts, audit and historical MatchEngine replay.

The test confirms byte-identical persisted `payload_json`, content hashes, complete revision envelopes, saved/restore history and Run/Branch owners. It proves original source/root physical rows remain unchanged, catches an injected late audit INSERT failure and proves full transaction rollback on **both Save and Restore**. It then performs a successful Save/Restore and replay in each variant.

Fast CI run [43856392285](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43856392285) on the integration-test commit: **6 targeted tests passed** (5 earlier unit + 1 real SQLite), plus **24 tournament-config tests passed**; source compilation passed. The real integration test took **56.24 seconds** in CI. Heavy Draft-only acceptance workflows remained **skipped**, not passed.

Measured on this *small* actual native-v2 payload (previous root JSON **42,897 bytes**, four source players plus a new born player), two measurements per variant on one shared GitHub-hosted runner:

| Real operation (A/B/B/A, medians) | Original full copy | Reduced copy |
|---|---:|---:|
| Copy helper during Save | 0.88 ms | 0.34 ms |
| Complete production repository SQLite Save | 661.98 ms | 395.34 ms |
| Copy-helper fraction of full Save | 0.15% | 0.09% |

**Causality warning:** This is an observational, underpowered, only two-per-variant Save comparison. Runner noise, cold/warm proof caches and other Save work dominate. **Do not interpret the ~662 → ~395 ms difference as a 40% Save speedup caused by this PR.** The directly attributable copy saving is only ~0.54 ms on this small case; the copy represents <0.2% of total Save. Neither actual 1,000-player Save nor full-season W6/W52/W61/W80 speed is measured.

Static call-path inspection of `NativeForkRuntimeService` found `_append` invoked directly only by the native fork `save()` and `restore()` methods. The native Full Simulation explicitly performs sporting child actions without automatic Saved commits; manual Save is a separate boundary. Thus this PR cannot credibly claim a generic improvement to per-match simulation or a 50-season runtime. It can remain as a small, safe optimization, but its merge priority should be based on the tiny observed saving and Work's final independent review.

## Regression and verification plan

`tests/application/test_native_fork_append_copy_performance.py` checks:

- Exact canonical persisted bytes and identical full Saved content hash compared with the old complete-`deepcopy` algorithm.
- A writer envelope through `_append`, including post-write read in a lightweight stub and source integrity.
- Mutation isolation for retained nested Run, Branch, unrelated content and future extension values.
- The discarded prior runtime is not traversed by `deepcopy`.
- A previously absent key cannot cause unrelated component loss.

These are **unit-level checks**. The added `tests/api/test_native_fork_append_sqlite_equivalence.py` is separate real SQLite service-level evidence, including Save/Restore, rollback and replay; it is **not** a full HTTP Save/Restore, heavy workflow or long-season acceptance. The PR stays Draft until independently reviewed and any required broader checks have run.

## Risk and Work review

The critical proof is local: between the original `deepcopy` statement and `canonical_json(payload)`, the writer already overwrote the sole omitted key `KEY` unconditionally. Verify this fact remains true in the exact diff and in every `_append` call site. Verify the helper cannot accidentally omit any other field and the resulting hash and Saved bytes remain identical for real native v2 SQLite input.

This PR does **not** modify #1803 (Saved canonical text/validation), #1804 (MatchEngine) or #1805 (Merkle prototype). If another implementation starts mutating the discarded original runtime *before replacement*, this optimization must be re-reviewed. If an integration test fails on both candidate and `buuk`, compare failure causes, not only labels.
