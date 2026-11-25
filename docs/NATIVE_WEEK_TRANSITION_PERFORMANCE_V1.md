# Native Week Transition performance — 25 November 2026

Engineering evidence for one Draft PR. Not product canon and not a release gate.
Base `buuk 8af660dc84e038ca1c6bc24539509993af376b90`; candidate commits
`e713ce2` (successor checkpoint hash) and `2b0f94e` (development kernel).

## What was measured

`scripts/profile_native_week_transition.py` drives the production HTTP API on
SQLite with Saved v2 and the ordinary 120-second client deadline:

1. `prepare` builds one native birth Run through real HTTP commands: initial
   world of N players, a signed 15-year-old prospect source with arrivals in
   every week from W3 and in Season 2 Week 1, four simultaneous 8-player ranked
   Editions played in week 4 by the real MatchEngine through shared global
   slots, and an explicit Save after every command and Week Transition. A SQLite
   backup of every Saved week is kept (`week-SS-WW.db`).
2. `measure` copies one snapshot (the input is opened read-only), runs cold GET,
   Preview, Execute, the draft GET, explicit Save and the first Saved GET, checks
   `PRAGMA quick_check`, then starts a fresh interpreter on the same database,
   compares the complete inspection with the pre-restart one and previews the
   next real command (the next transition, or a new Edition when the next
   boundary is legitimately blocked by a due Edition). Persistence UUIDs are
   derived from the input SHA-256, so the complete inspection, the Preview and
   Execute bodies, the Save receipt hash, players and ranking can be compared
   byte for byte between trees.
3. `--phases` (separate runs) wraps the transition stages with per-thread CPU
   accounting: inclusive time and self time = inclusive minus wrapped children.
   `--profile` adds cProfile per endpoint in the server worker thread.
4. `stage` repeats the exact Execute preparation in process (context loaded and
   fingerprints primed as Execute does) and reports digests of the preview body
   and successor checkpoint.
5. `report` requires the same input hash and instrumentation mode, successful
   SQLite integrity checks and matching restart metadata. It exits with status
   2 if the complete inspection or transition evidence differs.

The tool uses the shared process measurement helpers for Linux, Windows and
macOS. The measurements below were taken on Linux.

Hardware: Intel Xeon @ 2.10 GHz, 4 logical CPUs, 15.7 GiB RAM, Linux 6.18,
CPython 3.11.18 with the Fast CI lock file (pydantic 2.14.2, SQLAlchemy 2.1.6).
Every A/B used separate copies of the same input on this machine, sequentially,
in alternating order. Wall time on this shared 4-vCPU container varies by
about ±1.5 s at W7; the CPU phase numbers are the more reliable signal.

Inputs (`fixture.json` records the steps and hashes):

| input | players | Saved revisions | SHA-256 |
|---|---:|---:|---|
| 16-player W6 Run, week 5 (built by an intermediate harness revision with one Edition) | 19 | 17 | `8721df8d…6459` |
| 1,000-player W8 Run, week 3 (before the Editions) | 1,004 | 13 | `0e5eba10…2bad` |
| same Run, week 7 (four played Editions in history) | 1,020 | 28 | `dff468c2…c2ed` |
| same Run, week 8 → Season 2 Week 1 (4 arrivals, ranking) | 1,024 | 29 | `da120295…8dec` |

## Where a week's time goes (base, 1,000 players, W7)

| phase | wall s |
|---|---:|
| cold GET (first read after start) | 53–60 |
| Preview | 7.5–8.4 |
| Execute | 32.7–34.9 |
| draft GET | 15.3–16.9 |
| explicit Save | 24.9–27.6 |
| first Saved GET | 11.3–12.6 |
| cold GET after restart / continuation Preview | 57–61 / 15 |

