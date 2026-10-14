# Real Hybrid Ranking Closure — explicit points and canonical Saved Result

**14 October 2026**, starting from merged #1452, `buuk` commit
`4e09869b44c5afd7518be8c0a07d53da85668290`.

## New real Admin capability

After the actual Group Match Day, canonical completed Group Standings, configured
post-group Entrants, frozen Knockout Bracket and real knockout Match Days,
the Admin's hybrid panel lets the operator:
- Enter **explicit, non-negative integer** Ranking points for each *played*
  group match win and every knockout finish demanded by the bracket depth:
  champion, finalist, semifinalist, quarterfinalist, etc. Nothing is
  prepopulated or inferred from the current player Ranking or event name.
  A nonzero group win reward cannot be applied over unresolved group walkovers.
- Review and confirm the exact entire points table, freeze once through the
  canonical Hybrid Ranking Policy authority with original Run/Branch/Event
  and immutable response checks. Edits revoke prior confirmation.
- Inspect the persisted actual knockout terminal replay (not a future winner),
  independently confirm the Ranking closure and publish **one** canonical
  OwnedTournamentRankingSource, one Result/Points authority and prize-money
  authority. The engine composes group and knockout phase components into
  exactly one award per player and controls first eligible publication week.
- After reload or SQLite process restart, read back the already-frozen
  source from a dedicated side-effect-free GET and display result/award/source
  fingerprints. Never offer silently changing or recreating an existing source.

## Real browser acceptance

Full Chromium+FastAPI+SQLite flow:
1. Two natural production MatchEngine group matches and one real knockout final;
   canonical frozen standings, explicit crossing, entrants and winner-tree.
2. Assert `GET /hybrid-ranking-policy` and `GET /hybrid-ranking-close`
   initially return 404; `POST /hybrid-ranking-close` before policy gets 409
   rather than creating an unconfigured award.
3. Operator chooses **10** points per played group win, **100** for champion,
   **60** for finalist **in the test only**, confirms and freezes policy.
   Frontend never offers these numbers by default.
4. Operator confirms recorded real MatchEngine replay and explicitly closes.
   Canonical `total_ranking_points=180` (2 actual group wins × 10 + 100 + 60),
   with separate valid Result/Award/Prize/Owned-source fingerprints.
5. Explicit Simulation Save creates a new Saved Revision whose published
   Tournament Result has actual played champion/finalist and three authentic
   matches. Old Saved Revision must remain unchanged.
6. Restart SQLite-backed backend, compare complete policy, closed result,
   all prior sporting authorities and final rally replay.
   Prior six-match group and genuine cyclic tie browser regressions stay green.

## Still outside this PR

Actual eligible week Official Ranking publication/long-run Season rollover,
multi-round full sporting acceptance, full 50-season simulation scale,
Ranked Walkover reward policy, and legacy/fork historical remapping remain
separate explicit release gates. This PR **does not** silently define a global
tour category point table and does not auto-assign points to tournaments other
than the one selected and confirmed.
