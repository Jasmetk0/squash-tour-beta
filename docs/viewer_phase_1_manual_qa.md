# Viewer Phase 1L Manual QA Checklist and Visual Review Guide

## Purpose

Use this checklist to manually review Viewer Mode Phase 1 in a browser. The goal is to confirm that the MSA Website Mode is a read-only, sports-facing Viewer surface and that it does not expose Admin/Engine controls, fake data, or duplicate Viewer run navigation.

This is a documentation-only QA guide. It does not request product, React, backend, or test changes.

## Phase 7B Viewer UI contract hardening note

- Viewer UI component/class contracts were hardened after Phase 7A.
- Shared active-run, section-card, metadata-list, status-message, deferred-source-card, and CSS safety contracts are now covered.
- The `.viewer-jump-demo::before` flex pseudo-element risk is guarded against.
- No production Viewer/Admin behavior changed.


## Phase 7D responsive and accessibility visual QA note

- Viewer responsive/accessibility manual QA scenarios were documented.
- CSS regression guards now cover topbar/search/card/link wrapping and focus-safety contracts.
- Routes, data fetching, visible copy, metadata labels, links, and read-only safety remain unchanged.
- No backend/Admin route behavior changed.

## Phase 6B deferred infrastructure exactness note

- Deferred infrastructure exactness tests were added after Phase 6A consolidation.
- Hook query enablement, includeRun/includeFinals behavior, event count fallback behavior, source-card empty/error/loading behavior, and source-link order are now covered.
- Deferred visible behavior and routes remain unchanged.
- No backend/Admin route behavior changed.

## Assumptions and setup

- Start the frontend and backend using the normal local development workflow for this repository.
- Use a clean browser profile or clear the Viewer active run value when testing the no-active-run state.
- Viewer active run selection is stored in browser local storage under the Viewer active run key, so browser state matters.
- If the backend has no generated runs, active-run checks that require real run metadata should be recorded as blocked by missing local data, not as UI failures.
- Treat Viewer pages as read-only sports website pages. Admin/Engine pages remain the only place where simulation, commissioner, repair, import, edit, or other mutation workflows should appear.

## Manual QA pass metadata

Fill this in before each manual pass.

- Date:
- Browser and version:
- Screen sizes checked:
  - Desktop:
  - Tablet/mobile:
- Backend running:
- Frontend running:
- Test run ID used:
- Tester:
- Notes:

## 1. Viewer topbar checklist

Open `/viewer` and review the global Viewer header/topbar.

### Navigation structure

- [ ] The page header says `MSA Squash` in Viewer Mode.
- [ ] The mode subtitle says `Viewer / MSA Website Mode`.
- [ ] There is one Viewer primary navigation topbar.
- [ ] There is no second duplicate run navigation row in Viewer Mode.
- [ ] The Viewer topbar order is: `MSA`, `Rankings`, `Tour`, `Players`, `Countries`, `H2H`, `Stats`, `Predictions`, `Search`, Season/Week selector.
- [ ] `MSA` is a direct link to `/viewer`, not a dropdown.
- [ ] `Search` is a direct link to `/viewer/search`, not a dropdown category.
- [ ] The mode switcher is visible and offers `Viewer / MSA` and `Admin / Engine`.
- [ ] The mode switcher does not replace or duplicate the Viewer topbar.

### Dropdowns

For each dropdown, open it with mouse and keyboard where possible.

- [ ] `Rankings` opens and contains sports-facing ranking destinations.
- [ ] `Tour` opens and contains Season Hub, Season Calendar, Current Week, All Tournaments, Match Center, Tournament Categories, and Past Champions destinations; All Tournaments points to `/viewer/tour/tournaments`.
- [ ] `Players` opens and contains player hub/list/status/compare destinations.
- [ ] `Countries` opens and contains Countries Hub, Country Ranking, All Countries, Hosting Nations, Talent Pipeline, and Country Records destinations; Country Ranking points to `/viewer/countries/ranking` and is not listed under Rankings.
- [ ] `H2H` opens and contains explorer, rivalry, matchup, comparison, and predict destinations.
- [ ] `Stats` opens and contains Stats Hub (`/viewer/stats`), Records (`/viewer/records`), leaders, streaks, awards, Hall of Fame, and era destinations.
- [ ] `Predictions` opens and contains predictor, odds, qualification, season-end, upset, and futures destinations.
- [ ] Dropdown links are readable and do not overlap the page content in a confusing way.
- [ ] Clicking each dropdown item closes or navigates in a normal browser-expected way.
- [ ] Shared shortcut links lead to a single shared destination rather than duplicate-looking pages:
  - [ ] Countries → Country Ranking lands on `/viewer/countries/ranking`; Rankings no longer owns or shares the Country Ranking nav item.
  - [ ] Tour → All Tournaments lands on `/viewer/tour/tournaments`; `/viewer/tournaments` remains available as a public alias/shortcut to All Tournaments.
  - [ ] Stats → Stats Hub lands on `/viewer/stats`; Stats → Records lands on `/viewer/records`.
  - [ ] Players → Compare Players and H2H → Player Comparison both land on `/viewer/players/compare`.
  - [ ] H2H → Predict Matchup and Predictions → Match Predictor both land on `/viewer/predictions/match-predictor`.

- [ ] Active navigation state matches the current canonical ownership:
  - [ ] `/viewer/countries/ranking` marks `Countries` and `Country Ranking` active, not `Rankings`.
  - [ ] `/viewer/stats` marks `Stats` and `Stats Hub` active, not `Records`.
  - [ ] `/viewer/records` marks `Stats` and `Records` active, not `Stats Hub`.
  - [ ] `/viewer/tour/tournaments` marks `Tour` and `All Tournaments` active.
  - [ ] `/viewer/tournaments` is accepted as a public shortcut/alias and keeps Tour topbar ownership.

### Season/Week selector

- [ ] The Season/Week selector is always visible on the right side of the Viewer topbar on desktop.
- [ ] The selector shows season, season week, calendar year, year week, and selected viewer context status when expanded/available.
- [ ] Changing or jumping week updates the displayed Viewer context.
- [ ] The selector remains readable at narrower widths.
- [ ] The selector does not expose simulation or Admin mutation controls.

### Admin/Viewer switcher

- [ ] From a top-level Viewer page, `Admin / Engine` navigates to the closest Admin equivalent or Admin home.
- [ ] From a run-scoped Viewer page, `Admin / Engine` navigates to the matching Admin run page where an equivalent exists.
- [ ] Returning to `Viewer / MSA` preserves or restores the closest Viewer equivalent.
- [ ] The switcher is clearly a mode switch, not a Viewer content navigation menu.

## 2. No active run state checklist

Clear the active Viewer run first. A practical browser-console method is to remove the Viewer active run key from local storage and refresh the page. If the UI provides a clear action, use it instead.

For every route below, verify:

