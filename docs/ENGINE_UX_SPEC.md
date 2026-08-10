# Engine UX & Architecture Migration Guide (FAX / MSA)

## Status and authority

This document is **implementation/migration guidance**, not a second product constitution.

The current product-level source of truth is:

- `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md`
- synchronized through **Squash Engine Master Vision v42** (updated 10 Aug 2026) and preserving newer explicit post-v42 decisions recorded in the constitution

If this guide, older beta code, `Beta_Engine.docx`, an old handoff or an older UX proposal conflicts with the current constitution/Master/newer explicit decision, the higher-authority source wins.

Repository overview/operating documents (`README.md`, `ROADMAP.md`, `AGENTS.md`) summarize that canon; they do not outrank it or turn a target into implemented behavior.

**Important:** planned target behavior must never be described as already implemented unless verified in the repository. Omission from a shorter summary is not evidence that an older still-valid decision was superseded.

---

# 1. Application-shell target

## 1.1 Global root

`Squash Engine Home`

Current confirmed global entries:

- Runs
- Packages

It is not a Viewer/Admin chooser and does not silently restore an old Run.

## 1.2 Global Admin scope

Global Admin has no active Run, branch or season/week. It manages genuinely global data such as Runs and source Packages.

Viewer cannot be opened from a global page until a Run is selected.

## 1.3 Run Admin scope

Run Admin always has selected Run, active Admin branch and viewed season/week context.

The exact final sidebar remains provisional. Current working direction groups the product around areas such as Home, World, Players, Tour/Seasons, Simulation, Analysis, History/Branches and supporting operator/settings tools.

Do not canonize a more detailed tree merely because current beta routes exist.

---

# 2. Run Home

Run Admin landing page is **Home**.

It should quickly answer:

- Which Run/branch/time context is open?
- Where is simulation currently positioned?
- How far is the full 50-season Run?
- How far is the current 61-week season?
- What is happening now or next?
- What needs Admin attention?
- Are there active/failed tasks, unsaved changes, warnings or blockers?

**Confirmed fixed elements:**

- segmented overall-Run progress indicator,
- segmented current-season progress indicator.

Home is not the primary place for every simulation mutation. Execution-heavy workflows belong in dedicated Simulation pages.

---

# 3. Run, branch and mode context

## 3.1 Runs

All Runs is global and neutral. Confirmed presentation direction remains wide rows rather than oversized cards.

Distinct Run actions:

- Open in Admin
- Open branches
- Open in Viewer

The compact Run switcher is for quick context changes, not destructive/complex management.

## 3.2 Branches

Branches are equal alternative timelines. UI must not imply a superior Official/Main branch.

Exactly one branch per Run is the **Viewer Branch**; its only special meaning is which saved timeline Viewer displays.

## 3.3 Viewer ↔ Admin

Switching should preserve Run, time, object and matching subpage when possible.

Admin → Viewer never silently changes Viewer Branch. If an exact counterpart is unavailable in Viewer Branch, open the closest meaningful fallback and explain the context shift.

---

# 4. Header and time controls

Current target order on Run-scoped pages:

### Viewer
`Run → Time → Viewer/Admin`

### Admin
`Run → Branch → Time → Viewer/Admin`

Global search/`Ctrl+K` remains part of the shell.

Time control changes **viewing context only**; it never advances or rewinds simulation.

Visible relation to actual simulation state:

- Viewer: `PRESENT / PAST`
- Admin: `PRESENT / PAST / FUTURE`

---

# 5. Packages and World UX

Clearly distinguish:

- **source Package authoring** — global,
- **Run snapshot inspection/editing** — Run-scoped.

Selected World + Category Package versions become independent Run snapshots at Run creation; no live synchronization exists afterwards.

Country/profile pages should separate authored configuration from generated historical output.

Travel Regions/Timezone Areas may appear only at the coarse level actually supported by the current product decision; do not invent precise map-distance/acclimatization UX from unresolved mathematics.

---

# 6. Players UX

Player identity is stable (`player_id`); time-varying state belongs to Run/branch/week history.

Admin player UX ultimately needs to cover:

