# Atomic Run prospect cohort reconciliation (19 October 2026)

This change repairs a source-authority race in the existing materialized
15-year-old cohort workflow. Previously a reviewed overwrite checked conflicts,
inserted/updated records and deleted stale records across separate SQLite
transactions. A late failure could leave half a policy's cohort in the Run.

The reviewed preview fingerprint and deterministic profile generation remain
unchanged. The production writer now takes one SQLite BEGIN IMMEDIATE
transaction and computes source-policy/stale-record conflicts and activated
identity protections **inside** it, then upserts and removes only the
reviewed Run/season/country/source scope. It rejects colliding IDs already
owned by a different season and returns counts from that committed transaction.
Original prospect profile, seed, snapshot and Saved Revision schemas do not
change. Immutable activated rows remain protected.

New real SQLite regressions check idempotence and foreign-season collisions and
inject a database DELETE trigger failure *after the other changes were staged*,
asserting complete rollback. Existing cohort materialization/overwrite/activated
player tests remain required. No timeout or browser population reduction.

**Boundary:** This is a real integrity fix for the existing Run-scoped
materialization writer, not native W52/W80 generation, sporting-state insertion,
automatic 15th-birthday activation, full Tour Entry or Full Simulation. The
native Calendar Tour prospect guard remains intact pending the versioned,
coupled lifecycle + sporting + Health + ranking insertion.
