# Canonical Saved Players / profile — implementation slice (11 October 2026)

Authority: Master v77, `docs/PRE_ALPHA_FRONTEND_V1.md`, `docs/PRE_ALPHA_TEST_POLICY.md`.
Status: proposed implementation on `feat/canonical-saved-players-20261011`; not a pre-alpha release.

## Implemented contract

- `GET /admin/runs/{run_id}/branches/{branch_id}/saved-players` returns an independently validated, deterministic, **server-paged** roster (limit 1–100), built solely from the exact current immutable Saved Revision of a selected Branch. The endpoint verifies Run/Branch ownership, HEAD identity and saved-component fingerprints; identity duplicates, foreign ranking or malformed state fail closed.
- Filters: name or ID, sport-country code, exact status, and explicit `include_prepared` Admin opt-in. Prepared prospect snapshots may contain future identities; they are not enumerated by default and this does not change Viewer or player AI reveal semantics. The endpoint remains Admin-only.
- Saved Initial World and an explicitly opted-in saved Run prospect source are the only identity inputs. No legacy Run player list, live source, Viewer Branch, new RNG or invented defaults are used.
- Latest saved Official Ranking is independently verified. `ranked` means exact stored rank; `unranked` / NR only after ranking publication. When unpublished, rank is unavailable, not NR.
- Present-time age, 0–200 OVR and Potential OVR are currently **null/unavailable**, not reinterpreted from legacy 1–99 abilities, a birth year observed at another time or a different Branch.
- Canonical `/admin/runs/:runId/players` now uses this contract, keyed to Run + Branch + Saved HEAD + time mode/checkpoint + filter + page. It does not query in historical checkpoint mode. Named profile links go only to canonical `/people/:playerId`.
- Player profile has read-only **Overview / Attributes / Career & results** tabs. Overview uses the existing verified saved profile and ranking; Career reuses saved tournament finals, match history and replay links. Attributes honestly reports the missing canonical attribute projection.
- Run-only player Explorer is retained as explicitly labeled **legacy diagnostics** at `/admin/runs/:runId/players/legacy`; it cannot silently assign Run-level health or abilities to the selected canonical Branch profile.

## Evidence and boundaries

- `tests/application/test_saved_players_inventory.py`: 1,050-player page, identity and scope checks, filters, unpublished vs ranked vs unranked, prepared opt-in, no fallback for empty saved snapshots.
- `web/src/pages/PlayersPage.test.tsx`: Branch/revision/time query identity, 50-row server pages, hidden prepared default, response mismatch fail-closed.
- `web/src/pages/SavedPlayerIdentityPage.test.tsx`: separate profile tabs and current/historical/foreign-HEAD behavior.
- `web/acceptance/prealpha_shell_browser_smoke.py`: Chromium, production FastAPI and SQLite; verifies actual empty canonical Saved Run API and read-only search/filter behavior without legacy fallback.
- Required Fast CI and browser workflows must both complete successfully **on final PR HEAD** before sharing as merge-ready. A full internal-release test is independent.

## Follow-ups (not in this PR)

1. Add an authoritative present-time sporting-attribute read projection (0–200 OVR, potential and comprehensive attrs/status/age), versioned independently of obsolete 1–99 pool DTOs; no guessed numbers.
2. Implement historical player projection at selected Saved Revision/checkpoint with appropriate time-specific identities/status; this PR blocks unsupported historical mode instead.
3. Assess run-prospect disclosure and explicit future preparation controls in the wider generation/UI integration, including direct-profile access rules.
4. Connect the single unified Generate preview / confirm / Working Draft / manual Save flow using production generation kernels, preserving unresolved remainder and group-overlap decisions.

This slice does not update sporting coefficients, migrate country ratings, import Player Packages, mutate Viewer Branch, or create Saved Revisions during reads.
