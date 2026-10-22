# Parallel Chat B — World Packages authoring handoff

Date: 2026-10-22. Owner: ordinary ChatGPT (parallel Chat B).
Repository: `Jasmetk0/squash-tour-beta`; base: `buuk` at owner-merged
`0bd062166150283e22163f52a97aa96649bcbf04` (#1631); own Draft PR
[#1632](https://github.com/Jasmetk0/squash-tour-beta/pull/1632), branch
`feat/world-package-authoring-chat-b-20261022`. **User merges; this chat never merges.**

## Boundaries and decisions

- File ownership: `web/src/pages/WorldLibraryPage.tsx`, its direct
  `WorldLibraryPage.test.tsx` and `WorldPackageAuthoring.test.tsx`,
  new `web/src/components/worldPackageAuthoring/review.ts` with focused unit tests,
  and this handoff only. No routing, global translations/styles, client/types,
  backend, simulation, protected templates, CI or canonical Master edits.
- Read AGENTS, CURRENT_STATE, ROADMAP, PRE_ALPHA_TEST_POLICY and relevant Master v85
  country / package library safety rules; inspected actual API types, Country V1
  schemas, World Package mutation service, domain rating version constraints and
  #1631. Only UI authoring flow changes are intended.
- Existing Run snapshots remain independent of later World Package edits. Built-in
  and official packages are read-only. Only editable `custom_config` clones
  can create, edit or delete country data.
- Country v2 ratings: 1–10 in tenths; legacy v1: 1–5 finite values without invented
  one-decimal rule. Preserve the selected version, and never silently migrate
  a legacy country. Historical rating-evidence countries remain non-editable
  for scalar strength attributes via this editor; no interpolation logic was
  introduced. Population year: integer 1955–2050; population: positive strict
  integer; creation requires year 2020; area: optional positive integer.
  Existing legacy court count is retained as compatibility data during edits;
  no new court-count editor field exists.
- World Package API uses expected semantic fingerprint and HTTP 409 on conflicting
  edits. A reviewed write freezes source World ID, country code, fingerprint and
  complete payload. A 409 never silently re-fetches and retries the write.
  A user may explicitly discard/reload current source data for another review.

## Implemented candidate scope

1. Validates empty versus zero, integers, authored rating precision, mandatory
   ID/name/geography, duplicate population years and country-code syntax before
   preparing a command, alongside unchanged backend enforcement.
2. Creates an explicit before→after review table for country fields and population
   year additions/changes/removals, with exact source World ID, Country and package
   fingerprint. Saving needs a separate confirmation; no-op reviews cannot write.
3. Creates a review/confirmation for new Country and built-in → Custom World clone.
   Keeps dry-run clone preview and separate real clone command.
4. Mutation functions now receive exact captured World ID and Country code, rather
   than consulting a subsequently selected route. Late completions show no
   success or navigation on a different route/source; relevant cache refreshes
   target the original source.
5. Conflict shows a focused message, prevents automatic retry and offers
   explicit reload. UI routes and browser unload warn before abandoning unsaved
   country/clone edits; save-in-progress buttons/fields are disabled.
6. Adds local CS/EN wording to the new authoring flow without touching shared
   translation files. Previous library read-only tables remain as inherited from
   #1631.

## Focused tests and limits

- `web/src/components/worldPackageAuthoring/review.test.ts`: empty/zero/NaN,
  fractional numbers, rating scale/precision, duplicate/default years and diff.
- `web/src/pages/WorldPackageAuthoring.test.tsx`: exact reviewed Country payload,
  conflict 409 / no automatic retry / manual reload, late response after switching
  World Package/Country, read-only protection and population review/confirm.
- `web/src/pages/WorldLibraryPage.test.tsx`: existing creation/clone contracts
  adapted to explicit confirmation.
- Required verification: run targeted Vitest files, production `web` TypeScript/Vite
  build, and inspect Fast CI / CodeQL / path-applicable acceptance on **latest
  exact PR head**. Green checks on prior heads, cancelled tests and skipped
  Draft gates do **not** count. Do not call this merge-ready based on Draft alone.
- Frontend tests are mocked at the API boundary, not actual production
  HTTP/SQLite/Chromium E2E; an end-to-end manual/hosted walkthrough and
  adversarial audit before merge remain necessary.
- The previously direct-save Timezone Area editor is now replaced with a
  separate authored-review component in the allowed World Package directory:
  `web/src/components/worldPackageAuthoring/TimezoneAreaEditor.tsx`.
  It checks the backend ring constraints (nonempty, unique uppercase-format
  codes, nonempty trimmed names, contiguous positional indexes), stages a
  position-by-position before→after diff, captures exact source/fingerprint,
  and handles HTTP 409 with user-authorized reload rather than automatic retry.
  An external fingerprint change cannot silently rebase a reviewed mutation.
  Existing Country Timezone Area references are still protected by backend
  referential-integrity checks; UI does not invent a separate authority.
- `TimezoneAreaEditor.test.tsx` now exercises preview confirmation, reorder
  submission, invalid/duplicate codes, protected sources, 409 with explicit
  reload, stale fingerprint and delayed response after source switching.
  `WorldLibraryPage.test.tsx` verifies dirty Timezone Area navigation,
  including browser POP/Back and the user's Stay/Discard choice, and a
  late create-country response after the editor is abandoned.
  `WorldPackageAuthoring.test.tsx` also verifies a late delete-country
  response after the user has navigated elsewhere.
- Remaining limitations: Country historical ratings with source evidence are
  intentionally not mutable through the scalar form; a supported explicit
  year/evidence authoring surface requires separate agreed implementation.
  SPA Back/Forward and same-app programmatic navigation now use a shared
  `UnsavedWorldPackageNavigationGuard.tsx` with React Router v7 `useBlocker`.
  Production uses `createBrowserRouter` and the focused tests use
  `createMemoryRouter`. Users explicitly Stay or Discard/Leave; pending
  writes cannot redirect after the original editor unmounts or location key
  changes. Normal create-success navigation bypasses the blocker only after
  server confirmation. Hard reload/tab close still uses `beforeunload`; no
  claim is made about custom cross-origin navigation protection.
- Full pre-alpha acceptance and prior 78 Viewer baseline failures from #1631
  remain independent. No claims of release readiness.

## Continuation

Continue on **the same branch and #1632 only**. First inspect latest tests/CI,
correct actual failures without dropping controls, then adversarially review paused mutation, browser back/forward navigation,
clone error/success source switches, Timezone Area conflicts and manual reload
with production services. After successful scoped checks and adversarial review,
coordinate with Work for possible Ready/full relevant acceptance; only the
user may merge.

## Continuation checkpoint — SPA navigation and stale-write safety

- **Final code candidate before this documentation commit:** `ed6bff47fffeb3d6cbe060922aa5e0f9a08274d1`.
- **Hosted Fast CI success:** [run 39837599596](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39837599596).
  Critical frontend: **198/198 passed** (14 files); direct World Package
  contract/navigation tests: **23/23 passed** (4 files); `tsc -b` and Vite
  production build passed. Path-skipped jobs are not claimed as passes.
- Added `UnsavedWorldPackageNavigationGuard` for SPA navigation protection,
  with original location/mount guards against late Country create/delete/update
  navigation or success after leaving the original editor. All mutations
  target their original frozen World Package identity and fingerprint;
  no automatic retries on 409.
- The documentation update itself changes PR HEAD; required checks must be
  reassessed on the exact latest commit. Still **Draft**, not a production E2E
  pass: actual backend/SQLite/Chromium acceptance was not executed here.
  No branch merge performed.

## Continuation checkpoint — frozen delete/clone review and conflict classification

- New Country deletion review freezes `worldId`, `countryCode`, `locationKey`,
  country display name and `fingerprint` when the review opens. The final
  destructive API call uses exactly the saved fingerprint; if the package
  changes, the action is disabled, not silently rebound to the new version.
- Built-in → Custom cloning now shows the source fingerprint in review and
  checks that fingerprint before dispatch. The target ID validation matches
  the backend pattern `^[a-z0-9][a-z0-9_]{2,63}$`; a leading underscore
  is rejected. Late results from another route/source are not presented.
- **Important backend-contract limit:** `WorldPackageCloneRequest` does not
  carry an expected source fingerprint. The client-side clone review can
  reject a visibly changed source *before dispatch*, but cannot guarantee
  atomic source-version consistency if the built-in contents change between
  dispatch and the server copying them. This is a coordinated backend/API
  enhancement, **outside this chat's file ownership**. Built-in packages are
  read-only in the normal product, reducing but not eliminating that theoretical
  deployment/replacement race. No backend workaround was invented here.
- After HTTP 409 on Country/population/delete edits, stale Save stays locked
  until the user explicitly reloads. UI distinguishes a duplicate Country
  code (also HTTP 409 in the backend) from a stale package fingerprint, and
  offers a code correction instead of the irrelevant conflict reload.
- Focused tests additionally cover deletion review after a fingerprint
  change, duplicate Country creation, clone ID format, source version changing
  during clone review, and locked Save after 409.
- No actual backend/SQLite/Chromium E2E has been run in this chat, and no
  protected World Package data have been modified. Draft status remains
  mandatory until Work coordinates applicable acceptance.

## Continuation — October 22 authoring guards and navigation

- Timezone Area editor: after a rejected fingerprint (HTTP 409) or successful
  response that cannot be reconciled with current authoritative package and
  geography, the reviewed Save is **locked** until explicit user-approved
  reload and review. No repeated dispatch of the old fingerprint. The error
  is not mislabelled as an in-progress save.
- Timezone Area success comparison now uses code, name and zero-based position,
  not JSON object serialization order. A response with equivalent values and
  differently ordered object properties is accepted.
- Built-in → Custom World clone: editing ID, name or description clears an
  obsolete dry-run preview/error. Upon successful creation, the clone draft
  (including manually edited description) resets while retaining the confirmed
  result and Open-new-world link. The source page's unsaved-change navigation
  blocker must no longer obstruct opening the successfully created package.
- Focused tests now exercise reload-required Timezone Area conflicts, a
  mismatched post-write refresh, property-order-insensitive success,
  stale dry-run preview clearing, and successful clone navigation even with
  a custom description.
- Remaining integration boundary: this chat cannot run local server or
  SQLite/Chromium E2E via repository checkout because the execution
  environment has no direct DNS access to GitHub. GitHub connector and hosted
  Fast CI checks are used instead. Real API behavior is not claimed tested.
- Keep extending the **same Draft PR #1632** on
  `feat/world-package-authoring-chat-b-20261022`. No merge; user controls
  merging. Never modify source Earth historical data or other parallel owners.
