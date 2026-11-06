# Four actual native Editions in two consecutive overlapping weeks

## Motivation

The existing real native Tour regression proves two overlapping Editions
on the same week's global Simulation Slots; another proves two consecutive
single-Edition weeks across SQLite restarts. The new acceptance tests the
combined *running* lifecycle: **two overlapping Editions in W4, then two
overlapping Editions in W5 of the same persistent Run** without starting
a new world or rewriting any previous match/score.

A deterministic 52-week/8-player Run keeps the test sufficiently bounded.
The real release reference is separately **FAX W61, 1,000 initial players,
80 World Tour Editions actually played per season, 50 seasons**. A four-event
test is a progressive sporting and persistence gate, not proof of that scale.

## Production workflow tested

1. Normal production HTTP/SQLite initial population, health, initial
   sporting checkpoint, Tour initialization and explicit signed Saves.
2. At W2, create four v2 knockout Editions with immutable individual IDs,
   seeds and point tables, two scheduled W4 and two W5, all announced W3.
   Each preview/execute is reviewed by the ordinary production command
   service and then explicitly Saved.
3. Open W3 and W4 with real signed Week Transitions. Enter/approve/draw
   W4's two Editions with disjoint four-player fields; manual Save is required
   before MatchEngine can use each draw.
4. Play the actual overlapping global Simulation Slots via the existing
   `next-slot` reviewed commands and explicit Save after every slot.
   Verify 6 real rally-bearing matches, two independently confirmed
   tournaments and original Edition point awards of **220 + 440 = 660**.
5. Week Transition publishes W4's results in W5 only. Verify eight Official
   Ranking player rows and only W4's two authenticated Edition references
   (all real result points are not invented rank estimates).
6. Stop/reopen the actual API and SQLite before any W5 play. Compare
   original matches, two signed results, Saved HEAD, Official Ranking and
   Viewer publication with the pre-restart values.
7. Approve two additional Editions with the same players in disjoint fields
   at W5; play and Save 6 **new** real matches on that week's original
   global slots. The W5 Official Ranking remains unchanged until W6's
   separately reviewed Week Transition.
8. W6 publishes both weeks: exact original awarded totals are now
   **660 + 660 + 880 = 2,200** across four Editions, each player with
   two authentic counted Edition sources and the correct first-publication
   weeks 5 and 6.
9. Cold-reopen SQLite again and verify all 12 actual match logs, four
   frozen result sets, exact Saved HEAD, Viewer and Official Ranking.
   Replay original reviewed global-slot, confirmation and final Week
   Transition requests; they must return original receipts with no new
   sporting outcome or duplicate points.

## Deliberate boundaries

- No changes to sport, RNG, player development, scoring, eligibility,
  content, initial FAX bootstrap, official points policy, or real Saved
  persistence. All assertions query actual production HTTP API results.
- A 52-week eight-player two-week run does not demonstrate realistic FAX
  61-week/1,000-player/80 World Tour/50-season endurance; nor does this
  exercise full real Entry AI validation, qualification, Finals or
  career/health distributions. Those remain their own release blockers.
- Shared-player same-slot collisions remain rejected by the original
  global slot tests; the new acceptance intentionally uses **different**
  players in concurrent tournaments and reuses them only on a later week.
- The proposed CI workflow executes this complete production HTTP/SQLite
  case on the Draft PR (unlike expensive Ready-only full-matrix jobs)
  and retains the actual disposable SQLite file. Fast `pr_critical`
  runs only a pure schedule-invariant companion, not the lengthy real
  simulation twice.
- Owner merges. One isolated Draft PR; no changes to parallel Jules,
  Codex, browser, Admin UI or research files.