- [ ] The page does not crash.
- [ ] The page shows a sports-facing empty, deferred, or “needs selected run” state.
- [ ] The page does not show fake players, fake rankings, fake odds, fake H2H records, fake tournament results, or fake storylines.
- [ ] The page does not show Admin/Engine controls.
- [ ] The page does not show mutating action buttons such as Simulate, Generate, Persist, Apply, Execute, Delete, Edit, Import, Rollover, Rebuild, Override, Save changes, Commit, Regenerate, Repair, Merge, or Overwrite.
- [ ] The page does not show raw JSON/debug payloads as the primary Viewer UI.

### Routes to check without an active Viewer run

- [ ] `/viewer`
- [ ] `/viewer/rankings`
- [ ] `/viewer/rankings/race`
- [ ] `/viewer/tour`
- [ ] `/viewer/tour/current-week`
- [ ] `/viewer/tour/tournaments`
- [ ] `/viewer/tournaments`
- [ ] `/viewer/players`
- [ ] `/viewer/countries`
- [ ] `/viewer/history`
- [ ] `/viewer/records`
- [ ] `/viewer/stats`
- [ ] `/viewer/h2h`
- [ ] `/viewer/predictions`
- [ ] `/viewer/search`

### No-active-run route notes

Use this table while testing.

| Route | Pass/fail | Notes |
| --- | --- | --- |
| `/viewer` |  |  |
| `/viewer/rankings` |  |  |
| `/viewer/rankings/race` |  |  |
| `/viewer/tour` |  |  |
| `/viewer/tour/current-week` |  |  |
| `/viewer/tour/tournaments` |  |  |
| `/viewer/tournaments` |  |  |
| `/viewer/players` |  |  |
| `/viewer/countries` |  |  |
| `/viewer/history` |  |  |
| `/viewer/records` |  |  |
| `/viewer/stats` |  |  |
| `/viewer/h2h` |  |  |
| `/viewer/predictions` |  |  |
| `/viewer/search` |  |  |

## 3. Active run state checklist

Select or set an active Viewer run, then refresh `/viewer`. Confirm the active run is visible in the Viewer active run bar or in the relevant page card where expected.

For every route below, verify:

- [ ] The active run ID is visible where expected.
- [ ] Only real metadata returned by existing read-only APIs is shown.
- [ ] Counts, sample lists, event metadata, snapshot metadata, and Finals availability are clearly labeled as metadata or samples when they are not complete sports read models.
- [ ] Links go to run-scoped Viewer pages under `/viewer/runs/:runId/...` when they are meant to open real run data.
- [ ] The page does not invent fake rankings, fake Race standings, fake tournament results, fake odds, fake H2H records, fake predictions, fake records, or fake player/country achievements.
- [ ] The page does not show Admin/Engine controls.
- [ ] The page does not show mutating action buttons such as Simulate, Generate, Persist, Apply, Execute, Delete, Edit, Import, Rollover, Rebuild, Override, Save changes, Commit, Regenerate, Repair, Merge, or Overwrite.
- [ ] The page does not show raw JSON/debug payloads as the primary Viewer UI.

### Routes to check with an active Viewer run

- [ ] `/viewer`
- [ ] `/viewer/rankings`
- [ ] `/viewer/rankings/race`
- [ ] `/viewer/tour`
- [ ] `/viewer/tour/current-week`
- [ ] `/viewer/tour/tournaments`
- [ ] `/viewer/tournaments`
- [ ] `/viewer/tour/calendar`
- [ ] `/viewer/players`
- [ ] `/viewer/countries`
- [ ] `/viewer/history`
- [ ] `/viewer/records`
- [ ] `/viewer/stats`
- [ ] `/viewer/h2h`
- [ ] `/viewer/predictions`
- [ ] `/viewer/search`

### Active-run route notes

| Route | Active run visible? | Real metadata only? | Run-scoped links OK? | Notes |
| --- | --- | --- | --- | --- |
| `/viewer` |  |  |  |  |
| `/viewer/rankings` |  |  |  |  |
| `/viewer/rankings/race` |  |  |  |  |
| `/viewer/tour` |  |  |  |  |
| `/viewer/tour/current-week` |  |  |  |  |
| `/viewer/tour/tournaments` |  |  |  |  |
| `/viewer/tournaments` |  |  |  |  |
| `/viewer/tour/calendar` |  |  |  |  |
| `/viewer/players` |  |  |  |  |
| `/viewer/countries` |  |  |  |  |
| `/viewer/history` |  |  |  |  |
| `/viewer/records` |  |  |  |  |
| `/viewer/stats` |  |  |  |  |
| `/viewer/h2h` |  |  |  |  |
| `/viewer/predictions` |  |  |  |  |
| `/viewer/search` |  |  |  |  |

## 4. Run-scoped Viewer pages checklist

Replace `:runId` with the active run ID used for the pass.

### Routes to check

- [ ] `/viewer/runs/:runId/rankings`
- [ ] `/viewer/runs/:runId/race`
- [ ] `/viewer/runs/:runId/tournaments`
- [ ] `/viewer/runs/:runId/calendar`
- [ ] `/viewer/runs/:runId/players`
- [ ] `/viewer/runs/:runId/countries`
- [ ] `/viewer/runs/:runId/history`
- [ ] `/viewer/runs/:runId/finals`

### Expected behavior

- [ ] Real read-only data pages still load and display the run context.
- [ ] There is no duplicate run navigation row in Viewer Mode.
- [ ] The global Viewer topbar remains the only Viewer navigation model.
- [ ] There are no simulation controls in Viewer Mode.
- [ ] There are no commissioner/admin controls in Viewer Mode.
- [ ] Planned event detail pages opened from `/viewer/runs/:runId/calendar/:eventId` are read-only.
- [ ] Planned event detail pages do not show wildcard, withdrawal, late replacement, commissioner, save, apply, or commit controls.
- [ ] The Finals page at `/viewer/runs/:runId/finals` has no simulate button.
- [ ] Finals qualification and result detail links, if opened, are read-only and sports-facing.
- [ ] Links inside run-scoped pages either stay in Viewer for read-only browsing or clearly switch to Admin only through the explicit mode switcher.

### Run-scoped route notes

| Route | Pass/fail | Notes |
| --- | --- | --- |
| `/viewer/runs/:runId/rankings` |  |  |
| `/viewer/runs/:runId/race` |  |  |
| `/viewer/runs/:runId/tournaments` |  |  |
| `/viewer/runs/:runId/calendar` |  |  |
| `/viewer/runs/:runId/players` |  |  |
| `/viewer/runs/:runId/countries` |  |  |
| `/viewer/runs/:runId/history` |  |  |
| `/viewer/runs/:runId/finals` |  |  |

## 5. Visual review checklist

Review at desktop width and at least one narrow/mobile width.

### Layout and spacing

- [ ] Page content has enough breathing room around cards, headings, metadata lists, and status messages.
- [ ] Cards align consistently across pages.
- [ ] Similar page sections use similar spacing and visual hierarchy.
- [ ] The active run bar does not crowd the topbar or page title.
- [ ] Empty states are visually intentional, not broken-looking placeholders.

### Card layout

- [ ] Landing cards feel like sports website content cards rather than debug panels.
- [ ] Card titles are short, readable, and user-facing.
- [ ] Metadata cards distinguish labels from values clearly.
- [ ] Sample lists are clearly labeled as samples or existing metadata, not full rankings/results.
- [ ] Deferred feature lists explain what is not connected yet without looking like errors.

