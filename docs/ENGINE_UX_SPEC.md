# Engine UX & Architecture Direction (FAX / MSA)

## Status and scope
This document is the detailed **planning/specification source** for the long-term Admin UX and product architecture direction.

- **Current implementation:** mixed maturity across World, Players, Seasons, and run simulation tooling.
- **Planned target:** workflow-oriented Admin experience centered on World, Players, Tour & Seasons, Runs, Simulate, and Diagnostics.
- **Implementation status rule:** this file must never imply that planned features are already implemented.

Assumptions for this planning slice:
- `PROJECT_CONSTITUTION_TECHNICAL_PLAN.md` remains the active blueprint for implementation constraints and non-negotiables.
- `Beta_Engine.docx` remains background/historical context only.
- No backend/API/database/frontend behavior is changed by this documentation update.
- Existing routes/pages can remain during transition while navigation and workflows are consolidated.

---

## Key Product Decisions (authoritative UX decisions)

### 1) Top-level Admin information architecture (IA)
Long-term top-level Admin navigation target:
1. **World**
2. **Players**
3. **Tour & Seasons**
4. **Runs**
5. **Simulate**
6. **Diagnostics**

Notes:
- A future Settings page is allowed, but is not a central workflow pillar.
- Existing top-level pages can remain operational during transition.

### 2) World hub simplification
World should eventually expose only:
- **Countries**
- **Talent Preview**

Country Momentum should not remain a separate top-level world destination in the long run; it is folded into country detail as authored **Development Curves** plus run-derived output.

### 3) Run model and defaulting
- The engine supports multiple runs technically.
- The normal UI should prioritize one active **Master Run**.
- **Sandbox Runs** are for experiments and may be archived/deleted/compared/promoted.
- Default generated output views (country/player/viewer) should use Master Run unless explicitly changed.

### 4) Season model hard rules
- Fixed season range: **2000/01 through 2049/50**.
- Every season has exactly **61 season weeks**.
- **Season Week 1 maps to Year Week 37**.
- This is an intentional engine simplification even if deeper FAX lore may be more complex.

### 5) Talent Intake operating model
- Intake is **season-based**, not independent random weekly generation.
- Intake cohort includes players who turn 15 during the selected season.
- Each generated player can have `eligible_week`.
- Admin can review the full cohort before all players are currently eligible.

### 6) Simulation granularity decisions
- No global day-by-day simulation model for now.
- Main simulation levels are:
  - Match
  - Round
  - Tournament
  - Week
  - Season
  - Full Timeline
- Tournament internal schedules may map rounds to week segments.

---

## A) Current implemented state (high-level)

### World
- Countries editor exists and is operational for CRUD/import/export-style authoring.
- Country Momentum exists as a separate world surface today.
- Talent tooling exists in a technical/diagnostic orientation.

### Players
- Admin Players page is functional but dense; multiple workflows are grouped together.
- Initial/seeded generation and lock/regenerate foundations exist.

### Tour/Seasons
- Admin Seasons command-center workflows exist with substantial orchestration foundations (entries, draws, matches, progression, points/snapshots, week/range preflight/run).
- Tournament template/category concepts exist but naming and UX are still technical for end users.

### Runs/Simulate/Diagnostics
- Run-scoped simulation actions and lifecycle diagnostics exist in operational form.
- Top-level Simulate and Diagnostics are not yet the final workflow-first launcher/control-center experience.

---

## B) Planned target architecture (detailed)

## 1) World module target
World should focus on:
- **Countries**
- **Talent Preview**

Country Momentum should be folded into country-level development curves and generated history displays.

### 1.1 Countries list target (`/admin/world/countries`)
The countries list is a database-style management table:
- search
- filters
- sortable columns
- quick status summaries where helpful
- one primary row action: **Open**

Action simplification:
- Copy/Duplicate should move from noisy list-row actions to secondary actions inside country detail.
- Existing drawer-centric editing is transitional, not final target UX.

### 1.2 Country detail target (`/admin/world/countries/:countryCode`)
Country detail should be a sports-profile style country page (not only a form). Target sections:
1. Overview
2. Inputs
3. Development Curves
4. Talent Preview
5. Generated Output from Master Run
6. Top Players
7. History
8. Titles / Results

### 1.3 Authored vs Generated separation (required)
- **Authored Country Model** = manually edited pre-generation country inputs.
- **Generated Output** = run-derived outcomes for selected run (default Master Run).

