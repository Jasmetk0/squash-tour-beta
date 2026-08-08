# Engine UX & Architecture Migration Guide (FAX / MSA)

## Status and authority

This document is **implementation/migration guidance**, not a second product constitution.

The current product-level source of truth is:

- `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`
- synchronized from **Squash Engine Master Vision v31** (updated 6 Aug 2026)

If this guide, older beta code, `Beta_Engine.docx`, an old handoff, or an older UX proposal conflicts with the current constitution/Master, the current constitution/Master wins.

Repository overview/operating documents (`README.md`, `ROADMAP.md`, and `AGENTS.md`)
also summarize that canon; they do not outrank the constitution or turn a target into
implemented behavior.

**Important:** planned target behavior must never be described as already implemented unless verified in the repository.

---

# 1. What changed relative to the older UX spec

The previous version of this file contained several concepts that are now obsolete or too strong.

| Older UX assumption | Current Master v31 direction |
|---|---|
| One privileged **Master Run** | Runs are normal independent worlds; no user-facing privileged Master Run concept |
| **Sandbox Runs** as the normal alternative-history model | Alternative history primarily lives in **branches inside a Run**; separate Runs are independent worlds/copies/imports |
| `Official/Main Branch` as a superior branch | No superior branch. One **Viewer Branch** only selects what the Viewer displays |
| One global Admin IA mixing Runs, World, Simulate, etc. | Clear split between **Global Admin** and **Run Admin** |
| App opens into a run-centric/admin-centric surface | Neutral **Squash Engine Home** is the application root |
| Global run-aware World pages as the default model | Global **source Packages** are separate from editable **Run snapshots** |
| Dashboard as a generic global engine dashboard | Main dashboard/Home is **Run-scoped** and reflects current Run + active branch |
| Home contains generic simulation execution controls | Home primarily provides overview/attention/continuation; simulation execution belongs in **Simulate/workflow surfaces** |
| Existing beta navigation can define the target | Existing beta routes/pages are transitional implementation details only |

Do not reintroduce the older assumptions in new work without an explicit newer product decision.

---

# 2. Current application-shell target

## 2.1 Global root

`Squash Engine Home`

Current confirmed global entries:

- **Runs**
- **Packages**

This is not a Viewer/Admin chooser and does not silently restore an old Run.

## 2.2 Global Admin scope

Global Admin has no active:

- Run,
- branch,
- season/week.

It manages genuinely global data, especially:

- Runs,
- source World Packages,
- source Category Packages,
- future global areas only when they are explicitly designed as global.

Viewer cannot be opened from a global page until a Run is selected.

## 2.3 Run Admin scope

Run Admin always has:

- selected Run,
- selected active Admin branch,
- viewed season/week context.

The exact final sidebar is still open, but the current working direction is:

1. **Home**
2. **World**
3. **Players**
4. **Tour / Seasons**
5. **Simulate**
6. **Analysis**
7. **History / Branches**
8. supporting settings/diagnostics/operator pages where they logically belong

Do not canonize a more detailed tree just because the current beta already has routes for it.

---

# 3. Run Home target

The Run Admin landing page is the working **Home / command center** for the selected Run and branch.

It should answer quickly:

- Which Run is open?
- Which branch is active?
- What season/week is currently being viewed?
- Where is the actual simulation currently positioned?
- How far is the Run overall and within the current season?
- What is currently happening?
- What requires Admin attention?
- Are there unsaved changes, failed/active jobs, validation problems or important warnings?
- Where should the Admin go next?

### Preferred content direction

- concise Run identity/context,
- overall Run progress,
- current season progress,
- current/next activity,
- health/validation/attention,
- Viewer Branch/publication context where useful,
- task/job state,
- recent meaningful activity,
- shortcuts into major Run areas.

### What Home should not become

- a copy of Viewer pages,
- a huge statistics portal,
- a generic navigation landing page,
- the main place for every simulation mutation,
- a page filled with fake summary data when the backend does not provide it.

The current implementation of `/admin/runs/:runId` can evolve incrementally into this target while preserving working APIs/routes.

---

# 4. Run and branch UX

## 4.1 Runs

The full `All Runs` page is global and neutral. Current confirmed presentation direction is wide rows rather than oversized cards.

Distinct actions for a Run:

- **Open in Admin**
- **Open branches**
- **Open in Viewer**

