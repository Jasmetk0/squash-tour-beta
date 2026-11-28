# Native Week Transition under Master v87: lifecycle and Turn Pro — 27 November 2026

Engineering evidence for one Draft PR (issue #1925). Not product canon and not a
release gate. Base `buuk 29784d51d01d9d747705be8abae30f0c82706c1e` (src tree
`494a35ec`), which already contains #1883, #1889 and #1900. Measurement commit
`bf105bc` (A, unchanged src); candidate `17c744d` (B, src tree `e6b7570b`).

## Inputs and procedure

`scripts/profile_native_week_transition.py prepare --policy v87` builds the Run
through the production HTTP API on SQLite with Saved v2, adopting the initial
world under the explicit v87 lifecycle policy and keeping the default Turn Pro
calibration (`pre-alpha-turn-pro.v2`, self-perception). 1,000 players, a short
**W8 test calendar** (3 seasons), four arrivals in every week from W3 and in S2W1,
four simultaneous 8-player ranked Editions played in W4 by the real MatchEngine,
and an explicit Save after every command. The fixture was built at base `29784d5`.

| input | players | Saved revisions | SHA-256 |
|---|---:|---:|---|
| W5 → W6 (ordinary week, births, 4 played Editions in history) | 1,012 | 27 | `5d23b715…5f11` |
| W8 → S2W1 (Season Transition, births, ranking) | 1,024 | 30 | `67dc8dfe…f799` |

Machine: Intel Xeon @ 2.10 GHz, 4 logical CPUs, 15.7 GiB, Linux 6.18, CPython
3.12.3 with the Fast CI lock file. Every run is its own process on a fresh SQLite
backup of the same input (checked by SHA-256 before and after every run), with
separate detached worktrees for A1/A2 and B and the same driver bytes. Order per
scenario: A/A `A1 A2 A2 A1`, then A/B `A B B A` and `B A A B`. Timing runs install
nothing; `--phases` and `stage` are separate runs.

```bash
export BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2 PYTHONHASHSEED=0 PYTHONPATH=src
python scripts/profile_native_week_transition.py prepare --out work/fx-v87 --players 1000 --policy v87
sha=$(sha256sum work/fx-v87/week-00-05.db | cut -d' ' -f1)
python scripts/profile_native_week_transition.py measure --input work/fx-v87/week-00-05.db --sha256 "$sha" --root work/w05-A1
python scripts/profile_native_week_transition.py measure --input work/fx-v87/week-00-08.db --action season-transition --root work/w08-A1
python scripts/profile_native_week_transition.py measure --input work/fx-v87/week-00-05.db --root work/w05-phases --phases
python scripts/profile_native_week_transition.py stage --input work/fx-v87/week-00-05.db --root work/w05-stage --repeat 5
python scripts/profile_native_week_transition.py report work/w05-A1 work/w05-B1
```

## Where the time goes (base, `--phases`, per-thread CPU s)

| | W5 Preview | W5 Execute | W8 Preview | W8 Execute |
|---|---:|---:|---:|---:|
| process CPU of the request | 7.13 | 28.63 | 13.55 | 44.19 |
| authenticated context + Signed replay (`_context`) | 4.04 | 23.05 (2 calls) | 9.39 | 37.52 (2 calls) |
| of which post-write re-read (`_verify_installed`) | – | 18.96 | – | 28.01 |
| transition preparation (`_transition_candidate`) | 2.75 | 2.41 | 3.36 | 2.76 |
| … Saved lifecycle input (2 loads) | 1.25 | | 1.70 | |
| … Saved Health input (1 load, re-loads lifecycle and world) | 0.99 | | 1.27 | |
| … Saved InitialWorld loads (3) | 0.90 | | 0.94 | |
| … `prepare_native_tour_week` | 1.13 | | 1.19 | |
| … … Turn Pro total (country map, candidates, decisions) | 0.040 | | 0.055 | |
| … … lifecycle advance, preliminary + final | 0.021 | | 0.029 | |
| … … arrivals / Health / development+form / ranking | 0.002 / 0.042 / 0.109 / 0.150 | | 0.003 / 0.070 / 0.101 / 0.208 | |
| opening Turn Pro evidence recomputed (calls) | 1.26 (5) | 3.04 (12) | 1.26 (5) | 3.02 (12) |

The issue's hypothesis was checked first: the country map is below 1 ms, the
preliminary lifecycle about 10 ms and all Turn Pro work about 40–55 ms per
preparation at 1,000 players. Removing the duplicated preliminary lifecycle
(possible only when there are no decisions; in a birth week it is a different
function from the final `advance_calendar_lifecycle_with_prospects`) would save
about 0.01 s per preparation, far below the whole-request noise, so it was not
changed.

The repeated work that does matter inside the preparation is input loading:
every parse of a v87 Saved InitialWorld recomputes the complete opening Turn
Pro evidence (1,000 self-perceptions and sporting bootstraps, ≈0.25 s), and one
preparation parsed the same component three times (lifecycle, Health, and
Health's own lifecycle load).

## Change

Inside a private scope entered only around those two loads in
`_transition_candidate`, `load_saved_initial_world` reuses the frozen model it
parsed from exactly the same JSON text. A failed parse is never remembered;
identity, fingerprint, Run clock and lifecycle checks still run on every call;
nothing outlives the scope. The Signed replay, `_context`, Save and GET paths
are unchanged.

## Results

**Isolated preparation** (`stage`, in-process thread CPU of the exact Execute
preparation, median of 5 repetitions per process):

| scenario | A/A (A1 / A2) | A median (range) | B median (range) | B − A |
|---|---|---|---|---:|
| W5 → W6 | 2.46 / 2.62 | 2.45 (2.38–2.49) | 1.87 (1.85–1.97) | **−0.58 s (−24%)** |
| W8 → S2W1 | – | 2.95 (2.88–3.03) | 2.36 (2.35–2.43) | **−0.59 s (−20%)** |

`--phases` (one run per side): `_transition_candidate` W5 Preview 2.75 → 2.23,
Execute 2.41 → 1.59; W8 Preview 3.36 → 2.67, Execute 2.76 → 2.22 s. Opening
evidence recomputations: Preview 5 → 3, Execute 12 → 10.

**Whole requests, real HTTP/SQLite** (medians of 4 runs per side; A/A is the
difference between the A1 and A2 medians):

| scenario | metric | A/A | A | B | B − A |
|---|---|---:|---:|---:|---:|
| W5 → W6 | Preview s (CPU) | 1.7% | 7.24 (7.22) | 6.84 (6.84) | **−0.40 (−5.6%)**, ranges 7.18–7.58 vs 6.61–7.22 |
| | Execute s (CPU) | 5.3% | 29.95 (29.69) | 29.71 (29.48) | −0.24 (−0.8%), below noise |
| | Save s | 4.1% | 18.38 | 18.41 | +0.03, unchanged |
| | first Saved GET s | 5.6% | 6.81 | 6.78 | unchanged |
| | first GET after restart s | 4.0% | 73.34 | 72.36 | below noise |
| | peak RSS MiB | | 2,603 | 2,551 | within run variation (B max 2,611) |
| W8 → S2W1 | Preview s (CPU) | 4.2% | 14.43 (14.46) | 14.00 (14.01) | −0.43 (−3.0%), below noise |
| | Execute s (CPU) | 5.4% | 47.92 (47.50) | 46.84 (46.48) | −1.08 (−2.3%), below noise |
| | Save s | 2.6% | 28.52 | 28.43 | unchanged |
| | first Saved GET s | 7.1% | 12.79 | 12.45 | below noise |
| | first GET after restart s | 2.5% | 91.75 | 91.27 | below noise |
| | peak RSS MiB | | 3,419 | 3,418 | unchanged |

Peak SQLite + WAL: 279 MiB (W5) and 386 MiB (W8), the same on both sides.

Within each scenario all 12 runs (A and B) produced byte-identical Preview and
Execute bodies, Save receipt hash, players, ranking, checkpoint and Tour
fingerprints and the complete Saved inspection; `quick_check` was `ok`, the
restarted process returned the identical inspection and accepted the next
command's Preview. The `stage` digests (preview fingerprint, preview body and
successor checkpoint fingerprint) were identical in all 20 runs.

Conclusion: a reproducible −0.58 s CPU per transition preparation; visible in
the whole ordinary-week Preview; within noise for Execute, which is dominated
by its two `_context` passes.

## Handoff to Work (outside this lane)

- Execute spends 23 s (W5) / 37.5 s (W8) of CPU in its two `_context` calls, of
  which the post-write re-read is 19 / 28 s. The remaining ten opening Turn Pro
  recomputations per Execute (≈2.4–2.5 s) are InitialWorld parses inside
  `_context` and its Signed replay (`load_saved_lifecycle`/`load_saved_health`
  through `verify_native_tour`/`verify_competition_payload`). The same parse
  scope around `CalendarTourService._context` would remove most of them; it is
  the Tour GET/verification path (#1921) and was left unchanged here.
- cProfile of base Execute at W5 (server thread, profiled times): post-write
  `_verify_installed` 34 s of 50 s; `native_fork_source_projection._copy_decoded_value`
  deep copies 14.7 s; `calendar_sporting_checkpoint.load_checkpoint` 10.8 s;
  `_decode_checkpoint_row` 6.9 s.
- Inside the preparation, the next isolated candidate is the second Saved
  lifecycle parse (directly and again inside `load_saved_health`, ≈0.33 s each
  at W5–W8 and growing with weeks × players), in `player_lifecycle_state.py`,
  which the older Draft #1831 also touches.

## Limitations

- Short W8 test calendar, 8 Saved weeks, four 8-player Editions; no W52/W61
  season, 25-season Run or hosted runner was measured.
- Legacy-policy whole-request timing was not repeated here; the legacy path is
  covered by the byte-equality HTTP test (its InitialWorld parse has no opening
  Turn Pro evidence, so its saving is small).
- Fork, Restore and the native browser matrices were not executed.