This separation should be visible in naming, grouping, and UI text to avoid conceptual mixing.

### 1.4 Development Curves
Planned first implementation:
- no drag graph editor initially
- use editable season-value tables
- add automatic chart rendering later

Example table concept:
- `Season | Value`
- `2000/01 | 4.40`
- `2001/02 | 4.42`
- `...`

Curves may include:
- squash popularity
- squash tradition
- system quality
- competition density
- federation quality
- court count
- talent multiplier/momentum

Important distinction:
- authored curves are inputs
- generated/real momentum is derived from run outcomes and displayed separately

### 1.5 Talent Preview in World
Talent Preview in World is:
- **Expected Mode only**
- no seeded concrete player samples
- no concrete player objects
- used for balancing and forecasting, not player creation

Main aggregate outputs:
- Elite Talents
- Tour Talents
- Pro Depth

Detailed letter-tier breakdown is available only in advanced/detail views.

---

## 2) Talent Preview and talent generation logic

### 2.1 Aggregate definitions
- **Elite Talents:** expected elite/world-class output (roughly L through S- tiers)
- **Tour Talents:** expected stable top-tour professional potential (roughly A+ through B+, exact mapping may be finalized later)
- **Pro Depth:** broader professional/development/national depth (roughly B through C-ish, exact mapping may be finalized later)

### 2.2 Presentation rule
Main UI should not expose every letter tier as a column in the default table.

Default UX:
- aggregate categories (Elite / Tour / Pro Depth)

Advanced UX:
- exact tier distributions (`L, S+, S, S-, A+, ... F-`)

### 2.3 Generation chain (target concept)
`Total population`
→ `male 15-year-old cohort`
→ `squash participants`
→ `competitive juniors`
→ `elite development pool`
→ `expected talent output`

### 2.4 Seasonal normalization model
For each season:
- all countries are summed into global seasonal talent pools
- each country receives a relative share of Elite/Tour/Depth pools

Intended behavior:
- if all countries improve together, world output should not explode uncontrollably
- global depth growth should be controlled by explicit global era multipliers or pool settings

Conceptual share formula:
- `country_weight = eligible_cohort × participation × quality factors`
- `world_weight = Σ country_weight`
- `country_share = country_weight / world_weight`
- `expected_output = global_pool × country_share`

Separate weighting models are expected for Elite vs Tour vs Pro Depth.

---

## 3) Potential Tier System

### 3.1 Target scale (authoritative)

`L`

`S+`
`S`
`S-`

`A+`
`A`
`A-`

`B+`
`B`
`B-`

`C+`
`C`
`C-`

`D+`
`D`
`D-`

`E+`
`E`
`E-`

`F+`
`F`
`F-`

### 3.2 Rules
- `L` is standalone only (no `L+` or `L-`).
- Potential Tier maps internally to expected potential OVR anchors.

Example anchor concept (illustrative, not finalized):
- `L ≈ 192`
- `S+ = 191`
- `S = 190`
- `S- = 189`
- `A+ = 188`
- (continues downward)

### 3.3 Performance interpretation
- Potential is not a hard cap.
- Most players peak below potential.
- Some players can briefly exceed potential.
- Very rare players can sustain above expected ceiling.

Later systems that affect realization (future phases):
- progression model
- work ethic/training environment
- injuries/recovery
- mentality/consistency
- style fit and coaching/system quality

---

## 4) Players module target
Long-term Players navigation:
- Player Database
- Talent Intake
- Custom Players
- Locks & Overrides
- Player Audit
- Player Detail

### 4.1 Player Database
Target behavior:
- search
- country/age/potential/status filters
- sort by name, age, country, potential, OVR, cohort, status

Target table shape:
`Name | Country | Age | Potential | OVR | Status | Cohort | Action`

Primary row action should be **Open**.

### 4.2 Talent Intake (`/admin/players/intake`)
Talent Intake should be a standalone page, not a minor subsection.

Workflow:
1. Select Season
2. View Expected Intake
3. Generate Preview
4. Review Preview
5. Lock/edit/customize
6. Persist Intake
7. Regenerate Unlocked

Statuses:
- Not generated
- Preview generated
- Persisted
- Locked/finalized

Generated Preview table target:
`Name | Country | Eligible Week | Potential | Category | Status | Action`

Actions:
- Generate Preview
- Regenerate Preview
- Regenerate Unlocked Only
- Persist Intake

