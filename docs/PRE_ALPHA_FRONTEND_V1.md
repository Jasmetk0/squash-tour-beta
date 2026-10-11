# Pre-alpha frontend V1 — approved shell, Runs and Packages decisions

Decision dates: 10–11 October 2026. Status: **approved product design; not implementation evidence**.
Authority: Master v76 §§27.6, 27.9, 27.17–27.18 and 31.30–31.31; newer explicit user decisions prevail.
Older illustrative route trees are not an alternative source of authority.

## Appearance and context

- First pre-alpha Admin has one dark theme; no Light/Dark/System selector.
- No Viewer/Admin selector in the first pre-alpha shell, including global pages.
- Active Run controls are `Run → Branch → Time`. Global pages have none of them.
- Selecting time changes viewing context only. It never advances, rewinds or regenerates simulation.
- Czech/English, readable state labels/icons, global search/Ctrl+K and attention/task access remain part of the product contract.
- Preserve future Viewer code and read-only/public-knowledge contracts without making Viewer part of the first-pre-alpha navigation.

## Global navigation and Home

Sidebar: Home, Runs, Packages, Test Lab. Application settings are separated at the bottom.
The existing collapsible/icon/hover/pin sidebar contract remains.

Startup opens neutral Squash Engine Home with no silently activated/restored Run.
Home contains three useful entries — Runs, Packages, Test Lab — each with a short description and supported factual summary.
A compact recent-Runs list appears below; opening is an explicit user action.
Exact summary fields, graphic layout and entry actions are still to be designed.
The Test Lab hub covers Match, Tournament and Player modules and needs no selected Run.

## Run navigation

After a Run opens, replace global navigation with these seven main categories:
1. Home
2. World
3. Players
4. Tour
5. Rankings & Analytics
6. Simulation
7. History & Branches

Separate **Run Management** at the bottom. It combines the earlier provisional Data and Settings categories without dropping their functions.
The Squash Engine logo returns to global Home and respects the draft/navigation safeguards.

| Category | Approved responsibility |
| --- | --- |
| World | Countries, population, country attributes, Talent Preview and expected-versus-realized intake. |
| Players | Players/prospects, profiles, attributes, development, health, training, creation and generation. |
| Tour | Seasons, calendar, systems/Tours/categories, Series/Editions, entries, draws/groups, matches and results; sporting policy and points tables. |
| Rankings & Analytics | Computed ranking and source breakdown, statistics/H2H, records, rivalries and supported analytical comparisons. |
| Simulation | Execution/controls, ranges, Week/Season Transitions, AI intervention and stop policy. Match stepping is also reachable in its detail. |
| History & Branches | Branch map/timeline, revisions/checkpoints, restoration and Compare States; separate world-event, AI-decision-history and audit subpages. |
| Run Management | Run settings, override overview, applying Packages, import/export, backups, validation and storage. |

Contextual imports also belong near their objects, such as player import in Players and country import in World.
Results/Replay remain reachable from their source matches/tournaments/players.
Task Center, Notification Center and favorites are cross-page utilities; do not conflate their data with history.

## Run Home composition

- Top: Run/branch identity and unsaved-change state.
- Full-width below: two segmented position indicators, exactly 50 seasons and 61 Season Weeks.
- Left: **Next steps / Další postup** — actual upcoming simulation events, active/paused task and link to Simulation.
- Right: **Needs attention / Vyžaduje pozornost** — concrete blockers/warnings and pending interventions, with direct links.
- Below: **World activity / Dění ve světě** — factual results, ranking/health/talent/record changes and access to the latest simulation digest.

Empty sections stay compact and factual; an empty Run is legitimate.
Unavailable/error/unsupported data must not become an invented zero or “no problems”.
Exact metrics, ordering, colors, filters and historical-versus-current progress semantics remain open.
For an initial current-state implementation, expose that boundary explicitly; do not substitute today's values for a historical snapshot.

## Players in Packages

Players are approved as part of pre-alpha Packages (Player Package scope).
This is no longer merely a possible future type.
Exact payload/schema, temporal basis, supported identity mapping/dependencies and Setup composition remain open.
Reuse preview, validation, provenance, built-in read-only protection and independent Run-copy principles.
Approval does not authorize copying fictional career history, silent identity merge or treating an unimplemented editor as complete.

## Runs and Package navigation — approved 11 October 2026

Runs uses wide rows. A simple expandable section lists actual Branch names, their supported season/week positions and Open actions.
Full Branch creation, maps, histories, comparisons and restore belong to Run → History & Branches.
Do not imply one shared simulation week for a multi-Branch Run or promote a Main/Official Branch.
Exact row metrics and the quick-open default are not settled by this simple-expansion approval.

Packages opens as a category hub, not a mandatory combined list.
Clicking a category opens its own list; All packages opens one searchable/filterable inventory.
Use supported types/content categories; do not replace existing World/Category/Series/Calendar/Setup schemas with the illustrative UI labels.
A genuinely multi-content package appears in Hybrid and every category whose data it contains, but only once in All packages.
A dependency/reference does not by itself count as contained data. Navigation classification does not settle Player/hybrid serialization.

Package detail starts on Overview and has:
- Overview: name, description, version, provenance, actual content summary.
- Contents: supported object-type sections, lists and item details.
- Validation: errors, missing dependencies and warnings, linked to affected items.

Supported actions: Apply to Run, Copy and Export; custom sources may be edited.
Built-in source editing normally creates an editable copy and preserves protected originals.

Apply to Run is a separate page with:
1. Target Run and Branch, or entry to create a new Run.
2. Contents and supported selection.
3. Before → after preview, conflicts/warnings and explicit confirmation.

The user can choose only part of the content and supported changes/values.
Recompute the exact diff and validation after selection changes; distinguish selected and excluded changes.
Confirmation is bound to the exact target, source version and reviewed selection; stale inputs require a new preview.
Unselected contents remain unchanged. No silent overwrites/deletion or identity merges.
Preserve existing Working Draft, manual Save, audit/provenance and independent-copy rules.
This approves the UI contract, not unresolved dependency mapping, conflict priorities, Player careers or payload schemas.

## Implementation sequencing and unchanged boundaries

Build the shell and two Home pages first, reusing canonical Product Run context and functioning routes.
This document does not settle every submenu, player/tournament detail, form or package serialization field. Current implementation/review evidence is separately recorded in PRE_ALPHA_FRONTEND_CHECKPOINT_2026_10_11.md.
Full Viewer, Live Ranking, advanced Forecast/Markets, deep training, mobile and court/shot animation retain their earlier deferred status.
Do not add backend sporting decisions, mutate sources or manufacture dashboard values to satisfy this layout.
Preserve creation → packages → players → calendar/entries/draw/match → ranking → Save/reopen/Replay.
CI/browser evidence must identify the actual source and covered scope; mocks are not production integration.
