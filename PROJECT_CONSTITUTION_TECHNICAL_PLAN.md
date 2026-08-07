# Squash Engine / FAX Squash / MSA World Tour

## Active Product Constitution — synchronized from Master Vision v31

**Repository status:** canonical product-level specification for current design and implementation decisions.  
**Source version:** Master Vision **31**.  
**Source updated:** **6. 8. 2026**.  
**Imported source file:** `SQUASH_ENGINE_MASTER_VISION_2026-07-21(2)(2).md`.  
**Source SHA-256:** `3cc7c26efc8812c2b47def02f92b742c3df793c49b5add5e8b5155a52056e43c`.

> This file replaces the older `Beta_Engine — Active Product & Technical Blueprint` as the repository's product constitution. It intentionally follows Master Vision v31 rather than preserving obsolete assumptions from the beta UI. The detailed Master remains broader than the currently implemented application: a decision being specified here does **not** mean it is already implemented.

---

## 0. How to read this document

Decision states used by the Master:

- **[DECIDED]** — current rule/design; build against it until explicitly changed.
- **[PROVISIONAL]** — working rule or strong direction, not final canon.
- **[TARGET]** — required long-term capability whose exact details may still be open.
- **[OPEN]** — not decided yet.
- **[DEFERRED]** — intentionally postponed.
- **[LATER]** — future-version idea, not current scope.
- **[OLDER IDEA]** — historical context only unless reconfirmed.

A second independent axis defines scope:

- **ENGINE INVARIANT** — universal technical contract for all Runs in the current engine version.
- **RUN CONFIG** — configurable state of a Run/package/season/category/tournament/etc.
- **OFFICIAL RUN DEFAULT** — default/canon for the Official Run, but not a universal engine restriction.
- **OVERRIDE** — explicit narrower exception.

### Precedence

When sources disagree, use this order:

1. explicit newer user decisions,
2. Master Vision v31 and later synchronized Master revisions,
3. provisional directions,
4. older docs, handoffs and existing code only as implementation/history evidence.

Existing beta behavior must not silently overrule the target product model.

---

# 1. Product identity and current scope

**[TARGET]** Squash Engine is a long-term simulator and manager of the professional men's squash world FAX. It must cover countries and population, player generations and careers, tournaments and qualification, match simulation, rankings/statistics/history, alternative timelines, Admin workflows and a historically faithful read-only Viewer.

It is **not** merely a match generator.

**[DECIDED] Current scope:**

- men's squash only,
- singles matches only,
- one-user local product; no user accounts/roles/login,
- current engine horizon is 50 seasons, `2000/01–2049/50`, exactly 61 Season Weeks per season,
- team competitions are made from individual singles matches,
- no women's tour, doubles, coaches, personal sponsors/contracts, player salaries, detailed travel costs, AI player photos, automatic articles, simulated attendance, standalone junior ranking or mandatory day-by-day world model in the current version.

---

# 2. Viewer and Admin are two different product surfaces

## 2.1 Viewer

**[DECIDED]** Viewer is always read-only. It cannot edit, simulate, import, regenerate or perform Admin mutations.

Viewer is not just one MSA page. It is the read-only environment for multiple fictional public websites above the same Run/time context; the primary current website is official **MSA Squash**.

Viewer must never fabricate unavailable data. Historical views must not leak future results or future-derived information.

## 2.2 Admin

**[TARGET]** Admin is the working environment for creating, editing, validating, simulating and auditing the world. It includes Run/branch/history management, packages, players, seasons/calendar/tournaments, simulation, manual intervention, import/export and diagnostics.

**[DECIDED]** The main page of a Run-scoped Admin is a **working Run Home / dashboard**, not another landing chooser. It is centered on the currently selected Run + active branch and should surface current simulation position/state, meaningful warnings/errors, jobs, unsaved changes and fast continuation of work.

Normal simulation workflows belong to dedicated simulation/workflow surfaces; Home should primarily orient the Admin and surface what needs attention.

## 2.3 Viewer ↔ Admin context mapping

**[DECIDED IN PRINCIPLE]** Switching mode should preserve as much context as possible: Run, season/week, object and matching subpage when a counterpart exists.

