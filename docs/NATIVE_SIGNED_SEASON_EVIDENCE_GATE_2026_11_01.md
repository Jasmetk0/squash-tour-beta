# Native Tour signed-season evidence gate — 1 November 2026

## Problem / scope

**A season calendar that advanced to W80 is not 80 played Editions.**
Likewise, having 1,000 initial players is not proof of 1,000 actual careers
and an agent reaching S50 is not evidence of 50 authentic season closures.

The standalone read-only command
`tools/audit_native_signed_seasons.py` verifies **only** signed,
already completed, native Tour seasons through the existing production Admin
GET interfaces. No server process is started by the script, no mutable
Draft, match or ranking is created, no API is extended and no sport rule
is inferred. The existing Saved revision/authentication services remain
the only authority for sporting results.

### Example

After starting an **existing** Squash Engine backend with a real signed Run:

```bash
python tools/audit_native_signed_seasons.py \
  --base-url http://127.0.0.1:8000 \
  --run MY_RUN_ID --branch MY_BRANCH_ID \
  --required-seasons 50 --minimum-completed-editions 80 \
  --output signed-season-evidence.json
```

This is a **deliberately strong scoped gate**, not proof of all pre-alpha
requirements. To inspect a small real two-season scenario use
`--required-seasons 2 --minimum-completed-editions 1` and retain
`SCOPED_EVIDENCE_PASS` as a bounded result.

- The 80 minimum is **80 confirmed played Editions of any Tour category**,
  not a category-verified roster of 80 FAX World Tour tournaments. The
  separately audited full FAX calendar/#1717 and actual eligibility/fields
  must still be verified; no sporting threshold is changed by this tool.
- The `GET /admin/runs/{run}/branches/{branch}/calendar-tour/records`
  source is authenticated by the existing backend Saved Tour and complete
  immutable Saved Revision lineage. The script first reads this cumulative
  signed record, obtains every completed index and its actual Saved HEAD,
  then reads **every** signed season from
  `GET /admin/runs/{run}/branches/{branch}/calendar-tour/seasons/{index}`,
  then rereads Records to detect concurrent changes. A 409, 404, timeout,
  malformed JSON, incomplete season or source revision change fails closed.
- Every season must have its **real Saved terminal Season Transition** ID,
  valid Week W published ranking and immutable ranking fingerprint,
  unique actually confirmed Edition IDs, actual distinct champion/finalist
  when the sporting format has an Edition champion, aggregate Country and
  Player totals that reconcile with actual placements and awarded points.
  Pure multi-group Editions (Signed schema v2) may legitimately have
  **no** final champion and are never given one by this audit.
- Reconcile each closed season with the corresponding cumulative Records
  `source_seasons` identity, actual Edition count, terminal command and
  ranking source. Reconcile all reported seasons with the Records'
  `completed_edition_count`, **all six** career/country record maxima and
  all tied record holders. This catches an inconsistent report even when
  simple counts happen to agree.
- The command reads **only HTTP GET** and writes only optional local JSON
  evidence. HTTP errors never produce a passing evidence file. No auth
  credentials are put in the URL. All report counts are bounded to actual
  completed seasons and do **not** count future planned Editions.
- The output reports `SCOPED_EVIDENCE_PASS`, not `RELEASE_APPROVED`,
  and includes the exact Signed HEAD/Tour fingerprint, requested thresholds,
  season-level completed counts, actual champion counts, original Edition
  awarded points, boundaries and final-week ranking fingerprints. On failure
  the process exits nonzero and emits a `FAIL` error to stderr.

## Deliberate limitations and next integrated step

The script cannot independently verify Server-side cryptography: it trusts
the already implemented Saved-revision integrity checks in the responding
production server. It cannot attest a remote server's identity. It also
does not measure stochastic realism of this deterministic global FAX world,
cross-seed career distributions, ELO-style skill, duration/health/injury,
individual actual entrants/1000-player cohort, the 80 **World Tour**
category memberships, match/rally replay, Windows binary, runtime/memory
performance, security, or release QA. These require independent gates in
`docs/PRE_ALPHA_TEST_POLICY.md` and the Master.

The next experimental full-scale Run should store this output alongside
real per-Edition tournament identity/category diagnostics, actual
1000-player historical/intake coverage and a 50-season resource/realism
report. Only explicit owner review and the full internal-release gate can
approve pre-alpha.

## Regression tests

`tests/tools/test_native_signed_season_evidence.py` uses pure synthetic
fixtures **only to attack the verifier**, not to claim an actual 50-year Run.
It exercises missing/in-progress seasons, insufficient actually played
Editions, corrupt tournament counts and participant distributions, stale
Saved heads, changed underlying lineages, missing Ranking W, forged
published finals, multiple legitimately championless pure-group Editions,
every record metric, full tied co-holders, and an actual loopback HTTP server
to prove GET-only requests. Existing production HTTP/SQLite season closure
tests remain the genuine sporting behavior evidence.

Only a separate Draft PR is created; the user reviews/merges.
