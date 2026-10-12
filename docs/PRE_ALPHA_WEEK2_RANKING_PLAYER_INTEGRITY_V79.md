# F79-10 — real Week-1 Official Ranking → Week-2 consistency acceptance

The existing browser tournament workflow already completes the initial Official
Ranking, entry/draw, three real matches and a successful Week Transition.
This slice adds an **independent production Chromium / SQLite integrity witness**
without changing simulation mechanics. It is not a new sporting algorithm.

## Real journey
1. Create an isolated custom Run and Run-owned World; generate, adopt and save
   64 initial players through real Admin forms; calculate and publish the
   first Official Ranking and commit applications for a real four-player event.
2. Capture raw canonical SQLite InitialWorld bytes, the original Published
   Ranking and candidate bytes, Saved Revision ancestry (IDs, hashes and full
   payloads), world clock and Week-1 player states.
3. Through real UI simulate the complete tournament (two semifinals and final),
   save authority, derive Week-2 Ranking Transition Authority and run the exact
   reviewed Week Transition with the explicit **Save transitioned week**.
4. Verify the Viewer shows the historical Week-2 table of 64 players and
   **100 / 60 / 30 / 30** points for the played tournament.
5. Compare each original immutable Saved Revision including its content hash
   and full bytes. Week-1 published ranking and ranking candidate stay exactly
   unchanged. New Saved Revision extends ancestry and Week-2 Official Ranking
   is published. The authoritative world clock points at ordinal 1.
6. Verify Week 1/2 player lifecycle/sporting/health projections: both are
   season 0, correct week ordinal, have only original player IDs, Week-2
   predecessor evidence and exact InitialWorld provenance. Sporting need not
   fabricate profiles for inactive identities not in its source model.
7. Stop and restart the actual production backend, open a **new** Chromium
   session and verify Viewer ranking is identical and the entire inspected
   persisted SQLite authority snapshot (rankings, revisions, player projections,
   world clock, original InitialWorld) is byte-identical.

## Automation and scope
- Production acceptance: `scripts/admin_week2_integrity_browser.py`.
- Path-scoped GitHub workflow:
  `.github/workflows/prealpha-week2-ranking-integrity-browser.yml`.
- Fast focused tests: `tests/api/test_week2_browser_integrity_contract.py`
  feed the actual pure comparator adversarial forged examples: a rewritten
  ancestral revision, altered Week-1 ranking, invented player, missing health
  player, erased predecessor, absent Week-2 ranking, missing Week-2 Save or
  wrong canonical clock.
- Reuse `scripts/admin_first_tournament_smoke.py` as the already-supported
  genuine Admin/Runs backend and tournament workflow. It remains untouched.

This is **not** an internal pre-alpha release declaration; the complete
50-season and Week-61/Season Transition release checks remain separate.
The workflow only triggers on changes to this new scenario or explicitly via
workflow_dispatch; unrelated routine PRs do not incur extra browser cost.
