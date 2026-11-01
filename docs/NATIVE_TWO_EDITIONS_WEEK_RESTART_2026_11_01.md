# Two consecutive native Editions: real HTTP/SQLite recovery acceptance

## Goal and ownership

A focused, always-executed Draft PR gate demonstrates that one signed Run-owned
Calendar Tour can finish a genuine four-player Edition, publish its results,
restart the API and physical SQLite engine, then proceed to another distinct
Edition in the **next** event week. Both histories must survive a second
physical restart. The production MatchEngine performs the actual matches;
the test performs no direct SQL repair or forged ranking snapshots.

This is deliberately isolated from:
- #1713, the separate one-Edition HTTP/SQLite gate (not assumed merged);
- #1717 Jules' FAX 80-Edition Calendar audit;
- #1716 Jules' three Labs test work; and #1715 Earth data validation;
- the existing long two-Edition/horizon-rollback native Tour test.

## Exact scenario

1. Use existing production HTTP/SQLite setup, Run calendar W52, four generated
   actual players, two distinct editable native Editions in W4 and W5. The
   two Editions are published as separate Saved calendar facts.
2. Explicitly advance to the first Edition; actual players apply, the
   operator approves the field and creates the draw, and each step remains
   unsaved. The Viewer must still show the previous Signed state.
3. The real HTTP preview **rejects a Play before manually signing the draw**.
   Save the draw, execute the real MatchEngine (three matches), manually Save
   match receipts, explicitly confirm result and Save again. Confirm the
   original Edition awards 30/30/60/100 before advancing the Official Week.
4. Confirm the next published Official Ranking and then physically close the
   server and open the same unmodified SQLite database again.
5. The second Edition must still exist and remain unplayed. Repeat all
   Entry/field/draw/MatchEngine/confirm-result/Save boundaries for that Edition.
   Its distinct authored two-times point table awards 60/60/120/200.
6. Advance one more Official Week, confirm the second Official Ranking, and
   physically reopen the same SQLite file again.
7. Confirm both exact match/result histories, the final Saved HEAD and Viewer
   state, then exact-replay the two original Play and transition requests.
   The second replay MUST not create duplicate matches, Signed results,
   rankings or revisions. A foreign Branch's Tour source is rejected.

The two real backend probes use existing `tests.api.test_calendar_tour_flow`
production helpers, not a mock or a new sporting contract.

## CI and evidence boundaries

- `tests/api/test_native_two_editions_restart.py` includes one tiny
  `pr_critical` command-scope test for the standard Fast CI.
- The additional workflow
  `prealpha-native-two-editions-restart.yml` runs the **real HTTP/SQLite**
  test on every Draft PR change, with `GITHUB_EVENT_NAME=workflow_dispatch`
  so GitHub's changed-file selector does not inadvertently remove the
  explicitly requested test. Its final-head success, not a skip, is the
  acceptance criterion for this PR.
- This does **not** prove a complete season, a 1,000-player FAX cohort, 80
  actual World Tour Editions, or the required 50-season reference run.
  It is not a Chromium browser UI test, and uses the existing **manual**
  application/field/result validation rather than inventing automatic
  eligibility or an AI tournament-attendance policy.
- The untouched complete Master and dedicated pre-alpha release acceptance
  remain authoritative. Production code and existing fixtures are unchanged.
  No automatic merge; owner reviews and merges.