A compact Run switcher is for fast context changes only. Complex management belongs on the full Runs page.

## 4.2 Branches

Branches are equal alternative timelines inside one Run.

A branch may diverge after its fork in:

- calendar,
- tournament editions,
- entrants/draws,
- results,
- rankings/statistics,
- player attributes/form/fatigue/health,
- rules/configuration,
- other time-valid state.

The target data model preserves common history once and stores branch-specific divergence.

## 4.3 Viewer Branch

Exactly one branch per Run is the **Viewer Branch**.

Its only special meaning is publication/display: the read-only Viewer uses it.

UX must not imply:

- “official winner”,
- main simulation authority,
- privileged historical truth,
- branch priority.

Use `Viewer Branch` terminology in new UI. Existing backend names such as `official_branch_id` or “main” must be treated as migration debt, not product language.

---

# 5. Header and contextual controls

On pages with an active Run, the current target order is:

### Viewer
`Run → Time → Viewer/Admin`

### Admin
`Run → Branch → Time → Viewer/Admin`

Global search / `Ctrl+K` remains part of the application shell; exact placement can be refined.

The time control changes **viewing context only**. It never advances or rewinds simulation.

Status below/near the time control:

- Viewer: `PRESENT / PAST`
- Admin: `PRESENT / PAST / FUTURE`

Changing mode should preserve Run, time, object and matching subpage when possible. Viewer always resolves against the Run's current Viewer Branch.

---

# 6. Packages UX

## 6.1 Global source Packages

Confirmed initial types:

- World Packages
- Category Packages

Built-in GitHub source Packages are read-only. Local/custom source Packages can be editable.

## 6.2 Run snapshots

When a Run is created, selected World + Category Package versions are copied into the Run as independent versioned snapshots.

Both snapshots are required. Their source identities/versions remain provenance only:
neither snapshot is a live link, and later global source edits must not alter the Run.

Therefore UX must clearly distinguish:

- **Edit source Package** — global operation affecting future Runs,
- **Edit this Run's Package snapshot** — Run-scoped operation affecting only this Run/branch according to historical rules.

There is no live synchronization from a source Package into existing Runs.

Future package types (for example Player Package) are a strong direction only, not current canon.

---

# 7. World UX

Do not assume the old global `World → Countries / Talent Preview` structure is the final target for every context.

We now have two different concepts:

### Global Package authoring
Edit source World Packages outside a Run.

### Run World
Inspect/edit the Run's embedded world snapshot and its generated state in the active Run/branch.

Country/profile pages should keep authored/configuration inputs clearly separated from generated historical output.

Population, talent quantity/quality and country strength are important concepts, but exact generation mathematics remain open and should not be hard-coded from an old illustrative UX proposal.

---

# 8. Players UX

Player identity is stable (`player_id`) while time-varying state belongs to Run/branch/week history.

The Admin player system ultimately needs to cover:

- prospects/juniors,
- Tour players,
- historical state,
- attributes/OVR/potential,
- physical profile,
- form/fatigue/health,
- status/lifecycle,
- manual edits and locks,
- generation/regeneration provenance.

Viewer exposes public/historical information and must not automatically reveal authoritative internal health/potential information.

The exact page/tab structure is still to be designed page-by-page.

---

# 9. Tour / Seasons UX

This area should consolidate the sporting structure of a Run:

- seasons,
- calendar,
- Tournament Series and Editions,
- categories and their historical configuration,
- entries,
- qualification,
- draws,
- matches/results,
- Finals and team/continental/world competitions where relevant.

Existing technical pages can survive during migration, but they should progressively become understandable Admin workflows rather than a collection of backend-shaped screens.

Do not convert currently open sport rules into permanent UI assumptions.

---

# 10. Simulate UX

`Simulate` and manual/step-by-step work are complementary.

The dedicated simulation area should eventually be the primary launcher/control center for supported scopes such as:

- Next Match,
- Next Round,
- Next Tournament,
- Next Week,
- Next Season,
- Full Simulation,
- custom target/range.

Before execution, Admin should understand:

- target Run + branch,
- starting state,
- requested stopping point,
- prerequisites,
- blocking errors,
- warnings,
- likely impacted history/configuration.

Long-running simulation belongs in a Task Center/job model with progress and safe stop/recovery behavior.

### Migration rule

