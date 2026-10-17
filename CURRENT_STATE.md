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

**A84-01 regression repair (this PR; verification required):** the older
`test_old_calendar_immutability_and_new_extension_remains_explicit` now expects
the correct strict-extension predecessor behavior for W52/61/80. It checks
preserved predecessor JSON/hash/clock, exact lineage, and rejection of horizon
shrinkage, different W/offset/start, skipped weeks and legacy clocks. The
production ranking implementation is unchanged. The v84 audit's 146/147
pre-fix result remains historical evidence, not a current green claim. Run
both directly related backend modules together and verify this PR's final HEAD
before merge. Release regression remains a separate gate.

**Next integration:** PR #1521 fixes A84-01. This proposed slice implements
a calendar-native real standalone BO5 MatchEngine match from a Saved v2
population, with exact SQLite receipt/replay and regular immutable manual Save
on W52/W80. It does **not** migrate official Tournament/Slot/Health/57-attribute
sporting effects, points or transitions. A CS/EN Admin panel is implemented;
a real Chromium acceptance of that new panel is not yet proven. Forking from a
match-containing Saved Revision is currently guarded; see
[match contract](docs/CALENDAR_STANDALONE_MATCH_V84.md).

Continue with native sporting state, main-only tournament, and
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

## New implementation candidate — opening-week four-player knockout

#1522 is merged on `buuk` at `f4e4b06eae162bf441b4e1ff279361115ed0ce05`.
This candidate adds a real four-player W52/W80 opening-week main-only
knockout with two independent frozen-input semifinal MatchEngine runs,
winner-fed final, deterministic replay of three authoritative logs,
normal atomic SQLite command receipt and existing explicit immutable
Saved Revision capture/restart/restore. The original one-match exhibition
schema remains loadable with unchanged bytes; the shared Saved calendar
match component now explicitly discriminates the new bracket schema.
CS/EN Run Simulation selector exposes the new operation.

This is **not** a canonical tournament ranking writer, official point
publication, developed 57-attribute sporting state or Week/Season
Transition. One first-week operation per Branch remains the deliberate
boundary; a match-containing Saved fork is still blocked. See
[calendar opening knockout contract](docs/CALENDAR_OPENING_KNOCKOUT_V84.md).
Verification and browser acceptance remain required on the candidate
final HEAD, not assumed green.

## Next merged milestone and scored candidate (October 17, 2026)

`buuk` is now `b76172a358d7b33ef1b0760b94ecd836647fcd67`
after owner merge of #1523. The W52/W80 three-match real knockout,
exact immutable Save/replay/restart, historical restore and CS/EN Chromium
acceptance are merged (not Official tournament point publication).

This new candidate builds a second real writable/Saved vertical slice:
reviewed operator-authored knockout points derived from the exact previously
Signed MatchEngine bracket; four placements, W-year validity, W2 proposed
first publication, strict preview/confirm, exact receipt and a distinct
second immutable manual Save. The input policy remains **operator-configured,
not original Category/Edition authority**, and all points retain
`prepared_not_official` status. No ranking transition writer, Week/Season
Transition, World Events, viewer exposure or durable Full Simulation bridge
is claimed. See `docs/CALENDAR_KNOCKOUT_PREPARED_AWARDS_V84.md`.

Check final-head backend/frontend/Chromium results before calling it merge
ready. Never rewrite historical Signed v1 match data or remove W61 guards.

## Current candidate: exact Signed W52/W80 as-of tournament standings

After owner merge of #1524 into `buuk` (at
`5610776a1e1708a5f46bc7b2acf6fe7c4d537513`), the scored
`calendar_scored_opening_knockout.v1` is durable behind two explicit Saves.
This next candidate delivers a read-only, production SQLite-authenticated
**one-event tournament scoreboard**, derived from those genuine signed
matches/points at a user-selected Run season/week, with correct W-year
expiry (S2W2), signed provenance, API and CS/EN browser controls.

This remains **NOT** the Official Tour Ranking, not a published ranking
snapshot and not a completed Week Transition. Explicit reasons:
`population_only` lifecycle is not Tour entry, the operator-authored
policy is not authenticated Category/Edition configuration, and no native
W-aware transition has advanced the clock. No 1,000-player world ranking
is fabricated. Older Saved payloads, legacy W61 writes and historical
ranking are untouched. See `docs/CALENDAR_SIGNED_KNOCKOUT_STANDINGS_V84.md`.
Final-HEAD checks and browser acceptance are required before merge handoff.