- prospect/Tour/historical state,
- attributes/OVR/potential,
- physical profile,
- form,
- fatigue/health,
- three physical stamina match dimensions/bars,
- provisional mental match-state dimension(s),
- status/lifecycle,
- style/gameplan,
- individual player-AI decisions,
- manual edits/locks/provenance.

Viewer exposes public/historical layers and must not leak authoritative hidden health/potential/AI knowledge.

## 6.1 Attributes, physical bars and mental state

Current post-v42 V1 direction deliberately keeps the attribute model relatively lightweight and extensible.

The three physical stamina bars/dimensions used during a match should **derive from underlying attributes/state** rather than be represented as three independent standalone trainable attributes. Their exact derivation remains open.

One or more mental match-state bars/dimensions are desired only as a **provisional direction**. Do not freeze their number, names or mechanics without a later explicit decision.

UX should distinguish long-term player attributes from derived/current match-state bars.

## 6.2 Form UX

Form is one current player state, not a collection of disconnected tournament forms.

Admin should distinguish:

- current Form,
- long-term attributes,
- physical stamina capacity/current state,
- mental match-state direction when implemented,
- health/fatigue.

Do not visually imply Form resets between tournaments or weeks.

Exact numeric scales/visualizations remain open unless implementation has an explicit temporary contract.

---

# 7. Tour / Seasons UX

This area should consolidate:

- seasons,
- calendar,
- Tournament Series/Editions,
- categories/policies,
- entries,
- qualification,
- draws,
- matches/results,
- major individual/team competitions.

## 7.1 Tournament Edition lifecycle

Admin may see internal Draft/component/deadline state; Viewer sees only historically public state.

Public stage should be derived from authoritative Edition/event state rather than independently editable display flags.

Incomplete Drafts can be saved. Missing fields should block only dependent operations.

## 7.2 Announcement and public knowledge

Every Edition has historical `announcement_week`.

Before public activation:

- Admin may display/edit the private future Edition,
- Viewer must not display it,
- player-AI-facing surfaces must treat it as unknown.

Once the announcement World Event becomes public, historical Viewer pages may show it from that week onward.

Later public updates should appear as explicit update events; emergency changes require a visibly exceptional path.

## 7.3 Entries

Entry decisions belonging to the same Simulation Slot should be presented as one simultaneous batch/state rather than implying one player's decision causally changed another player's inputs through UI click order.

Retries should preserve unrelated successful results where the underlying command contract allows it.

---

# 8. Simulation UX — chronological model

Simulation is no longer best thought of only as `Next Match / Next Round / Next Week` buttons. The first-version model has explicit chronological boundaries and slots.

## 8.1 Week Transition

Week Transition is a boundary operation, not a normal slot.

UX should make clear that it prepares the next week from information known through the completed week and may include ranking activation, birthdays/prospect intake and weekly player development.

A red blocker prevents only the affected transition/operation and explains cause/fix.

## 8.2 Simulation Slots

A week contains a variable chronological sequence of **Simulation Slots**.

UI must communicate that events within one slot are simultaneous and share one input snapshot.

Primary first-version controls include:

- `Simulate Next Slot`
- split `Simulate Next Match`

When multiple matches exist in the same slot, selecting one manually must not visually imply that the remaining matches now read its result unless the authoritative model explicitly creates that dependency.

## 8.3 Season Transition

Season Transition is the Week 61 → Week 1 special boundary.

UX should separate it from normal slot progression and surface:

- closing-season prerequisites,
- policy changes activating next season,
- scoped resets,
- any blocking problems,
- successful Season Closure Marker/history entry.

## 8.4 Long-running simulation

Long-running operations belong in Task Center with visible progress/state and safe stop/recovery boundaries.

Existing direct simulation buttons may remain temporarily for compatibility, but new UX should converge toward the chronological model rather than proliferating unrelated shortcuts.

---

# 9. Match Engine UX

First-version match simulation is **rally-by-rally**, not shot-by-shot.

Admin match detail should be capable of exposing authoritative rally chronology without requiring the UI to reproduce every hidden internal transition.

Useful authoritative per-rally data includes:

