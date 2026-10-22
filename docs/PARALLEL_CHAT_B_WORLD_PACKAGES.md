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
- Known limitation outside ownership: the full read-only World Package geography
  editing section has its own direct-save UI and is not fully staged/reviewed by
  this focused Country authoring slice. Further changes there must stay in this
  file and follow explicit backend contracts, or be coordinated with Work.
  Country historical ratings with source evidence are intentionally not
  mutable through the scalar form; a supported explicit year/evidence authoring
  surface would require a separate agreed implementation.
- Full pre-alpha acceptance and prior 78 Viewer baseline failures from #1631
  remain independent. No claims of release readiness.

## Continuation

Continue on **the same branch and #1632 only**. First inspect latest tests/CI,
correct actual failures without dropping controls, then review paused mutation,
back/forward navigation, clone error/success source switches and manual reload
with production services. After successful scoped checks and adversarial review,
coordinate with Work for possible Ready/full relevant acceptance; only the
user may merge.