### Mobile and narrow widths

- [ ] The topbar remains usable without horizontal content becoming unreadable.
- [ ] Dropdowns can be opened and links can be tapped on a narrow screen.
- [ ] Cards stack cleanly and do not require awkward horizontal scrolling.
- [ ] Metadata grids collapse or wrap in a readable way.
- [ ] Long run IDs, event IDs, and player IDs wrap without breaking the layout.

### Dropdown usability

- [ ] Dropdown menus are easy to discover.
- [ ] Dropdown menus stay open long enough to select an item.
- [ ] Menu items have sufficient click/tap target size.
- [ ] The dropdown visual style is consistent across all categories.
- [ ] Dropdown menus do not obscure critical controls such as the Season/Week selector in a confusing way.

### Text readability

- [ ] Body text is legible against the background.
- [ ] Metadata labels are not too faint.
- [ ] Error, loading, empty, and status messages are visually distinct.
- [ ] Sports-facing language dominates; implementation terms such as raw payloads, debug, engine internals, or database terms are avoided in primary Viewer UI.

### Metadata grid readability

- [ ] Label/value pairs are easy to scan.
- [ ] Missing data uses a clear placeholder such as `—`, `Not available`, or an explicit deferred message.
- [ ] Counts and IDs are labeled precisely.
- [ ] Active run ID, season, week, event index, snapshot sequence, and source event metadata do not look like rankings or results.

### Empty states

- [ ] Empty states explain what is missing and why.
- [ ] Empty states do not imply data exists when it does not.
- [ ] Empty states provide clear next steps only when appropriate, such as selecting an active Viewer run.
- [ ] Empty states do not direct users into Admin mutation workflows except through the explicit mode switcher when necessary.

### Links and CTAs

- [ ] Links look clickable and use clear labels.
- [ ] Read-only links use browsing language such as `Open`, `View`, or `Browse`.
- [ ] CTAs do not use forbidden mutating labels in Viewer Mode.
- [ ] Run-scoped links include the active run ID in the destination URL.
- [ ] The user can tell whether a link stays in Viewer Mode or switches to Admin Mode.

### Sports-site feel

- [ ] Pages feel like an MSA sports website rather than a debug UI.
- [ ] The word `Engine` does not dominate Viewer pages.
- [ ] The main Viewer experience emphasizes rankings, tour, players, countries, H2H, stats, predictions, search, and season/week context.
- [ ] Deferred areas still feel planned and polished, not broken.
- [ ] No page suggests the Viewer can authoritatively simulate or decide sporting outcomes.


## Responsive and accessibility visual QA

Use this Phase 7D checklist after the Viewer UI polish passes to protect the public Viewer surface from responsive, keyboard, and read-only regressions. These checks are manual visual QA scenarios only; they should not change product behavior, route ownership, data fetching, metadata labels, link destinations, or visible product copy.

### Desktop width

- [ ] Viewer topbar categories fit or wrap cleanly without crowding the header.
- [ ] Dropdown menus open on hover and on keyboard `focus-within`.
- [ ] Active route styling remains visible for topbar links and dropdown links.
- [ ] Search input and button remain aligned.
- [ ] Active-run compact selector remains usable and readable.

### Tablet width

- [ ] Topbar wraps without horizontal overflow.
- [ ] Dropdown menu panels remain inside the viewport.
- [ ] Search form remains full-width when needed.
- [ ] Cards maintain readable spacing and do not collapse into cramped columns.

### Mobile width around 360–430px

- [ ] No horizontal page scroll appears.
- [ ] Long run IDs wrap in metadata cards.
- [ ] Long event/player/country names wrap inside cards.
- [ ] Active-run link pills stack or wrap safely.
- [ ] Search input and button remain usable.
- [ ] Context selector panel is reachable and not clipped.

### Keyboard-only navigation

- [ ] Tab focus is visible on topbar links.
- [ ] Tab focus is visible on dropdown links.
- [ ] Tab focus is visible on the search input.
- [ ] Tab focus is visible on the search button.
- [ ] Tab focus is visible on active-run links.
- [ ] Tab focus is visible on context selector controls.
- [ ] Dropdown links are reachable through `focus-within` behavior.
- [ ] No focus trap exists while moving through Viewer navigation, search, active-run links, and context selector controls.

### Viewer read-only safety

- [ ] Viewer pages do not expose forbidden mutation labels: Simulate, Generate, Persist, Apply, Execute, Delete, Edit, Import, Rollover, Rebuild, Override, Save changes, Commit, Regenerate, Repair, Merge, Overwrite.

### Representative pages to manually check

- [ ] `/viewer`
- [ ] `/viewer/runs`
- [ ] `/viewer/runs/:runId/rankings`
- [ ] `/viewer/runs/:runId/calendar`
- [ ] `/viewer/runs/:runId/players`
- [ ] `/viewer/runs/:runId/countries`
- [ ] `/viewer/runs/:runId/history`
- [ ] `/viewer/runs/:runId/finals`
- [ ] `/viewer/predictions/match-odds`
- [ ] `/viewer/stats`
- [ ] `/viewer/records`

## 6. Bug report template

Copy this template for each issue found.

```text
Route:
Mode:
Active run selected:
What I expected:
What happened:
Screenshot:
Severity:
Notes:
```

Suggested severity scale:

- `Blocker`: Page crashes, Viewer exposes dangerous mutation controls, or data integrity/replayability appears at risk.
- `High`: Viewer shows fake authoritative sports data, wrong route mode, duplicate navigation, or confusing Admin controls.
- `Medium`: Page works but has misleading labels, broken links, poor empty states, or significant visual/layout issues.
- `Low`: Minor copy, spacing, polish, or consistency issue.

## 7. Phase 2 planning notes

After manual QA, likely next implementation phases could be:

- Real top 10 rankings preview.
- Real Race preview.
- Real tournament cards.
- Player profile polish.
- Country profile polish.
- Search read model.
- Match/history read model.
- Prediction read model.
- No-future-knowledge enforcement.

## Manual QA Repair 1 note — topbar, context selector, and search

This repair does not mark Viewer Phase 1 complete. It records the intended QA behavior for the repaired Viewer shell:

- Main Viewer topbar category labels navigate to their landing pages: Rankings, Tour, Players, Countries, H2H, Stats, and Predictions are links, while MSA still links to `/viewer`.
- Category dropdowns are submenu access points opened by desktop hover, keyboard focus, or the explicit submenu control; clicking the main category label is navigation, not a dropdown toggle.
- Dropdown item active state uses exact route matching. Parent topbar categories may be active for their route group, but only the exact dropdown destination should be highlighted inside the menu.
- The Season/Week selector keeps the compact `Season 2004/05 · W10` style, now includes local season/week controls, and persists the selected Viewer context in browser localStorage only.
- Jump to Week updates the same local Viewer context as the Season/Week selector; it does not mutate backend state.
- Topbar Search is now a search input shell. Pressing Enter or using the search control opens `/viewer/search` with an optional `q` query string; no backend search endpoint or complete result set is implied.
- Existing run-scoped Viewer pages remain available and read-only, but technical payloads still need future Viewer polish. Later work should hide raw payloads behind an explicit `Show technical payload` control instead of showing debug-style data as primary sports UI.
- Future Viewer/Admin product work should add a Run Library / World Saves concept with multiple independent worlds, a Viewer run switcher, and Admin run creation/management. Viewer must remain read-only. This is deferred and is not implemented in this repair.