Rules:
- Preview does not write final records.
- Persist writes players into Player Database/run data.
- Intake is seasonal; players become eligible in-world based on `eligible_week`.

### 4.3 Custom players, locks, and budget interaction
- Custom players default to locked.
- Locked players are not overwritten unless explicitly unlocked.
- Custom/locked players count against country-season talent budget.
- They should strongly reduce probability of additional same-cohort top-tier output, not force absolute zero.

### 4.4 Player Detail split
Admin and Viewer detail pages serve different goals.

Admin Player Detail:
- editing/overrides
- lock management
- audit/development management

Viewer Player Detail:
- public sports profile
- rankings/results/titles/stats/rivalries
- no technical lock/regeneration internals

### 4.5 Future identity roadmap (explicitly future phase)
- country-specific name pools
- flag assets
- weighted name-origin distributions
- nationality vs name-origin distinction
- height/weight/handedness/body-type profile depth

---

## 5) Tour & Seasons module target
Top-level consolidation target:
- Categories
- Tournaments
- Season Templates
- Seasons
- Calendar Compare / Apply
- Validation

### 5.1 Season Registry
Hard model decisions:
- Season range: 2000/01 to 2049/50
- 61 season weeks per season
- Season Week 1 = Year Week 37 mapping

Target season statuses:
- Draft
- Validated
- Locked
- Running
- Completed

Status intent:
- Draft: editable
- Validated: passed checks but editable (edits invalidate validation)
- Locked: prepared for simulation; calendar edits require reopen
- Running: simulation artifacts exist; edits require invalidation handling
- Completed: historical state; changes via explicit reopen/override only

### 5.2 Category model
Use user-facing term **Category**.
Do not expose Category Definition vs Category Version complexity in everyday UI.

Category meaning:
- a rules package valid for a season range

Examples:
- Diamond 2000/01–2015/16
- Diamond 2016/17–2049/50

Category fields:
- category name
- valid season range
- tour level
- prestige rank
- mandatory flag
- main draw size
- qualification draw size
- direct entries
- qualifiers
- wildcards
- lucky losers
- seeds count
- points by round
- prize money + distribution
- match format
- entry rules
- qualification rules
- schedule footprint

### 5.3 Schedule footprint semantics
Footprint includes:
- qualifying weeks count
- main draw weeks count
- required consecutive block flag
- optional round-to-week assignment

Example default (Diamond):
- 1 qualifying week
- 2 main draw weeks
- total 3 consecutive weeks

### 5.4 Tournaments model
Use **Tournaments** in UI (not Tournament Templates).

Tournament = reusable master tournament brand.
Examples:
- Némarque Open
- Ameriga Open
- Bogemia Gold
- World Championship

Tournament stores reusable defaults/identity, not concrete entries/draw/results.

### 5.5 Tournament Edition / Event Instance model
A concrete tournament in a concrete season (e.g., Némarque Open 2030/31).

When placed into a season:
- keep tournament reference
- keep category reference
- copy category snapshot
- allow edition-level overrides

Edition owns:
- actual entries
- draw and match schedule
- results/champion
- points awarded
- prize awarded

### 5.6 Season Templates and creation paths
Season Template = reusable calendar plan.

Season creation starts from:
- blank calendar
- season template
- another season
- copied tournament from anywhere
- blank custom tournament

### 5.7 Compare / Apply
Compare current season with:
- template
- another season

Statuses:
- Same
- Modified
- Missing from current
- Only in current
- Conflict

Actions:
- Apply to this season
- Replace current
- Keep current
- Ignore
- Open editor

### 5.8 Season Calendar Editor
Both views should exist:
- Week View
- Tournament Table View

Week View:
- W01..W61
- Edit Week panel supports add/remove/move/open and conflict view
- multi-week tournaments are block objects

Tournament Table View:
- sort by week, name, category, host, status, duration, qualification
- filters: category, week range, host, status, mandatory, has qualification

### 5.9 Event block rules
- Multi-week events move as one block.
- Diamond-style 3-week footprint is a canonical example.
- Validation must catch broken/non-consecutive footprints.

---

## 6) Simulation, lifecycle, reopen/invalidation, and narrative locks

### 6.1 Tournament lifecycle states
Target lifecycle:
1. Planned
2. Entries Generated
3. Draw Generated
4. In Progress
5. Completed
6. Points Applied
7. Archived

