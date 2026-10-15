# Real hybrid Week 2 → next Week after actual SQLite server restart

PR #1482 follows merged #1481. The first Full Simulation parent is an
immutable audited terminal `target_reached` command at Week 2. Reopening it
would breach the existing parent contract, so this acceptance **never**
pretends that the same terminal parent continues. Instead, after real
MatchEngine group matches, knockout and original-worker Week-1→2 transition,
Admin explicitly Saves the published Week-2 Edition and kills/restarts the
SQLite server process. The test validates the first parent remains terminal
after restart.

A genuinely **new** server-owned Full Simulation task with distinct parent,
original immutable Run/Branch/saved Week-2 fingerprint and idempotent
start receipt then advances at least one additional canonical week, with
real full task worker execution, without creating any new sporting replay.
The original three group+knockout receipts and prior published ranking
remain byte-for-byte identical. The later world position may become newer
than public Viewer (Save still requires an operator). Both original and
second task must appear in real Chromium Task Center.

Separate CI workflow `.github/workflows/prealpha-full-sim-real-hybrid-second-week-browser.yml`
runs in addition to the original Week-1→2 browser acceptance and backend
PR-critical tests. This does not claim that a terminal target can be
extended, or that all 50 seasons finish automatically.
