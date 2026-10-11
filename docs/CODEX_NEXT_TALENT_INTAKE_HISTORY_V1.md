# Codex task — freeze Talent Intake history and reviewed scope

Repository: `Jasmetk0/squash-tour-beta`
Target branch: current `buuk`
Role: implement one coherent vertical slice, prepare a PR; the user decides merge.

## Why this task is next

Talent Intake now materializes and inspects concrete prospects, but read-time quality
classification still uses today's global policy. Review confirmation can also survive a
Run switch and is not bound to an exact server-side preview. Correct those boundaries
before any rarity/potential calibration or additional diagnostic features.

Read `AGENTS.md`, current Master v70 §§4, 5, 9, 25, 31.25–31.26, this checkpoint's
`docs/PRE_ALPHA_CHECKPOINT_2026_10_02.md`, `CURRENT_STATE.md`, `ROADMAP.md`, and
`docs/PRE_ALPHA_TEST_POLICY.md`. Explicit newer user decisions take precedence.
The audited baseline was `aceb144d79924a985ada34b9eefaec53f548cf1c` after #1093.
Obtain current `buuk`, verify that work is present, and read any newer changes before
editing. Do not overwrite newer work with the checkpoint's older file copies.
The documentation PR containing this task must be in the chosen base, or its product
decisions must be supplied explicitly. Do not implement against an unexplained stale base.

## Required behavior

1. Freeze the quality policy used by each materialized cohort/prospect, including its
   policy/schema identity, normalized weights or a resolvable immutable snapshot,
   deterministic selection version and fingerprint. Keep innate quality separate from
   Potential OVR, potential labels and realized sporting performance.
2. Listing prospects and producing historical summaries must resolve the stored policy
   and result rather than applying the latest global defaults. A later policy can affect
   new cohorts without relabeling existing players. Same seed under a different policy
   is not sufficient proof of the same history.
3. Provide a safe, explicit compatibility path for old records that predate stored quality
   provenance. Their known v1 derivation may be preserved as legacy-derived evidence;
   never pretend a new policy was historically stored, change IDs, regenerate profile
   attributes or rewrite sporting history during a GET. Unresolvable provenance fails
   closed with a useful message. Follow existing schema/migration/recovery conventions.
4. Bind Review→Confirm to an immutable reviewed scope: exact target identity, season,
   World snapshot/configuration and cohort inputs plus a fingerprint/expected-version
   guard. Revalidate server-side before writing. A stale preview cannot materialize a
   different cohort. Exact command retry is idempotent; conflicting retry is rejected.
5. In the UI, any relevant scope/data change invalidates review. Specifically cover
   editing Run ID after checking confirmation, route Run changes, season/world drift,
   and changed intake controls. The displayed result belongs to the request's target,
   never a newly selected Run. Do not describe the complete page as read-only once it
   exposes a materialization command.
6. Use the actual ownership model. Existing intake calls `get_simulation_run`; inspect
   its relationship to Product Run/Branch instead of treating equal strings as proof of
   ownership. Preserve intentional legacy reads, but do not create a new parallel
   authority or claim Product Run/Branch integration without a demonstrated binding.
7. Carry the new immutable evidence through the relevant existing capture, Saved
   Revision, restore and supported fork paths. Protect the source Run, other branches
   and built-in FAX sources. If an existing unsupported fork boundary remains, report
   it precisely rather than silently returning an incomplete fork.

## Explicit boundaries

- Master is product authority; do not edit it in this implementation PR.
- Do not choose new rarity weights, OVR ranges, label mappings, development curves,
  retirement ages, initial-ranking canon or sanctions. Numeric calibration stays deferred.
- Keep production generation outcomes for existing v1 inputs unchanged.
- Keep the Calibration Lab read-only. Do not auto-apply or recommend a candidate.
- Do not turn the five technical quality bands into the canonical L+–F− potential scale.
- Do not add a live Woorld FAX dependency or mutate protected source Packages/Official Runs.
- This task does not require new Viewer pages, full Elite simulation or a complete new
  forecast engine. The later true Expected vs Generated feature must use pre-generation
  expectations and retain zero-output countries; today's conditional diagnostic must not
  be described as having already delivered that contract.
- Audit normal Run visibility of pre-generated future prospects; preserve the existing
  age-15 activation boundary. Do not expose future players simply to demonstrate the fix.

## Meaningful verification

- Persist a v1 cohort, change the defaults in an isolated test, and prove list/summary
  output and quality provenance stay identical for the old cohort; a new cohort can use
  its explicitly selected newer policy.
- Exercise real persistence/API commands: stale fingerprint, wrong Run/season/world,
  conflicting retry, exact retry and rollback/no partial writes. Avoid mocked service
  tests presented as end-to-end integration.
- Save, restore and supported fork preserve policy/result fingerprints and source isolation.
- UI regression: review Run A, change to Run B, and confirm that no write is possible
  without a fresh review of B. Cover a late response from A after selecting B.
- Preserve the existing prospect profile, lifecycle/Tour-entry and numeric-output fixtures.
- Run the repository's focused PR-critical checks, relevant frontend tests and required
  build/static checks. Confirm hosted required checks are green on the exact final head.
  Do not describe red/pending CI or unrelated locally passing subsets as merge-ready.

## Delivery

Update `CURRENT_STATE.md` and `ROADMAP.md` with what is actually integrated, the audited
commit/test evidence and remaining boundaries. Open one focused PR to current `buuk`.
Return its link, concise change explanation, tests actually run, compatibility behavior,
and any remaining blocker. Perform a separate adversarial pass on stale-preview writes,
legacy policy resolution and recovery before declaring it ready. Do not auto-merge.
