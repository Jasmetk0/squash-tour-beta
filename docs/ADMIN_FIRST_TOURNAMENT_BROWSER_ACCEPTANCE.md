# Real Admin first-tournament browser acceptance

This acceptance drives the existing React Admin/Viewer against the production
FastAPI application and SQLite persistence on localhost. It does not test a
deployed production host, automatic application validation, Official Run release
acceptance, another tournament format, Branch forks or multiple seasons.

## Repeat

Use the existing Python virtualenv and Node 20/npm 10 dependency setup. Do not
regenerate lockfiles. The Python environment needs Playwright; the browser can be
an existing Chromium executable (`--chromium /path/to/chromium`). This session used
Python 3.11.16, Node 20.20.2, npm 10.9.9, Playwright 1.63 and Chromium 151.
The frontend and browser must reach both localhost ports. Leave backend port 8001
free: the acceptance owns its backend process and restart.

From the repository root, terminal 1:

```sh
VITE_API_BASE_URL=http://127.0.0.1:8001 npm --prefix web run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Terminal 2:

```sh
.venv/bin/python scripts/admin_first_tournament_smoke.py --acceptance work/browser-acceptance-new --port 8001
```

Always choose a fresh disposable directory. Existing databases are refused; a
busy backend port is refused rather than accidentally testing somebody else's
Run. The script ends its backend process after the verification. To inspect the
saved Run manually afterwards:

```sh
.venv/bin/python scripts/admin_first_tournament_smoke.py --serve work/browser-acceptance-new --port 8001
```

Open the URL in `work/browser-acceptance-new/artifacts/run-url.txt`, use Admin or
Viewer navigation, and inspect the saved Week 2 results. If Playwright is absent,
install it into the existing disposable virtualenv; it is not a new application
runtime dependency. If using the prepared workspace, prepend
`/workspace/.runtimes/node20/node_modules/.bin` to PATH for npm commands.

## Source preparation, separate from browser actions

`create_smoke_app` copies built-in source World packages into isolated paths,
copies unchanged Entry tuning, initializes category points using existing
services, and builds/validates a source Calendar with one Week-1 World Tour Cup.
The validated template has Main 4, no Qualification/WC/BYE, two seeds and points
100/60/30. The source registry is persisted through existing Calendar service
storage. This preparation creates no players, applications, winners or match
results and changes no built-in or Official Run source.

## Actions actually performed through UI

1. Create custom Product Run, copy World and Calendar into its draft, Save each.
2. Generate/adopt/Save 64 real owned players (seed 4201, Best 15).
3. Derive/confirm/Save initial ranking, publish, Save publication and check saved
   Viewer readback.
4. Adopt that published ranking for the tournament, generate/freeze real Entry AI
   decisions, and explicitly review and commit all proposed applications as valid
   using the existing admin batch form. No automatic validation policy is added.
5. Review/commit the actual four-player Entry Field, Draw Input, generated bracket
   and full global Week Schedule.
6. Play the first match, then use reviewed Next Round twice for the other semifinal
   and final. Check three stored replays, final feeder identity and verified replay.
7. Save sporting changes, derive/confirm/Save Ranking Transition Authority, then
   review/commit/Save Week Transition. Viewer Week 2 has 64 rows, tournament points
   100/60/30/30 and zero points for the other players; results are Published.
8. Terminate/restart the backend using the same isolated paths, open a fresh browser
   context, and compare complete Viewer ranking rows and all three saved replays.
9. In reopened Admin, confirm Calendar-proven zero-match Week 2 through the existing
   audited backend command, Save, and successfully review Next Week (W2 → W3).
   W3 execution is not committed by this acceptance.

The script observes real browser request completion rather than assuming a
navigation `networkidle` state also covers later Save/publish invalidations.
Every Run write is a browser form submission. An additional eight-concurrent-GET
Position check is explicitly API read-only evidence, not a UI action.

## Artifacts and boundaries

The artifacts directory contains six main full-page screenshots, reopened Viewer
screenshots, Playwright traces before/after restart, `evidence.json` and Run URL.
Success requires no page errors or HTTP 5xx responses. The fixture's actual Entry
count is recorded; the observed unchanged-tuning run generated 41 applications.
Failures retain a screenshot and page text for debugging and never overwrite a
previous database.

Component tests mock API boundaries and are not browser integration evidence.
`tests/api/test_browser_entry_bootstrap_api.py` independently uses production HTTP,
SQLite and generated player state for initial Entry preview/non-mutation, stale
Position rollback and actual wire fingerprint. Its roster hash test instruments
property access counts; the acceptance uses unmodified production hashes.

Next work after merge: compare fixed-seed FIFA Earth/ATP Earth generation using
existing Lab tools and copied inputs, report distributions/provenance side by side,
and propose any model changes separately. Do not retune from this smoke.