Admin → Viewer never silently changes the Run's Viewer Branch. If the same object does not exist/is not public in the Viewer Branch, use the closest meaningful fallback and explain the context change.

---

# 3. Global application shell and scopes

## 3.1 Squash Engine Home

**[DECIDED]** The application root is neutral **`Squash Engine Home`**. It currently provides entry into global areas:

- `Runs`
- `Packages`

It is not a Viewer/Admin landing chooser and does not automatically activate a Run.

## 3.2 Global Admin vs Run Admin

**[DECIDED]** Admin has two distinct scopes:

### Global Admin
- no active Run,
- no active branch,
- no season/week context,
- manages Runs, source Packages and genuinely global data,
- Viewer control remains visible but unavailable with an explanation that a Run must be opened first.

### Run Admin
- one active Run,
- one active Admin branch,
- season/week viewing context,
- Run-specific navigation and working dashboard.

The sidebar is contextual: global and Run-specific sections must not be mixed into one giant menu.

## 3.3 Header hierarchy

**[DECIDED] Admin:**
- `Squash Engine` logo → global `Squash Engine Home`,
- in Run Admin only, a generic Run icon + current Run name → that Run's Home/dashboard.

**[DECIDED] Viewer:**
- Viewer logo → public-web hub for the current Run,
- current website logo → that site's homepage.

## 3.4 Global controls

Run-scoped pages keep controls in the upper-right area:

- Viewer: `Run → Time → Viewer/Admin`
- Admin: `Run → Branch → Time → Viewer/Admin`

Global search and `Ctrl+K` remain part of the application shell; exact placement may be refined.

Global pages without a Run do not show Run/Branch/Time selectors.

---

# 4. Run model

**[DECIDED]** A Run is an independent saved simulation world containing at minimum stable identity/name, optional description, embedded package snapshots + provenance, the 50-season horizon, branches/history, players/tournaments/matches/rankings, checkpoints/metadata and simulation/configuration state.

- number of Runs is not artificially limited,
- displayed Run names are unique across active and archived Runs,
- technical identity is stable `run_id`,
- normal lifecycle is `Working / Completed / Archived`,
- `Built-in / Local`, `Read-only / Editable` and `Valid / Warnings / Errors` are independent axes, not lifecycle states,
- completion at Week 61 of `2049/50` does not auto-archive the Run,
- a completed Run may still branch from earlier history.

**[DECIDED] No blocking setup phase.** A Run can be built incrementally and any currently valid operation can be simulated. Validation is operation-scoped rather than one global “Run ready” gate.

## 4.1 Runs page and switcher

`Runs` opens a neutral `Všechny Runy / All Runs` global page outside Run Admin and Viewer. The full list uses wide rows, not a grid of oversized cards.

A Run exposes distinct actions:

- Open in Admin — opens its normal Run Home using its Viewer Branch as initial branch context,
- Open branches — opens full branch management/history,
- Open in Viewer — opens the Run's Viewer Branch.

The compact Run switcher shows at most a small set (current/favorites/recent) plus entry to All Runs; destructive/complex management does not belong in this quick panel.

---

# 5. Branch, history and Viewer Branch

**[DECIDED]** A branch is an alternative timeline inside a Run. Branches share `run_id` and common pre-divergence history, but each has its own `branch_id` and can diverge in calendar, results, rankings, player state, rules/configuration and other time-valid data.

There is **no privileged `Official Branch` or `Main Branch` concept** in the product model.

**[DECIDED]** Each Run always has exactly one **`Viewer Branch`**:

- it only selects which saved timeline the read-only Viewer displays,
- it is not more important than other branches,
- the technical pointer is `viewer_branch_id`, not `official_branch_id`,
- it cannot be archived until another active branch is chosen for Viewer.

**[OPEN]** Exact save/activation moment of the explicit `Show in Viewer` operation remains to be finalized.

## 5.1 History model