## Manual QA Repair 2 note — neutral hover/focus topbar polish

This repair does not mark Viewer Phase 1 complete. It records the intended QA behavior for the polished Viewer topbar:

- Visible submenu arrows/caret buttons were removed from Rankings, Tour, Players, Countries, H2H, Stats, and Predictions.
- Main category labels remain landing-page links to their category routes.
- Category dropdowns open from desktop hover and keyboard focus/focus-within on the category area; dropdown links remain keyboard reachable.
- On desktop, the topbar should remain one row with MSA, all category labels, the Search input, and the Season/Week selector.
- Active nav styling is neutral and subtle; color/accent styling is reserved for hover/focus states, not permanent filled active pills.
- Dropdowns should close after selecting a dropdown item or after navigation/route changes.
- Mobile and genuinely narrow widths may wrap the topbar, search, and Season/Week selector for usability.

## Viewer Phase 2A note — run-scoped rankings/race publication polish

This note does not mark Viewer Phase 1 or full Viewer Phase 2 complete. It records the intended QA behavior for the Phase 2A run-scoped rankings/race polish:

- Run-scoped Viewer ranking and Race pages now use sports-facing, read-only publication layouts for `/viewer/runs/:runId/rankings`, `/viewer/runs/:runId/rankings/:snapshotSequence`, `/viewer/runs/:runId/race`, and `/viewer/runs/:runId/race/:snapshotSequence`.
- Ranking/Race list pages should show active run context, publication counts, selected publication metadata, and Viewer detail links without exposing raw JSON as primary page content.
- Ranking/Race detail pages should show sports-facing sequence, kind, source event, week, planned category/tour/template, plan position, and safe Viewer links before any technical data.
- Raw payloads are hidden behind collapsed `Show technical payload` sections on detail pages only. The section is read-only and exists for technical inspection without making debug payloads the primary Viewer UI.
- Admin snapshot/debug pages remain separate and stable; Admin routes may continue to use technical wording and raw payload displays where appropriate.
- No fake ranking rows, fake Race rows, fake players, or new ranking engine behavior were added.
- Full ranking/Race table previews remain deferred unless the payload shape is already safely parsed by future Viewer read-model work.

## Viewer Phase 2B note — run-scoped tournaments/event polish

This note does not mark Viewer Phase 1 or full Viewer Phase 2 complete. It records the intended QA behavior for the Phase 2B run-scoped tournaments/event polish:

- Run-scoped Viewer tournaments/event pages now use sports-facing, read-only layouts for `/viewer/runs/:runId/tournaments` and `/viewer/runs/:runId/tournaments/:eventId`.
- The tournaments list should show active run context, event counts, completed/persisted event counts where available, and real event metadata from existing event/calendar APIs only.
- Tournament/event detail pages should show sports-facing run, event, season, week, category, tour, template, sequence, status/result availability, and safe Viewer links before any technical data.
- Raw event/result payloads are hidden behind collapsed `Show technical event data` sections on detail pages only. The section is read-only and exists for technical inspection without making debug payloads the primary Viewer UI.
- Admin technical/debug pages remain separate and stable; Admin event/calendar routes may continue to use technical wording and raw payload displays where appropriate.
- No fake tournaments, fake results, fake draws, fake matches, fake winners, fake players, fake odds, or fake storylines were added.
- Rich tournament detail, draw, match, winner, and score previews remain deferred until safe Viewer read models/payload parsers exist.

## Phase 2C note — Run-scoped Players/Countries polish

- Run-scoped Viewer players and countries pages now use sports-facing, read-only layouts for the selected run.
- Technical player and country payloads are hidden behind collapsed technical sections where relevant.
- Admin technical/debug player and country pages remain separate and stable.
- No fake player rankings, country achievements, titles, records, storylines, or country stats were added.
- Rich player/country profiles remain deferred until safe read models exist for those views.

Do not use this note to mark full Viewer Phase 2 complete; this is only the Phase 2C players/countries polish slice.

## Phase 2D note — run-scoped Calendar and Planned Event polish

- Run-scoped Viewer calendar and planned event pages now use sports-facing, read-only layouts for the selected run.
- Technical calendar and planned-event data is hidden behind collapsed technical sections where relevant.
- Admin technical/calendar pages remain separate and stable for Admin workflows.
- No fake results, draws, matches, winners, odds, or storylines were added.
- Rich event draw and match previews remain deferred until safe read models exist.

## Phase 2E — Viewer run history/finals polish

- Viewer run-scoped history and World Tour Finals pages now use sports-facing, read-only layouts.
- Technical history/finals payload data is collapsed behind technical disclosure sections.
- Admin history/finals pages remain separate from Viewer routes.
- Viewer pages do not invent fake Finals results, qualifiers, matches, odds, or storylines.
- Rich Finals bracket and match previews remain deferred until authoritative read models are available.

## Phase 2F — Viewer Active Run Picker

- Viewer now has an active run picker using existing read-only run APIs.
- Selection is local Viewer context/localStorage only.
- No backend run mutation was added.
- Future Run Library / World Saves remains deferred.

## Phase 2G — Viewer topbar active run indicator

- The Viewer topbar now has a compact active run control/indicator near the Season/Week selector.
- Active run selection remains local Viewer context/localStorage only.
- The homepage active run picker remains available.
- No backend run mutation was added.

## Viewer Phase 2G Repair — compact active-run auto-apply

- The compact topbar active-run selector now auto-applies when a run is selected.
- The homepage active-run picker remains explicit and keeps its `Set active run` button.
- No backend run mutation was added.

## Viewer Phase 2H — Viewer copy and UI consistency cleanup

- Viewer copy and empty states were normalized.
- No data logic or backend behavior changed.
- Technical data remains collapsed.
- No fake data was added.

## Phase 3A rankings preview note

- Viewer rankings can now show a real Top 10 preview when the latest ranking snapshot payload shape is safely parsed.
- Unknown payload shapes still show deferred previews.
- Raw technical payload remains collapsed.
- No fake ranking rows or new ranking engine were added.

## Phase 3B race preview note

- Viewer Race to Finals can now show a real Top 10 preview when race snapshot payload shape is safely parsed.
- Unknown payload shapes still show deferred previews.
- Raw technical payload remains collapsed.
- No fake race rows or new Race engine were added.

## Phase 3C tournament result preview note

- Viewer tournament detail can now show a real result preview when event result payload shape is safely parsed.
- Unknown payload shapes still show deferred previews.
- Raw technical event data remains collapsed.
- No fake tournament winners, matches, scores, or new tournament engine were added.


## Phase 3D tournament list result badges note

