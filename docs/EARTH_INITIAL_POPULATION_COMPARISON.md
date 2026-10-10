# Production initial populations in the global Player Lab

This operation uses `InitialPlayerPoolGenerator`, the production kernel also used
by Run-owned initial-pool preview/adoption. It does not use synthetic Talent
Calibration profiles or annual Talent Intake. Built-in Earth sources remain
read-only; the existing World Package adapter supplies independent typed inputs.

Open `/admin/labs/player`, select FIFA Earth and ATP Earth, a supported initial
season, players per population (1–2000), and explicit distinct seeds (1–10).
**Generate and save population comparison** writes an immutable global Test
Session to SQLite, outside every Run and Branch. Choose a saved comparison or
reopen its `population_session` URL to read it without regeneration. Identical
requests reuse a session if both source snapshots and engine source fingerprint
are unchanged. Source snapshots are checked again on POST; a GET never generates.

The panel shows individual and pooled distributions, all source countries
including true zero counts, seed variation, existing initial-pool potential tiers,
analytical histogram bins, and actual stored players. It uses the existing 1–99
initial-pool ability/attribute scale, distinct from the other Lab's 0–200 model.
JSON includes the full raw populations, source fingerprints, effective per-country
historical input values/source years/fallbacks, identity configuration, generator
policy/source and commit. CSV contains one player per world/seed and all seven
attributes. JSON's country lists also preserve countries absent from the raw rows,
so zero representation can be recomputed. Quantiles use the existing Lab's linear
interpolation; observed pooled summaries are not theoretical probabilities.

Tour registration counts are unavailable: these fresh generated profiles have no
first valid application or authoritative registration history. Neither age nor
career stage substitutes for entry. No retired player history is imported and no
retirement simulation runs; generated ages remain 15–45. Master §9.1 additionally
requires fifteenth birthdays *before* opening Week 1: the reproduced seed 315,
country BOG, sequence 1 previously yielded age 15 with birthday 1985/W37, exactly
in opening Week 1. The fix only resamples that birthday collision on its separate
birth RNG stream and updates the corresponding birth-cohort weights. It does not
retune potential, current ability, growth or historical country attributes.

## Repeatable local measurement and browser check

Use the existing Python/Node setup; no lockfile/dependency refresh is needed.
Run from the repository root. All generated populations and SQLite stores remain
in disposable `work/`; do not commit raw exports.

```sh
.venv/bin/python scripts/earth_initial_population_experiment.py
```

This measures the specified `2000/01`, 2 × 5 × 1000 experiment with seeds
101,202,303,404,505 through the actual production service. It saves JSON/CSV and a
measured summary under `work/earth-population/production`, verifies source byte
hashes before/after, and reuses identical saved sessions. The summary records the
commit/source fingerprint used; later documentation-only commits do not cause a
new generation. Timings include read-only source preparation separately from each
population's generator time.

With Playwright installed and system Chromium available, the optional browser
script starts production FastAPI/SQLite and Vite on isolated localhost ports,
performs all writes by clicking actual Lab UI, downloads JSON/CSV, compares UI
counts/players/metrics with exports, restarts the backend, opens a fresh browser
context and verifies read-only restoration. It also opens the main measured
session when present, without rerunning the experiment.

```sh
PATH=/workspace/.runtimes/node20/node_modules/.bin:$PATH \
  .venv/bin/python scripts/earth_initial_population_browser_smoke.py
```

Override `--root`, `--chromium`, `--api-port`, or `--web-port` where necessary.
Playwright is an optional local verification dependency, not required by Fast CI.
The small HTTP regression uses synthetic disposable source fixtures and real
production generator/API/SQLite. Component/client tests mock only the HTTP
boundary and are not browser evidence. The main 10000-player experiment is a
separate measurement and is never a CI load test.

## Interpretation boundaries

Country allocation uses deterministic largest-remainder counts from historical
birth-cohort weighting, so it is seed-independent. Country quantity resolves
cohort-year population and ratings; development resolves the initial season year,
not a blanket 2026 reference. Every used historical fallback is exported.

