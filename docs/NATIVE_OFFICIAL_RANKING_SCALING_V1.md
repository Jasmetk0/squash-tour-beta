# Native Official Ranking scaling — V1 evidence (25 November 2026)

Implementation and measurement evidence only. No sporting rule, Saved format,
seed, MatchEngine, explicit Save, timeout, CI coverage or production check
changes. Timings are diagnostic and never a pass criterion.

## What a native Week Transition spends on the Official Ranking

`prepare_native_tour_week` builds the published results of **every** confirmed
Edition completed before the target week, then the bridge replays the signed
lifecycle (eligibility/Entry/retirement), checks the previous Ranking owner,
calculates Best N/NR/tie-break and hashes every source into the proof.

Measured separately (`scripts/profile_native_official_ranking.py --phases` /
`stage`, per-thread CPU) on real HTTP/SQLite Saved v2 fixtures:

| Phase (one fresh request) | 64 players, 10 Editions | 1,000 players, 4 Editions |
|---|---|---|
| derive the played tournaments (`completed_tournaments`) | 1.20–1.36 s | 0.44 s |
| rebuild + hash each Edition's results (`edition_results`) | 0.08 s | 0.03 s |
| lifecycle replay (eligibility) | 0.02 s | 0.05 s |
| previous-owner check, Best N calculation, proof hashes | < 0.01 s | < 0.01 s |

The derivation grows linearly with confirmed Editions, about 0.12–0.13 s per
Edition, mostly encoding every match's rally log for the tournament's sporting
fingerprint, which every award (and so every result source) contains. It
happened in **each** of Preview, Execute and Execute's post-write replay of the
same transition, and again for every replayed earlier transition of a read.

Synthetic growth (pure domain inputs, clearly no MatchEngine or Saved data;
8 results per Edition, validity W, target after the Season boundary so part
of the results has expired but stays in the proof):

| players | Editions | results | owner check original → index | Best N | proof hashes |
|---|---|---|---|---|---|
| 250 | 256 | 2,048 | 0.0045 → 0.0005 s | 0.106 s | 0.019 s |
| 1,000 | 64 | 512 | 0.0748 → 0.0023 s | 0.054 s | 0.006 s |
| 4,000 | 16 | 128 | 1.2134 → 0.0093 s | 0.131 s | 0.001 s |
| 4,000 | 256 | 2,048 | 1.2816 → 0.0089 s | 0.190 s | 0.015 s |

The previous-owner check was quadratic in classified players (a rebuilt
identity set and a linear search per row). Best N grouping in
`calendar_official.py` is already one linear pass per result plus one sort per
player; it is not a bottleneck and is unchanged.

## Changes

1. **Exact owner index** (`calendar_native_ranking_bridge.py`): one index of the
   previous lifecycle snapshot, first occurrence as `next(...)` did, same check
   order and messages. A test compares the original verbatim on all cases.
2. **Replay-scope memo**: inside the existing private replay scope, the
   published results of the very same authority/played-event objects on the
   same Run clock are rebuilt once, and the Edition authority's execution
   fingerprint and embedded ranking-snapshot fingerprints once per object.
   Failures are never remembered; outside a scope nothing changes.
3. **Verified results across one Week Transition**
   (`calendar_native_tour_week.native_confirmed_results`): the results are a
   pure function of the complete Tour state, sporting checkpoint, target week
   and Run clock. They are recorded under the canonical fingerprints of the
   two complete values that the operation **already** computed or primed from
   its authenticated context (priming happens only after the complete physical
   Saved gate); a missing hash is never computed and means the full path.
   Only Tour v5 / checkpoint v13. Any changed state, checkpoint, clock or
   target is a different key. Bounded: 4 entries and 65,536 results (about
   2.3 KB each, at most about 150 MB); a larger history is not retained.
   Values are deeply immutable (strings, integers, booleans, frozen weeks).

Unchanged: rows, order, Best N, NR, tie-break, validity, disciplinary zeros,
Entry and retirements, publication, Season boundary and extension semantics,
the complete `source_result_fingerprints` (expired sources stay), Run/Timeline
binding and every proof value.

## Measured A/B (same host, separate copies of one SQLite input)

Host: 4-vCPU Intel Xeon 2.1 GHz, 16 GB, Linux, CPython 3.11.18, Fast CI lock.
A = `buuk 574d5a765`, B = this branch. Fixtures were built by A in an
isolated worktree.

### Short real scenario: 64 players, Season boundary (W8 → S2 W1, 10 Editions)

Input `week-00-08.db` SHA-256 `09930fa92281…` (76 players, 61 Saved
revisions). In every run the complete Preview and Execute responses, draft and
Saved inspections, Saved receipt hash and revision id, ranking, ranking and
proof (`ranking_adoption_fingerprint`) fingerprints and the restarted
inspection are **byte-identical**; SQLite `quick_check=ok`.

`--phases` pair (B at `6d5f9ce`, the same results path with an 8-entry bound):

| HTTP phase | A transition CPU | B transition CPU | Editions rebuilt A → B |
|---|---|---|---|
| Preview | 2.71 s | 2.43 s | 10 → 10 (first request) |
| Execute (candidate + post-write replay) | 5.26 s | 2.60 s | 20 → 0 |
| cold GET (replayed transitions) | 0.32 s | 0.39 s | 20 → 8 |
| restart cold GET | 0.45 s | 0.40 s | 30 → 10 |