- Viewer tournaments list can now show small real result metadata when event result payload is safely parsed.
- Unknown result payloads do not show fake winners/status.
- Raw tournament result payloads remain hidden from the list page.
- No backend/tournament engine changes were added.

## Phase 3E player profile summary note

- Viewer player profile now shows real player identity/attribute/source summary from existing data.
- Missing/unknown detail shapes still show deferred previews.
- Technical player data remains collapsed.
- No fake rankings, titles, records, Elo, or career achievements were added.

## Phase 3F country profile summary note

- Viewer country profile now shows real country overview/player-base/source/talent-band summary from existing data.
- Missing/unknown detail shapes still show deferred previews.
- Technical country data remains collapsed.
- No fake country rankings, Team Championship wins, titles, records, medals, hosting stats, or top 100 counts were added.

## Phase 3G ranking/race player profile links note

- Ranking and Race preview player names now link to Player Profile pages when `player_id` is available.
- Rows without `player_id` remain plain text.
- No parser/backend/Admin behavior changed.

## Phase 3H tournament result player profile links note

- Tournament result preview champion/finalist names now link to Player Profile pages when `player_id` is available.
- Tournament list champion badges link when `player_id` is available.
- Rows without `player_id` remain plain text.
- No parser/backend/Admin behavior changed.

## Phase 3I country profile links note

- Ranking/Race preview country values now link to Country Profile pages when a country code is available.
- Player list/profile country values now link to Country Profile pages.
- Missing country values remain plain text.
- No parser/backend/Admin behavior changed.

## Phase 3J player tournament history links note

- Player Profile Tournament History event names now link to Tournament Detail pages when `event_id` is available.
- Entries without `event_id` remain plain text.
- No backend/Admin behavior changed.

## Phase 3K tournament week detail links note

- Tournament list/detail week values now link to Week Detail pages when week is available.
- Missing week values remain plain text.
- No backend/Admin behavior changed.

## Phase 3L player tournament history week detail links note

- Player Profile Tournament History week values now link to Week Detail pages when week is available.
- Entries without week remain plain text.
- Existing event links remain unchanged.
- No backend/Admin behavior changed.

## Phase 3M country top player profile links note

- Country list/profile top player values now link to Player Profile pages when `player_id` is available.
- Rows without `player_id` remain plain text.
- No backend/Admin behavior changed.

## Phase 3N week detail sports-facing polish note

- Week Detail now shows sports-facing run/week context and real events for the selected week.
- Week event links point to planned event and tournament detail pages when available.
- Publication previews remain metadata-only/deferred unless safely matched.
- No fake tournament results, matches, odds, or storylines were added.
- No backend/Admin behavior changed.

## Phase 3O week detail tournament result badges note

- Week Detail tournament rows now show small real result metadata when event `tournament_result` is safely parsed.
- Champion links to Player Profile when `player_id` is available.
- Unknown result payloads do not show fake winners/status/matches.
- No backend/Admin behavior changed.

## Phase 3P season calendar tournament result badges note

- Season Calendar rows now show small real result metadata when persisted event `tournament_result` is safely parsed.
- Champion links to Player Profile when `player_id` is available.
- Unknown result payloads do not show fake winners/status/matches.
- No backend/Admin behavior changed.

## Phase 3Q planned event result preview note

- Planned Event page now shows small real result metadata when persisted event `tournament_result` is safely parsed.
- Champion links to Player Profile when `player_id` is available.
- Unknown result payloads do not show fake winners/status/matches.
- No backend/Admin behavior changed.

## Phase 3R shared Viewer route helpers note

- Viewer route path construction was centralized in shared helpers.
- Existing Viewer links keep the same href behavior.
- No backend/Admin/parser/result-preview behavior changed.

## Viewer Phase 3S — Tournament Result Metadata Helper

- Tournament result metadata rendering was centralized in a shared read-only Viewer helper.
- Existing Season Calendar, Planned Event, Week Detail, Tournament list, and Tournament Detail result previews keep the same behavior.
- No backend/Admin/parser behavior changed.

## Viewer Phase 3T — Rankings/Race publication list polish

- Run-scoped Ranking/Race publication list pages now show clearer sports-facing snapshot metadata and safe source-event links.
- Unmatched source events remain safe fallback text.
- No parser/backend/Admin behavior changed.

## Viewer Phase 3U — top-level Viewer landing links polish

- Top-level Viewer landing/hub pages now link existing sample players, countries, events, weeks, rankings, and race metadata to run-scoped detail pages when IDs are available.
- Missing IDs remain plain text.
- No backend/Admin/parser/result-preview behavior changed.

## Viewer Phase 3V — History / Storyline links polish

- Viewer History/Storyline sections now link existing activity events, weeks, and snapshot metadata to run-scoped detail pages when IDs are available.
- Missing/unmatched IDs remain plain text.
- No backend/Admin/parser/result-preview behavior changed.

## Phase 3W — Viewer Finals page sports-facing polish

- Run-scoped Finals page now shows sports-facing finals summary, qualification, and result metadata from existing finals data when available.
- Player/snapshot links are added only when IDs are available.
- Missing finals data remains deferred/no-data.
- No backend/Admin/finals-engine behavior changed.

## Phase 3X — Viewer Finals qualification/result subpage polish

- Finals qualification/result subpages now show sports-facing metadata from existing finals APIs when available.
- Player/snapshot/source-event links are added only when IDs are available.
- Missing or unknown finals payloads remain deferred/no-data.
- No backend/Admin/finals-engine behavior changed.

## Phase 3Y — Viewer Finals/History route helpers cleanup

- Remaining run-scoped History/Finals route path construction was centralized in shared Viewer route helpers.
- Finals Summary calendar-back link label now matches its calendar destination.
- Existing History/Finals href behavior remains unchanged.
- No backend/Admin/finals-engine behavior changed.

## Phase 3Z — Records/Stats landing polish note

- Records/Stats landing pages now show clearer source metadata and safe links to existing run-scoped events, snapshots, and finals pages.
- Record/stat groups remain deferred unless real read models exist.
- No fake records, stats, awards, or Hall of Fame data were added.
- No backend/Admin behavior changed.

## Viewer Phase 3AA — Search sports-facing MVP

- Viewer Search now shows read-only active-run results for players, countries, and tournaments using existing APIs.
- Result links are added only when IDs are available.
- Empty/no-match states remain safe.
- No backend/Admin behavior changed.

## Phase 3AB — H2H / Player Comparison MVP note

- Viewer H2H / Player Comparison now shows read-only player comparison from existing active-run player data.
- Player/country links are added only when IDs are available.
- Missing params/data remain deferred or no-data.
- No fake H2H records, predictions, odds, or match results were added.
- No backend/Admin behavior changed.

## Phase 3AC — Match Predictor input preview MVP note

- Viewer Match Predictor now shows read-only predictor input previews from existing active-run player data.
- Player/country links are added only when IDs are available.
- Missing params/data remain deferred or no-data.
- Prediction/odds outputs remain deferred; no fake winners, odds, probabilities, or match results were added.
- No backend/Admin behavior changed.