- score context,
- compact sporting cause,
- official decision,
- duration,
- estimated shot count,
- physical stamina state/context where appropriate for Admin,
- future mental-state context only when its provisional mechanics have been explicitly implemented.

Viewer should surface public match progress/statistics without automatically exposing hidden player-AI or internal physical/mental truth.

## 9.1 Interference and timing

V1 uses `No Let / Yes Let / Stroke` for simplified interference.

Match timeline should support authoritative non-rally time events such as:

- game intervals,
- configured health breaks,
- other explicitly supported pauses.

Official Run defaults currently include 2 minutes between games and 3 minutes for the simplified configured health break. UI should read stored configuration rather than hard-code these globally.

Recovery continues through elapsed time; breaks should not be represented as magical resets.

---

# 10. Match Reconstruction UX

**Match Reconstruction** is a distinct Admin workflow for reconstructing a plausible detailed match history from known facts.

Recommended workflow contract:

1. Enter/confirm known facts as constraints.
2. Choose candidate count.
3. Generate candidate histories.
4. Compare compact candidate summaries.
5. Open complete read-only detail for any candidate.
6. Explicitly select one candidate to commit as authoritative history.

Critical UX rules:

- generating candidates must not mutate history,
- candidate detail is read-only,
- selection/commit is a separate explicit mutation,
- commit should show validation/provenance/audit consequence,
- the UI must not suggest that a candidate is “the real match” before explicit selection.

Default candidate count, remembering the previous count, compact-card fields, probability displays and session retention remain provisional/open at their actual status.

---

# 11. Rankings and historical policy UX

Ranking screens must respect historical policy snapshots.

Official Run:

- season `2000/01` begins with Best 15,
- later seasons initially inherit the previous season's effective Best N,
- each season remains independently configurable.

Admin policy editors should distinguish inherited vs explicit override and show the source/effective value.

Historical ranking views must never be recomputed from the latest default merely because configuration changed later.

---

# 12. World Events, Audit, Tasks and Notifications

These four surfaces are intentionally distinct.

## 12.1 World Event Log

Chronological world facts/events for a branch. It supports historical causality/public knowledge and is not merely an Admin notification feed.

## 12.2 Audit Log

Who/what changed authoritative data, when, why and from which provenance.

## 12.3 Task Center

Running/completed operations such as long simulations, imports or other jobs.

## 12.4 Notification Center

Things requiring Admin attention. It may aggregate system notifications and watchlists.

Notification UX uses a consistent severity contract:

- blue information — no block,
- orange warning — no block,
- red critical — block/stop only affected operation or branch.

Every warning/block should explain cause, impact and repair options.

Reading/dismissing a notification never deletes its source event/audit/task/validation.

Viewer shows none of the technical Admin alerts.

---

# 13. Historical MSA homepage/news behavior

Historical MSA homepage includes automatic public messages derived only from structured public World Events valid at the viewed time.

This means:

- no future leak,
- no independent article database inventing facts,
- private Admin events remain private,
- publication starts when the underlying event becomes public.

Standalone News page and News Importance Score remain unresolved/provisional and must not be treated as required first-version navigation.

---

# 14. Forecast and Future Locks UX — provisional

Forecast remains a non-authoritative analysis environment.

Strong working direction includes reproducible Forecast Sessions, scenario comparison, conditional focus, individual sample reconstruction, pins and explicit branch materialization.

Future Locks remain a strong direction for testing/constraining possible futures with feasibility separated from natural probability.

Do not hard-code final layouts, probability controls, retention rules, conflict UX or lifecycle behavior until those provisional areas are explicitly resolved.

Viewer never sees hidden locks or Forecast internal provenance unless a future explicit public feature says otherwise.

---

# 15. History / Branches UX

Target experience connects:

- branch map,
- divergence points,
- Viewer Branch badge,
- selected-branch timeline,
- World Events,
- saved versions/checkpoints,
- simulation/import/manual/reconstruction provenance,
- restore/branch/compare operations.

Viewer Branch must be identifiable without implying that it is the best/official timeline.

---

# 16. Records, rivalries and prestige

Records should appear contextually across Viewer/Admin from authoritative historical data.

Rivalries exist as a product concept, but automatic detection, groups/overlaps, scoring, lifecycle and exact Viewer placement remain only partially decided.

