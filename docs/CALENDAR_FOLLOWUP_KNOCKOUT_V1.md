# Later-week native sporting knockout — implementation contract

Scope: **actual playable state**, not Official Tour/Ranking or a Week/Season Transition.
Based on merged #1533 on `buuk` fcc9501227e394fa3ce4cfdf43ed85917f77a2d0.

## Production flow

After a **Saved** v5 opening knockout and at least one explicit **Saved** sporting
advance to Week 2+, Admin may run a real four-player knockout. It consumes any four
distinct players from the saved full population and the exact Saved HEAD and
checkpoint fingerprints. An HTTP command creates three MatchEngine matches
(semi 1, semi 2, and a winner-fed final) inside **one BEGIN IMMEDIATE** transaction.
No partial tournament may survive a failing semifinal/final or failed row replacement.

All four players come from their latest canonical **57-attribute** sporting records.
Actual earlier semifinal state is consumed by the final; unaffected population
records remain identical. Both semifinals are played with the pre-tournament
attributes of their disjoint pairs. Every match stores frozen projection, input
context, Health projection (where saved), real rally/timeline/stamina log, applied
form/load effects, parent checkpoint fingerprint and MatchEngine replay anchor.
All players continue with the same owner for later tournaments and weeks.

`calendar_followup_knockout.v1` is one root ledger event with three nested
`calendar_continuation_match.v2` events, explicit sorted history order, entrants,
source and audited command. Only newly changed checkpoint states gain
`calendar_sporting_checkpoint.v4`. Old v1/v2/v3 JSON/hash/replay are not upgraded
or rewritten. Reducer replays **every** historical sporting week, exhibition and
tournament, verifies each nested match, bracket wiring and the final full-population
state against the immutable component. Original retry after Save, future weeks,
restart, or horizon extension reconstructs its original successor receipt.

The existing manual sporting Save stores the v4 component in a separate
immutable Saved Revision. The next command requires that Save. A restore of an
earlier revision removes the tournament and its sporting effects, and restoring
forward reproduces exact history. Existing individual replay URLs work for all
three nested matches. `/calendar-continuation` also exposes an explicit
`tournaments` summary with winner, match IDs and saved flag.

## Explicit limits

The command creates an **exhibition knockout**, *not* an official Tour Edition.
No canonical Edition binding, Tour Entry, configured point award, Official
publication, discipline, calendar public-clock advancement, lifecycle/Health
healing or Season Transition is manufactured. The legacy/full simulation guards
remain. Existing provisional 57→MatchEngine projection and Health numeric-effect
limits still apply. No standings may count these matches as Official points.

## Acceptance

PR-critical real production HTTP/SQLite scenarios on W52 and W80 cover
Saved checkpoint gating, actual finalist wiring and three match replay, exact
idempotent retry, concurrent-independent identity guards, simulated DB write
failure/rollback, separate Save, immutable old hashes, corrupted-v4 rejection,
later sporting recovery (3 matches = six player participations), restart and
backward/forward restore. Full 50-season pre-alpha release gate is still pending.