Inside the transition (per-thread CPU, `--phases`), Preview spent 3.8 s and
Execute about 7.0 s (candidate plus the post-write replay of the same week) in
work that Week Transition owns. The 2.9 s `prepare_native_tour_week` split into:
re-hashing the whole successor checkpoint history ~47%, re-deriving every
completed tournament ~16%, development/form ~18%, the rest ranking, Health,
lifecycle and fingerprints. Development and form 0.23 s, ranking 0.09 s, Health
0.06 s, lifecycle and arrivals below 0.01 s each.
`load_saved_lifecycle` runs twice per candidate (directly and inside
`load_saved_health`), 0.29 s each at W7.

Everything else in Execute (22–26 s self) and the cold GET (41–51 s self) is
Saved/context work, outside this PR (see the handoff below).

## Changes

1. **Successor checkpoint hash** (`e713ce2`). The canonical JSON of a v13
   checkpoint is a prefix, its events and a suffix. The SHA-256 state after the
   last event is recorded under the digest it was computed for; a successor that
   appends exactly one event to such a checkpoint hashes only that event. A
   predecessor without a recorded state is encoded once and must reproduce its
   own fingerprint first. Any other relation falls back to the full hash.
2. **Development kernel** (`2b0f94e`). Age comparisons, the rate split and the
   roll prefix are evaluated once per player instead of once per attribute; a
   stateless roll that cannot change the value is skipped. The hashed roll text
   and every result are unchanged.

## Results

Stage, same input, identical preview body and successor fingerprint at every
point (W7: preview `61d35ead…`, successor `13c1b2c9…`):

| W7 preparation | base | after 1 | after 1+2 |
|---|---:|---:|---:|
| whole preparation, s | 3.8–4.1 | 2.2–2.5 | 2.0–2.4 |
| development kernel, s | 0.16 | 0.16 | 0.085 |

HTTP per-thread CPU at W7, base → candidate: Preview transition work 3.82 →
2.13 s; Execute transition candidate 3.93 → 1.94 s and its two
`prepare_native_tour_week` calls 6.04 → 2.36 s; the five replayed weeks in the
cold GET 4.17 → 3.31 s (development 0.98 → 0.56 s).

Whole week, real HTTP/SQLite, alternating order (wall s; CPU = Preview+Execute
process CPU):

| scenario | tree | Preview | Execute | Save | first Saved GET | CPU P+E |
|---|---|---:|---:|---:|---:|---:|
| 16 players, W5 (ABBA) | base | 1.3/1.7 | 5.0/5.3 | 2.6/2.6 | 1.1/1.4 | 6.2/7.0 |
| | c2 | 1.3/1.3 | 5.0/5.0 | 2.6/3.0 | 1.1/1.3 | 6.3/6.3 |
| 1,000, W3 (ABBA) | base | 2.8/2.5 | 10.0/9.8 | 5.7/5.9 | 1.7/1.6 | 12.6/12.0 |
| | c2 | 2.3/2.2 | 8.7/8.4 | 5.4/6.1 | 1.7/1.8 | 10.7/10.4 |
| 1,000, W7 (A B1 B2 B2 B1 A) | base | 8.4/7.5 | 34.9/32.7 | 27.6/24.9 | 12.6/11.3 | 42.8/39.7 |
| | c1 | 7.0/8.1 | 30.5/31.9 | 25.9/28.2 | 12.3/12.2 | 36.9/39.1 |
| | c2 | 7.5/7.5 | 31.3/33.9 | 26.4/26.2 | 11.2/13.1 | 38.3/40.8 |
| 1,000, W8 → S2W1 (ABBA) | base | 16.5/14.5 | 53.6/47.5 | 30.6/27.8 | 13.4/12.0 | 69.2/61.2 |
| | c2 | 13.5/12.7 | 48.1/45.2 | 28.5/27.7 | 12.3/12.2 | 60.6/57.1 |

Peak RSS stayed within 3% and SQLite + WAL was identical: W3 0.94 (base) and
0.97 (c2) GiB / 69.8 MiB,
W7 2.77–2.79 GiB / 339.5 MiB, season 3.15 GiB / 374.2 MiB, 16 players
0.62 GiB / 38.4 MiB. Each 1,000-player Saved week adds about 20 MiB of SQLite.