State behavior intent:
- Planned: calendar/details editable
- Entries Generated: entry review/regeneration possible; structural edits may invalidate downstream artifacts
- Draw Generated: bracket exists; entry changes invalidate draw
- In Progress: match-level simulation/manual actions available; result changes invalidate downstream path
- Completed: outcomes exist; points can be reviewed/applied/recalculated
- Points Applied: ranking effects posted; score/result changes invalidate later snapshots
- Archived: historical locked state; reopen required for mutation

### 6.2 Reopen/invalidation principles
Any post-downstream edit must expose invalidation scope and mark dependent artifacts.

Examples:
- Calendar changed → invalidates entries/draws/results/rankings from affected week onward
- Entries changed → invalidates draw/results/rankings for tournament onward
- Draw changed → invalidates results/rankings for tournament onward
- Match result changed → invalidates later bracket/points/ranking snapshots
- Points/ranking changed → invalidates later ranking/race snapshots

Required UX pattern:
- show impact preview before apply
- allow cancel or apply+mark-invalidated
- persist audit trail of intervention scope

### 6.3 Simulation levels and shortcuts
Simulation levels:
- Match
- Round
- Tournament
- Week
- Season
- Full Timeline

Shortcuts:
- Next Match
- Next Round
- Next Tournament
- Next Week
- Rest of Season
- Full Timeline

Need both Next Tournament and Next Week because tournaments can span multiple weeks.

### 6.4 Manual controls (where applicable)
At match/round/tournament level support:
- simulate
- resimulate
- resimulate unlocked
- enter manual result
- lock result
- unlock
- downstream invalidation handling

### 6.5 Narrative / outcome locks (future feature)
Lock types:
- Soft Lock
- Hard Lock
- Winner Lock
- Round Lock
- Exact Match Lock
- Path Lock

Rules:
- visible in UI
- audited
- conflict-checked
- respected by generation/simulation flows

Optional diagnostic:
- estimated natural probability

Example:
- Constraint: Arebady must win Némarque Open 2030/31
- Estimated natural probability: 42%
- Status: Plausible

---

## 7) Runs model target
- Keep multi-run engine capability.
- UI defaults to Master Run for normal use.
- Sandbox Runs support experiments and can be archived/deleted/compared/promoted.
- Country/player generated output panels default to Master Run unless user explicitly switches.
- Calendar structure editing remains a Tour & Seasons responsibility; run simulation should not silently mutate authored calendar models.

---

## 8) Diagnostics control center target
Target sections:
1. Overview
2. World Balance
3. Calendar Validation
4. Run Health
5. Invalidated Data
6. Narrative Locks
7. Audit / Warnings

Diagnostics output expectations:
- what happened
- why it matters
- what is affected
- what to do next
- where to click

Example categories:
- World Balance: dominance risk, zero-chance risk, preview distribution issues
- Calendar Validation: footprint errors, missing mandatory events, out-of-range weeks
- Run Health: unfinished events, missing results, stale snapshot chains
- Invalidated Data: source changes and impacted downstream artifacts
- Narrative Locks: conflicts and plausibility indicators

---

## 9) Transition from current implementation
Migration principles:
- Keep existing routes operational during transition.
- Do not break current Countries Editor, Admin Players, Admin Seasons, Runs, or run diagnostics during IA migration.
- Introduce new IA progressively with compatibility links.
- If legacy pages remain temporarily, label them clearly (Advanced / Legacy / Placeholder).
- Route consolidation should be phased and regression-tested.

Operational approach:
- prefer additive wrappers and redirects later rather than abrupt route removals
- preserve existing orchestration capabilities while improving discoverability
- gate risky structural changes behind clear phase boundaries

---

## C) Phased implementation plan for future tasks

- **Phase 0 — Documentation alignment** (this task)
- **Phase 1 — Navigation/UX shell cleanup**
- **Phase 2 — World cleanup**
- **Phase 3 — Talent Preview redesign**
- **Phase 4 — Player module restructure**
- **Phase 5 — Tour & Seasons architecture**
- **Phase 6 — Tournament lifecycle + simulation controls**
- **Phase 7 — Narrative locks**
- **Phase 8 — Diagnostics**
- **Phase 9 — Future realism updates**

---

## D) Expanded gap analysis (current vs target)