Timing ABBA at `d1517bb` (the machine was concurrently building the 1,000-player
fixture, so wall times are noisy): Execute A 32.7 / 29.6 s, B 28.5 / 28.7 s;
Preview + Execute CPU A 39.7 / 36.2 s, B 35.1 / 35.3 s; Save 19.6 / 17.0 vs
18.7 / 16.6 s; peak RSS 2.80–2.84 GiB in all four.

### Target: about 1,000 players, Season boundary (W8 → S2 W1, 10 Editions)

Input `week-00-08.db` SHA-256 `2dc7a50140bb…` (1,010 players, 10 confirmed
ranked Editions in five weeks, 59 Saved revisions). Order A B B A, timing
mode (no instrumentation), then one `--phases` pair. All six runs produced
byte-identical complete evidence; `quick_check=ok`; restarted inspection equal.

| Seconds (wall) | A1 | B1 | B2 | A2 |
|---|---|---|---|---|
| cold GET | 110.8 | 110.7 | 113.6 | 112.8 |
| Preview | 21.2 | 20.9 | 21.7 | 21.7 |
| **Execute** | **72.4** | **66.1** | **67.5** | **71.7** |
| draft GET | 38.0 | 37.4 | 37.7 | 37.8 |
| explicit Save | 48.2 | 47.3 | 47.5 | 46.4 |
| first Saved GET | 20.0 | 18.3 | 20.0 | 19.6 |
| restart cold GET | 115.7 | 115.8 | 115.0 | 116.6 |
| Preview + Execute + Save | 141.9 | 134.3 | 136.7 | 139.8 |
| Preview + Execute process CPU | 92.3 | 86.4 | 88.4 | 92.5 |
| peak RSS (MiB) | 4,731 | 4,744 | 4,729 | 4,800 |

`--phases` (per-thread CPU of the Week Transition preparation):

| HTTP phase | A | B | Editions rebuilt A → B | tournament derivations A → B |
|---|---|---|---|---|
| Preview | 4.56 s | 4.53 s | 10 → 10 | 1 → 1 |
| Execute (candidate + post-write replay) | 7.03 s | 3.64 s | 20 → 0 | 2 → 0 |
| cold GET (6 replayed transitions) | 3.96 s | 4.00 s | 20 → 8 | 164 → 164 |
| restart cold GET (7) | 4.96 s | 4.75 s | 30 → 10 | 165 → 165 |

Cache at the end: 4 entries, 224 results. The restart cold GET is close to the
tests' 120 s transport bound on this host (115–124 s, also on A); the script
therefore waits up to 600 s (`--client-timeout`, recorded per phase as
`over_test_transport_bound`). That cold read belongs to the Saved loading /
lineage validation area and is unchanged here. The continuation Preview after
restart was not run: the next boundary is legitimately blocked by the Edition
due in S2 W1.

### Growth across weeks (64 players, in-process `stage`, one fresh scope each)

| Snapshot | Editions | A transition / derivation | B 1st request | B next request, same inputs |
|---|---|---|---|---|
| W5 | 4 | 0.99 / 0.45 s | 1.04 s | 0.63–0.74 s (results 0 s) |
| W6 | 6 | 1.73 / 0.72 s | 1.52 s | 0.80–0.94 s |
| W7 | 8 | 2.03 / 0.98 s | 2.01 s | 0.97–1.04 s |
| W8 | 10 | 2.78 / 1.36 s | 2.42 s | 1.16–1.30 s |

Preview body and successor checkpoint digests are equal in every A/B pair.

## Architectural obstacle: the first request of each new week

The first request for new inputs still derives every earlier Edition's played
tournament. Its awards contain the sporting fingerprint over all rally logs,
and every verified identity that survives a request covers a whole Saved
component, not one Edition. Reusing one Edition across *different* weeks would
need a verified per-Edition played-tournament identity bound to the Saved
bytes (Saved v2 component structure: Work's area) or an append-only checkpoint
hash state (the separate #1883 mechanism).

Experiment (`stage --same-scope`, A, the upper bound if every private value
survived to the next request): W8 transition 2.54 → 0.096 s; W5 at 1,000
players 2.64 → 1.10 s. At about 0.13 s per Edition, a history of 1,500
confirmed Editions would cost about 190 s of derivation per first request.

## Reproduce

```bash
python scripts/profile_native_official_ranking.py prepare --out fx --players 1000 --width 8 --edition-weeks 7 --editions 2 --stop-season 1 --stop-week 3
python scripts/profile_native_official_ranking.py measure --client-timeout 600 --input fx/week-00-08.db --root out-a   # per tree
python scripts/profile_native_official_ranking.py report out-a out-b
python scripts/profile_native_official_ranking.py stage --input fx/week-00-08.db --root st-a [--same-scope]
python scripts/profile_native_official_ranking.py synthetic
```

Both fixtures were built by A (`--edition-weeks 9` and `7`, two
eight-player Editions per week, Season 1 Weeks 4–8). Each build then executed
the real Season Transition after W8; the 64-player build stopped at its S2 W1
Edition because the generator picked a newly retired player, and the
1,000-player build was stopped there. `prepare` now picks only active players;
that fix has not been exercised yet. Points do not expire before S2 W5 in
these fixtures, so expiry of real results is covered by the synthetic table
and the existing calendar ranking tests, not by the HTTP runs. No 5-, 25- or
50-season run was started.

Fixture SHA-256: 64 players W5 `da7ecca2…`, W6 `ee85e434…`, W7 `c7f997eb…`,
W8 `09930fa9…`; 1,000 players W5 `8a8ec8a6…`, W8 `2dc7a501…`.