- branch can be created from any saved historical point,
- differing simulated histories never auto-merge,
- shared history should be stored once with branch deltas,
- full Admin history target combines an interactive branch map and selected-branch timeline,
- every successful Save creates a recoverable version,
- checkpoint is a named/technical bookmark, not the only mechanism for recovery,
- Undo/Redo is for the working session; long-term rollback uses versions/history/checkpoints.

---

# 6. Time model

**[ENGINE INVARIANT CURRENT VERSION]**

- every Run: exactly 50 seasons `2000/01–2049/50`,
- each season: exactly 61 Season Weeks,
- FAX calendar year: exactly 61 Year Weeks,
- Season Week 1 maps to Year Week 37,
- Year Week 1 maps to Season Week 26,
- no exact calendar dates/days are required in the core time model,
- player birth is `birth_year + birth_year_week`.

Viewer can inspect completed historical weeks and the currently progressing week using only then-known saved data. Future not-yet-started weeks are not Viewer states.

The global time control changes **viewing context only** and never advances/rewinds simulation.

Visible relation to current state:

- Viewer: `PRESENT / PAST`
- Admin: `PRESENT / PAST / FUTURE`

Clicking a non-present state returns viewing context to Present; it does not mutate simulation.

---

# 7. Packages

## 7.1 World + Category Packages

**[DECIDED]** Every Run has exactly one World Package and one Category Package selected during Run creation.

At creation, the selected versions are copied into the Run as independent, versioned snapshots. Source identity/version is stored as provenance only; there is no live link afterwards.

Consequences:

- editing a global source Package changes future Runs only,
- editing an embedded snapshot in an editable Run changes that Run only,
- an existing Run never silently absorbs later source updates,
- built-in GitHub source Packages are read-only,
- local/custom source Packages are editable,
- embedded snapshots may be editable inside an editable local Run even if the source was built-in,
- World and Category Packages are content-independent and are validated independently.

Defaults:

- `Official FAX World`
- `Official FAX Category Package`

## 7.2 Global Packages area

**[DECIDED]** Source World and Category Packages have global Admin pages outside all Runs. UI must clearly distinguish editing a global source from editing an embedded Run snapshot.

**[PROVISIONAL STRONG DIRECTION]** Package architecture should be extensible to future types such as Player Packages and perhaps distinguish base Packages from one-time import Packages. Do not treat those future types as decided yet.

---

# 8. Countries, population and talent generation

- population history currently covers 1955–2050,
- player generation uses the country's population in the player's birth year,
- changing population/generation parameters does not retroactively rewrite already generated players,
- quantity and quality of talent are separate concepts,
- population alone must not determine squash strength,
- exact formulas/weights/global pools remain open.

CSV/XLSX imports into editable local data use staging + preview + validation. Errors identify exact row/column/value/reason/expected format/example/fix. Meaning-changing corrections require explicit approval. Valid independent rows may be imported selectively only when referential consistency remains valid. Confirmed writes are atomic and auditable.

---

# 9. Players and lifecycle

Current product direction includes:

- stable `player_id`; display names do not need to be globally unique,
- player profile exists from prospect/junior visibility onward and continues into Tour career,
- time-varying profile/state is historical,
- height/weight can change over time,
- Admin owns authoritative internal state; Viewer exposes only public/estimated layers where applicable,
- generation includes an initial mixed-age pool and continuing intake,
- generated prospects are intended to eventually enter Tour according to lifecycle rules,
- manual creation, lock/unlock and safe regeneration are supported concepts,
- no separate “player licence” requirement in the current target model.

Potential, OVR, attributes, development, form, fatigue, health, style/gameplan and player decision AI are part of the target engine, but much of the exact mathematics/calibration is intentionally still open.

---

# 10. Tournaments, calendar, entries, qualification and draws

The engine distinguishes persistent tournament identity (`Tournament Series`) from season-specific editions/configuration.

Calendar and category systems are time-aware/configurable rather than hard-coded global constants.

Core draw direction already includes:

- seeded tiers and controlled seed placement,
- BYEs,
- qualifier (`Q`) slots,
- bracket or group qualification,
- Lucky Losers,
- withdrawal/replacement logic,
- qualification/main-draw freeze concepts,
- manual Admin editing/regeneration with strong warnings once play has begun.