The child RNG is keyed by seed, season, country code and country sequence, with
versioned BLAKE2b derivation; World ID is absent. Shared country/sequence profiles
can share latent draws. Different country allocation and effective environment
prevent treating the entire populations as perfectly paired observations.

Both packages remain `realism_validated=false`. Differences and five seeds do not
establish realism or the behavior of extremely rare talent tails. Real-world
squash population and talent distributions have not been supplied for calibration.
Measured findings and browser evidence are recorded below after acceptance.

## Measured experiment — 10 October 2026

Production engine commit: `74c0d21ef9ad19cf35cf1a150ae9607819f3fae8`;
Python source fingerprint:
`fafeb4ed0a4f4f9ae469d4b54367f07c7ea29194d30b3fc7f625a804f313b166`.
Later changes only clarify UI presentation/tests/documentation; the measured
production generator and Python source remain unchanged.

Saved session:
`player-population-c05b5ef1aa2b6b2a4bf0fb442e302021051e6c58b85115f56a2a6d7c480b8c7b`.
Payload fingerprint:
`d5dee02adebf4085b306f8a195165d6048be15161993da5554fcc4cbf787b6fe`.
The full exact fingerprint is also in the compact evidence JSON.

The pre-experiment engineering benchmark measured one real FIFA snapshot in
14.38 s and 1000-player generation in 0.53 s. It preceded the birthday-boundary
fix, and is not mixed into the accepted experiment. The accepted 10-run experiment
uses the corrected policy, takes 43.88 s including input preparation/statistics,
and 0.585–0.687 s per production generation (6.03 s total generation). Total timing
is captured before final payload fingerprinting, SQLite save and file export;
the remaining time primarily covers historical input loading/validation.

Both sources have 250 countries. FIFA source fingerprint:
`a7c1eac680175b0a0c128bff769f8da24438071bc408ad8bdc123b6dab6d9428`;
ATP: `7b4335c2fe50ad274ee384f1f07accaecee51931a77d719c27ed15c363576e60`.
Both used ratings from 1955–1985 for birth cohorts and 2000 for development,
with explicit 1954→1955 nearest-year fallback for each country's oldest cohort.
No 2026 ratings were silently used in these runs.

### Country differences

Counts below are **per 1000-player population**, identical for all five seeds.
Pooled counts are exactly five times these; the full 250-country table is in the
compact evidence and Lab, including zero-capable rows.

| Country | FIFA count / share | ATP count / share |
| --- | ---: | ---: |
| China | 41 / 4.1% | 20 / 2.0% |
| United States | 6 / 0.6% | 49 / 4.9% |
| India | 15 / 1.5% | 47 / 4.7% |
| Brazil | 21 / 2.1% | 28 / 2.8% |
| Japan | 7 / 0.7% | 28 / 2.8% |
| United Kingdom | 24 / 2.4% | 27 / 2.7% |
| Germany | 26 / 2.6% | 21 / 2.1% |
| Egypt | 15 / 1.5% | 15 / 1.5% |
| Pakistan | 3 / 0.3% | 12 / 1.2% |

The existing allocation is more than proportional largest remainders: it floors
weighted quotas, gives an initially empty country one player when the pool can
cover all countries, then reconciles excess/remaining quotas. At 1000 players,
**every country is represented**; 121 FIFA countries and 150 ATP countries have
only one player. Monaco and Vatican City each have one. This deterministic rule
can materially inflate small-country representation and dilute stronger countries.
It is current model behavior, not corrected as an implementation bug in this PR.
The broad statement “largest remainders” in saved interpretation should be read
with this minimum-one and quota-reconciliation rule; the exact generator source
is preserved in the export.

### Abilities, ages and seed variation

Pooled values use 5000 observations per world on the existing initial-pool scale.

