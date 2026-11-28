# Native Tour inspection: full GET read-path measurement and decode change

Issue #1918. Base `buuk` `29784d51d01d9d747705be8abae30f0c82706c1e`. Read path only:
no sporting rule, RNG, schema, Saved writer/reader format, Save, Execute
mechanism, cache budget, timeout, API DTO or workflow changes.

## Inputs

Copies of the genuine Saved v2 backups from the nightly matrix
[45902907173](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45902907173),
artifact `giant-nov26-snapshots-x64-1`. They were written by `buuk 29784d5`
plus the cherry-picked #1905 commits `ea9978f`/`dfb2e3a` and local diagnostic
merges of `72764c4`, `47beee7` (#1875 head) and `091ac6c`; unchanged `buuk`
`29784d5` reads all three through its full strict gates (every GET below is 200).

| snapshot | SHA-256 (manifest = copy) | size | Saved revisions | players | live checkpoint JSON | live Tour JSON |
|---|---|---:|---:|---:|---:|---:|
| after-W09 | `438f70915ff88e23d27cddcfdbe8cd38522d09ac2d46b042f21f1582d03e932c` | 287 MB | 53 | 1 020 | 109.6 MB | 5.2 MB |
| after-W12 | `32d1deae476ece76c4444396874726b9b7994e134db6332b7282e8d92534e16f` | 425 MB | 76 | 1 020 | 161.9 MB | 7.3 MB |
| after-W15 | `d9ddd3f0358627e4029ffa4ab20adcf01f8e65630b74755e3cf2544dee9b3c42` | 533 MB | 95 | 1 040 | 203.6 MB | 9.6 MB |

Each case copies the backup into a fresh empty root; the script checks SHA-256,
`PRAGMA quick_check` (= `ok`), Run `run` / Branch `branch`, `saved_v2.rope.1`,
Saved HEAD, revision count and Tour position on the copy. Originals are
read-only and never opened for writing; no database is committed.

## Where a full GET spends its time

`scripts/profile_native_tour_inspection.py --mode phases` (wall/CPU timers on
named production functions, no profiler), real uvicorn HTTP + SQLite, W9:

| W9 (A = `buuk`), s | after restart | repeated | after draft change | repeated | after Save | repeated |
|---|---:|---:|---:|---:|---:|---:|
| whole GET (client wall) | 66.7 | 11.4 | 15.3 | 18.5 | 11.9 | 12.9 |
| Saved lineage validation | 59.8 | 1.0 | 1.0 | 1.2 | 1.1 | 1.1 |
| Saved checkpoint decode | 0.1¹ | 7.6 | 7.4 | 9.6 | 8.0 | 8.8 |
| live checkpoint/Tour/match rows | 2.7 | 0.4 | 0.4 | 0.8 | 0.5 | 0.5 |
| `native_working_context` | 0.2 | 0.2 | 1.5 | 1.8 | 0.2 | 0.2 |
| `verify_tour_origins` (changed draft only) | – | – | 2.5 | 2.7 | – | – |
| projection + JSON render | 0.5 | 0.5 | 0.6 | 0.6 | 0.6 | 0.6 |

| W15 (B = this branch), s | after restart | repeated | after draft change | repeated | after Save | repeated |
|---|---:|---:|---:|---:|---:|---:|
| whole GET | 169.4 | 19.6 | 37.9 | 38.6 | 20.9 | 20.8 |
| Saved lineage validation | 156.0 | 2.1 | 2.4 | 2.1 | 2.2 | 2.3 |
| Saved checkpoint decode | 0.2¹ | 12.3 | 11.5 | 11.2 | 13.0 | 12.8 |
| `native_working_context` | 0.3 | 0.3 | 3.1 | 3.2 | 0.3 | 0.3 |
| `verify_tour_origins` | – | – | 15.9 | 16.8 | – | – |
| projection + JSON render | 1.2 | 1.0 | 1.1 | 1.3 | 1.1 | 1.2 |

¹ The cold read reuses the checkpoint its own lineage replay just built.
The response body is 5.38 MB at W9 and 9.80 MB at W15. Process CPU equals wall
within 0.1 s for every request (single-threaded CPU-bound work). Peak RSS of
the sequence is 3.97 GB at W9 and 7.41–7.46 GB at W15 in both arms (set by the
cold read), SQLite main file unchanged in size, WAL 10.5 MB / 19.4 MB after
the sequence in both arms.

* **After a restart** the GET is the physical Saved lineage prevalidation
  (`_prevalidate_cold_global_lineage`, 60–64 s of 67–72 s). This is the Saved
  storage layer, not the Tour read; see *Findings for other owners*.
* **Every warm GET** (repeated, after a Working Draft change, after Save)
  spends 65–70 % in one step: strictly decoding the Saved HEAD's v13 sporting
  checkpoint (`decoded_global_checkpoint_component`). Its 110–204 MB component
  never fits the 64 MiB value cache, so it is decoded again on every read and
  grows linearly with history.
* The projection itself (`_project_inspection`) is ≈0.5 s at W9: readiness
  0.04 s, current lifecycle 0.025 s, Edition results 0.035 s, groups and
  next slot < 0.01 s, JSON render 0.05 s; the rest is the `state` dump and
  the player list. The response body is 5.38 MB.

Decode steps measured directly on the W9 HEAD (cyclic GC paused as in the GET):

| step | s |
|---|---:|
| `canonical_json` of the whole component only to learn that it exceeds the cache | 1.22 |
| `json.dumps(state)` of the payload's own decoded state | 1.14 |
| `json.loads` of that same text | 0.50 |
| `json.dumps` of each part for the strict JSON validator | 1.02 |
| strict `model_validate_json` of all parts | 2.74 |
| outer model validation | 0.41 |
| canonical fingerprint of the decoded model (scope/hash check) | 1.83 |

## Change

`decode_prevalidated_calendar_sources` (its `_repository` branch, called only by
`CalendarTourService._context`) decoded the authenticated payload's state by
`parse_checkpoint_json(json.dumps(state))`: the same body built twice inside one
verified read. `parse_checkpoint_json(None, _decoded=state)` now starts from the
decoded body when `decoded_checkpoint_body(state)` proves the round trip cannot
change what the v13 parser reads (exact `dict`, string keys, a `list` of
events, scalar remaining top-level fields; nested parts are re-encoded by the
parser itself either way). Every part is still encoded and strictly validated,
the outer validator, the fingerprint/scope check, the Saved lineage gate and
every live comparison are unchanged; any other body keeps the round trip.
On the real W9 HEAD both paths give an equal model, byte-identical
`model_dump_json` (109.6 MB) and the declared fingerprint.

This also benefits Preview/Execute, which assemble the same context.

## A/B

Same host (4 vCPU Intel Xeon 2.30 GHz, 15.7 GiB, Linux, Python 3.11.18 venv with the
`pyproject` dependencies: FastAPI 0.165, SQLAlchemy 2.1.9, Pydantic 2.14.4),
`PYTHONHASHSEED=0`, `saved_v2`, one fresh interpreter and one fresh copy per
case, alternating order (W9: A B C B A C, W15: A B B A; C = #1829). Scenario
`states`: restart GET, repeat, Preview + confirmed Execute of the next real
harness command (`create-edition` of the next planned Edition), two GETs,
explicit Save, two GETs, then the first GET in a new process. A low-priority
(`nice 19`) test run overlapped W9 runs 3–6 and W15 runs 1–2.

Median (min–max), seconds, n = 2 per arm:

| W9 | A `29784d5` | B `c980cb9` | Δ |
|---|---:|---:|---:|
| GET after restart | 69.48 (68.96–70.01) | 69.27 (68.70–69.84) | −0.3 % |
| GET repeated | 12.52 (12.13–12.92) | 11.21 (11.13–11.30) | −10.5 % |
| Preview | 12.30 (12.23–12.37) | 9.90 (9.81–9.99) | −19.5 % |
| Execute | 32.99 (32.56–33.42) | 27.94 (27.09–28.78) | −15.3 % |
| GET after draft change | 17.68 (17.52–17.84) | 15.53 (15.33–15.74) | −12.1 % |
| GET repeated | 17.59 (17.44–17.73) | 14.99 (14.33–15.64) | −14.8 % |
| Save | 28.04 (27.64–28.43) | 27.05 (26.36–27.74) | −3.5 % |
| GET after Save | 11.98 (11.34–12.63) | 10.34 (10.19–10.49) | −13.7 % |
| GET repeated | 11.75 (11.54–11.97) | 10.49 (10.26–10.72) | −10.8 % |
| GET after restart (new process) | 70.21 (69.76–70.66) | 68.87 (67.02–70.72) | −1.9 % |
| whole sequence (one run each shown) | 218.8 | 204.0 | −6.8 % |

| W15 | A | B | Δ |
|---|---:|---:|---:|
| GET after restart | 170.80 (168.88–172.72) | 166.51 (163.87–169.16) | −2.5 % |
| GET repeated | 22.28 (21.97–22.59) | 19.12 (18.93–19.31) | −14.2 % |
| Preview | 21.75 (20.22–23.29) | 19.67 (19.38–19.97) | −9.6 % |
| Execute | 67.53 (67.02–68.04) | 58.64 (58.20–59.08) | −13.2 % |
| GET after draft change | 40.21 (40.03–40.38) | 35.56 (34.54–36.57) | −11.6 % |
| GET repeated | 40.68 (38.31–43.05) | 36.03 (34.27–37.78) | −11.4 % |
| Save | 66.65 (66.16–67.13) | 69.60 (68.56–70.64) | **+4.4 %** |
| GET after Save | 24.69 (24.62–24.75) | 20.30 (19.82–20.79) | −17.8 % |
| GET repeated | 24.14 (23.99–24.29) | 20.16 (19.33–20.98) | −16.5 % |
| GET after restart (new process) | 164.63 (164.19–165.08) | 165.03 (160.57–169.49) | +0.2 % |
| whole sequence | 476.8 / 488.6 | 449.4 / 449.6 | −6.8 % |

* Every warm read is 1.3–2.6 s faster at W9 and 3.2–4.7 s at W15: the saving
  grows with history, as the decoded component does. Arm ranges do not overlap.
  The cold read is unchanged (it does not take this path).
* **Save at W15 is ~3 s slower in B.** Save does not execute the changed
  branch (its decoder call passes no `_repository`), so the code it runs is
  identical; the difference is most likely process heap/GC state left by the
  preceding reads (the same pattern #1907 reported). Not proven; W9 Save is
  1 s faster in B.
* **Correctness:** in all 10 states runs the final inspection digest
  (W9 `4489c91d9fbb…`, W15 `b8b81e27f3cf…`), the inspection after restart,
  the live checkpoint, Tour and lifecycle row digests, the Saved revision count
  and kinds (54 / 96) and the audit event count and kinds (53 / 95) are
  identical across A, B and C. Saved revision IDs are deterministic.

## Separate diagnostic arm: request count (late week W16)

One complete next real week from the W15 backup (S1 W16 → W17): planning of
the W18 Edition, two 8-entrant W16 Editions (submit, approve, draw), three
global slots with 14 real MatchEngine matches, two result confirmations and
the Week Transition, each with Preview, explicit confirmation and an explicit
Save (9 Saves), then a GET in a new process. `--variant harness` issues exactly
the request sequence of the unchanged `tests.api.test_calendar_tour_flow`
helpers as `giant_native_five_season_load.py` uses them (38 GETs: 1 after
restart + 37 in the week, 13 Previews, 14 Executes including the transition
idempotency retry, 9 Saves). `--variant minimal` keeps every Preview,
confirmation, Execute, the idempotency retry and every Save, but reads each
distinct state once: Execute uses `include_inspection` (its inspection cost is
charged to Execute) and one GET follows each Save (9 in-week GETs). The
official harness, its idempotency checks and the nightly workflow are
unchanged. One run per arm (≈ 40–60 min each); A-minimal was not run.

| s (week only, without the first GET after restart) | A harness | B harness | B minimal |
|---|---:|---:|---:|
| in-week GETs | 37 → 1 203.8 | 37 → 1 061.6 | 9 → 206.1 |
| Preview (13) | 358.1 | 313.6 | 316.4 |
| Execute (14) | 1 062.9 | 973.3 | 1 004.6 |
| Save (9) | 739.5 | 698.1 | 733.2 |
| **whole week** | **3 372.2** | **3 053.7** | **2 266.0** |
| GET after restart / in new process | 165.4 / 189.5 | 160.7 / 194.6 | 165.6 / 177.8 |

* **Engine saving** (A → B, identical request sequence): −318.5 s (−9.4 %)
  for the week; in-week GETs −142.2 s (−11.8 %), Preview −12.4 %, Execute
  −8.4 %, Save −5.6 %.
* **Request-count saving** (B harness → B minimal, identical engine):
  −787.7 s (−25.8 %): 28 fewer GETs save 855.5 s; Execute's 13 included
  inspections cost +31.3 s; Save +35.1 s with identical Save requests
  (variance/heap state, not request work).
* Together A harness → B minimal: −1 106.2 s (−32.8 %).
* GETs before each Save (changed draft) average 51.2 s (A) / 47.5 s (B);
  `verify_tour_origins` dominates them (finding 2).
* All three runs: final inspection `8a0efca864f5…`, inspection after restart
  equal, checkpoint/Tour/lifecycle digests, 104 Saved revisions and 103 audit
  events (same kinds) identical: the Saved ID sequence is the same, so equal
  digests are equal sporting results, Saves and audit.
* Peak RSS 8.70–8.83 GB in every arm (above the 8 GB reference PC), WAL
  462 MB, SQLite main file 601 MB after the week.

## #1829 measured separately

Temporary tree `buuk 29784d5` + merge of the #1829 head `e524ccb` (`a762bde`,
never pushed), same script and copies, runs 3 and 6 above. Against A it is
within noise in both directions (repeat 11.98 vs 12.52 s, after Save 12.51 vs
11.98 s, after draft change 17.28 vs 17.68 s). This matches the phase timers:
its targets (both readiness evaluations, the per-match slot scan, the
tournament and counted-result lookups) cost < 0.1 s together at W9 inside a
0.5 s projection. Its patch is therefore **not** carried into this branch; it
remains independently reviewable in #1829, with full-response equivalence
already identical here (final digest `4489c91d9fbb…`).

## Findings for other owners (measured, not changed here)

1. **Cold read after restart (Saved storage / lineage, #1875 owner).**
   60–64 s at W9 and 156 s at W15 in `_prevalidate_cold_global_lineage`
   (cProfile W9: `_to_branch_saved_revision` 35 s over 54 revisions,
   `load_saved_calendar_sources` 31 s, `verify_competition_payload` 21 s,
   canonical-text proofs 11 s, MatchEngine re-simulation of accepted slots
   5 s). The W15 cold read alone exceeds the harness's 120 s client timeout.
2. **Origin verification on every changed-draft read (shared verifier).**
   `verify_tour_origins` grows from 2.5 s (W9) to 16 s (W15). For each of the
   14 played Editions it loads the played Saved revision row (2.9 s), hashes
   its text (2.5 s) and `json.loads` the whole 100–200 MB payload (5.9 s, cProfile)
   only to read that revision's Tour component and run calendar. The 32 MiB
   cross-request origin-projection budget holds ~3 of the ~9 MB projections,
   and the per-walk `(row digest, Edition) → frozen pre-play authority` memo
   is deliberately not retained. The same function is the Saved lineage gate's,
   Save's, the native fork's and the appended-slot verifier's, so it is not
   changed here. Candidates for its owner: retain that tiny frozen authority
   per exact row digest within the existing bound, or skip Editions whose
   authority equals the verified Saved prefix and gain no new terminal clock.
3. **Value-cache size probe (projection cache, #1907 owner).** For an
   oversize component `_decoded_value` serializes the whole component with
   `canonical_json` (1.2 s at W9) only to learn that it cannot be cached.
4. **Warm reads lose the head text proof (repository lineage).**
   `_saved_head_payload_proof` exists only after a cold validation; with it the
   checkpoint decoder could use proven spans instead of re-encoding parts.
5. **No cross-request reuse of the decoded Saved checkpoint.** The 64 MiB
   budget is below every nightly snapshot's component, so the strict decode
   (≈5 s at W9, ≈9 s at W15 after this change) repeats on every read of an
   unchanged HEAD. Retaining it would cost hundreds of MB to GBs of heap against
   an 8 GB reference PC with a 7.4 GB peak already at W15; that budget is an
   owner decision, not a read-path change.
6. **`working_proof_signature`** hashes the complete candidate payload
   (1.4 s at W9, ~3 s at W15) on every changed-draft read; it is also Save's
   proof key.

## Reproduce

```bash
PYTHONHASHSEED=0 BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2 python scripts/profile_native_tour_inspection.py \
  --input after-W09.sqlite --sha256 438f70915ff88e23d27cddcfdbe8cd38522d09ac2d46b042f21f1582d03e932c \
  --root <fresh-empty-dir> --out result.json --scenario states --mode timing
```

`--scenario week --variant harness|minimal` replays the next complete giant
week; `--mode phases|profile|alloc` are separate diagnostic runs (states runs
used script `b8ddd80`, the week runs `b0f135f`; the states code path is the
same). A = `29784d5` + the identical script file, B = `c980cb9` (engine
change; later commits only touch the script, tests and this document),
C = `29784d5` + #1829 `e524ccb`. Not measured: the W12 backup, the
allocation (`alloc`) mode, A-minimal, and any multi-season or giant run. Saved revision
IDs come from the same deterministic factory as `scripts/profile_native_week_ab.py`,
so A and B history digests compare directly.