`Simulate` and `Manual / Step-by-step` are complementary workflows, not mutually exclusive global modes.

---

# 11. Match and simulation engine

Default individual match format for Official Run is BO5 to 11, win by 2 unless a narrower competition configuration overrides it. Individual matches never end in a draw; abnormal statuses such as walkover/retirement/etc. need explicit stored semantics.

Simulation target supports ranges such as:

- Next Match,
- Next Round,
- Next Tournament,
- Next Week,
- Next Season,
- Full Simulation,
- custom supported ranges.

Long jobs belong in Task Center and should support visible progress/state. Direction includes pausing, safe stopping after a consistent unit, planned stop points, recovery and eventual Windows tray/background continuation.

**[OPEN]** Complete deterministic seed contract for the entire engine remains unresolved even though some local algorithms, especially draw behavior, can already be deterministic.

---

# 12. Rankings, statistics, history and predictions

The engine needs historically versioned ranking snapshots and read-only historical browsing. Official/Live ranking concepts and multiple analysis rankings can coexist, with sport-specific policies stored in configuration/history rather than globally hard-coded.

H2H, statistics, records, awards and historical timelines are first-class generated data products.

Predictions/odds must be derived from available model state and must not reveal future truth in historical Viewer contexts.

Country Ranking's exact meaning/formula is intentionally deferred until the base simulation is mature enough to calibrate it.

---

# 13. Configuration inheritance and overrides

**[DECIDED]** Stored Runs must preserve the actual values/rules that applied historically; loading old history must not recompute it from today's Official defaults.

Each supported configurable value has:

- `Inherited`
- `Override`

Admin shows effective value + inheritance/override source. Changing a parent updates dependent inherited values only; explicit overrides remain overrides until `Restore inheritance`.

**[PROVISIONAL STRONG DIRECTION]** Working hierarchy:

`engine default → Run package → Run → season → category → Tournament Series → Tournament Edition → phase/round → match`

Exact placement/availability per setting is still to be finalized.

---

# 14. Save, audit, import/export, storage and safety

- normal Save stores the current coherent working changes,
- advanced Save may select safe logical bundles,
- every successful Save creates a recoverable version,
- important mutations are auditable,
- data/provenance can identify sources such as Built-in, Generated/Simulated, Imported, Manual, Regenerated,
- imports use preview and atomic commit,
- Run export/import supports complete archives and narrower safe forms,
- version migration must not silently lose data,
- no artificial storage quota or silent automatic deletion,
- Admin should expose physical storage use and block only operations that actually lack required space,
- crash recovery must distinguish saved state from Recovery Draft rather than pretending unsaved history was committed.

---

# 15. Major competition areas

The product specification has dedicated systems for:

- World Tour Finals,
- Individual World Championship,
- Team World Championship,
- continental championships,
- national championships,
- possible later IFSL/league squash.

Many exact competition formats remain Run/Official defaults or open items rather than engine invariants.

For Team World Championship, the currently specified Official format uses six singles matches; at 3–3, tie-break proceeds by aggregate set difference, then point difference, then the position-1 singles result. Overall field/qualification/calendar/order details remain open.

---

# 16. UX and design contract

**[PROVISIONAL STRONG PREFERENCE]** Premium but practical sports-manager / sports-data product:

- high readability,
- clear hierarchy,
- desktop-first,
- no overlapping panels,
- tables optimized for desktop,
- concise summary first, technical detail lower,
- strong distinction between Viewer and Admin,
- explicit preview vs mutation,
- no unnecessary neon/sci-fi styling.

**[DECIDED]**

- UI languages: Czech + English,
- global appearance: `Light / Dark / System`,
- important states are never conveyed by color alone,
- Viewer and Admin have distinct accent + textual mode indication,
- suitable Admin tables support multi-select and only valid bulk actions,
- global search exists with keyboard shortcut,
- current version is designed for desktop rather than full mobile responsiveness.

---

# 17. Run Admin information architecture — current direction

The exact final Run sidebar is **not yet canonized**. Do not treat today's beta navigation as the target structure.

