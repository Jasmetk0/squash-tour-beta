# Two simultaneous native Editions on both sides of a Signed Season boundary

## New integration gap

Earlier separate, independently green acceptance:
- #1724: **one** actual final-week Edition in S1, then **one** in S2 W1,
  two Signed seasons, real MatchEngine and physical SQLite reopen.
- #1726: **two** overlapping shared-global-slot Editions in each of two
  consecutive weeks **within the same season**, actual 12 MatchEngine
  matches and separate Official publication after each week.
- Existing global-slot contract tests independently prove overlap,
  partial-slot reversals, same-player conflicts and rank recomputation.

The new real HTTP/SQLite acceptance **combines concurrency and closure**:
two independently confirmed simultaneous S1 final-W4 tournaments,
followed by S1's Signed Season Transition into S2 W1 and two other
simultaneous tournaments on new S2 global slots. A later real S2 Signed
closure must preserve both seasons' original matches, countries and
points. No shortcut for actual results or manual Save is allowed.

## Concrete run

- Set up a short, explicit `RunCalendar(4,2,2030,3)` through the existing
  real production initial population and health, with 8 actual players.
  This short calendar bounds integration runtime; reference FAX W61 and
  1,000 players remain separate release targets.
- S1 W2: review/save two v2 four-player tournament plans scheduled W4,
  announced S1 W3 (unique IDs and frozen point tables).
- S1 W3: review/save two additional v2 tournaments scheduled **S2 W1**
  and announced S1 W4. Attempt to submit S2 entries before their
  announcement and expect a production 409.
- S1 W4: sign two disjoint four-player Entry fields and draws, play both
  tournaments through **global Simulation Slots** (six actual rally-by-rally
  matches), with explicit Save after every slot and after each separate
  result confirmation. No published Official Ranking change yet; no
  Signed S1 read is allowed before closing. Total original award: **660**.
- **Season Transition** S1 W4 to S2 W1: manual Save publishes both actual
  S1 results at S2 W1, while closing S1 as exactly two actual completed
  Editions with two real titles and 660 awarded points. S2 remains unsigned.
- Physically stop/reopen the API and SQLite. Verify S1 signed summary and
  all original matches and Official Ranking survive unchanged.
- S2 W1: review/save disjoint current Entry fields/draws, play two more
  overlapping global slots (six new real rally-by-rally matches), confirm
  results separately. The original Signed S1 historical countries, Edition
  list and Closing Ranking remain unchanged; W1's published ranking must
  not already contain the newly played S2 events.
- S2 W2: real Week Transition publishes the second pair of tournaments,
  with exact S2 W2 publication identity, four independent Editions,
  two counted results per actual player and **2,200** combined original
  awarded points (660 + 660 + 880).
- W2→W3→W4→S3 W1: explicit real transitions and Saved S2 closure.
  S2 has exactly two actual completed Editions and 1,540 points.
  Signed records include two closed seasons, four Editions and the true
  all-country total. The *country record maximum* is the maximum of
  cumulative amounts per country, never assumed equal to the grand sum.
- Physical second restart: unchanged twelve original matches,
  four separately confirmed point-award ledgers, two Signed summaries,
  complete records, viewer publication, immutable Saved HEAD and exact
  original global-slot/confirm-result/season-transition receipt replay.

## What it doesn't certify

This is a *genuine but bounded* integrated production experiment:
**4 actual Editions, 12 genuine matches, 8 players, a W4 clock and two
Signed seasons**. It does not execute the mandatory W61 1,000-player /
80-actually-played World Tour Edition season or the 50-season release
endurance. It does not certify all real Entry AI eligibility policies,
qualification/FAX content, historical age cohorts, true sport-science
distributions, Windows runtime or security. No canonical runtime or
Master rules are changed; no auto-Save, result fabrication, direct SQL
or mutation of unrelated PRs. The CI workflow runs this *real* experiment
even on its Draft PR and uploads the disposable SQLite artifact.
