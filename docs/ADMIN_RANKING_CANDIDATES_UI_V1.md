# Admin ranking candidates UI

Read-only UI: link from each branch, scoped history and URL-selected week detail, counted results and unpublished status. Uses the existing read-only API. Query keys include Run and Branch; no placeholder history is carried across branches. Empty, missing, invalid and error states are explicit. Names are not fabricated: the API supplies player IDs.

Validation after #698: 102 component tests passed across AdminRankingCandidatesPage and AdminRunBranchesPage, and TypeScript/Vite production build passed. Candidate coverage includes populated detail and award breakdown, provenance, branch isolation during loading, retry after failure, invalid coordinates, empty history and exact-week selection. Both suites are included in Fast CI. The ranking table uses the existing keyboard-focusable horizontal scroll region.

Dependencies installed successfully using npm 10 (matching CI), without lockfile changes. npm 11 previously failed on optional platform entries. Browser screenshot verification remains unavailable because the local Playwright browser is not installed; component tests use mocked API responses and do not constitute end-to-end backend verification. Backend publication and week advancement are unchanged.

## Historical source inspection

Each candidate detail offers an on-demand Source results section backed by
`GET /admin/runs/{run_id}/branches/{branch_id}/ranking-candidates/{season_index}/{week}/sources`.
It returns the latest effective source version per Edition/player at that exact
stored candidate boundary, including uncounted/unranked/expired sources. Each item
identifies whether the candidate counted it and exposes original publication and
validity, correction predecessor and source/version fingerprints.

The read uses one SQLite transaction, validates source chains and verifies that
every counted candidate result matches its resolved source. Missing counted sources
or inconsistent/corrupt data produce 409; missing scope/candidate produces 404.
Uncounted-source completeness cannot be proven from the candidate alone; this is
inspection of stored history, not a replacement for authoritative input manifests.
Later effective corrections are excluded. No ranking recalculation or writes occur.
The response remains Admin-only and explicitly unpublished.

The UI fetches only on request, isolates its cache by Run/Branch/week/candidate,
checks the candidate fingerprint, and exposes retry without hiding the candidate.
Backend tests exercise real HTTP routing and SQLite, correction boundaries,
nonmutation and corruption; frontend tests mock the API for loading, retry,
uncounted results, scope navigation and candidate mismatch. Browser screenshot
verification remains unavailable in this environment.

For candidates prepared with complete input manifests, source inspection now also
compares all effective source results against those frozen inputs. Deleting or
changing an uncounted result is detected. The earlier completeness limitation still
applies to legacy candidates without a manifest; manifests do not prove that the
original command supplied every eligible real-world input.

## Inspect stored calculation inputs

The candidate detail now offers an on-demand Stored calculation inputs panel.
`GET /admin/runs/{run_id}/branches/{branch_id}/ranking-candidates/{season_index}/{week}/inputs`
returns the verified frozen roster and result manifest for that exact candidate,
including NR/retired players and tie-break tokens. Later lifecycle updates do not
replace the stored inputs. The endpoint uses the existing manifest reconstruction
checks and a single SQLite read transaction; it does not read current award files
or mutate history.

Responses distinguish `complete_manifest` from `legacy_without_manifest`. Legacy
candidates return a null manifest, not a fabricated empty roster; the UI explains
that complete inputs were not stored. Verified empty manifests have their own
empty states. Corrupt/unsupported inputs return 409 with a generic error, missing
scope/week returns 404, and invalid coordinates return 422. All data remains
Admin-only and candidate-only, with no publication or clock advancement.

The panel validates scope/week and candidate hash, loads only on request, isolates
its cache by candidate identity and supports retry. API tests use real HTTP/SQLite
for historical lifecycle, read-only nonmutation, missing scope/week, legacy status
and corrupted-input redaction. Page tests mock the API for lazy NR-roster display,
branch navigation, legacy versus empty status and mismatch/retry. Browser screenshot
verification remains unavailable; no visual QA is claimed.