| Area | Current implementation | Planned target | Difference/gap | Suggested phase |
|---|---|---|---|---|
| Countries list action cleanup | Countries management exists with operational row actions and drawer workflows. | Database-style list with primary **Open** action and reduced row noise. | Copy/Duplicate action placement and list ergonomics need cleanup. | Phase 2 |
| Country detail route | Country editing exists, mostly list/drawer-driven. | Dedicated `/admin/world/countries/:countryCode` profile/editor. | Route-level country profile page not yet established as primary workflow. | Phase 2 |
| Development curves | Momentum concepts exist but not integrated as detailed per-country season tables. | Editable seasonal development curves with later charting. | Need authored curve model/UX and generated momentum separation. | Phase 2 |
| Talent Preview aggregates | Technical/diagnostic flavor with dense detail. | Aggregate Elite/Tour/Depth first, advanced tier detail optional. | Needs UX reframing and aggregate-first data presentation. | Phase 3 |
| Talent Intake page | Player generation foundations exist. | Standalone `/admin/players/intake` seasonal intake workflow. | Needs dedicated page, statuses, and preview→persist lifecycle semantics. | Phase 4 |
| Custom/locked budget behavior | Lock/regeneration support exists in part. | Budget-aware custom/locked behavior with strong-but-not-zero elite suppression. | Requires explicit model + UX messaging + diagnostics. | Phase 4 |
| Player detail split | Admin-centric player management is present. | Separate Admin and Viewer detail experiences. | Viewer-friendly profile depth and admin-only internals separation needed. | Phase 4/9 |
| Categories model clarity | Technical category/template concepts exist. | User-facing “Category” rules packages by season range. | Terminology and object semantics need simplification in UI workflows. | Phase 5 |
| Tournaments as reusable master records | Tournament template-like entities exist. | Reusable Tournaments as tournament brands. | Need clearer identity vs season-edition separation. | Phase 5 |
| Tournament editions + category snapshots | Event workflows exist with artifacts. | Edition retains references + copied category snapshot + overrides. | Snapshot/override UX and historical-stability semantics need formalization. | Phase 5/6 |
| Season compare/apply | Some season orchestration tooling exists. | Explicit compare/apply with statuses/actions. | Compare UX/status taxonomy and action flows are incomplete. | Phase 5 |
| Week view + Edit Week panel | Season command workflows exist. | Rich Week View with Edit Week controls and conflict context. | Purpose-built calendar editing UX needs expansion. | Phase 5 |
| Tournament table view | Event-centric data exists but not fully consolidated into planner table UX. | Sort/filter-heavy tournament edition table view. | Needs robust list ergonomics and bulk operations. | Phase 5 |
| Event block validation | Validation foundations exist. | Strict multi-week block and footprint validation with actionable guidance. | Block semantics and human-friendly fix guidance need tightening. | Phase 5 |
| Tournament lifecycle gating | Lifecycle diagnostics exist in foundation form. | Full lifecycle state machine with action gating per state. | State/action contracts need unified UX and policy. | Phase 6 |
| Reopen/invalidation UX | Partial diagnostics/preflight exist. | Explicit intervention-impact scope and downstream invalidation controls. | Need consistent model and user-facing impact confirmations. | Phase 6 |
| Narrative locks | Not first-class yet. | Soft/Hard and path/outcome lock system with conflict checks and audit. | New constraints domain and UI integration required. | Phase 7 |
| Master vs Sandbox defaulting | Multi-run capability exists. | Master-first UX default with optional sandbox workflows. | Run selection friction and default behavior need standardization. | Phase 6/8 |
| Simulate launcher | Top-level simulate is not fully launcher-centric. | Central launcher with levels + shortcuts. | Action discovery and control consistency require redesign. | Phase 6 |
| Diagnostics control center | Run-scoped diagnostics exist. | Cross-module diagnostics control center with guided remediation. | Aggregation, triage UX, and action linking need expansion. | Phase 8 |

---

## Appendix: non-negotiable guardrail reminders for future implementation prompts
- Do not weaken determinism/replayability.
- Keep world/tour content data-driven.
- Keep Admin and Viewer responsibilities conceptually separate.
- Preserve historical traceability and auditability after manual interventions.
- Do not represent planned features as implemented before delivery.


## Season Label Transition Note
- Canonical season label for the season registry is compact `YYYY/YY`.
- Legacy flows may still display or use long labels `YYYY/YYYY`.
- API boundaries should accept both compact and long formats during migration.