Existing direct Run-level simulation buttons/endpoints can remain temporarily for compatibility, but new Home/dashboard UX should route the user toward dedicated simulation workflows rather than expanding direct execution on Home.

---

# 11. Analysis UX

Current working direction is an Admin analysis area for generated insight and technical/sporting inspection, potentially including:

- Official and alternative rankings,
- ranking policy inspection,
- Elo/other analytical ratings,
- model-derived odds/predictions,
- comparisons,
- diagnostics tied to generated sporting data.

The exact boundary between Analysis and Diagnostics remains open. Do not duplicate the same tool in multiple top-level areas simply to fill navigation.

---

# 12. History / Branches UX

Target experience connects:

- interactive branch map,
- branch divergence points,
- Viewer Branch badge,
- selected-branch timeline,
- saved versions,
- checkpoints,
- simulation/import/manual-change history,
- restore/branch/compare operations.

Viewer Branch must be visually identifiable without implying that it is the “best” or “official” branch.

---

# 13. Global vs Run navigation migration

When refactoring current navigation, classify every destination first:

### Global
Examples:
- Squash Engine Home
- All Runs
- source Packages

### Run-scoped
Examples:
- Run Home
- Run World
- Players of a Run
- Tour/Seasons
- Simulate
- Analysis
- Branches/History
- run diagnostics/settings

A page must not silently inherit a previous Run if it is meant to be global.

---

# 14. Current implementation principles

During migration:

1. Reuse real existing APIs and data where valid.
2. Do not create fake dashboard values to match mockups.
3. Preserve current working routes while introducing clearer target navigation when practical.
4. Do not destructively rename persisted backend fields solely for UI terminology; plan migrations.
5. New user-facing labels should follow current terminology even if adapters still call old endpoints.
6. Keep Viewer read-only.
7. Keep historical time semantics explicit.
8. Every mutating action needs appropriate validation/preview/confirmation according to risk.
9. Tests should verify product behavior, not only that components render.
10. Planned target features must be clearly distinguished from implemented features.

---

# 15. Highest-priority migration backlog

### P0 — stop reinforcing obsolete architecture

- Remove new user-facing `Master Run`, `Sandbox Run`, `Official Branch` and privileged `Main Branch` assumptions.
- Standardize product terminology around Run, active Admin branch and Viewer Branch.
- Treat old backend naming as migration debt.

### P1 — shell and scopes

- Add/complete neutral `Squash Engine Home`.
- Build global Runs area.
- Build global Packages area.
- Separate Global Admin and Run Admin sidebars/headers.
- Standardize Run/Branch/Time/Mode controls.

### P1 — Run Admin

- Continue evolving `/admin/runs/:runId` into concise Home command center.
- Move generic simulation execution toward dedicated Simulate workflows.
- Add two useful progress indicators: overall Run progress and current-season progress when supported by real data.
- Make warnings/attention actionable through links to the correct Admin workflow.

### P1/P2 — data model alignment

- Introduce/complete `viewer_branch_id` semantics through APIs/schema/migrations.
- Ensure Package sources and Run snapshots are truly independent.
- Ensure branch-specific configuration/history is correctly persisted.
- Audit time-travel queries for branch/week correctness.

### P2 — workflow consolidation

- Consolidate Tour/Seasons technical pages into sporting workflows.
- Design Players and World pages page-by-page against the Run/global split.
- Build History/Branches map/timeline.
- Define Analysis vs Diagnostics boundary.

---

# 16. Explicitly unresolved UX areas

Do not silently finalize these from the old spec:

- complete final Global Admin sidebar,
- complete final Run Admin sidebar,
- full Viewer public-site navigation,
- exact MSA homepage blocks,
- Viewer reveal modes,
- exact `Show in Viewer` save timing,
- complete branch lock/concurrency UX,
- final Analysis/Diagnostics split,
- exact source/Run Package editor layouts,
- detailed player profile Admin tabs,
- full Tournament/Season page hierarchy,
- exact Task Center behavior and progress estimation,
- mobile/responsive design beyond current desktop-first scope.

---

# 17. Historical note

The former detailed proposals in this file — including Master Run/Sandbox terminology, global World hub assumptions, specific Talent Preview aggregates/formulas and several fixed page structures — are **not automatically current decisions**.

They may still contain useful implementation ideas, but they must be re-evaluated against the current product constitution before reuse.

For product decisions, consult `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` first.
