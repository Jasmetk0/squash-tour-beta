# Manual Tour Save: live checkpoint copy (26 November 2026)

Task: [owner comment in #1905](https://github.com/Jasmetk0/squash-tour-beta/pull/1905#issuecomment-7195363786).
Area: the copy of the **current live checkpoint** in the manual Tour Save.
Not touched: dependency graphs and Saved v2 storage (#1875), appended-increment
verification and the Full Simulation worker (#1901/#1905), sporting rules,
RNG, schemas, history, configuration and the 120 s HTTP limit.


## Revision 27 November 2026: exclusive transfer inside the writer transaction

Work's review of `72764c4` reproduced that `decoded_live_calendar_component`
held the retained model past the cache lock and copied it afterwards, while
`take_live_calendar_component` could hand that same object to a Save as
"private"; after a committed Save the reinstalled value was also referenced by
the global decode cache. That proves shared references, not a corrupted
database. The candidate is now:

- **Pins.** A reader pins the retained entry (under the repository lock) while it
  copies it outside the lock, and unpins it afterwards.
- **Transfer only when exclusive, inside the Save transaction.**
  `read_checkpoint_for_save(take_live=True)` (manual Tour Save only) hashes the
  complete actual row and calls `take_live_calendar_component` with that digest.
  An entry is transferred only if it is unpinned and not `shared`; it leaves the
  cache under the lock, so no later reader can reach it. Its retained Run/Branch
  and value fingerprint must equal the row's, otherwise it is dropped and the
  original decode reports any mismatch.
- **Shared after commit.** A committed value returns to the live cache marked
  `shared`, because the global decode cache owns it too. It is never transferred
  again; such bytes take the copying path.
- **A1 removed.** The decode before `BEGIN IMMEDIATE` cost an extra row read,
  full hash and copy on a cold miss or changed bytes (+5–8 % per Save). A miss is
  now exactly the original path: one row read, one digest, one strict decode.

The sections below describe the superseded 26 November candidate (A1 + A2) and
its measurements; the new A/B is in "A/B of the 27 November candidate".

## A/B of the 27 November candidate

Container, 4 vCPU Xeon 2.30 GHz, 15 GiB, Python 3.12.3 (lock `fast-ci-linux`),
`PYTHONHASHSEED=0`, `BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2`, nothing else
running. Order A B B A per depth, every run a fresh backup of the pinned fixture
in its own process, restart as a fresh spawned process, script
`scripts/profile_native_save.py` (SHA-256 `0fb10cb6…`) in both trees.

- A = `buuk 29784d5` (`src` `494a35ec`) + this script.
- B = this branch `7b38b5e` (`src` `e23f7a3e`; `buuk 29784d5` merged in).

Fixtures were made again on `buuk 29784d5` with
`profile_native_week_ab.py prepare --slot-depth N` from #1895 (`45893e5`):
d2 `d97f1931e85217f0813196fd2cd6d8f7a117e3b3a1276e44848ced13044b47ca`
(25 → 28 revisions, live checkpoint 16.9 MB) and d8
`da01e094107b55cbb49b7cc4eec8704d9b59c67271515d699783d5138491358a`
(live checkpoint 49.8 MB). History digest, live checkpoint fingerprint and bytes
were identical in all eight runs (d2 `d9113dfe…`, d8 `e7e7700a…`).

Medians (n = 2 + 2), Save wall / writer lock:

| | d2 A → B | d8 A → B |
| --- | --- | --- |
| warm Save | 4.62 → 4.07 s (−12 %), lock 3.48 → 3.01 (−13 %) | 14.40 → 13.70 s (−5 %), lock 10.70 → 10.14 (−5 %) |
| Save after restart | 5.37 → 4.40 s (−18 %), lock 4.08 → 3.15 (−23 %) | 14.97 → 13.23 s (−12 %), lock 11.18 → 9.84 (−12 %) |
| cold miss | 5.71 → 6.16 s (+8 %), lock 4.41 → 4.79 | 18.37 → 20.39 s (+11 %), lock 14.33 → 16.02 |
| GET after warm Save | 1.73 → 1.92 s | 5.42 → 6.04 s |
| first GET after restart | 17.72 → 17.08 s | 57.40 → 58.52 s |
| peak RSS | 1 052 → 1 071 MiB | 2 612 → 2 609 MiB |

The cold-miss path executes exactly the original work. Separate `calls` runs on
d8 (A and B concurrently, so absolute times are inflated) count, per cold Save:
`read_checkpoint_for_save` 1, `decoded_live_calendar_component` 2,
`parse_checkpoint_json` 2, `_value_identity` 3, `remember_committed_global_sources`
1 in both trees; B adds one `take_live_calendar_component` (0.00 s). There the
cold Save took 18.20 s (A) and 18.35 s (B) and the warm Save 14.19 → 12.70 s.
The sequential +2 s is therefore not additional work in the cold path. My
tentative explanation is a different position of cyclic garbage collection after
the warm Save, which allocated less. That is not proven, and the cold-miss
result stays a limitation. Compared with the 26 November candidate (G), the
warm saving is smaller (G also decoded before the lock), and the cold miss no
longer reads, hashes and decodes twice.

## What the Save did before

`save_viewer_branch_selection_atomically` (native Tour Save) runs inside
`BEGIN IMMEDIATE`, i.e. under the SQLite writer lock. There,
`read_checkpoint_for_save` read the live
`calendar_player_sporting_checkpoints` row and called
`decoded_live_calendar_component`:

- **warm hit** (the usual case after the draft GET): a defensive
  `deepcopy` of the retained private decode of exactly these bytes;
- **cold miss** (evicted or not yet decoded): strict parse, plus the copy
  that the cache retains.

That private model is then captured into the new payload. After a successful
commit, `remember_committed_global_sources(..., _take_ownership=True)` hands
it to the global decode cache without another copy. Within one Save the
inclusive cost splits into three parts (calls mode, see below):

- the read-side copy or parse (`decoded_live_calendar_component`, called via
  `read_checkpoint_for_save`);
- hashing the whole current value: `_value_identity` (canonical JSON of the
  complete payload or component) and the canonical hash of the captured
  component;
- the post-commit handoff (`remember_committed_global_sources`), which runs
  outside the lock.

`_checkpoint_for_capture` only re-reads and re-hashes the row. It does not
copy.

## Change (two parts, both kept)

1. **A1. Prepare outside the writer lock.** `prepare_checkpoint_for_save` reads
   the live row in an ordinary read snapshot before `BEGIN IMMEDIATE` and
   produces a private value. Inside the writer transaction,
   `read_checkpoint_for_save` re-reads the actual row and uses that value only
   if all of the following hold. Otherwise it discards the value and runs the
   original strict decode.
   - Run/Branch are the same (both the stored scope and the model's own
     `run_id`/`branch_id`);
   - the fingerprint column is the same;
   - the SHA-256 of the **complete current payload bytes** is the same.

   The value can be taken only once. The column or digest alone never
   authorises anything.
2. **A2. Ownership instead of a copy.** On a warm hit, prepare does not copy:
   it removes the retained entry for exactly these bytes from the live cache
   (`take_live_calendar_component`, under the repository lock). Only the Save
   coordinator holds it from then on. Concurrent readers miss and decode the
   row themselves. The value goes back into the live cache
   (`reinstall_live_calendar_component`) **only after a successful commit**,
   and only if the Save used this value and the committed component
   fingerprint equals the row fingerprint recorded with the value. In that
   case the global and the live decode cache own the same model. Both return
   only defensive copies, so no reader can reach it. A rollback, a declined
   value or a mismatch drops it: the next reader decodes again.

Who can mutate the value: while taken, only the Save coordinator. Save uses it
read-only, which is the existing `_take_ownership` contract of the global
handoff: the coordinator transfers models it never exposed. A regression test
mutates a nested `result.sets_won` of the taken value. The Save is then
rejected by the unchanged replay (409). Nothing is written, nothing returns to
the cache, and the next reader decodes the unchanged row.

Every other Save gate is unchanged and independent of where the value came
from:

- draft version and status, read-only/active Branch, Viewer target, Saved
  HEAD, physical lineage/ancestry;
- `capture_*` of every live component, the complete-payload proof key or full
  replay;
- flushed-byte receipt checks, origins/terminal/closure gates;
- install/append assertions.

No new positive proof is published; existing ones are still published only
after commit.

## Measurement

**Environment:** this container. 4 vCPU Intel Xeon @ 2.30 GHz, 16 GiB RAM,
Linux 6.18, Python 3.11.18, Pydantic 2.14.4, SQLAlchemy 2.1.9,
`PYTHONHASHSEED=0`, `BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2`. Saved and
audit IDs are deterministic. Every run uses a fresh SQLite backup of the same
pinned fixture, in a separate process; each restart is a fresh spawned
process. Timing runs ran one at a time with nothing else running and without
instrumentation, apart from the writer-lock clock: SQLAlchemy
`before_cursor_execute`/`commit`/`rollback` listeners measure each actual
`BEGIN IMMEDIATE` until its end.

**Fixtures:** `scripts/profile_native_week_ab.py prepare --slot-depth N` from
#1895, run on `buuk f00f64a`:

| | SHA-256 | revisions | matches | live checkpoint |
|---|---|---:|---:|---:|
| d2 | `4326f0ff98929931a0142fa4babab00fde6d766345bf5a0bce3085665055f2bb` | 25 → 28 | 14 → 21 | 16.9 MB at the end |
| d8 | `de1896ce6c764fe0a40eafa100c82793b10b7cc300863274599683507ac89bfd` | 67 → 70 | 56 → 63 | 49.8 MB at the end |

#1905 used `88727b8f…`/`f83fd637…` and #1895 used `e4ace375…`/`347fcbf7…`.
Both were produced from older source trees, so their bytes differ. The
scenario itself is identical: W52, 16 players, the same measured week. Their
CPU was 2.1 GHz.

**Plan** (`scripts/profile_native_save.py --slot-plan`). The measured week's
three next-slot commands, each followed by GET → explicit POST Save → GET ×2:

1. **warm**: Save directly after its draft GET in the same process (cache hit);
2. **cold miss**: the process-local decode-value caches are emptied after the
   draft GET, which is exactly the state eviction leaves. No row or proof is
   touched;
3. **after restart**: the process exits with the dirty draft; a fresh process
   runs GET, GET, Save, GET, GET.

The final inspection and every Saved revision envelope/content hash are
compared across all runs.

```
cd <checkout>   # clean, committed src; PYTHONPATH must be <checkout>/src
PYTHONHASHSEED=0 BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2 PYTHONPATH=$PWD/src \
  python scripts/profile_native_save.py --slot-plan --input work/slots-d8.db \
  --input-sha256 de1896ce6c764fe0a40eafa100c82793b10b7cc300863274599683507ac89bfd \
  --root work/t-d8-1-A [--mode calls]
```

**Trees** (source tree in brackets):

- A = `buuk f00f64a` + script `5718d48` (`d24d8e30`);
- B = A1 only `2d28283` (`017e49af`);
- E = an A1+A2 draft without the fingerprint guard (local, `24d40e0`);
- G = final candidate `d4e35fd` (`bc81bb34`);
- C = A + exact #1905 HEAD `dfb2e3a` (local merge `adc67aa`, `5cfad473`);
- D = C + A1 (`53cd7c3`);
- F = C + final (`032923e`, `8215ed16`).

Order: A B E E B A, A G G A, C D D C (d2) and C F F C.

Results are identical in all 38 runs. Final inspection: d2 `b5002d885a12…`,
d8 `e1ad5c1b1990…`. Complete history digest: d2 `107d703d6bc2…`,
d8 `66710ce8378c…`. Live checkpoint bytes are identical too.


#### d2: current buuk base (A = buuk + script, B = A1, E = A1+A2 draft, G = final)

| run | Save warm: wall / CPU / lock | cold miss | after restart | 1st/2nd GET after warm Save | restart 1st/2nd GET | 3× next-slot | peak RSS MiB | max DB+WAL MB | inspection | history |
|---|---|---|---|---|---|---|---:|---:|---|---|
| t-d2-1-A | 4.22 / 4.21 / 3.14 | 5.07 / 5.07 / 3.75 | 4.22 / 4.22 / 3.15 | 1.91 / 1.53 | 14.49 / 3.52 | 9.6 · 10.1 · 10.4 | 1227 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-2-B | 3.91 / 3.92 / 2.43 | 5.45 / 5.45 / 2.23 | 4.97 / 4.95 / 3.06 | 1.78 / 1.48 | 14.97 / 3.55 | 9.6 · 9.4 · 10.6 | 1202 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-3-E | 3.50 / 3.49 / 2.55 | 5.61 / 5.62 / 2.42 | 3.66 / 3.67 / 2.63 | 1.62 / 1.48 | 14.86 / 3.09 | 10.0 · 10.6 · 10.3 | 1170 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-4-E | 3.92 / 3.92 / 2.84 | 6.07 / 6.08 / 2.80 | 4.01 / 4.02 / 2.86 | 1.91 / 1.82 | 14.27 / 3.29 | 9.7 · 10.6 · 11.3 | 1235 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-5-B | 4.38 / 4.38 / 2.73 | 5.11 / 5.13 / 2.13 | 4.55 / 4.55 / 2.79 | 2.05 / 1.82 | 14.78 / 3.67 | 10.9 · 10.6 · 11.2 | 1227 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-6-A | 4.16 / 4.16 / 3.04 | 4.65 / 4.67 / 3.58 | 4.56 / 4.57 / 3.45 | 2.00 / 1.48 | 14.04 / 3.06 | 10.2 · 9.0 · 9.6 | 1236 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-g1-A | 3.65 / 3.65 / 2.74 | 5.05 / 5.06 / 3.77 | 4.12 / 4.13 / 3.08 | 1.59 / 1.54 | 13.60 / 3.17 | 8.9 · 9.0 · 10.1 | 1228 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-g2-G | 3.22 / 3.22 / 2.34 | 5.69 / 5.68 / 2.54 | 3.49 / 3.50 / 2.51 | 1.59 / 1.65 | 13.38 / 2.97 | 8.9 · 9.6 · 9.8 | 1227 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-g3-G | 3.34 / 3.34 / 2.29 | 4.95 / 4.96 / 2.16 | 3.68 / 3.69 / 2.66 | 1.75 / 1.68 | 14.57 / 3.26 | 9.0 · 9.0 · 10.1 | 1227 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-g4-A | 3.71 / 3.71 / 2.81 | 5.52 / 5.54 / 4.24 | 4.77 / 4.79 / 3.48 | 1.68 / 1.46 | 15.10 / 3.49 | 8.8 · 9.0 · 10.5 | 1227 | 93 | b5002d885a12 | 107d703d6bc2 |

#### Medians d2 buuk

| | A → B | A → E | A → G |
|---|---|---|---|
| warm wall | 3.93 → 4.14 s (+5 %) | 3.93 → 3.71 s (-6 %) | 3.93 → 3.28 s (-17 %) |
| warm CPU | 3.93 → 4.15 s (+5 %) | 3.93 → 3.70 s (-6 %) | 3.93 → 3.28 s (-17 %) |
| warm writer lock | 2.92 → 2.58 s (-12 %) | 2.92 → 2.69 s (-8 %) | 2.92 → 2.32 s (-21 %) |
| cold miss wall | 5.06 → 5.28 s (+4 %) | 5.06 → 5.84 s (+15 %) | 5.06 → 5.32 s (+5 %) |
| cold miss CPU | 5.07 → 5.29 s (+4 %) | 5.07 → 5.85 s (+15 %) | 5.07 → 5.32 s (+5 %) |
| cold miss writer lock | 3.76 → 2.18 s (-42 %) | 3.76 → 2.61 s (-31 %) | 3.76 → 2.35 s (-37 %) |
| after restart wall | 4.39 → 4.76 s (+8 %) | 4.39 → 3.83 s (-13 %) | 4.39 → 3.58 s (-18 %) |
| after restart CPU | 4.40 → 4.75 s (+8 %) | 4.40 → 3.85 s (-12 %) | 4.40 → 3.59 s (-18 %) |
| after restart writer lock | 3.30 → 2.92 s (-11 %) | 3.30 → 2.75 s (-17 %) | 3.30 → 2.58 s (-22 %) |
| GET after warm Save wall | 1.79 → 1.92 s (+7 %) | 1.79 → 1.77 s (-1 %) | 1.79 → 1.67 s (-7 %) |
| GET after warm Save CPU | 1.80 → 1.92 s (+7 %) | 1.80 → 1.77 s (-1 %) | 1.80 → 1.67 s (-7 %) |
| first GET after restart wall | 14.27 → 14.87 s (+4 %) | 14.27 → 14.57 s (+2 %) | 14.27 → 13.98 s (-2 %) |
| first GET after restart CPU | 14.27 → 14.88 s (+4 %) | 14.27 → 14.57 s (+2 %) | 14.27 → 13.99 s (-2 %) |
| peak RSS | 1228 → 1214 MiB | 1228 → 1202 MiB | 1228 → 1227 MiB |

#### d2: buuk + exact #1905 (C), C + A1 (D), C + final (F)

| run | Save warm: wall / CPU / lock | cold miss | after restart | 1st/2nd GET after warm Save | restart 1st/2nd GET | 3× next-slot | peak RSS MiB | max DB+WAL MB | inspection | history |
|---|---|---|---|---|---|---|---:|---:|---|---|
| t-d2-c1-C | 3.65 / 3.65 / 2.75 | 5.24 / 5.25 / 4.07 | 4.18 / 4.18 / 3.01 | 1.61 / 1.41 | 14.35 / 3.40 | 7.8 · 6.8 · 7.3 | 1088 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-c2-D | 3.70 / 3.71 / 2.30 | 4.60 / 4.61 / 1.99 | 4.17 / 4.19 / 2.53 | 1.61 / 1.32 | 14.30 / 2.99 | 7.8 · 7.3 · 7.5 | 1086 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-c3-D | 4.08 / 4.06 / 2.66 | 5.14 / 5.14 / 2.21 | 4.81 / 4.79 / 2.97 | 1.52 / 1.52 | 13.56 / 3.50 | 7.7 · 7.4 · 7.6 | 1080 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-c4-C | 4.20 / 4.17 / 3.14 | 4.54 / 4.56 / 3.50 | 4.05 / 4.06 / 3.03 | 1.53 / 1.58 | 13.62 / 3.02 | 6.9 · 7.6 · 7.1 | 1071 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-f1-C | 4.15 / 4.15 / 3.12 | 4.99 / 5.00 / 3.73 | 4.56 / 4.57 / 3.24 | 1.82 / 1.61 | 13.52 / 3.15 | 8.0 · 7.6 · 8.6 | 1078 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-f2-F | 3.32 / 3.31 / 2.40 | 4.66 / 4.68 / 2.02 | 4.24 / 4.24 / 3.05 | 1.51 / 1.45 | 14.95 / 3.30 | 7.1 · 6.8 · 7.5 | 1104 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-f3-F | 3.15 / 3.16 / 2.29 | 4.61 / 4.63 / 2.00 | 4.09 / 4.09 / 2.95 | 1.42 / 1.37 | 12.90 / 2.89 | 7.3 · 6.5 · 7.9 | 1089 | 93 | b5002d885a12 | 107d703d6bc2 |
| t-d2-f4-C | 3.67 / 3.68 / 2.73 | 4.59 / 4.60 / 3.54 | 4.50 / 4.51 / 3.34 | 1.56 / 1.42 | 13.98 / 3.28 | 7.9 · 6.5 · 7.2 | 1063 | 93 | b5002d885a12 | 107d703d6bc2 |

#### Medians d2 combination

| | C → D | C → F |
|---|---|---|
| warm wall | 3.91 → 3.89 s (-1 %) | 3.91 → 3.23 s (-17 %) |
| warm CPU | 3.92 → 3.88 s (-1 %) | 3.92 → 3.23 s (-17 %) |
| warm writer lock | 2.93 → 2.48 s (-15 %) | 2.93 → 2.34 s (-20 %) |
| cold miss wall | 4.79 → 4.87 s (+2 %) | 4.79 → 4.64 s (-3 %) |
| cold miss CPU | 4.80 → 4.87 s (+1 %) | 4.80 → 4.65 s (-3 %) |
| cold miss writer lock | 3.64 → 2.10 s (-42 %) | 3.64 → 2.01 s (-45 %) |
| after restart wall | 4.34 → 4.49 s (+3 %) | 4.34 → 4.17 s (-4 %) |
| after restart CPU | 4.35 → 4.49 s (+3 %) | 4.35 → 4.17 s (-4 %) |
| after restart writer lock | 3.14 → 2.75 s (-12 %) | 3.14 → 3.00 s (-4 %) |
| GET after warm Save wall | 1.59 → 1.57 s (-1 %) | 1.59 → 1.46 s (-8 %) |
| GET after warm Save CPU | 1.60 → 1.56 s (-2 %) | 1.60 → 1.47 s (-8 %) |
| first GET after restart wall | 13.80 → 13.93 s (+1 %) | 13.80 → 13.93 s (+1 %) |
| first GET after restart CPU | 13.81 → 13.93 s (+1 %) | 13.81 → 13.90 s (+1 %) |
| peak RSS | 1074 → 1083 MiB | 1074 → 1096 MiB |

#### d8: current buuk base (A = buuk + script, B = A1, E = A1+A2 draft, G = final)

| run | Save warm: wall / CPU / lock | cold miss | after restart | 1st/2nd GET after warm Save | restart 1st/2nd GET | 3× next-slot | peak RSS MiB | max DB+WAL MB | inspection | history |
|---|---|---|---|---|---|---|---:|---:|---|---|
| t-d8-1-A | 13.07 / 13.10 / 9.38 | 15.25 / 15.29 / 11.85 | 13.74 / 13.78 / 10.03 | 5.29 / 6.35 | 50.39 / 10.40 | 28.0 · 32.3 · 33.0 | 2800 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-2-B | 14.19 / 14.21 / 8.84 | 18.37 / 18.40 / 7.93 | 13.44 / 13.45 / 8.09 | 5.53 / 7.13 | 50.25 / 9.55 | 29.0 · 30.8 · 33.8 | 2675 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-3-E | 10.44 / 10.47 / 7.27 | 16.62 / 16.68 / 7.06 | 12.38 / 12.42 / 9.31 | 5.14 / 6.06 | 50.13 / 10.42 | 27.5 · 32.0 · 32.9 | 2703 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-4-E | 10.29 / 10.32 / 7.51 | 16.75 / 16.77 / 7.39 | 11.92 / 11.94 / 8.92 | 4.96 / 6.19 | 51.96 / 10.13 | 29.6 · 30.4 · 32.2 | 2799 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-5-B | 13.99 / 14.00 / 8.34 | 16.76 / 16.77 / 7.42 | 14.19 / 14.24 / 8.49 | 6.23 / 6.93 | 49.44 / 10.34 | 32.1 · 31.3 · 31.3 | 2715 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-6-A | 13.16 / 13.13 / 9.68 | 16.41 / 16.44 / 13.00 | 14.76 / 14.82 / 11.02 | 5.96 / 6.33 | 48.67 / 10.49 | 29.5 · 29.4 · 31.2 | 2800 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-g1-A | 12.21 / 12.23 / 9.15 | 15.16 / 15.19 / 11.53 | 13.00 / 13.03 / 9.80 | 4.92 / 6.81 | 49.08 / 9.67 | 28.3 · 30.8 · 31.3 | 2695 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-g2-G | 10.31 / 10.32 / 7.42 | 16.46 / 16.47 / 6.82 | 11.09 / 11.13 / 8.09 | 5.21 / 5.27 | 48.41 / 9.47 | 28.8 · 29.8 · 30.0 | 2780 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-g3-G | 11.75 / 11.75 / 8.89 | 17.14 / 17.22 / 7.70 | 11.93 / 11.92 / 8.55 | 4.74 / 5.28 | 51.26 / 9.23 | 30.2 · 28.7 · 32.0 | 2725 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-g4-A | 13.68 / 13.71 / 10.12 | 15.76 / 15.80 / 12.49 | 15.36 / 15.39 / 11.21 | 5.55 / 6.54 | 50.70 / 9.29 | 29.3 · 30.1 · 33.0 | 2728 | 266 | e1ad5c1b1990 | 66710ce8378c |

#### Medians d8 buuk

| | A → B | A → E | A → G |
|---|---|---|---|
| warm wall | 13.12 → 14.09 s (+7 %) | 13.12 → 10.37 s (-21 %) | 13.12 → 11.03 s (-16 %) |
| warm CPU | 13.11 → 14.11 s (+8 %) | 13.11 → 10.40 s (-21 %) | 13.11 → 11.03 s (-16 %) |
| warm writer lock | 9.53 → 8.59 s (-10 %) | 9.53 → 7.39 s (-22 %) | 9.53 → 8.15 s (-14 %) |
| cold miss wall | 15.51 → 17.57 s (+13 %) | 15.51 → 16.69 s (+8 %) | 15.51 → 16.80 s (+8 %) |
| cold miss CPU | 15.55 → 17.58 s (+13 %) | 15.55 → 16.72 s (+8 %) | 15.55 → 16.85 s (+8 %) |
| cold miss writer lock | 12.17 → 7.67 s (-37 %) | 12.17 → 7.22 s (-41 %) | 12.17 → 7.26 s (-40 %) |
| after restart wall | 14.25 → 13.82 s (-3 %) | 14.25 → 12.15 s (-15 %) | 14.25 → 11.51 s (-19 %) |
| after restart CPU | 14.30 → 13.84 s (-3 %) | 14.30 → 12.18 s (-15 %) | 14.30 → 11.53 s (-19 %) |
| after restart writer lock | 10.52 → 8.29 s (-21 %) | 10.52 → 9.11 s (-13 %) | 10.52 → 8.32 s (-21 %) |
| GET after warm Save wall | 5.42 → 5.88 s (+9 %) | 5.42 → 5.05 s (-7 %) | 5.42 → 4.98 s (-8 %) |
| GET after warm Save CPU | 5.43 → 5.87 s (+8 %) | 5.43 → 5.05 s (-7 %) | 5.43 → 4.99 s (-8 %) |
| first GET after restart wall | 49.73 → 49.84 s (+0 %) | 49.73 → 51.04 s (+3 %) | 49.73 → 49.83 s (+0 %) |
| first GET after restart CPU | 49.66 → 49.88 s (+0 %) | 49.66 → 51.13 s (+3 %) | 49.66 → 49.90 s (+0 %) |
| peak RSS | 2764 → 2695 MiB | 2764 → 2751 MiB | 2764 → 2752 MiB |

#### d8: buuk + exact #1905 (C), C + A1 (D), C + final (F)

| run | Save warm: wall / CPU / lock | cold miss | after restart | 1st/2nd GET after warm Save | restart 1st/2nd GET | 3× next-slot | peak RSS MiB | max DB+WAL MB | inspection | history |
|---|---|---|---|---|---|---|---:|---:|---|---|
| t-d8-c1-C | 12.95 / 12.95 / 9.53 | 16.56 / 16.49 / 12.46 | 13.47 / 13.49 / 9.97 | 4.86 / 5.03 | 48.44 / 10.33 | 20.4 · 19.2 · 22.3 | 2595 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-c2-F | 10.86 / 10.87 / 7.92 | 17.33 / 17.33 / 7.55 | 10.73 / 10.77 / 7.85 | 4.46 / 5.04 | 46.30 / 9.60 | 24.0 · 21.3 · 22.7 | 2545 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-c3-F | 11.88 / 11.88 / 8.40 | 15.86 / 15.89 / 6.71 | 13.12 / 13.14 / 9.43 | 4.91 / 5.49 | 46.42 / 10.72 | 23.2 · 21.7 · 23.2 | 2595 | 266 | e1ad5c1b1990 | 66710ce8378c |
| t-d8-c4-C | 11.71 / 11.74 / 8.61 | 15.53 / 15.57 / 12.19 | 13.12 / 13.17 / 9.67 | 4.61 / 5.55 | 49.37 / 10.37 | 21.9 · 21.9 · 24.0 | 2578 | 266 | e1ad5c1b1990 | 66710ce8378c |

#### Medians d8 combination

| | C → D | C → F |
|---|---|---|
| warm wall | – | 12.33 → 11.37 s (-8 %) |
| warm CPU | – | 12.34 → 11.38 s (-8 %) |
| warm writer lock | – | 9.07 → 8.16 s (-10 %) |
| cold miss wall | – | 16.04 → 16.60 s (+3 %) |
| cold miss CPU | – | 16.03 → 16.61 s (+4 %) |
| cold miss writer lock | – | 12.33 → 7.13 s (-42 %) |
| after restart wall | – | 13.29 → 11.93 s (-10 %) |
| after restart CPU | – | 13.33 → 11.95 s (-10 %) |
| after restart writer lock | – | 9.82 → 8.64 s (-12 %) |
| GET after warm Save wall | – | 4.73 → 4.69 s (-1 %) |
| GET after warm Save CPU | – | 4.73 → 4.70 s (-1 %) |
| first GET after restart wall | – | 48.90 → 46.36 s (-5 %) |
| first GET after restart CPU | – | 49.02 → 46.42 s (-5 %) |
| peak RSS | 2586 → 2570 MiB |


### Calls mode, d8 (separate instrumented runs, concurrent with tests)

Inclusive seconds and call counts inside the Save request. Absolute times are
inflated by the concurrent test process; the counts are exact.

| | A warm | G warm | A cold miss | G cold miss | A after restart | G after restart |
|---|---:|---:|---:|---:|---:|---:|
| writer lock | 10.20 | 8.30 | 12.06 | 7.65 | 10.00 | 7.29 |
| `read_checkpoint_for_save` (inside lock) | 1.93 | 0.11 | 5.14 | 0.13 | 1.80 | 0.06 |
| `prepare_checkpoint_for_save` (before lock) | – | 0.13 | – | 6.46 | – | 0.06 |
| defensive checkpoint copies (`_copy_decoded_value` from `decoded_live_calendar_component`) | 1 / 1.75 s | **0** | 1 / 1.58 s | 1 / 2.01 s | 1 / 1.62 s | **0** |
| `parse_checkpoint_json` | 0 | 0 | 2 / 2.52 s | 2 / 3.18 s | 0 | 0 |
| `_checkpoint_for_capture` (row re-read + hash) | 0.12 | 0.12 | 0.11 | 0.13 | 0.12 | 0.06 |
| `_value_identity` (complete-value canonical JSON + hash) | 3 / 1.15 s | 3 / 1.09 s | 3 / 1.11 s | 3 / 1.32 s | 3 / 1.15 s | 3 / 1.09 s |
| `remember_committed_global_sources` (after commit) | 1.99 | 1.90 | 1.91 | 2.23 | 2.00 | 1.91 |

## Assessment

- **Warm hit and after restart (the normal paths):** the read-side copy is
  gone, so both the writer lock and the whole Save are shorter. On current
  `buuk`, d8: Save −16 % / −19 %, lock −14 % / −21 %. Combined with #1905, d8:
  Save −8 % / −10 %, lock −10 % / −12 %. The following GET is unchanged or
  slightly faster.
- **Cold miss (evicted entry):** parsing moves out of the lock, so the lock is
  about 40 % shorter at both depths. The whole Save is **slower by
  3–10 %**: there is a second physical row read and full-byte hash, and the
  parse itself is no cheaper. This is reported as a limitation, not a gain.
- **A1 alone (B, D)** shortens the lock but lengthens the whole d8 Save by
  7–13 %, so it is not a candidate by itself.
- Peak RSS and DB+WAL are unchanged within run-to-run variation.
- The growth from d2 to d8 is visible: the warm Save copy is about 0.4 s at d2
  and about 1.7 s at d8.

The 1,000-player intermediate state, giant or multi-season runs and the 120 s
limit are not measured or changed. No 1,000-player worker-compatible fixture
is available (see #1905).

## Next measurable attempt (not implemented)

After commit, `remember_committed_global_sources` still spends about 2 s at
d8. Inside the lock, `_value_identity` (three calls, about 1.1 s) re-encodes
the complete canonical payload and component that the Save had already
encoded once as `canonical_payload_json`. Reusing that exact text as the
cache identity would remove the duplicate encoding. Both call sites are in
`repositories.py` and `native_fork_source_projection.py`, which overlap #1875
and the decode-cache layer. Hand the experiment to Work for coordination
first.

