# F79-07: Add Selected real browser + SQLite + restart

A narrow, production API/Chromium/SQLite acceptance for F79-06.
Test script: `scripts/admin_selected_append_browser.py`.
Hosted workflow: `.github/workflows/prealpha-selected-append-browser.yml`.

The acceptance boots one temporary production application with a disposable
SQLite database and separate Vite UI, creates a true custom Run and saved
World, generates 32 players through browser and uses the real Adopt and
manual Saved Revision buttons.

It then creates a separate 200-player generation source via the UI:
- Identifies source country-serial ID collisions with the saved world, selects
  one existing ID and verifies the Add action is blocked *without a write*.
- Deselects the collision, uses actual player-ID search UI to select two
  different non-colliding source IDs across search/filter transitions.
- Sends production server selected-append Preview; checks selected IDs,
  32 preserved player models and count 34, without changing saved or live data.
- Confirms the exact returned fingerprint through production Commit and
  checks no Saved Revision was silently written.
- Checks SQLite Week-1 lifecycle, sporting and health source fingerprint
  and exact 34-player identity coverage as well as original full player bytes.
- Executes manual `Save InitialWorld revision`, compares all *old revision*
  row IDs, payload JSON and content hashes against pre-append copies, verifies
  newly saved revision contains 34 profiles and append lineage.
- Terminates backend, starts the same production API against the same SQLite,
  opens a new browser context and checks 34 saved players, identical immutable
  revision history and identical Week-1 player state payloads/fingerprints.
- Retains screenshots, Playwright trace, server logs and machine-readable
  evidence to diagnose any failure without rerunning unrelated workflows.

**Scope:** pre-ranking Week-1 opening only. This asserts true Add Selected
rather than conflating the previous whole-cohort 1000-player acceptance with
selected append. Does not authorize midseason inserts, overwrite players,
post-ranking append or 57-field canonical calibration.

**Cost:** a dedicated path-limited workflow, not bundled into every routine
Fast CI run. Full internal-release gates are unchanged.