| Metric | FIFA | ATP |
| --- | ---: | ---: |
| Age mean / median / P99 | 25.10 / 24 / 44 | 25.12 / 24 / 44 |
| Potential mean / median / P99 | 75.23 / 75 / 99 | 75.22 / 75 / 99 |
| Current ability mean / median / P99 | 60.50 / 60 / 93 | 60.27 / 60 / 92 |
| Existing S tier count / share | 563 / 11.26% | 536 / 10.72% |
| Potential ≥95 (analytical threshold) | 297 / 5.94% | 295 / 5.90% |
| Potential =99 (model ceiling) | 57 / 1.14% | 51 / 1.02% |

All ages lie in 15–45 and all fifteenth birthdays precede Week 1. Individual
attribute distributions and quantiles are available in the Lab/compact evidence.
Their pooled mean ATP−FIFA differences range from −0.1946 (mental) to −0.2836
(recovery), consistent with the slightly lower overall current ability in these
samples. These small pooled differences do not establish population realism.

| World / seed | Potential mean | Current ability mean | Existing S count |
| --- | ---: | ---: | ---: |
| FIFA / 101 | 74.880 | 59.651 | 108 |
| FIFA / 202 | 75.641 | 60.998 | 108 |
| FIFA / 303 | 75.483 | 60.824 | 130 |
| FIFA / 404 | 74.788 | 60.339 | 110 |
| FIFA / 505 | 75.358 | 60.683 | 107 |
| ATP / 101 | 75.106 | 59.531 | 102 |
| ATP / 202 | 75.601 | 60.888 | 103 |
| ATP / 303 | 75.189 | 60.673 | 120 |
| ATP / 404 | 75.204 | 60.190 | 108 |
| ATP / 505 | 75.011 | 60.056 | 103 |

Population SD of seed potential means is 0.337 FIFA and 0.202 ATP; current-ability
means 0.476 and 0.478. Country count SD is zero. At seed 101 the worlds share 808
country/sequence IDs, all with identical sampled potential and age: the common RNG
stream materially correlates samples. These are not independent paired populations;
country allocation and historical development environment still differ.

Potential is never below 50 in these samples because the current generator's
lowest tier samples 50–62. The S label is present in roughly 11% of profiles,
so it cannot be assumed to signify a very rare real-world superstar class. These
are explicit behaviors of the existing model, not evidence for probability tuning.
The P99/ceiling observations and five correlated seeds cannot validate extremely
rare talent or actual squash ability distributions. Tour entry and retirement
history are absent from initial profiles; career-state realism cannot be assessed.

### Actual verification and evidence

- Independent recomputation from all ten raw populations and 10000 CSV rows checked
  100 metric distributions' means, medians, P99s, histogram totals and country
  totals, with exact per-world/seed CSV sums. Main raw exports are not committed.
- Actual Chromium/Vite/FastAPI/SQLite generated and saved FIFA and ATP populations
  of 32 players at seed 909 **through UI**. UI world selection, country counts
  (all 250 rows, including real zeros), actual player identity, current metrics and
  both downloaded exports matched. No mocked responses supplied this evidence.
- Backend termination/restart and a fresh browser context reopened that session
  with the same raw gameplay fingerprints and no POST/regeneration. The main
  measured 10-run session also opened in the browser without regeneration.
- Source byte-tree hashes matched before/after both measurement and browser flow;
  no Run was selected/created, no Run store or official source was modified.
- A repeat browser check after table spacing fixes reused the identical saved
  32-player session; it did not regenerate populations.
- Local targeted checks: 42 backend tests including the existing initial-pool
  regressions; the final new targeted modules contain 12 PR-critical tests.
  Eight frontend component/client tests passed; frontend production build passed.
  Fast CI status is verified separately on the final PR commit before delivery.

Screenshots and compact measured/session evidence:
[`earth-initial-population-evidence/20261010`](earth-initial-population-evidence/20261010).
Large raw populations and disposable databases stay in `work/`.

**One recommended next PR:** add a controlled allocation-size sensitivity
experiment in this existing Lab (250/500/1000/2000), comparing the actual
minimum-one/quota-reconciliation outputs with the exported authored model weights.
Reuse this 1000-player result, quantify small-country inflation, and then present
any proposed allocation calibration for an explicit product decision. No automatic
probability/model retuning and no annual-intake mixing.