## Phase 3AD — Shared Player Comparison / Match Predictor helper cleanup

- Shared Player Comparison / Match Predictor helper logic was cleaned up while preserving existing read-only behavior.
- H2H and Match Predictor still use active-run player data only.
- Prediction/H2H outputs remain deferred; no fake odds, winners, records, or match results were added.
- No backend/Admin behavior changed.

## Phase 3AE — Viewer Run Browser note

- Viewer Run Browser now shows available runs and safe links to run-scoped Viewer pages using existing run list data.
- Active Viewer run status remains client-side and uses existing selection behavior.
- Empty/error states remain safe.
- No backend/Admin behavior changed.

## Phase 3AF — Run Browser hub discovery note

- Run Browser is now discoverable from Viewer hub/link areas.
- Existing active-run links and selection behavior remain unchanged.
- No backend/Admin behavior changed.

## Phase 3AG — Predictions subpages deferred polish

- Prediction/odds subpages now show conservative active-run metadata and safe links while keeping outputs deferred.
- No fake odds, probabilities, winners, markets, projections, or results were added.
- No backend/Admin behavior changed.

## Phase 3AH — Stats/Records subpages deferred polish

- Stats/Records subpages now show conservative active-run metadata and safe links while keeping outputs deferred.
- No fake records, stats, awards, Hall of Fame entries, rankings, leaders, or achievements were added.
- No backend/Admin behavior changed.

## Phase 3AI — Tour subpages deferred polish

- Tour subpages now show conservative active-run metadata and safe links while keeping match/category/champion outputs deferred.
- No fake matches, categories, champions, brackets, scores, winners, or storylines were added.
- No backend/Admin behavior changed.

## Phase 3AJ — Rankings subpages deferred polish

- Rankings subpages now show conservative active-run metadata and safe links while keeping ranking outputs deferred.
- No fake rankings, Elo ratings, Power Ratings, form scores, Next Gen standings, No.1 history, leaders, or storylines were added.
- No backend/Admin behavior changed.

## Phase 3AK — Players subpages deferred polish

- Players subpages now show conservative active-run player metadata and safe links while keeping directory/status/prospect outputs deferred.
- No fake player lists, statuses, prospects, bios, rankings, awards, or storylines were added.
- No backend/Admin behavior changed.

## Phase 3AL — Countries subpages deferred polish

- Countries subpages now show conservative active-run country metadata and safe links while keeping directory/hosting/talent/record outputs deferred.
- No fake country rankings, hosting records, talent pipelines, medals, awards, records, or storylines were added.
- No backend/Admin behavior changed.

## Phase 3AM H2H subpages deferred polish note

- H2H subpages now show conservative active-run metadata and safe links while keeping rivalry, matchup, and finals-rivalry outputs deferred.
- No fake H2H records, rivalry records, matchup counts, finals records, scores, winners, or storylines were added.
- No backend or Admin behavior changed.

## Phase 3AN — Deferred source metadata helper cleanup

- Deferred Viewer source metadata helper logic was cleaned up while preserving existing read-only behavior.
- Deferred pages keep the same labels, links, no-data states, and safety behavior.
- No backend/Admin behavior changed.

## Phase 3AO — Remaining ViewerShell placeholder audit note

- Remaining top-level Viewer routes were checked for generic `ViewerShellPage` placeholders.
- The only remaining generic top-level Viewer route found is `/viewer/countries/ranking` (`Country Ranking`), which should become a conservative deferred country-ranking metadata page later.
- No new deferred pages were implemented in this phase.
- Viewer remains read-only; no backend/Admin behavior changed.

## Phase 3AP — Country Ranking deferred metadata page

- Country Ranking now shows conservative active-run country metadata and safe links while keeping ranking output deferred.
- No fake country rankings, ranking positions, medals, awards, records, talent rankings, hosting rankings, or storylines were added.
- No backend/Admin behavior changed.

## Phase 3AQ — Viewer Phase 3 completion audit

- Viewer Phase 3 completion audit was performed across Viewer routing, Viewer page/test coverage, and this QA note.
- Remaining generic top-level `ViewerShellPage` placeholders: none found under `/viewer` or `/viewer/*` routes.
- Viewer remains read-only with no backend/Admin behavior changes.
- Full `npm test` and `pytest` were not run; only targeted Viewer frontend test/build checks were run for this audit.

## Phase 4A — Viewer route/link registry audit

- Viewer route/link registry audit was performed across Viewer routes, Viewer navigation, active-run links, route helpers, and this QA note.
- Findings by severity: blocker 0, medium 3, low 2.
- No broken Viewer links to missing `App.tsx` routes were found in the inspected Viewer nav/link areas.
- No backend/Admin behavior changed; Viewer remains read-only.
- Full `npm test` and `pytest` were not run; this documentation-only phase ran `git diff --check` only.

## Phase 4B — Viewer nav canonicalization and route helpers

- Viewer top-level route helpers and conservative navigation canonicalization were added.
- Stats/Records nav mismatch was resolved: Stats uses `/viewer/stats`, and Records uses `/viewer/records`.
- Country Ranking nav ownership was clarified under Countries navigation only.
- `/viewer/tour/tournaments` and `/viewer/tournaments` remain available; Tour navigation uses `/viewer/tour/tournaments`, while `/viewer/tournaments` remains an alias/public shortcut to the same ViewerTournamentsPage. Future cleanup may choose one canonical public URL.
- No backend/Admin behavior changed.

## Phase 4C — Mode switcher route-helper cleanup

- Mode switcher Viewer targets now use shared Viewer route helpers where available.
- Existing Admin/Viewer mode switch behavior remains unchanged.
- Dynamic Viewer run IDs remain safely encoded where helpers are used.
- No backend/Admin behavior changed.

## Phase 4D — Inline Viewer route string cleanup audit

- Remaining inline top-level Viewer route strings were audited.
- Obvious top-level Viewer links now use shared route helpers where safe.
- Inline route strings without helpers were left unchanged and documented for future cleanup: deferred Rankings, Tour, Players, Countries, H2H, Stats, and Predictions subpage links still live inline until a broader route registry pass.
- No backend/Admin behavior changed.

## Phase 4E — Viewer dropdown subroute helper cleanup

- Viewer dropdown subroute helpers were added.
- Viewer dropdown links now use shared route helpers while preserving labels, order, and destinations.
- Deferred page behavior and route availability remain unchanged.
- No backend/Admin behavior changed.

## Phase 4F route helper coverage note

- Viewer route helper coverage was audited against the real Viewer routes registered in `web/src/App.tsx`.
- Dropdown helper destinations were verified against existing Viewer routes, including the `/viewer/tour/tournaments` and `/viewer/tournaments` All Tournaments aliases.
- No backend or Admin behavior changed.

## Phase 4G — Viewer page link route-helper cleanup

- Viewer page links now use shared dropdown route helpers where safe.
- Link labels and destinations remain unchanged.
- Deferred page behavior and route availability remain unchanged.
- No backend/Admin behavior changed.

## Phase 4H — Run-scoped Viewer route helper coverage audit

