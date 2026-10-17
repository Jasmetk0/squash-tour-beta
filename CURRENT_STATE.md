# Current implementation — Master v84

Audited `buuk`: `5dce12a07acb980882a5454485681f9eb7e5af79` after merged #1519
(17 October 2026). All #1508–1519 merged, no open PR at inventory. Refresh before
new work. This documentation candidate adds product decisions/evidence, no runtime
fix and no release claim.

**Usable merged flows:** versioned Run creation/calendar/first Save; exact Saved
clock reads and annual age helpers; calendar-owned initial player adoption +
manual Save/fork/restore; initial Health and Injury/Illness editing. #1508 now
really delivers reviewed all-Branch horizon extension + explicit atomic Save,
immutable history, origin-clock provenance, exact receipt/retry and CS/EN UI.
#1509 adds current Saved-content Home readiness with repair links. Extension
preserves Completed/task states; it does not start work or unlock sporting writers.

**Ranking progress, bounded:** #1510–1512 provide W52/61/80 point reports,
Official Ranking candidates, corrections/zeros/history and monotone-horizon
lineage. #1513–1514 persist/recover internal staging only. #1516–1517 bind full
main-only knockout and MatchEngine-shaped evidence. #1515/#1518/#1519 verify
Saved canonical awards and/or real Saved Slot match receipts against live SQLite,
but only for reference FAX W61/offset37/start2000/50 seasons. No native W52/W80
sporting publication, Saved ranking ownership or actual transition is thereby done.

**Confirmed regression A84-01:** the old domain test
`test_old_calendar_immutability_and_new_extension_remains_explicit` contradicts
#1512's correct strict-extension behavior. Joint audit: 146/147 new backend tests
pass, this one fails; isolated reproduction 1 failed/3 passed. Fix the stale test,
retain extension support and old bytes/hashes, run both affected modules together.
Do not call the backend completely green based on narrow final-HEAD CI subsets.

**Next:** repair A84-01, then a usable calendar-native Run-owned real match/
main-only tournament with production manual Save/replay/restart. Follow with
real configured point publication, Saved capture/restore/fork, Week/Season
Transition and Full Simulation migration. Prefer operational integration over
more standalone source-attestation helpers. Exact task and reviewed limits:

- [v84 audit](docs/PRE_ALPHA_CHECKPOINT_V84_2026_10_17.md)
- [complete direct-ChatGPT task](docs/PRE_ALPHA_NEXT_CHATGPT_TASK_V84_2026_10_17.md)
- [Master](SQUASH_ENGINE_MASTER_VISION.md) 9.9/21.3.1/27.24/31.39/35.41

**New canon, not implementation evidence:** Automatic totals with exact partial
quotas; preserving unaffected concrete players; natural-model anomaly diagnostics
without invented causality; partial search does not meet unmet hard constraints.
Extendible records catalog, holder history/leaderboards, combined filters and
named Saved Views with fixed/rolling periods. v83 historical-cohort bootstrap,
full preparation workflow and selected Package export remain incomplete targets.
Initial-rule inheritance to future intake remains explicitly deferred.

## Boundaries and verification

Owner alone merges; ordinary ChatGPT implements directly, no paid Codex/agents
unless explicitly requested. Preserve simultaneous Slot inputs, exact history,
source Packages, equal Branches, task leases/frozen targets and explicit recovery.
Old FAX snapshots are not reinterpreted by a new W. Legacy guards still reject
unsupported clocks, including extended reference horizons. Candidate/staging
rows are not Saved facts or permission to simulate.

All triggered CI on final heads #1508–1519 succeeded; see audit for exact run IDs
and selection counts. New local frontend 21 tests + production build passed.
Another 39 directly affected authority/transition/fork/restore tests passed.
The joint new backend audit has the explicit A84-01 failure above. No new browser run, whole
populated season, 50-season release or realism acceptance was performed here.
Earlier evidence remains in Master chapter 35 and Git history; v84 replaces stale
candidate appendices rather than preserving them as active instructions.