Strong current working direction is to organize Run Admin around a small number of understandable product areas such as:

- **Home** — Run command center/dashboard,
- **World** — Run-embedded world/package snapshot and countries,
- **Players** — player/prospect database and player-state workflows,
- **Tour / Seasons** — calendar, tournaments, categories, competitions and season structure,
- **Simulate** — actual simulation launcher/control workflows,
- **Analysis** — rankings, metrics, diagnostics/analytical inspection where appropriate,
- **History / Branches** — timelines, branch map, versions/checkpoints,
- secondary settings/diagnostics/operator tools where they logically belong.

This is a **direction**, not permission to invent a final tree without review. The Master v31 explicitly leaves the exact full Admin/Viewer route counterpart table, detailed Run sidebar and several page layouts open.

---

# 18. Immediate implementation implications after v31 sync

The current beta predates many product decisions above. Therefore the migration should prefer **incremental compatibility** over destructive rewrites, but new code must stop reinforcing obsolete concepts.

Highest-impact cleanup areas:

1. Replace `Master Run` / privileged `Official/Main Branch` UX assumptions with neutral Runs + `Viewer Branch` semantics.
2. Build `Squash Engine Home` as true global root with global `Runs` and `Packages` scopes.
3. Split global Admin navigation from Run-scoped Admin navigation.
4. Standardize Run-scoped header controls: Run, Branch, Time, Viewer/Admin.
5. Evolve `/admin/runs/:runId` into the real Run Home/dashboard while moving execution-heavy simulation actions to Simulate workflows.
6. Introduce global source Package management distinct from Run-embedded snapshots.
7. Audit code/schema fields named `official_branch`, `main_branch`, `master_run` or equivalent and migrate semantics carefully; do not blindly rename persisted fields without a migration plan.
8. Audit route/navigation fallbacks for context-preserving Viewer↔Admin switching.
9. Keep historical state/configuration immutable by later default changes.
10. Use the Master decision status explicitly: do not implement `[OPEN]`, `[DEFERRED]` or `[PROVISIONAL]` details as if finalized unless required for a reversible working slice.

---

# 19. Explicitly open/deferred areas that should not be invented silently

Examples from Master v31 include:

- exact complete Run Admin sidebar/page tree,
- exact Viewer public-site navigation and full MSA homepage layout,
- exact Viewer reveal modes,
- exact activation timing of `Show in Viewer`,
- final branch concurrency/lock matrix,
- full deterministic seed contract,
- exact country talent-generation mathematics,
- detailed attribute/development/form/fatigue/health/AI mathematics,
- complete Entry Freeze/cut-off rules,
- several competition formats and qualification rules,
- final Category Package seasonal data format,
- future Package types beyond World + Category,
- exact Country Ranking formula,
- detailed long-job performance/recovery behavior,
- final import/export formats and migration UX,
- detailed storage thresholds,
- complete page-by-page Admin↔Viewer counterpart map.

---

# 20. Current implementation vs target

This constitution describes **what Squash Engine should be**. The repository currently contains a beta with mixed implementation maturity and several older naming/navigation assumptions.

For implementation work:

- inspect current code/API/schema before editing,
- preserve working data contracts unless intentionally migrating them,
- distinguish `implemented now` from `specified target`,
- add tests for changed behavior,
- keep migrations backward-safe where saved Runs/data can exist,
- prefer real existing data over fake dashboard placeholders.

---

# 21. Product definition in one sentence

**Squash Engine is a long-term manager and simulator of the men's professional FAX squash world, capable of generating and evolving countries, players, tournaments, rankings and decades of history, safely branching alternative timelines, and presenting the result through both a powerful Admin workspace and historically faithful read-only public Viewer websites led by MSA.**

---

## Repository documentation rule

- This file is the active repository-level product constitution synchronized from Master Vision v31.
- `docs/ENGINE_UX_SPEC.md` is subordinate implementation/migration guidance and must not contradict this file.
- Older commits/documents are historical context, not current canon.
- Future Master revisions should update this file (or replace it with a complete canonical Master mirror) before major product architecture work is treated as finalized.