- Run-scoped Viewer route helper coverage was audited against real Viewer run routes.
- Dynamic route segments are covered by focused helper tests.
- No backend/Admin behavior changed.

## Phase 4I — Run-scoped Viewer inline route helper cleanup

- Remaining obvious inline run-scoped Viewer route strings were audited.
- Safe replacements now use shared run-scoped Viewer route helpers.
- Link labels and destinations remain unchanged.
- No backend/Admin behavior changed.

## Phase 4J — Viewer topbar active-state regression coverage

- Viewer topbar active-state regression coverage was added for Country Ranking, Stats/Records, and tournament aliases.
- Canonical nav ownership remains unchanged.
- No backend/Admin behavior changed.

## Phase 4K — Viewer manual QA navigation checklist sync

- Viewer manual QA navigation checklist wording was synced with the current canonical Viewer navigation behavior after Phases 4B–4J.
- Country Ranking is documented under Countries only; Stats Hub and Records point to their canonical Viewer routes; Tour All Tournaments points to `/viewer/tour/tournaments` while `/viewer/tournaments` remains documented as a public alias/shortcut.
- Active-state expectations now align with Phase 4J regression coverage.
- No backend/Admin/source behavior changed.

## Phase 4L — Viewer navigation registry extraction

- Viewer navigation registry was extracted from `Layout.tsx` into a dedicated Viewer navigation module.
- Labels, order, destinations, route ownership, active-state behavior, and route availability remain unchanged.
- No backend/Admin behavior changed.

## Phase 4M — Mode switcher route helper extraction

- Mode switcher route-target logic was extracted from `Layout.tsx` into a dedicated Viewer helper module.
- Existing Admin/Viewer mode switch behavior and encoding behavior remain unchanged.
- No backend/Admin behavior changed.

## Phase 4N — Viewer topbar component extraction

- Viewer topbar rendering was extracted from `Layout.tsx` into a dedicated component.
- Labels, order, destinations, search behavior, active-state behavior, and route ownership remain unchanged.
- No backend/Admin behavior changed.


## Phase 4O — Viewer navigation test module split

- Viewer navigation tests were split by module after ViewerTopbar/navigation/mode-switcher extraction.
- Coverage for canonical nav ownership, active states, aliases, search, and mode switcher mappings remains intact.
- No backend/Admin/source behavior changed.

## Phase 4P — Admin navigation registry extraction

- Admin navigation data/helpers were extracted from `Layout.tsx` into a dedicated navigation module.
- Admin nav labels, order, run-scoped links, and behavior remain unchanged.
- Viewer behavior remains unchanged.
- No backend/Admin route behavior changed.

## Phase 4Q — Admin navigation component extraction

- Admin navigation rendering was extracted from `Layout.tsx` into a dedicated component.
- Admin primary nav, run-scoped nav, and current run context behavior remain unchanged.
- Viewer behavior remains unchanged.
- No backend/Admin route behavior changed.

## Phase 4R — Mode switcher component extraction

- Mode switcher rendering was extracted from `Layout.tsx` into a dedicated component.
- Mode switcher labels, hrefs, active-link behavior, and route-target behavior remain unchanged.
- Viewer and Admin navigation behavior remain unchanged.
- No backend/Admin route behavior changed.

## Phase 4S — Layout shell extraction and regression hardening

- Layout shell mode/run/header logic was extracted into dedicated helpers/components.
- Layout remains a thin shell composing AppShellHeader, AdminNavigation, ViewerTopbar, and Outlet.
- Titles, subtitles, app-shell classes, current-run context behavior, and navigation behavior remain unchanged.
- No backend/Admin route behavior changed.

## Phase 4T — Layout/navigation architecture completion audit

- Layout/navigation architecture was audited after the Phase 4L–4S extraction sequence.
- `Layout.tsx` remains a thin shell composing the extracted header, Admin navigation, Viewer topbar, non-admin run-context fallback, and route outlet.
- Extracted Layout/navigation modules have focused regression coverage for shell mode helpers, header rendering, mode-switcher targets, Admin navigation, Viewer navigation, and Viewer topbar behavior.
- No backend/Admin route behavior changed.

## Phase 4U — Viewer active-run controls architecture cleanup

- Viewer active-run controls were audited and safely cleaned up after the Layout/navigation extraction sequence.
- Active-run labels, localStorage behavior, changed-event behavior, quick links, and topbar behavior remain unchanged.
- No backend/Admin route behavior changed.

## Phase 4V — Viewer Season/Week context controls architecture cleanup

- Viewer Season/Week context controls were audited and safely cleaned up after the Layout/navigation and active-run extraction sequence.
- Season/Week labels, context update behavior, selector metadata, and topbar behavior remain unchanged.
- No backend/Admin route behavior changed.

## Phase 4W — Viewer active-run and context architecture completion audit

- Viewer active-run and Season/Week context architecture was audited after helper extraction.
- Module boundaries and focused regression coverage were verified.
- Active-run storage/event behavior and Season/Week context behavior remain unchanged.
- No backend/Admin route behavior changed.

## Phase 4X — Viewer Run Browser architecture cleanup note

- Viewer Run Browser metadata/link display was audited and safely cleaned up.
- Run metadata labels/order, quick links, active-run behavior, and routes remain unchanged.
- No backend/Admin route behavior changed.

## Phase 4Y — Viewer hub/link-card configuration audit

- Viewer hub/link-card configuration was audited and safely cleaned up.
- Hub labels, descriptions, link order, active-run links, and routes remain unchanged.
- No backend or Admin route behavior changed.

## Phase 4Z — Viewer Home hub links integration + ModePages cleanup note

- Viewer Home and MSA landing hub links were audited after Phase 4Y.
- `viewerTopLevelHubLinks` is now used only where it exactly preserves existing top-level Viewer page title/description behavior for MSA Rankings, Race to Finals, and Run Browser.
- Viewer Home visible copy, active-run links, hub labels, descriptions, link order, and routes remain unchanged.
- Page-specific dynamic links and Admin/Engine links remain local to their existing pages.
- No backend or Admin route behavior changed.

## Phase 5A — Foundational Viewer page module split

- Foundational Viewer page infrastructure was split out of `ModePages.tsx`.
- `useActiveViewerRunId`, `ViewerShellPage`, and `ViewerRunBrowserPage` now live in dedicated modules.
- Visible Viewer shell, Run Browser, active-run behavior, links, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- No backend/Admin route behavior changed.

## Phase 5B — Viewer Home page module extraction

- `ViewerHomePage` was extracted from `ModePages.tsx` into a dedicated Viewer page module.
- Homepage helper logic moved with the page where safe.
- Visible Viewer Home copy, active-run summary, featured event, nearby events, previews, links, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- No backend/Admin route behavior changed.

## Phase 5C — Viewer Rankings/Race page module extraction

- Viewer Rankings/Race snapshot landing pages were extracted from `ModePages.tsx` into dedicated Viewer page modules.
- Shared snapshot landing behavior moved with the page family.
- Visible Rankings/Race titles, descriptions, empty states, snapshot links, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- No backend/Admin route behavior changed.

## Phase 5D — Viewer Season/Tour page module extraction

