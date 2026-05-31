# Viewer Phase 1L Manual QA Checklist and Visual Review Guide

## Purpose

Use this checklist to manually review Viewer Mode Phase 1 in a browser. The goal is to confirm that the MSA Website Mode is a read-only, sports-facing Viewer surface and that it does not expose Admin/Engine controls, fake data, or duplicate Viewer run navigation.

This is a documentation-only QA guide. It does not request product, React, backend, or test changes.

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
- [ ] `Tour` opens and contains season, calendar, current week, tournaments, match center, categories, and champions destinations.
- [ ] `Players` opens and contains player hub/list/status/compare destinations.
- [ ] `Countries` opens and contains country hub/ranking/list/hosting/talent/records destinations.
- [ ] `H2H` opens and contains explorer, rivalry, matchup, comparison, and predict destinations.
- [ ] `Stats` opens and contains records, leaders, streaks, awards, Hall of Fame, and era destinations.
- [ ] `Predictions` opens and contains predictor, odds, qualification, season-end, upset, and futures destinations.
- [ ] Dropdown links are readable and do not overlap the page content in a confusing way.
- [ ] Clicking each dropdown item closes or navigates in a normal browser-expected way.
- [ ] Shared shortcut links lead to a single shared destination rather than duplicate-looking pages:
  - [ ] Rankings → Country Ranking and Countries → Country Ranking both land on `/viewer/countries/ranking`.
  - [ ] Players → Compare Players and H2H → Player Comparison both land on `/viewer/players/compare`.
  - [ ] H2H → Predict Matchup and Predictions → Match Predictor both land on `/viewer/predictions/match-predictor`.

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
