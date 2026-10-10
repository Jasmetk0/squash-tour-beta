# Browser evidence — 10 October 2026

Actual Playwright/Chromium screenshots from `work/browser-final8` after the
production backend was terminated/restarted and a fresh browser context opened.
Runtime source commit: `8964261c5e2e7ac712bad94331e269a5c8f1d020` (same runtime
source as the final acceptance; subsequent commit adds these evidence files only).

- [Published Week-2 ranking](reopened-04-week2-ranking.png): real 64-player table,
  points 100/60/30/30 for the completed tournament.
- [Published tournament result](reopened-05-tournament-results.png): actual field,
  Draw, both semifinal outcomes, winner-fed final and three stored match results.
- [Machine-readable observation](evidence.json): Run identity, all 64 readback
  rows, three replay identities and empty page-error/HTTP-5xx list.

These images are unchanged real browser captures. The topbar's locally selected
legacy Viewer week (W10) is distinct from the saved Product Run context (Week 2);
this acceptance asserts the actual canonical ranking/result and Run context.
It does not prove the legacy historical-week selector drives canonical pages.

The complete traces and six main screenshots remain under
`work/browser-final8/artifacts`; generated database/state are under
`work/browser-final8`. Use the [repeat instructions](../../ADMIN_FIRST_TOURNAMENT_BROWSER_ACCEPTANCE.md)
to generate the complete artifact set in a fresh disposable directory.
