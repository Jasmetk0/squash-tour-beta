# Manual Draw Save at W16: reproduction, attribution and one removed duplicate (28 November 2026)

Task: [#1940](https://github.com/Jasmetk0/squash-tour-beta/issues/1940), from the
overnight matrix [#1936](https://github.com/Jasmetk0/squash-tour-beta/pull/1936)
run [46076041064](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/46076041064).
Area: the manual Tour Save path only. Not touched: the materialized fork writer
and archives ([#1939](https://github.com/Jasmetk0/squash-tour-beta/issues/1939)),
the live checkpoint transfer of #1907, Tour reads (#1921), match workers, sporting
rules, RNG, schemas, Saved history, configuration and the 120 s HTTP limit.

## Input and exact tree

- Artifact `giant-nov27-snapshots-x64-2-seq-46076041064` (zip SHA-256
  `00d901d4…2be60`, equal to the GitHub artifact digest). `after-W15.sqlite`
  SHA-256 `3f443dd390dab3a97891f04929cbca2e402efdf444f0e5a66cd4d7584593a304`
  equals its `manifest.jsonl`; `PRAGMA quick_check` = `ok`; Run `run`, Branch
  `branch`, Saved HEAD `saved-revision-93c68a95…5d` (95 revisions, 1,040 players,
  opens S1 W16). The original file stayed read-only; every run used a fresh copy
  whose SHA-256 was checked first.
- Tree: the workflow's local merge recipe rebuilt on `buuk 29784d5` gives tree
  `5ee76e2ce92dbef237c4f70484befd2d3915fc13`, identical to `candidate.txt`
  (HEAD differs only in commit metadata). This is arm **A**. Arm **B** = A + this
  PR's commit `e1ded04`. Harness `51dbde8990e0118af9827485ac12d3f27286c3e4`.
- Python 3.11.18 and `fast-ci-linux.lock.txt`: `pip freeze` equals the
  artifact's `dependencies.txt` except `pip` itself. `PYTHONHASHSEED=0`,
  `BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2`, `BETA_ENGINE_MATCH_WORKERS=0`
  (the sequential job). Container: Linux x86-64, 4 vCPU, 15 GiB, nothing else
  running during timed runs.

## What the CI telemetry shows

In the sequential x64 job the last accepted operation was the W16 Draw
(`execute` 201, request 735), then a 200 inspection (736). The Save (737) hit
the client timeout after 120.36 s with 119.18 s process CPU. The harness exited
6.9 s later (`ApiServer.__exit__` joins the server thread for at most 10 s, then
the interpreter ends the daemon thread). The same job's earlier W15 Saves took
72–84 s. A W16 Save follows submit → approve → draw of one Edition.

## Reproduction (real HTTP/SQLite)

`scripts/repro_w16_draw_save.py prepare` replays the harness from the snapshot:
plan W18 + Save, then W16 Edition 1 submit and approve (`pre-draw.sqlite`,
`1052bb55…19e08`), then draw (`pre-save.sqlite`, `8fc9820f…be353`). Deterministic
Saved/audit identities make both arms write comparable bytes.

- **warm**: one process; pre-draw copy, cold inspection, draw, inspection, Save.
- **cold**: a fresh process on the pre-save copy; inspection, Save.

On this machine the same operations are 8–18 % faster than on the CI runner
(W18 Save 69.1 vs 74.6 s, Draw 79.8 vs 93.9 s).

**Commit at timeout.** In arm A, run `warm-4-A`, the client timed out at 120 s
and the server committed at **120.99 s** (`cold-4-A`: 121.0 s). The client had
an uncertain answer although the Saved HEAD had moved. Retrying the identical
request returned `409 expected draft version 97, found 98`; the next inspection
reported `saved=true` and the new HEAD, and exactly one new revision existed.
For the CI job itself the artifacts do not show whether the server committed
within its remaining ~6.9 s: the snapshots stop at W15 and the final database
was not retained. SQLite WAL leaves either the old or the new HEAD, never a partial
revision. The retry path above resolves both.

## Where the Save spends its CPU (arm A, instrumented, attribution only)

Inclusive thread CPU of the Save request only. Nested entries overlap and must
not be summed. Warm and cold Saves perform **identical work**: every function
has the same call count in both cases. The live checkpoint row is 203.6 MB and
the Saved payload is 223.4 MB canonical JSON. Both exceed the 64 MiB live and
global decode caches, so no decode survives between requests.

| Area | warm | cold |
| --- | ---: | ---: |
| Saved HEAD/draft lineage (`_viewer_branch_working_draft_in_session`) | 2.4 s | 2.4 s |
| physical dependency signatures (`actual_dependency_signature`, 92×) | 5.6 s | 5.9 s |
| exact row text hashing (`row_text_sha256`, 359×) | 7.0 s | 7.3 s |
| live checkpoint read + strict decode (`read_checkpoint_for_save`) | 16.1 s | 14.5 s |
| Saved HEAD sources decode (`decoded_global_tour_source`) | 20.3 s | 18.7 s |
| Tour capture incl. origin verification (`capture_tour`) | 18.6 s | 20.6 s |
| full successor replay (`load_saved_calendar_sources`), proof cache missed | 27.4 s | 26.4 s |
| global origins / competition payload verification | 7.1 + 10.4 s | 7.1 + 10.8 s |
| checkpoint/Tour fingerprints (`_replay_fingerprint`, 18×) | 32.1 s | 31.6 s |
| `json.dumps` total / `json.loads` total | 52.7 / 12.5 s | 49.4 / 13.6 s |
| cyclic GC during the request (`gc.callbacks`) | 1.3 s | — |
| flush/write (`Session.flush`) | 4.1 s | 4.4 s |
| **post-commit retention** (`remember_committed_global_sources`) | **10.2 s** | **9.6 s** |

Peak RSS of a Save is 8.0–8.4 GiB; the DB stays 533 MB with a ~19 MB WAL.
#1907: `take_live_calendar_component` runs once per Save and returns `None`,
because it refuses anything above `MAX_LIVE_COMPONENT_BYTES` (64 MiB). At this
scale the transfer never applies. It helps only while the live checkpoint is at
most 64 MiB, as in its own d2/d8 fixtures (17/50 MB).

## The removed duplicate

After a committed manual Tour Save, `remember_committed_global_sources`
canonical-encoded and hashed the complete 223 MB payload (`_value_identity`)
only to learn it exceeds 64 MiB. It then took the component path, which
canonical-encoded the 203 MB checkpoint again, learned that it exceeds 64 MiB
and strictly re-checked the captured value's fingerprint. Nothing was retained
and the caller discarded the result. Before commit, the Save had already computed
`canonical_payload_json = canonical_json(payload)`, inserted it, and compared it
with the flushed row and the decoded receipt payload.

Change (`native_fork_source_projection.py`, call site in `repositories.py`):

- The Save passes that text as `_payload_text`. If it is an ASCII `str` longer
  than the limit, the whole-payload identity is skipped.
- The checkpoint's exact canonical length is derived from the text: the payload
  with only that value replaced by `null` is encoded (every other component,
  once), and the length difference gives the checkpoint's length. If the
  component envelope is also oversize, nothing is retained. This is exactly the
  original decision.
- A fitting payload or component keeps the original identities, keys, copies
  and fingerprint checks. A missing, short or non-ASCII text takes the original
  path.
- The text is never a cache key or a proof. Skipping a retention is always
  safe: every later reader misses and strictly decodes.

On the real W16 value (instrumented check in arm B): text equals
`canonical_json(receipt.payload)` (223,446,331 characters). The derived component
envelope is exactly 203,638,085, equal to the actual one. Both are oversize, as
in the original path. The call took 10.15 s CPU in A and 0.18 s in B (cold:
9.58 → 0.18 s). Call
counts differ only by the removed work: one `_value_identity`, one
`decoded_global_checkpoint_component`, one fingerprint, one `canonical_json`.

## Paired A/B (uninstrumented, separate processes, same input SHA, order A B B A)

| Save (client wall to headers) | A | B |
| --- | --- | --- |
| warm | 112.0 s · **121.3 s timeout** | 102.2 s · 111.6 s |
| cold | 118.4 s · **121.0 s timeout** | 116.8 s · 116.7 s |
| mean of all 4 | 118.2 s | 111.8 s (−6.4 s, −5.4 %) |
| instrumented service time (phases mode, attribution only) | warm 124.6 · cold 122.2 s | warm 110.3 · cold 106.9 s |

An earlier warm A (same tree and input, before the order) took 108.9 s. A/A
spread is ~9 s in the warm case: the whole container slowed during `warm-3-B` and
`warm-4-A` (their Draws took 170/165 s against ~154 s). Normalized by the
same-process inspection GET, warm Save/GET was A 2.78/2.83 against B 2.56/2.49.
The cold case is steadier (B/B 0.1 s, A/A 2.6 s). B succeeded 4/4 under the
unchanged 120 s limit and A 3/5 (counting the earlier warm run). The margin of
B stays thin (≈117 s cold on this faster-than-CI machine), so this PR alone does
not make the CI Draw Save reliable.

All 8 timed runs and both instrumented runs produced the same Saved bytes: head
content hash `cf545ca9…d5a9`, history digest `419c25cf…`, Merkle node digest
`9d4b81a4…`, 97 revisions, 96 audit events, clean draft v98. Each retry of the
identical request after the response returned `409` without a new revision.

## Restart and continuation

`restart` opens a fresh process on each arm's committed post-Save copy (A
`warm-4-A`, the timed-out-but-committed run; B `warm-2-B`). It inspects, checks
the history API and continues with W16 Edition 2: submit, approve, draw and Save.
Both arms saved revision 98 with identical bytes (content hash `dc6a5bb4…`,
history `30fe57a0…`, nodes `a13d1a9b…`, audit `40f34b9f…`) and passed the
harness's full Saved v2 ancestry check. The continuation Save took A 117.8 s and
B 104.0 s.

The first cold `GET /calendar-tour` after a restart took 162–206 s here. This is
a Tour read (#1921 boundary), not Save. Without a longer transport, a client
cannot even inspect the restored W15/W16 state within 120 s. That is a separate
blocker for restart continuation at this scale; this PR does not change it.

## Hand-off to Work: the remaining cost

These are measured costs outside this one removal. Each is either an
authority/proof boundary or owned by another candidate:

1. **Full successor replay despite a fresh post-command proof (≈27 s).**
   `proof_key in _global_working_proofs` misses in both warm and cold Saves.
   The inspection GET just replayed the live owner, but its payload signature
   evidently differs from the Save's captured payload. Making them equal would
   reuse an existing proof and needs an owner review of that boundary.
2. **The same checkpoint fingerprint is computed 18 times (≈32 s).** The value
   is the same, but the objects are distinct copies and decodes. The identity
   memo cannot see that, and value equality would itself be new proof logic.
3. **Two strict decodes of the 203 MB checkpoint (≈20–23 s)**: the live row
   (`read_checkpoint_for_save`) and the Saved HEAD
   (`decode_prevalidated_calendar_sources`). After a Draw the checkpoint is
   unchanged, but the live row is pydantic JSON and the Saved value is canonical
   JSON, so byte equality is not available. Above 64 MiB, #1907 never applies.
4. **The cold first Tour GET exceeds 120 s** (above).

The order 1 → 2 → 3 is my recommendation by size and risk. None of these is
safe to change without the owner's view of the proof boundary.

## Tests (actually run on this branch)

- `tests/infrastructure/test_committed_global_source_oversize.py` (new,
  `pr_critical`). Covers every size boundary, both ownership modes, exact
  derived lengths with escapes/non-ASCII, no complete re-encoding or re-check
  when oversize, the fallback for missing/short/non-ASCII text, and a fitting
  component that is still re-checked and rejected on mismatch. It fails on
  `buuk` sources.
- `tests/api/test_save_committed_oversize_text.py` (new, smoke, real
  HTTP/SQLite/MatchEngine, Saved v1 and v2, forced oversize and fitting). Every
  persisted row and the retained decode cache equal the forced original path.
  It also covers a 409 retry without a new revision, a restart, another
  command and a second Save.
- `tests/infrastructure/test_native_fork_source_projection.py` (existing).

## Reproduction commands

```bash
# exact tree A (as in the #1936 workflow), on buuk 29784d5
git config user.name "Diagnostic build"; git config user.email "diagnostic@example.invalid"
export GIT_AUTHOR_DATE=2026-11-27T22:20:00Z GIT_COMMITTER_DATE=2026-11-27T22:20:00Z
git cherry-pick -x ea9978fb3e41558fef5e9f00778f2cc18cf513ba dfb2e3a0d98bfca700ce1f9d801929ccec2544bf
for pin in 1372c31849e242cc2ca0f0a2d67cd73af04c816f 47beee7a2a999cce7d9fd71aea0412e95b1d56ac 091ac6c79852ddd1fc976c0fff808795703359f5 1935e53555c1f6d3d11481d3e83cb9687bceb3cd 18bf7156cb056e25a5fb22a306609597a2517fd0 b0f135fb83422b220f08ae1863f632e48f01bac6 b5e1ab34fd0574565224f28ac398b1a613cf4d18; do git merge --no-ff --no-edit "$pin"; done
git rev-parse HEAD^{tree}   # 5ee76e2ce92dbef237c4f70484befd2d3915fc13
# arm B: the same tree plus this PR's src commit (e1ded04)

export PYTHONPATH=src:.:tests/api BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2 \
  BETA_ENGINE_MATCH_WORKERS=0 PYTHONHASHSEED=0 REPRO_HARNESS=<harness 51dbde8>/scripts
python scripts/repro_w16_draw_save.py prepare --golden after-W15.sqlite \
  --golden-sha 3f443dd390dab3a97891f04929cbca2e402efdf444f0e5a66cd4d7584593a304 --out runs/prepare
# per arm and case, each in its own process, order A B B A
python scripts/repro_w16_draw_save.py save --case warm --mode timing --retry \
  --input runs/prepare/pre-draw.sqlite --sha 1052bb55e01ebda073d4db960cbcddbfc9661340c5fe72a3316f967a01719e08 --out ab/warm-1-A
python scripts/repro_w16_draw_save.py save --case cold --mode timing --retry \
  --input runs/prepare/pre-save.sqlite --sha 8fc9820fb32f505c16b91cae6bf7ab6001b7c435882dbdcb0986c44ed99be353 --out ab/cold-1-A
# attribution (separate, instrumented): --mode phases [--check-equivalence] or --mode cprofile
python scripts/repro_w16_draw_save.py restart --input ab/warm-2-B/post-save.sqlite --sha <its sha> --out ab/restart-B
```

The `prepare` checkpoints are produced by arm A and serve as the identical input
for both arms. The 5-season matrix was not rerun.
