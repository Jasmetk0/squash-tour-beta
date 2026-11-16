# Giant native Tour load experiment (five signed seasons)

**Status: experimental load harness, NOT a passing five-season release gate.**
This PR adds no production engine, model, sporting rule, persisted format, API, or
existing CI change. Work should review the implementation and the actual Actions
artifacts before interpreting any performance results. Only the owner merges.

## Purpose and exact workload

- Real production HTTP server and isolated SQLite database, not a synthetic
  arithmetic loop or fabricated tournament winners. Commands use existing
  preview/confirm/explicit Save; matches run through the global Simulation Slot
  and actual MatchEngine.
- Initial generated/signed world: **1,000 players**.
- **Five completed 52-week seasons**, i.e. 260 scheduled week positions. The
  native Tour initialization consumes Week 1 before the first explicit Tour
  transition; the fixture then completes all remaining weeks. A six-season
  *calendar horizon* is deliberately used solely to allow the final fifth
  Season Transition to create a signed archive. The sixth season is NOT simulated.
- **24 ranked Editions per season, 120 total**, at weeks 4,6,...,50.
  Four synthetic point-table tiers named Satellite, Challenger, International
  and Major with **4, 8, 16, 32 entrants**. These are load-profile labels and
  valid ranked Edition configurations, NOT claims about the final ATP/FAX
  category implementation. Each has its complete engine-required stage table.
- **16 signed new 15-year-old prospects each season**, 80 across five seasons;
  native weekly transitions, not direct insertion into a roster, activate them.
  Future eligibility remains governed by the engine's actual recorded policy.
  Tournament entry uses genuinely eligible initial professionals, never forces
  a new minor directly into the professional draw. This stresses population
  growth without falsifying the Turn Pro model.
- Deterministic seeds, separate edition IDs, explicit and immutable Saved
  history. No shared FAX/world config or real user Run is modified.
- Counts and evidence are asserted; an incomplete run remains *incomplete* even
  if it produced useful performance diagnostics.

## How the run is isolated

Workflow: `.github/workflows/giant-native-five-seasons.yml`.

1. Only this experiment's paths can trigger its automatic PR run.
2. The long run lives in its own GitHub Actions job, its own disposable runner
   and its own concurrency group keyed by PR; it is not imported into ordinary
   pytest, browser acceptance, Sonar or the main Fast CI workflow.
3. Opening the **Draft PR** intentionally triggers it. Changes to this PR
   cancel only the superseded giant benchmark, not jobs belonging to other PRs.
   Manual `workflow_dispatch` is also declared for later reruns once GitHub
   recognises the workflow on its default branch.
4. There is a **315-minute internal wall-clock budget** and **350-minute job
   timeout** (with time reserved for artifact upload), so a slow run is reported
   as `budget_exhausted` rather than silently presented as passing.
5. The script refuses to overwrite a previous benchmark database. It uploads
   **summary.json, timeline.jsonl and console log**, not a potentially huge
   SQLite database or player personal data. Artifact retention is 21 days.

**Important limitation:** separate workflows avoid *direct* merge-check and
concurrency cancellation interference, but GitHub-hosted jobs may still share
the account's runner-concurrency/billing quota. This cannot guarantee zero
queuing or resource impact on other PRs. If that resource contention matters,
cancel this run and use a dedicated/self-hosted runner later.

## How to read the results

`summary.json` gives the actual status (`complete`, `failed`, or
`budget_exhausted`), elapsed seconds, last completed position, actual player
counts, Editions, matches, season closures, SQLite bytes and Saved count
on full success. `timeline.jsonl` records timings by operation and week,
every completed Edition's participant/result evidence and each signed season's
overview. It also records peak process RSS.

**Do not extrapolate all five seasons from the first week using a linear
multiplier**: Saved history and re-validation cost can grow with history
length. A credible total-hours figure requires the actual completed run, or
at least a defensible model fitted to measured later-season data. The budget
limits one GitHub job; it is not a prediction of completion.

Useful quick checks (without running the costly simulation):

```bash
PYTHONPATH=src:. python -m pytest -q tests/application/test_giant_native_load_plan.py
python scripts/giant_native_five_season_load.py --plan-only
```

To run the real experiment locally, with **a separate empty output folder**:

```bash
PYTHONPATH=src:.:tests/api python scripts/giant_native_five_season_load.py \
  --seasons 5 --players 1000 --editions-per-season 24 \
  --born-per-season 16 --budget-minutes 315 \
  --output-dir /tmp/giant-native-test
```

This experiment does not claim a 50-season/FAX reference release result and
does not replace the independently hosted W52/W61/W80 reader benchmarks.
