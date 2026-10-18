# Native sporting-week preparation v1

Based on merged #1531 / buuk `642617430b66853285415ac6690d89165e2c47e2`.
Master remains v85. This changes implementation, not product canon.

After the Saved v5 opening knockout, Admin can inspect, confirm and manually Save
native weekly development/recovery, then play further actual exhibitions from
that Saved sporting state in week 2, 3, etc. Empty sporting weeks are supported.
The explicit stop is the end of the first season; Season Transition is unsupported.

## Authority and scope

`calendar_sporting_checkpoint.v3` retains the exact original opening continuation
prefix and an ordered `week_events` ledger of sporting advances and later v2
matches. Rebuilding the original population/knockout, folding the historical v1
matches, then every new event must equal the entire stored current population.
V1/v2 checkpoint serialization omits new fields; the old v1 hash remains pinned.
Old knockout v1–v5, prepared points, initial population and Health bytes stay exact.
No SQLite schema migration or second population owner is introduced.

This is the sporting substep on an **exhibition timeline**, not the complete
nine-step Official Week Transition. It does not advance the legacy scheduler,
publish/recalculate Official Ranking, add intake, update lifecycle, retire players,
activate seasonal policies or heal Health facts. Those operations remain guarded.
The existing Health snapshot is consumed unchanged by later matches; no future
medical facts or numeric Health effects are invented. This remains visibly stated
in CS/EN Admin. Native sporting time must not be confused with the legacy/public
world time, which is not advanced by this slice.

## Pure calculation and units

The completed-week terminal sporting owner supplies all 57 integer attributes,
individual potential identity/provenance, development timing, terminal Form and
current load. The immutable initial population supplies birth identity only.

1. Calculate development from completed-week age (an exact fraction of a Run year),
   individual timing, potential and terminal Form **before** regression.
2. Apply weekly Form regression toward the individual norm, sharpness decay only
   for players without a match in that completed sporting week, and fatigue recovery.
3. Make these records the valid starting state of the next sporting week.

`calendar-annual-development.provisional.v1` freezes a new explicit annual adapter
of the existing provisional development calibration: reference 18 bp/week at W61
becomes 1098 bp/year; reference Form influence 4 becomes 244 annually. The yearly
threshold is divided by W with integer arithmetic. Whole increments plus a
remainder draw preserve expected annual exposure even for very small W, subject
to attribute boundaries and the provisional potential-based growth cutoff. This is not a
claim of empirically calibrated development curves or identical random paths.

Age uses stored birth year/week and the native calendar offset, not a universal
RankingWeek ordinal. Recovery 8, inactivity decay 2 and Form regression divisor 8
retain explicit weekly units and are not divided by W. These are the already
existing provisional numbers; detailed training/deload and final calibration are
not decided here. New events freeze the actual outgoing policy and both development
and recovered-record fingerprints. No target-week scheduled event enters the math.

Completed match counts come only from real stored knockout evidence and the
continuation matches in the completed week. They are exhibition load evidence,
not a fabricated Official competitive-result classification.

## Commands, Save, history and UI

POST `calendar-sporting-week/preview` accepts exact Saved HEAD, checkpoint hash,
command ID, seed, operator and reason; it is read-only and returns a full reviewed
fingerprint, policy, before/after changes, completed/target positions and resulting
checkpoint hash. POST `…/commit` requires that exact preview and explicit consent.
It recomputes under `BEGIN IMMEDIATE`, validates everything, and replaces the owner
atomically. Any error rolls back the complete replacement. An exact retry rebuilds
its original prefix and returns the same original response after later Saves,
matches or horizon extension. Reused identities/conflicting reviews are rejected.

The resulting live owner requires separate manual Save through the existing
checkpoint Save path. No new play/advance can consume an unsaved predecessor.
Immutable history, restore backwards/forwards, cold restart and original match
replay use the same validated component. Save audit includes counts of both matches
and sporting weekly advances. Compatible horizon extensions preserve old event
calendars; newly appended events consume the extended native calendar.

Actual later MatchEngine calls use new `calendar_continuation_match.v2` and a v2
input anchor, current stored 57 attributes/form/load, and current age derived from
birth identity. Historical v1 matches keep their original opening-week semantics.

CS/EN UI provides a read-only review, changed-player/attribute counts, separate
weekly consent, weekly history and separate Save review/confirmation. Source
Run/Branch/HEAD and changed inputs invalidate stale responses and consent. Existing
match replay and population-record inspection expose the actually stored state.

## Validation

- Pure tests: exact annual units for W1/W52/W61/W80, unchanged weekly recovery,
  completed terminal Form before regression, fractional birth age, no future or
  missing-roster inputs, historical-schema rejection and Season boundary guard.
- Production HTTP/SQLite cases at W52/W80: read-only repeated preview, explicit
  consent, wrong-review rejection, failure after actual row replacement rollback,
  retries, manual Save, actual week-2 MatchEngine inputs/replay, week-3 load counts,
  empty week, immutable root, corruption after outer rehash, restart, restore and
  all-Branch horizon extension with exact old retry.
- UI contract/component tests mock only HTTP and cover separate review/consent,
  Save and stale scope/input protection. Existing knockout/population checks remain.
- Existing real Chromium flow extends its 1,000-player Saved Health/knockout/
  continuation acceptance with weekly review, confirmation, separate Save/reload,
  actual W2 match consuming saved developed/recovered inputs and exact replay.

The expanded browser flow waits for the complete source-authenticated Save review
before consent (120 seconds, matching existing request/review waits). Its workflow
has 25 minutes for the expanded end-to-end acceptance; it does not skip the prior
Run/Health/knockout/extension steps. Final latest-head CI/browser evidence is
recorded in the PR after completion.
