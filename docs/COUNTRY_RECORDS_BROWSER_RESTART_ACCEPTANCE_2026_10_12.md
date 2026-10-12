# Country Records: real Chromium, FastAPI, SQLite, historical and restart acceptance

## Purpose
Extend the existing dedicated `Pre-alpha Saved Player Replay Browser` CI scenario instead of introducing a parallel paid GitHub Actions job. Use the established real production browser workflow to build a fresh disposable Run, copy FAX World and Calendar, generate and save 64 genuine players, simulate/publish the actual three-match 4-player tournament, Save the official sporting revision, and restart the production SQLite backend.

## New concrete checks
`scripts/country_records_browser_checks.py` runs **after the canonical tournament result is actually saved and published**, and once more in a new browser context **after SQLite/backend restart**.

- Choose a real sport country via the national identity of an actual saved tournament finalist. Validate it exists in the copied Run World; no invented country or hard-coded CZE in the World.
- Read real published tournament results and Saved player nationalities, then independently derive all relevant real match IDs, winners/losers, scorelines and national win/loss counts. Compare to the new exact Saved `country-match-records` API and the earlier published `country-records` endpoint.
- Verify the real league scope: selected Run, Branch, Saved HEAD; no BYE, no fabricated completed Calendar-only match. Ensure one published event, three actual played matches, national wins and losses.
- Verify server-side `season_index=0`, `season_index=1`, `result_kind=played/walkover` and `outcome=win/loss`; invalid season, kind, outcome and inaccessible Saved Revision fail (422/404).
- Open real Run → World → Country → Records in Chromium. Assert the actual result rows, scorelines, source Saved Revision and functional season/completion/outcome filters.
- Select a **real earlier Saved World revision** from this exact Run's reachable Saved history where no tournament result was published. Verify it shows **zero** matches, not current results, with no present player/match links. Assert history reads do not mutate Saved HEAD.
- Restart SQLite-backed production API and open a fresh browser; repeat and byte-compare the compact, independently computed evidence.

## Scope and verification
Enable `--country-records` only for `--saved-replay-only` in `scripts/admin_first_tournament_smoke.py`, preserving other smoke modes. Existing saved-player replay and branch-fork acceptance remain running in the same CI job. Browser screenshots and evidence are written to its existing artifact directory, retained for 14 days.

This is genuine real-world data flow test evidence for **one real completed tournament**. It does **not** prove 50 seasons, long-term cross-season match counts, all future historical permutations, or multi-million-player performance. All production Run, saved package and official ranking writes remain through established UI/engine commands; all Country Records reads are non-mutating.
