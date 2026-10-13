# Real completed Group tournament → historical Saved Edition acceptance (phase 2)

Date: 2026-10-13. This adds the missing end-to-end proof after merged
[#1424](https://github.com/Jasmetk0/squash-tour-beta/pull/1424), which proved
only the *pre-result* group Schedule/Save/browser/restart. PR #1425 is separately
developing Admin Format/Topology setup UI; this acceptance does not modify it.

## What this dedicated Chromium acceptance tests

1. A new, temporary SQLite Run with real generated 64-player world; the real
   browser approves and freezes a four-player Event Entry Field.
2. Production FastAPI Group Rules v1, Format, Topology and exact six BO3
   round-robin matches across three Match Days.
3. The fingerprint-locked Simulation Save captures the *pre-result* revision.
   This revision must remain unchanged after subsequent sporting commands.
4. The authoritative global topological Week Schedule is **proposed and
   adopted** through production HTTP, not generated from test-owned fixtures.
5. The production AuthoritativeRunSimulationDriver executes the selected
   tournament's six real group matches. The replay/idempotency behavior is
   also checked with the same command ID.
6. Actual group result receipts are consumed by the production
   `group-standings/generate` command. Exactly four players, six played
   victories, six defeats and twelve player-match appearances are required.
   If an otherwise unresolved group tie arises, a separate explicitly
   confirmed and auditable Admin decision freezes the canonical player-ID
   ordering of *that exact evidence*, never silent automatic guessing.
7. A later fingerprint-locked Simulation Save stores frozen complete standings
   in a new immutable Saved Revision. Edition Results in *real Chromium*
   renders the actual four-row group table. No fake canonical published
   tournament result is introduced before independent ranking closure.
8. The process is restarted against the same SQLite file, and both old
   pre-result and new final Saved Revision responses must be byte-for-byte
   identical. Both historical Edition views are reopened in a new real
   browser context with screenshots and traces.

## Integrity constraints and honest limits

No mock API, synthetic scoreline, direct DB insertion of outcome, RNG mutation,
implicit Save, false Match Day dates or fake historical results. The old
pre-result Edition remains a six-fixture schedule *without* standings.
The last revision is verified as completed group standings, not necessarily
a ranking-closed tournament or a hybrid knockout champion. Phase 3 may add
pure-group ranking closure and a real *hybrid* knockout completion, with
its own canonical authorities and acceptance.

The existing dedicated
`.github/workflows/prealpha-saved-group-edition-browser.yml`
runs the original phase-1 checks **plus** phase 2 in one isolated workflow,
rather than running the long bootstrap twice or adding costly CI jobs.
Focused `pytest -m pr_critical` checks reject incomplete, forged or
walkover-filled simulated group summaries.