- Viewer Season/Tour page family was extracted from `ModePages.tsx` into dedicated Viewer page modules.
- Shared season/tour helper logic moved with the page family where safe.
- Visible Season/Tour titles, descriptions, metadata labels, event links, empty states, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- Deferred Tour pages stayed in `ModePages.tsx` because they share broader deferred source metadata behavior with remaining Viewer page families.
- No backend/Admin route behavior changed.

## Phase 5E — Viewer Players/Countries page module extraction

- Viewer Players/Countries page family was extracted from `ModePages.tsx` into dedicated Viewer page modules.
- Shared player/country display/render helper logic moved with the page family where safe.
- Visible Players/Countries titles, descriptions, metadata labels, sample lists, links, empty states, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- Country Ranking, H2H, and Compare stayed in `ModePages.tsx` because they share broader deferred/comparison behavior with remaining Viewer page families.
- No backend/Admin route behavior changed.

## Phase 5F — Viewer Search/Comparison page module extraction

- Viewer Search/H2H/Compare exploration page family was extracted from `ModePages.tsx` into dedicated Viewer page modules.
- Shared comparison/search display/render helper logic moved with the page family where safe.
- Visible Search/H2H/Compare/Match Predictor titles, descriptions, query behavior, metadata labels, links, empty states, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- H2H deferred subroutes and broader Predictions pages stayed in `ModePages.tsx` because they share broader predictions/deferred source metadata behavior with remaining Viewer page families.
- No backend/Admin route behavior changed.

## Phase 5G — Viewer History/Finals page module extraction

- Viewer History/Finals page family was extracted from `ModePages.tsx` into dedicated Viewer page modules.
- Shared history/finals display/render helper logic moved with the page family where safe.
- Visible History/Finals titles, descriptions, metadata labels, activity summaries, links, empty states, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- Existing run-scoped History/Finals detail pages stayed in `ViewerRunHistoryFinalsPage.tsx` because they were already outside `ModePages.tsx` and have focused route/detail coverage.
- Broader predictions/deferred Finals Qualification stayed in `ModePages.tsx` because it shares broader deferred/prediction source metadata behavior with remaining Viewer page families.
- No backend/Admin route behavior changed.

## Phase 5H — Viewer Stats/Records page module extraction

- Viewer Stats/Records page family was extracted from `ModePages.tsx` into dedicated Viewer page modules.
- Shared Stats/Records landing/display helper logic moved with the page family where safe.
- Visible Stats/Records titles, descriptions, metadata labels, deferred group labels, links, empty states, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- Stats/Records deferred subroute pages stayed in `ModePages.tsx` because they share broader deferred source metadata behavior with remaining Viewer page families.
- No backend/Admin route behavior changed.

## Phase 5I deferred source metadata extraction

- Shared Viewer deferred source metadata infrastructure was extracted from ModePages into dedicated Viewer deferred modules.
- Remaining deferred pages and Stats/Records landing now reuse the shared source metadata helpers where exact.
- Source metadata labels, loading/fallback text, latest event/snapshot/finals links, empty states, and routes remain unchanged.
- No backend/Admin route behavior changed.

## Phase 5J — Remaining Viewer deferred page module extraction

- Remaining Viewer deferred page families were extracted from `ModePages.tsx` into dedicated Viewer deferred modules.
- Deferred page configs moved into pure config helpers where safe.
- Existing shared deferred source metadata helpers continue to drive source metadata rendering.
- Visible deferred titles, descriptions, source metadata labels, sample lists, source links, empty states, and routes remain unchanged.
- `ModePages.tsx` keeps compatibility exports for existing routes.
- No backend/Admin route behavior changed.

## Phase 5K — ModePages final shell cleanup

- `ModePages.tsx` final shell cleanup was performed after major Viewer page family extraction.
- Landing, Admin landing/settings/wrapper pages, and simple Viewer read-only pages were moved into dedicated modules where safe.
- `ModePages.tsx` now acts primarily as a compatibility export shell.
- Visible Landing/Admin/read-only Viewer titles, descriptions, links, and routes remain unchanged.
- No complex leftovers stayed in `ModePages.tsx`; it now contains compatibility re-exports only.
- No backend/Admin route behavior changed.

## Phase 5L — App route import decoupling

- App route imports were decoupled from `ModePages.tsx` and now point directly to dedicated page modules/barrels.
- `ModePages.tsx` remains as a compatibility export shell.
- Route paths, route order, route params, visible page behavior, and compatibility exports remain unchanged.
- No backend/Admin route behavior changed.

## Phase 5M — ModePages retirement audit

- `ModePages.tsx` compatibility shell was removed after App route imports were decoupled.
- Page modules/barrels are now the source of truth for route imports.
- App route paths, order, params, visible behavior, and route availability remain unchanged.
- No backend/Admin route behavior changed.


## Phase 5N — Page module architecture completion audit

- Final page-module architecture audit confirmed `ModePages.tsx` remains removed and is no longer a current route import source.
- Historical Phase 5A–5L notes that mention `ModePages.tsx` compatibility exports describe those earlier phases only; Phase 5M and later reflect the current retired state.
- `App.tsx`, dedicated page modules, and page family barrels are now the source of truth for route page imports.
- No visible Viewer/Admin behavior, route paths, route order, route params, fallback behavior, or backend behavior changed.

## Phase 6A — Deferred page query/render consolidation

- Deferred page source-query/render patterns were audited and consolidated where exact.
- Shared deferred hooks/components/link helpers were introduced only for behavior-identical page patterns.
- Deferred page titles, descriptions, source metadata labels, source links, empty/loading/error text, sample lists, and routes remain unchanged.
- Pages with distinct structure kept local logic where safer.
- No backend/Admin route behavior changed.

## Phase 6C — Viewer test harness and deferred fixtures consolidation

- Viewer test harness and deferred fixture builders were consolidated.
- Deferred exactness tests now share common provider setup and fixture factories.
- Test assertions for query enablement, metadata fallback behavior, source links, empty/error/loading states, and read-only safety remain explicit.
- No production Viewer/Admin behavior changed.

## Phase 6D — Viewer test utility adoption audit

- Remaining Viewer tests were audited for shared harness/fixture adoption.
- Only behavior-identical/high-value duplicated setup was migrated.
- Exact assertions for routes, labels, metadata, links, empty states, and read-only safety remain explicit.
- No production Viewer/Admin behavior changed.

## Phase 7A — Viewer UI consistency polish

- Viewer UI consistency polish was applied through shared Viewer components/styles.
- Card spacing, metadata readability, empty/loading/error hierarchy, and responsive grids were improved.
- Routes, data fetching, active-run behavior, visible copy, metadata labels, links, and read-only safety remain unchanged.
- No backend/Admin route behavior changed.

## Phase 7C — Viewer responsive/accessibility polish

- Viewer responsive/accessibility polish was applied through shared styles/components.
- Focus visibility, mobile wrapping, long-value overflow safety, and small-screen Viewer layout were improved.
- Routes, data fetching, active-run behavior, visible copy, metadata labels, links, and read-only safety remain unchanged.
- No backend/Admin route behavior changed.
