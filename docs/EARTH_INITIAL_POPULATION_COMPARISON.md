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
