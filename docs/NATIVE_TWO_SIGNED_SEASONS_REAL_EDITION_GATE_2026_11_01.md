# Real native Tour: two adjacent-season Editions and two Signed closures (2026-11-01)

## Missing integration evidence

Existing long-running production checks already establish two successive
Tour Editions in **one season** (#1718), one genuine Edition announced in
S1 and played in S2, and single-Edition final-week/Season Transition flows.
This independent test checks their **interaction**: the final week of S1
contains real playing, the first week of S2 has a separate real Edition,
and both seasons eventually close and contribute to immutable historical
records without early/duplicate Official Ranking publication.

One bounded `RunCalendar(4,2,2030,3)` with four real generated players
permits a deterministic HTTP/SQLite run. Four-week calendars are an
integration stress fixture, **not** the real FAX 61-week or 80-Edition
configuration; this is not a short-cut release gate.

## Exact flow and protections

1. Real population/Health/opening-sporting checkpoint with initial manual
   Save and Signed S1 W2. Create Edition A scheduled for **S1 W4** and
   announcing W3. Explicit Save, real W3 transition and Save.
2. Create Edition B for **S2 W1** with announcement S1 W4, while S1 W3
   is still active. An early submission for B must be rejected. Transition
   to S1 W4; confirm B is announced but not played.
3. Explicit submissions, field approval and draw for A, manual Save,
   genuine 3-match rally-by-rally MatchEngine, separate manual Save,
   result confirmation and manual Save. Tournament A awards 220 points
   (100/60/30/30) but cannot retroactively rewrite the **published S1 W4
   ranking**. S1 is still not a Signed closed season.
4. Real S1 W4 to S2 W1 Season Transition, manual Save; only now are A's
   previously played points published at S2 W1, and only S1's Signed
   national/season record becomes readable. B remains unplayed. Verify
   exact first-publication dates, Signed S1 edition, national totals,
   Saved source and source Run immutability.
5. **Physically close and reopen** HTTP server/SQLAlchemy SQLite. Verify
   original A MatchEngine results and Viewer history. Play B with the
   same strict approval, draw, actual MatchEngine and three manual
   Save boundaries. No B result leaks into S1 or S2 W1 ranking.
6. Transition to S2 W2 and Save; check B points become published
   **only then**, with distinct first-publication dates. Continue actual
   weekly transitions W2→W3→W4 and **Signed S2 to S3** transition;
   now both historical signed seasons have one real, distinct completed
   Edition with 220 and 440 awarded points.
7. Read real Admin Signed Season summaries and the full Signed Records
   catalog: completed Seasons [0,1], total completed Editions = 2,
   published country awards sum 660, but **record maximum** is the
   maximum cumulative single-country amount, not 660 unless every
   participant shares a country. Both real champions exist. The
   unfinished S3 remains rejected.
8. Physically close/reopen SQLite **again** and verify signed historical
   summaries, exact Viewer state, original MatchEngine ledger, all six
   cumulative national/player Records, and idempotent retry of the
   original Season Transition and S2 W2 publishing command. No new
   points, matches or Saved HEAD on replay.

No direct SQL/JSON insertion, fake sport, static precomputed Tournament
results, new automatic approval, calendar policy change, hidden Save,
new browser feature or source Master amendment. Existing tests remain
the prerequisite for larger W52/W61/W80 and real FAX 80 Edition coverage.

## CI and release boundary

The dedicated `Pre-alpha Native Two Signed Seasons` workflow runs
on this Draft as a real hosted integration case and retains disposable
SQLite as a CI artifact. An isolated fast `pr_critical` test covers exact
two distinct intent IDs/authority. Passing these small and real tests
never certifies 50 seasons, 80 actual World Tour Editions, historical
1000-player intakes, scientific realistic distributions, or Windows
pre-alpha release.

The owner controls one Draft PR and all merges.