Tournament Prestige is provisional; Tournament Appeal is even weaker. UX must not present either as a finished universal metric until implemented against an approved contract.

---

# 17. Migration principles

1. Reuse real APIs/data where valid.
2. Do not create fake dashboard values to match mockups.
3. Preserve working routes while introducing clearer target navigation when practical.
4. Do not destructively rename persisted backend fields solely for UI terminology; plan migrations.
5. New user-facing labels follow current terminology even if adapters still call old endpoints.
6. Keep Viewer read-only.
7. Keep historical time/public-knowledge semantics explicit.
8. Every mutation needs validation/preview/confirmation appropriate to risk.
9. Tests should verify product behavior, not only component rendering.
10. Planned target features must be distinguished from implemented features.
11. Do not turn provisional/open Master items into permanent UI assumptions.
12. Simultaneous slot events must not become order-dependent because of UI interaction order.
13. Reconstruction candidate generation must remain non-mutating until explicit commit.
14. Historical Viewer/AI surfaces must respect `announcement_week` and public World Events.
15. Do not treat the three physical stamina bars as independent trainable attributes unless a newer product decision explicitly changes the current direction.
16. Do not freeze mental-bar count/names/mechanics from an illustrative screen or placeholder implementation.

---

# 18. Highest-priority migration backlog after v42 sync

### P0 — stop reinforcing obsolete architecture

- Remove new user-facing Master Run/Sandbox Run/Official Branch/privileged Main Branch assumptions.
- Standardize Run, active Admin branch and Viewer Branch terminology.

### P1 — shell and scopes

- Complete Squash Engine Home, Runs and Packages.
- Separate Global Admin and Run Admin navigation.
- Standardize Run/Branch/Time/Mode controls.
- Continue Run Home with the two fixed progress indicators and actionable attention state.

### P1 — chronological simulation foundation

- Implement/align Week Transition.
- Implement Simulation Slots and simultaneity contract.
- Add split Simulate Next Slot / Simulate Next Match UX.
- Implement Season Transition boundary UX.

### P1 — tournament/public-knowledge alignment

- Add derived Edition lifecycle/Public Stage.
- Persist and surface `announcement_week` correctly.
- Gate Viewer/player-AI knowledge behind public World Events.
- Align entry batching/retry UX with shared-slot snapshot semantics.

### P1/P2 — Match Engine v1

- Move toward authoritative rally-by-rally timeline/logging.
- Add the three derived physical stamina bars with appropriate Admin vs Viewer visibility once their attribute mapping is specified.
- Keep mental match-state UI provisional until mechanics are explicitly decided.
- Add Form/timing visibility appropriate to Admin vs Viewer.
- Add simplified interference/timing workflows without advanced referee systems.

### P1/P2 — Match Reconstruction

- Build constraint entry, candidate generation/inspection and explicit commit workflow.
- Ensure generation is non-mutating and commit is auditable.

### P2 — history/attention

- Separate World Event Log, Audit Log, Task Center and Notification Center in UI/data flow.
- Add historical public MSA messages from World Events.
- Build branch map/timeline and contextual records/rivalries when supporting data exists.

---

# 19. Explicitly unresolved UX areas

Do not silently finalize:

- complete final Global/Run Admin sidebar,
- full Viewer public-site navigation,
- exact MSA menu and standalone News page,
- Viewer reveal modes,
- exact Show in Viewer activation timing,
- branch lock/concurrency UX,
- exact Simulation Slot taxonomy/count,
- complete Entry Freeze/cut-off UI,
- final attribute catalogue and physical-stamina derivation,
- number/names/mechanics of mental match-state bars,
- detailed Form/health/stamina numeric visualization,
- advanced referee/review/court-condition UX,
- Forecast/Future Lock final UI and lifecycle,
- Match Reconstruction probability display/session retention/default-card design,
- mobile/responsive design beyond current desktop-first scope.

---

# 20. Historical note

Older proposals in this file — Master Run/Sandbox terminology, global World hub assumptions, fixed navigation trees and illustrative formulas — are not automatically current decisions.

For product decisions, consult `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` first.