Within each scenario all runs of all trees produced the byte-identical complete
Saved inspection after Save, Preview and Execute bodies, receipt hash, players,
ranking and checkpoint/Tour fingerprints; `quick_check` was `ok`, and the
restarted process returned the identical inspection and accepted the next
command's Preview.

## Growth

Stage (in-process Execute preparation), 1,000-player Run, median of 3 per run,
order base c1 c2 c2 c1 base per point, identical preview body and successor
fingerprint across all trees at every point:

| input week (revisions) | base s | after 1 (c1) s | after 1+2 (c2) s |
|---|---:|---:|---:|
| W2 (12) | 0.85 / 1.01 | 0.93 / 0.86 | 0.82 / 0.81 |
| W4, after 4 played Editions (25) | 2.67 / 2.84 | 1.75 / 1.82 | 1.70 / 1.67 |
| W6 (27) | 3.53 / 3.12 | 2.23 / 1.99 | 1.89 / 1.86 |
| W8 → Season 2 (29) | 3.93 / 3.79 | 2.34 / 2.52 | 2.26 / 2.18 |
| S2W1 → W2 (30, partial: base c1 c2 c2) | 4.07 | 2.30 | 2.41 |

From W4 to W8 the base preparation grows by ≈0.29 s per Saved week; the
candidate by ≈0.13 s. W2→W4 includes the first played Editions (11 extra Saves).

Per-preparation stage CPU (base): W2 0.95 s, W3 1.33 s, W4 2.8–3.0 s (first
played Editions in history), W5 3.2–3.7 s, W7 3.8–4.1 s for 1,000 players. The
history-proportional parts were the successor hash (now O(new event) once the
predecessor's state is known), re-deriving all completed tournaments and
parsing the Saved lifecycle/Health histories. The population-proportional
parts are development, the advance/record fingerprints and the new event
encoding. At 16 players the same week is Saved-bound and unchanged.

## Not changed / limitations

- The remaining largest owned costs at W7 are re-deriving every completed
  tournament for the ranking results (0.45 s, grows with the number of played
  Editions) and parsing the Saved lifecycle twice per candidate (0.29 s, grows
  with weeks × players).
- No long or 25-season load was run; no hosted runner was used. The fixture
  is 8 weeks with 4 Editions; a W52 season with 60 Editions has not been
  measured here.
- Fork, Restore and the full native browser matrices were not executed; the
  changed code is shared by those paths and is covered by the exact-equality
  tests and the targeted HTTP/SQLite regressions listed in the PR.

## Handoff to Work (Saved replay / context)

cProfile of the candidate at W7 (1,000 players, 28 revisions), server thread:

- cold GET 66 s profiled: `_prevalidate_cold_global_lineage` 54 s, of which
  `load_saved_calendar_sources`/`saved_checkpoint` per revision 40 s and five
  `verify_competition_payload` replays 30 s that re-simulate 28 MatchEngine
  matches (`accept_slot` 11 s); JSON encoding 15 s.
- Execute 38 s profiled: two `_context` calls 32.7 s — live checkpoint row
  decode (`_decode_checkpoint_row`) 7.0 s, defensive deep copies of decoded
  values (`_copy_decoded_value`) 7.6 s, JSON encoding 10.2 s, `validate_json`
  6.2 s.
- Save 28 s: `read_checkpoint_for_save` 7.3 s, JSON encoding 10.4 s,
  `remember_committed_global_sources` 4.1 s, `capture_saved_calendar_match`
  3.9 s. Draft GET 20 s: checkpoint decode 7.0 s, deep copy 3.9 s.

The same live checkpoint row is decoded in Execute (twice), the draft GET and
Save. This overlaps with Work's #1875/#1876 and the earlier #1837 proposal.
