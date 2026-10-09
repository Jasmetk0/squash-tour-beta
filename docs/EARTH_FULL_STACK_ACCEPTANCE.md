# Two-world Earth full-stack acceptance

The existing `tests/application/test_earth_world_package_run_integration.py`
contains **two** `smoke`-marked, real production HTTP/SQLite end-to-end
acceptances. Each independently covers:

1. Applying a frozen FIFA Earth or ATP Earth World Package and Calendar to an
   empty canonical Run, then removing the disposable original World source.
2. Deterministically previewing and adopting a **1,000-player** historical
   InitialWorld, creating/saving the initial Official Ranking and publishing it.
3. Completing **three** consecutive genuinely event-free weeks with saved
   authoritative Simulation, derived Ranking, and confirmed Week Transition.
4. Restarting the HTTP API against the same SQLite store and verifying the
   saved Run still uses its own World Package snapshot.
5. Creating a Week-4 Branch and verifying distinct target-owned sporting state,
   three Week Transition receipts and three World Events, and an unchanged
   source Branch.

Run from GitHub Actions **Earth Full-Stack Acceptance** → **Run workflow**
on `buuk`. The two packages execute in independent GitHub runners so a
failure in one does not conceal the other. All HTTP step timings and pytest
results are preserved as downloadable per-world artifacts even when a job
fails. The workflow also self-tests on PRs that change its own definition;
**ordinary PRs do not invoke this expensive smoke gate**.

A successful run proves these exact event-free, three-week, two-world paths.
It is *not* equivalent to full pre-alpha approval: tournament/discipline
completion, Season Transition, the 50-season Official Run, manually authored
matches, the complete backend regression suite, and full frontend checks
still have their own acceptance requirements
(`docs/PRE_ALPHA_TEST_POLICY.md`).

During investigation, a red/timeout result is an actual blocker for this
acceptance: do not weaken authoritative fork checks or shrink the 1,000
players/three-week requirement to make the workflow pass. Fast CI remains
focused and separate.
