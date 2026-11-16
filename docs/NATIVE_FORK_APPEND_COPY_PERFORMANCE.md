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

## Regression and verification plan

`tests/application/test_native_fork_append_copy_performance.py` checks:

- Exact canonical persisted bytes and identical full Saved content hash compared with the old complete-`deepcopy` algorithm.
- A writer envelope through `_append`, including post-write read in a lightweight stub and source integrity.
- Mutation isolation for retained nested Run, Branch, unrelated content and future extension values.
- The discarded prior runtime is not traversed by `deepcopy`.
- A previously absent key cannot cause unrelated component loss.

These are **unit-level checks**, not proof of HTTP/SQLite Save, restore, replay, rollback or long-season acceptance. Relevant existing integration tests and a genuine A/B Save/season profile must run and pass before proposing a merge. The PR stays Draft until independently reviewed.

## Risk and Work review

The critical proof is local: between the original `deepcopy` statement and `canonical_json(payload)`, the writer already overwrote the sole omitted key `KEY` unconditionally. Verify this fact remains true in the exact diff and in every `_append` call site. Verify the helper cannot accidentally omit any other field and the resulting hash and Saved bytes remain identical for real native v2 SQLite input.

This PR does **not** modify #1803 (Saved canonical text/validation), #1804 (MatchEngine) or #1805 (Merkle prototype). If another implementation starts mutating the discarded original runtime *before replacement*, this optimization must be re-reviewed. If an integration test fails on both candidate and `buuk`, compare failure causes, not only labels.
