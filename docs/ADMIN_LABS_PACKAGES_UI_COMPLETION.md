# Admin Test Labs / Packages: CS–EN presentation completion

Updated: 23 October 2026. Scope: frontend presentation only; base `buuk` `e39d962bb6797960c47c1c659d57be1dc67bba6b`.

## Implemented in this branch

- **Match Lab (3–10):** built-in loading/error/empty feedback; session inventory including missing selected Session; working scenario actions; isolation and historical-import labels; provenance columns; batch seed limit label; localized result diagnostics, winner filtering, and separate no-results/filter-empty messages. Scenario and result ID/fingerprint fields remain original.
- **Tournament Lab (11–16):** localized scenario/session workflows, safety boundaries, compatible/not-compatible explanations, draw/qualification/group tables, batch diagnostics, match status filter and assertions. Reviewed Run proposal explicitly distinguishes read-only preview, staging into Working Draft and the **separate Run Save** required for an immutable Saved Revision.
- **Player Lab (17–20):** existing configurable parameters and constraints kept; localized built-ins, session availability and safety descriptions; comparison metrics, variant filter and displayed saved-snapshot limits (all / 10 / 25); raw variant identifiers and state fingerprints intact.
- **Shared (1, 2, 21, 23, 24):** localized current-page Lab navigation and landing cards; conflict alert, explicit discard consent and reload label; historical Run/Branch/Saved Revision picker now separately reports loading, failures and genuinely empty inventories, using existing query responses. Native controls and stable technical ARIA selectors are retained.
- **Packages (25–27):** category labels and availability boundary: only World Packages currently have a portable registry. Source and status presentation on list/detail; separate loading/error/unavailable-category/zero-members/filter-empty states; localized World detail counts, tabs, geography and validation summary. Raw validation messages, unknown status codes, source metadata, IDs, versions and fingerprints remain unchanged.
- **Language safety (28):** all added language branches affect text only, without touching query keys, mutation handlers, values, forms or API payload shapes. Regression tests cover CS/EN navigation, a Match scratch scenario + batch seeds across a language re-render and a Packages filter preserved across a genuine LanguageProvider switch.

## Verified already present / deliberately left intact

- The three Labs already support scratch editing without an active Run.
- JSON structured authoring, local preflight, JSON import/export, explicit reviewed replacement, form changes/undo and many CS/EN messages already exist in `LabScenarioAuthoring`; no duplicate framework or actions added.
- Session editor conflict detection, explicit reload and dirty protection were already implemented; only the conflict panel presentation changed.
- Player Lab already enforces 10/25 snapshot display limits; no new calculation or hard limit added.
- Package catalog maps real World packages only; no fake independent category/hybrid registry has been introduced.
- World Package clone workflow from #1636 is untouched.

## Remaining review items / outside allowed scope

- Raw backend and validation diagnostics may be in English; they are intentionally preserved verbatim. Some old local parsing errors and status enum values also remain English technical strings.
- System-origin built-in scenario names and descriptions are data and are displayed unchanged rather than rewritten to a chosen language.
- The existing technical `aria-label` strings (including selector names for automation) remain stable while visible labels are localized; changing these requires coordinated browser selector review.
- Native-v2 tournament compatibility is determined by existing backend inspection only; Lab success does not certify a valid Run tournament.
- Wider Run, server-side registry, simulator, API and complex session-concurrency issues are outside this PR.
- Full real-browser verification and production build are required before owner merge; **Draft skips are not test passes**.

## Tests

Affected focused tests:
`web/src/components/LabNavigation.test.tsx`,
`web/src/pages/MatchTestLabPage.test.tsx`,
`web/src/pages/TournamentTestLabPage.test.tsx`,
`web/src/pages/PlayerTestLabPage.test.tsx`,
`web/src/pages/LabSessionConcurrency.test.tsx`,
`web/src/pages/admin/PackagesHomePage.test.tsx`,
`web/src/components/labAuthoring/LabScenarioAuthoring.test.tsx`.

Suggested local commands from `web/`:

```sh
npm test -- --run src/components/LabNavigation.test.tsx src/pages/MatchTestLabPage.test.tsx src/pages/TournamentTestLabPage.test.tsx src/pages/PlayerTestLabPage.test.tsx src/pages/LabSessionConcurrency.test.tsx src/pages/admin/PackagesHomePage.test.tsx src/components/labAuthoring/LabScenarioAuthoring.test.tsx
npm run build
```

**Verification record:** connector-only edits cannot execute npm locally in this environment. Do not claim the commands above have run; check actual head CI and have Work run the scoped suite/build before Ready.
