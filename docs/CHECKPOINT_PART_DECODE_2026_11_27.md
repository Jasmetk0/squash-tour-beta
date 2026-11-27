# Long Tour week: reuse the strict decode of unchanged checkpoint history (27 November 2026)

Task: [Work's review in #1909](https://github.com/Jasmetk0/squash-tour-beta/pull/1909#issuecomment-7212344976),
part 3. Base `buuk 29784d5`. Independent of #1907/#1909/#1875 (other functions and hunks).

## Input

The giant five-season diagnostic run #1908 ([run 45902907173](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45902907173))
left on-line backups after weeks 9, 12 and 15 of season 1 (artifact
`giant-nov26-snapshots-x64-1-45902907173`, zip SHA-256 `d78da4e9…a948`, equal to
the artifact digest). They were produced by `buuk 29784d5` combined with
#1905/#1907/#1875/#1899 heads (see the workflow) and open strictly on
`buuk 29784d5`.

| snapshot | SHA-256 (manifest = actual) | Saved revisions | players | live checkpoint | Tour authority |
| --- | --- | ---: | ---: | ---: | ---: |
| after-W09 | `438f7091…932c` | 53 | 1 020 | 109.6 MB | 5.2 MB |
| after-W12 | `32d1deae476ece76c4444396874726b9b7994e134db6332b7282e8d92534e16f` | 76 | 1 020 | 161.9 MB | 7.3 MB |
| after-W15 | `d9ddd3f0358627e4029ffa4ab20adcf01f8e65630b74755e3cf2544dee9b3c42` | 95 | 1 040 | 203.6 MB | 9.6 MB |

Run `run`, Branch `branch`, Saved v2, run calendar W52 × 6 seasons, positions
S1W13 and S1W16. The inputs are only copied (SQLite backup API, read-only
source) into a temporary directory per run. No database is committed.

## Replayed week

`scripts/replay_giant_week.py` replays the week that follows a snapshot with
exactly the functions of the pinned harness (`giant_native_five_season_load.py`
at `51dbde8`, profile `compatible`, 5 seasons, 60 Editions per season):
`create-edition` + Save for the Editions two weeks ahead, submit/approve/draw +
Save per Edition, every shared `next-slot` + Save, `confirm-result` + Save per
Edition, `transition` + Save. One real uvicorn server, SQLite, real MatchEngine.
New product ids are deterministic (`deps.uuid4` sequence) so that values hashed
over them are comparable between trees; ids stored in the snapshot are kept.
The snapshot is opened (cold strict verification of the whole lineage, 127–139 s
at W12) once before the measured week, without the 120 s client limit; the giant
run never restarts inside a week.

The W13 week plays one 4-entrant Edition (3 matches in 2 slots) and plans one
Edition; 49 HTTP calls. Even so it takes 32 minutes on `buuk`.

## Where the time goes (`buuk`, exclusive py-spy profile, 25 Hz)

W13 (`after-W12`): 1 994 s of samples in `beta_engine`, 1 938 s wall.

| work | inclusive s | share |
| --- | ---: | ---: |
| `decoded_global_checkpoint_component` (Saved HEAD sporting checkpoint, every context) | 716.6 | 36 % |
| — `parse_checkpoint_json` strict part decode (`model_validate_json` of every event) | 447.6 | 22 % |
| — `_checked_checkpoint` → full canonical fingerprint of the decoded value | 172.4 | 9 % |
| — `canonical_json` of the whole component only to find it exceeds the 64 MiB cache | 90.2 | 5 % |
| `GlobalCompetitionCheckpoint.fingerprint` (all callers) | 255.1 | 13 % |
| `verify_tour_origins` | 298.3 | 15 % |
| `_validated_branch_revision_lineage_in_session` | 235.4 | 12 % |
| `JSONEncoder.iterencode` (self) | 735.5 | 37 % |
| `JSONDecoder.raw_decode` (self) | 286.9 | 14 % |

Two unchanged GETs in a row cost 22.5 s and 21.7 s. The cause is a size cliff:
the checkpoint (162 MB) exceeds every value cache (`MAX_GLOBAL_TOUR_BYTES`,
`MAX_LIVE_COMPONENT_BYTES` 64 MiB) and the canonical-text proof references
(96 MiB). Every GET, Preview, Execute and Save therefore decodes and hashes the
complete history again, although all but the newest events are byte-identical
from request to request. The work grows with history: on the same host the
strict decode of the live row is 7.5 s (GC paused, as in requests) at W12, its
fingerprint 6.5–7 s, and the checkpoint grows by ~14 MB per week.

W16 (`after-W15`): see the A/B section; its exclusive profile is
`prof-w16-buuk` (numbers below).

## Change

1. **`infrastructure/db/checkpoint_part_decode.py`.** `decode(text, parse)` runs
   the caller's original strict parser on exactly the text the original path
   parses (`json.dumps(part)`). The key is SHA-256 + length of that complete
   text and the parser identity (model class), so a hit means the parser would
   receive the same characters. The stored form is the **pickled validated
   model**, never a model: every use unpickles a fresh private object graph.
   No caller can observe or mutate another caller's value; no ownership protocol
   is needed. 256 MiB byte budget, LRU; oversized parts, unpicklable values,
   damaged entries and validation inside the engine's deferred-hash factory take
   the original parse and are not retained. Invalid text raises the original
   error and is never retained.
2. **`parse_checkpoint_json`** uses it for every v13 part (root and each
   event) when no caller-scoped part cache is given, and accepts the already
   decoded Saved body instead of `json.dumps` + `json.loads` of the whole state.
   The outer `GlobalCompetitionCheckpoint` validator still runs.
3. **`prime_decoded_checkpoint_fingerprint`** (inside the private replay scope
   only): the SAME canonical hash, composed as `_incremental_checkpoint_fingerprint`
   does, but its prefix states are addressed by the content identities of the
   decoded parts instead of object identity. Unchanged history reuses its hash
   state; only new events are encoded. Tests compare it with
   `canonical_hash(model_dump)`.
4. **`decoded_global_checkpoint_component`** skips only the cache key (a full
   canonical encoding of the component) for a declared value already measured
   too large for that cache. The strict decode and every check run as on a miss;
   the hint never authorizes anything.

Unchanged: sporting rules, RNG, schemas, every stored byte, Save and its gates,
physical lineage/ancestry verification, replay authority, Run/Branch isolation,
timeouts, CI and the Master.

## A/B of the whole week

(Filled from `ab-w13-*`, `ab-w16-*` below.)

## Limitations

- Linux container, 4 vCPU, Python 3.12.3 (lock `fast-ci-linux`). The giant run
  used Python 3.11.18 on GitHub runners. Windows not measured.
- The first decode in a process additionally pickles every part (+5.4 s at W12,
  once); afterwards only new parts are pickled.
- The cache holds up to 256 MiB of pickled parts per process.
- Remaining dominant work for a next round: per-part `json.dumps` for the keys,
  `verify_tour_origins` and the lineage validation.
