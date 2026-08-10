# Squash Engine / FAX Squash / MSA World Tour

## Active Product Constitution — synchronized through Master Vision v42

**Repository status:** canonical repository-level product constitution for current design and implementation decisions.  
**Master baseline:** Squash Engine Master Vision **v42**, updated **10. 8. 2026**.  
**Synchronization rule:** this file preserves still-valid canon from earlier Master revisions and adds later decisions; later synchronization must be additive unless the Master explicitly supersedes an older rule.

> This constitution is a repository-facing distillation, not a lossless copy of the full Master Vision. A specified target does **not** imply that the repository already implements it. When a task depends on detail not stated here, use the latest audited Master or an explicit newer user decision rather than inventing the missing rule.

---

# 0. How to read this document

Decision states:

- **[DECIDED]** — current rule/design; build against it until explicitly changed.
- **[PROVISIONAL]** — working rule or direction, not final canon.
- **[TARGET]** — required capability whose exact details may still be open.
- **[OPEN]** — not decided yet.
- **[DEFERRED]** — intentionally postponed.
- **[LATER]** — future-version idea, not current scope.
- **[OLDER IDEA]** — historical context only unless reconfirmed.

Independent scope axis:

- **ENGINE INVARIANT** — universal technical contract for all Runs in the current engine version.
- **RUN CONFIG** — configurable state of a Run/package/season/category/tournament/etc.
- **OFFICIAL RUN DEFAULT** — default/canon for Official FAX/MSA content, not a universal engine restriction.
- **OVERRIDE** — explicit narrower exception.

## 0.1 Precedence

When sources disagree, use this order:

1. explicit newer user/product decisions,
2. latest audited Master Vision — currently v42,
3. this constitution,
4. subordinate migration guidance such as `docs/ENGINE_UX_SPEC.md`,
5. `README.md`, `ROADMAP.md`, and `AGENTS.md` as summaries/operating guidance,
6. older documents, handoffs, and current beta behavior only as implementation/history evidence.

Never silently promote `[PROVISIONAL]`, `[OPEN]`, `[DEFERRED]` or `[LATER]` material into a hard rule. Likewise, never silently delete an older `[DECIDED]` rule merely because a later repository summary does not repeat it.

## 0.2 Newer 10 Aug 2026 first-version direction after Master v42

The following current design discussion is newer than the v42 Master and therefore must be preserved with its actual uncertainty:

- **[PROVISIONAL STRONG DIRECTION FOR V1]** The first-version attribute model should intentionally stay relatively lightweight and expand in later versions rather than trying to freeze the final attribute/game-style model immediately.
- **[PROVISIONAL STRONG DIRECTION FOR V1]** The three physical stamina dimensions/bars used during a match should derive from the player's underlying attributes/state rather than be presented as three independent standalone trainable attributes. Their exact derivation remains open.
- **[PROVISIONAL]** Match state should additionally expose one or more mental-state bars/dimensions; exact number, names and mechanics remain open.

This newer direction changes how the v42 phrase “three separately trainable stamina systems” should be interpreted in implementation planning: the three physical stamina dimensions remain part of the match model, but do not hard-code them as three independent trainable attributes unless a later decision confirms that representation.

---

# 1. Product identity and current scope

**[TARGET]** Squash Engine is a long-term deterministic manager and simulator of the fictional men's professional FAX squash world. It covers countries and population, player generations and careers, tournaments and qualification, match simulation, rankings/statistics/history, alternative timelines, Admin workflows and historically faithful read-only public Viewer websites led by MSA.

It is not merely a match generator.

**[DECIDED] Current scope:**

- men's squash only,
- individual matches are singles only,
- one-user local product; no user accounts, roles or login,
- exactly 50 seasons, `2000/01–2049/50`,
- exactly 61 Season Weeks per season,
- team competitions are composed of individual singles matches,
- no women's tour or doubles,
- coaches, support teams, agents and training centers are not separate simulated entities in the current version,
- no personal sponsors/contracts, player salaries, detailed travel costs, AI player photos, simulated attendance or standalone junior ranking in the current version.

---

# 2. Viewer and Admin

## 2.1 Viewer

**[DECIDED]** Viewer is always read-only. It cannot edit, simulate, import, regenerate or perform Admin mutations.

Viewer is a historically faithful environment for multiple fictional public websites over the same Run/time context; the main current website is **MSA Squash**.

Viewer must never fabricate unavailable data or leak future results, hidden Admin state or future-derived information.

**[DECIDED]** Historical MSA homepage public messages are derived from the structured public part of the World Event Log valid at that time. A rendered message is not a second source of truth.

## 2.2 Admin

**[TARGET]** Admin is the working environment for creating, editing, validating, simulating, reconstructing and auditing the world.

**[DECIDED]** Global Admin and Run Admin are different scopes:

### Global Admin

- no active Run,
- no active branch,
- no season/week context,
- manages Runs, source Packages and genuinely global data,
- Viewer cannot be opened until a Run is selected.

### Run Admin

- one active Run,
- one active Admin branch,
- season/week viewing context,
- Run-specific navigation and workflows.

**[DECIDED]** Run Admin landing page is **Home**, not Dashboard. Home is an overview/command center, not the place for every execution-heavy simulation action.

**[DECIDED]** Run Home has two fixed segmented progress indicators:

- position in the full 50-season Run,
- position in the current 61-week season.

**[PROVISIONAL STRONG DIRECTION]** Full final Run Admin navigation remains open. Current working groups such as Home / World / Players / Tour / Rankings & Analytics / Simulation / History / Data / Settings must not be treated as final solely because they exist in a mockup or beta route tree.

## 2.3 Viewer ↔ Admin context mapping

**[DECIDED IN PRINCIPLE]** Switching mode preserves as much context as possible: Run, time, object and matching subpage where a counterpart exists.

Admin → Viewer never silently changes the Run's Viewer Branch. If the same object/time is unavailable there, use the closest meaningful fallback and explain the context change.

---

# 3. Application shell

**[DECIDED]** Application root is neutral **Squash Engine Home** with current global entries:

- Runs
- Packages

It does not automatically activate a Run and is not a Viewer/Admin chooser.

Global pages have no Run/Branch/Time selectors.

Run-scoped upper-right controls remain conceptually:

- Viewer: `Run → Time → Viewer/Admin`
- Admin: `Run → Branch → Time → Viewer/Admin`

Global search and `Ctrl+K` remain part of the shell.

**[DECIDED] Admin header hierarchy:** Squash Engine logo leads to global Home; in Run Admin a Run identity control leads to that Run's Home.

**[DECIDED] Viewer header hierarchy:** Viewer logo leads to the public-site hub for the Run; current site logo leads to that site's homepage.

---

# 4. Run model

**[DECIDED][ENGINE INVARIANT]** Every Run spans exactly 50 seasons `2000/01–2049/50`, each with exactly 61 Season Weeks.

**[DECIDED]** A Run is an independent saved simulation world containing stable identity/name, embedded package snapshots and provenance, seasons, branches/history, players, tournaments, matches, rankings and simulation/configuration state.

## 4.1 Run identity and lifecycle

**[DECIDED]** Number of Runs is not artificially limited.

**[DECIDED]** Every Run has a unique displayed name across active and archived Runs. An archived Run continues reserving its name. Technical identity is stable `run_id`.

**[DECIDED]** Run description is optional.

**[DECIDED]** Copy/import with a conflicting name proposes a new unique working name; a still-conflicting name cannot be saved.

**[DECIDED]** Normal lifecycle is:

- `Working`
- `Completed`
- `Archived`

`Built-in / Local`, `Read-only / Editable`, and `Valid / Warnings / Errors` are independent properties, not lifecycle states.

Completion at the last week does not automatically archive a Run, and a completed Run may still branch from earlier saved history.

## 4.2 Operation-scoped readiness

**[DECIDED]** There is no blocking global Setup → Active gate. A Run may be built incrementally and any currently valid operation may run.

Missing or invalid data outside the requested operation must not block an independent valid operation. Admin must explain which prerequisites are missing for the requested operation itself.

## 4.3 Runs page and switcher

`Runs` is a neutral global page outside Run Admin and Viewer. Full list direction uses wide rows.

Distinct Run actions include:

- Open in Admin,
- Open branches/history,
- Open in Viewer.

Quick Run switcher is for a small current/favorite/recent set plus entry to All Runs; destructive or complex management belongs on the full Runs page.

## 4.4 Built-in Runs and Match Test Lab

**[DECIDED]** Normal user Runs are local.

**[TARGET]** Some Runs may be built into the project/GitHub and read-only at source.

**[DECIDED IN PRINCIPLE][TARGET]** A built-in read-only **Match Test Lab** exists for rapid individual Match Engine testing. `New Test Session` creates an isolated editable session/copy; test changes and results must never mutate the built-in baseline.

Historical player snapshots may be brought into the Lab without silently linking the Lab back to another Run's mutable live state.

---

# 5. Branches, history and Viewer Branch

**[DECIDED]** A branch is an alternative timeline inside a Run. Branches share `run_id` and common pre-divergence history but have their own `branch_id` and may diverge in calendar, results, rankings, player state, configuration and rules.

There is no privileged `Official Branch` or `Main Branch` product concept.

**[DECIDED]** Each Run has exactly one **Viewer Branch**:

- it selects which saved timeline the read-only Viewer displays,
- it is not more authoritative than another branch,
- product terminology is `viewer_branch_id` / Viewer Branch even if legacy schema names still exist,
- Viewer Branch cannot simply disappear without another valid active branch being selected.

**[OPEN]** Exact persistence/activation timing of explicit `Show in Viewer` remains unresolved.

## 5.1 History model

- branch can be created from any saved valid historical point,
- differing simulated histories never auto-merge,
- shared pre-divergence history should be stored once,
- Admin history target combines branch map and selected-branch timeline,
- every successful Save creates a recoverable version,
- checkpoint is a bookmark/technical restore point, not the only recovery mechanism,
- Undo/Redo belongs to the working session; long-term rollback uses versions/history/checkpoints.

Explicit transfer of compatible configuration/manual changes between divergent branches is a new auditable operation, not a hidden merge.

---

# 6. Time model

**[DECIDED][ENGINE INVARIANT CURRENT VERSION]** FAX uses a calendar year of exactly 61 weeks. Exact calendar dates/days do not exist in the core world model; time is year + week.

The engine distinguishes:

- `Year Week` — 1–61 inside calendar year,
- `Season Week` — 1–61 inside season.

**[DECIDED]** Every new calendar year begins as `Year Week 1` and `Season Week 26`. For season `2000/01`:

- Season Week 1 = Year 2000, Year Week 37,
- Season Week 25 = Year 2000, Year Week 61,
- Season Week 26 = Year 2001, Year Week 1,
- Season Week 61 = Year 2001, Year Week 36.

**[DECIDED]** Player birth is stored as `birth_year + birth_year_week`; exact date of birth is not required by the core model.

## 6.1 Historical Viewer/time machine

Viewer can inspect any completed/generated historical week and the currently progressing week using only then-known saved data.

Future not-yet-started weeks are not Viewer states.

The global time control changes viewing context only; it never advances or rewinds simulation.

Visible relation to current simulation state:

- Viewer: `PRESENT / PAST`
- Admin: `PRESENT / PAST / FUTURE`

A week with no scheduled match/tournament still has to progress through required boundary processes rather than being silently skipped.

---

# 7. Packages

## 7.1 World + Category Packages

**[DECIDED]** Every Run selects exactly one World Package and one Category Package during creation.

Selected versions are copied into the Run as independent versioned snapshots. Source identity/version remains provenance only; there is no live link afterwards.

Consequences:

- editing a global source affects future Runs only,
- editing an embedded snapshot affects only that Run according to historical rules,
- existing Runs never silently absorb source updates,
- built-in GitHub source Packages are read-only,
- local/custom source Packages can be editable,
- embedded snapshots may be editable inside an editable local Run even when their source was built-in,
- World and Category Packages are content-independent and validated independently.

Official defaults:

- `Official FAX World`
- `Official FAX Category Package`

**[PROVISIONAL STRONG DIRECTION]** Future Package types such as Player Packages and possible base/import distinctions remain possible but not canonized.

## 7.2 Global Packages area

**[DECIDED]** Source World and Category Packages have global Admin pages outside all Runs. UI must clearly distinguish source authoring from Run snapshot editing.

---

# 8. Countries, population, travel and talent generation

- player generation uses population from the relevant birth-year context,
- changing population/generation parameters does not retroactively rewrite already generated players,
- talent quantity and talent quality are separate concepts,
- population alone does not determine squash strength,
- exact formulas, weights and infrastructure/tradition effects remain open.

Official/built-in population datasets may cover historical/future ranges such as 1955–2050 according to their Package; do not generalize one Package's range into a universal engine invariant.

## 8.1 CSV/XLSX import

**[DECIDED]** CSV/XLSX country/population import is available only for editable local data, not for direct mutation of built-in read-only sources.

Import uses staging + preview + validation before mutation. Error feedback should identify row/column/value/reason/expected format/example/fix. Meaning-changing corrections require explicit approval.

Valid independent rows may be imported selectively only when referential consistency remains valid. Confirmed writes are atomic and auditable.

## 8.2 Travel geography

**[DECIDED IN PRINCIPLE]** Travel Regions and circular Timezone Areas are independent coarse systems for first-version travel/jet-lag handling.

First version uses coarse region transitions and elapsed-time separation rather than a detailed physical-location simulation.

Exact region network, distances, acclimatization curves and detailed travel mathematics remain open/deferred. Home Base was explicitly skipped for the current version.

**[PROVISIONAL]** Individual `Jet Lag Resistance` and `Travel Resilience` remain directions rather than fully calibrated final rules.

---

# 9. Players, lifecycle, state and AI

**[DECIDED]** Player identity is stable `player_id`; display names need not be globally unique.

Player profile exists from prospect/junior visibility onward and continues through Tour career/history.

Time-varying player profile/state is historical. Height and weight may change over time.

Admin owns authoritative internal state; Viewer exposes public or legitimately estimated information according to the time context.

Generation includes an initial mixed-age pool and continuing intake. Automatically generated prospects are intended to enter the Tour through lifecycle rules rather than remain permanently unused.

Manual player creation, lock/unlock and safe regeneration are supported concepts. There is no separate mandatory player-licence concept in the current target model.

Current player-state target includes:

- attributes,
- potential and derived OVR,
- physical profile,
- form,
- fatigue,
- health/injury state,
- physical stamina dimensions,
- mental match state direction,
- style/gameplan,
- player decision AI.

Exact formulas/calibration remain open where not explicitly decided.

## 9.1 Individual AI

**[DECIDED]** Every player uses an individual AI and may make different decisions in the same external situation. First version may be simple; calibration follows a working simulation.

**[DECIDED FOR V1]** AI perceives its own fatigue relatively well but not as an exact hidden number. It estimates opponent fatigue from observable signals and may be wrong or late.

**[PROVISIONAL STRONG DIRECTION]** Player AI should not use Admin `Absolute Forecast` or its omniscient probabilities as a hidden decision aid. Forecast may be used by Admin to evaluate AI independently.

Scouting, memory, intelligence, gameplan creation/adaptation and exact decision mathematics remain deferred/open.

## 9.2 Form

**[DECIDED FOR V1]** Each player has one current Form.

- updates after every actually played match,
- reflects quality of performance relative to opponent and expectation, not only win/loss,
- affects the next match immediately, including within the same tournament,
- regresses gradually during Week Transition toward an individual long-term norm,
- never hard-resets,
- does not overwrite long-term attributes or physical stamina capacity.

W/O and pre-start DQ do not change Form. RET and post-start DQ use actual played performance with weight limited by available evidence. ABN/No Contest defers the single recalculation until final resolution. Disciplinary reason is not itself sporting form.

Exact Form scale, formula, norm and reversion speed remain open.

## 9.3 Retirement/inactivity

Inactive status is a real lifecycle decision/state, not an automatic label created solely because a player has not played for some fixed time.

Automatic/deliberate retirement and comeback are engine capabilities with Official Run defaults stored in lifecycle policy; exact voluntary-retirement behavior remains only partially specified.

---

# 10. Tournament, calendar, entries, qualification and draws

The engine distinguishes persistent **Tournament Series** identity from season-specific **Tournament Edition**.

Calendar/category systems are historically configurable rather than hard-coded global constants.

Core tournament/draw capability includes:

- seeded tiers and controlled placement,
- BYEs,
- qualifier (`Q`) slots,
- bracket or group qualification,
- Lucky Losers,
- withdrawals and replacements,
- walkovers/retirements/abnormal results,
- qualification and Main Draw freeze concepts,
- manual Admin editing/regeneration with increasing safeguards after play begins.

Qualification and Main Draw may have their own week ranges. Qualification must be completed before Main Draw begins; overlapping week ranges are possible only when the internal chronological order resolves qualification first.

One Tournament Ranking Snapshot is used for entry/ordering/seed-related policy where specified by the tournament contract.

`Simulate` and manual/step-by-step workflows are complementary; they are not mutually exclusive global modes.

## 10.1 Tournament Edition lifecycle and public knowledge

**[DECIDED]** Each concrete occurrence is a Tournament Edition with its own `edition_id`, season/weeks, parameters and edition number.

**[DECIDED]** Edition lifecycle is derived from actual events/component state and produces a public `Public Stage`; Admin can see internal prerequisites/deadlines while Viewer sees only public state.

**[DECIDED]** Incomplete Drafts can be saved. Missing fields block only dependent operations such as scheduling, entries, draw or simulation.

**[DECIDED]** Every Tournament Edition has historical `announcement_week`.

Before that week becomes active and its public World Event exists:

- Admin may know the Edition,
- Viewer must not know it,
- player AI must not use it.

First version uses one common public announcement time for Viewer and all players.

Normal announcement must be at least one full week before the earliest operational event. Later public changes use explicit Tournament Update events; emergency handling is a separate exceptional path.

## 10.2 Entry slots

**[DECIDED]** Entry decisions belonging to the same Simulation Slot read from one shared snapshot and commit transactionally.

Retry must not arbitrarily reshuffle unrelated successful decisions.

An application/entry is historical state, not an ephemeral UI choice.

Exact Entry Freeze/cut-off details remain open where not explicitly resolved.

---

# 11. Chronological simulation model

## 11.1 Week Transition

**[DECIDED FOR V1]** Moving into a new week uses explicit automatic **Week Transition**. It is not a normal Simulation Slot.

Week Transition prepares the new week's initial state from information known through the completed week and includes the relevant boundary processes such as point activation/ranking snapshot creation, birthdays/prospect intake and weekly development.

**[DECIDED FOR V1]** `Weekly Player Development Update` uses only state/history known through the end of the completed week; it cannot read newly opened/future-week information.

Continuous state such as fatigue and health does not automatically reset at week boundary.

## 11.2 Simulation Slots

**[DECIDED FOR V1]** Every week has one global chronological sequence with a variable number of **Simulation Slots**.

- events in one slot are simultaneous,
- all use the same pre-slot snapshot,
- technical execution order must not change their inputs,
- next slot begins only after the current slot is validly resolved.

**[DECIDED]** `Simulate Next Slot` resolves all remaining events of the nearest unresolved slot.

**[DECIDED]** Split `Simulate Next Match` may resolve the first stable-order match or a user-selected unresolved match in that slot without changing the inputs of other simultaneous matches.

Exact slot taxonomy/count remains open.

## 11.3 Season Transition

**[DECIDED FOR V1]** **Season Transition** is the special Season Week 61 → Week 1 extension of Week Transition, not another normal slot.

It completes only when mandatory closing-season events are terminally resolved. A red issue blocks only the affected transition/operation and identifies the cause.

New seasonal policies activate atomically. Only explicit season-scoped state resets; continuous player/history state continues.

A lightweight **Season Closure Marker** records closure rather than copying the entire world.

**[DECIDED]** All 50 seasons can use efficient virtual **Inherited Plans**. Drafts/Tournament Editions materialize only when editing, confirmation, Season Transition or simulation needs them; explicit overrides are protected.

---

# 12. Match Engine v1

Official Run individual-match default is BO5 to 11, win by 2 unless narrower stored configuration overrides it. Individual matches never end in a draw; abnormal statuses require explicit stored semantics.

**[DECIDED FOR V1]** Match simulation is **rally-by-rally**, not shot-by-shot.

A rally uses a hidden multi-phase process with five control/pressure states, individual physical load and separate sporting/officiating evaluation.

## 12.1 Physical stamina and effort

**[DECIDED FROM v42]** Match state contains three distinct physical stamina dimensions, each with capacity/current state/recovery, updated after every rally.

**[NEWER PROVISIONAL DIRECTION]** Do not implement those three dimensions as three independent standalone trainable attributes by default. Current V1 direction is to derive them from the lighter underlying attribute/state model and expose them as three physical match bars/dimensions. Exact mapping remains open.

**[PROVISIONAL]** One or more mental match bars/dimensions are additionally desired; exact mechanics remain open.

AI selects a baseline effort level before a rally and may change effort during hidden rally-state transitions. Exact decision weights remain open.

## 12.2 Rally log and serve

**[DECIDED]** Authoritative log unit is a **rally**, not a generic “point event”. The compact rally record stores sporting cause, official decision, duration, estimated shot count and relevant physical-state context for both players.

**[DECIDED]** Serve has a weaker opening influence appropriate to squash rather than tennis-like dominance.

## 12.3 Interference

**[DECIDED FOR V1]** Simplified correct squash interference uses:

- No Let,
- Yes Let,
- Stroke.

Referee errors, detailed reviews, edge interference cases, deliberate delay and individual referee profiles are later scope.

## 12.4 Match timing and health breaks

**[DECIDED FOR V1]** Match history includes authoritative timing events, not only scores.

Official Run defaults currently include:

- 2-minute interval between games,
- 3-minute simplified health break where that workflow applies.

Recovery follows actual elapsed time; breaks do not magically reset stamina/form/health.

Exact generation of normal between-rally gap and broader medical/injury mathematics remain open.

---

# 13. Match Reconstruction

**[DECIDED FOR V1]** Admin supports **Match Reconstruction** when some historical facts are known but detailed rally history is missing.

- manually supplied facts are constraints,
- Admin chooses candidate count,
- engine generates histories consistent with constraints,
- candidate cards allow compact comparison,
- every candidate has complete read-only detail,
- candidate existence does not mutate authoritative history,
- only an explicitly selected candidate becomes authoritative history.

Selection/commit must validate constraints and store audit/provenance.

**[PROVISIONAL/OPEN]** Default ten candidates, remembering last count, exact probability/statistical architecture, session retention and exact compact-card fields do not all have final status.

---

# 14. Rankings, statistics, history and predictions

Ranking snapshots and policies are historically versioned/configurable. Official and Live rankings may coexist with analytical rankings.

**[DECIDED][OFFICIAL RUN DEFAULT]** Season `2000/01` starts with **Best 15**.

**[DECIDED]** Every later season initially inherits the immediately previous season's effective Best N while remaining independently configurable.

Future policy changes must not silently recompute historical ranking truth from today's defaults.

Official MSA Ranking has deterministic unique ordering/tie-break behavior; pre-Tour prospects are not silently inserted into the MSA ranking population before formal Tour entry.

H2H, statistics, records, awards and historical timelines are first-class generated data products.

Predictions/odds must be based only on the information layer appropriate to their context and must not leak future truth in historical Viewer views.

Country Ranking's exact formula remains deferred until base simulation is mature enough to calibrate it.

---

# 15. Configuration inheritance and historical policy

**[DECIDED]** Stored Runs preserve the actual values/rules that applied historically; loading old history must not recompute it from current Official defaults.

Supported configurable values use the concepts:

- `Inherited`
- `Override`

Admin should show effective value plus inheritance/override source. Changing a parent updates only dependent inherited values; explicit overrides remain until Restore inheritance.

**[PROVISIONAL STRONG DIRECTION]** Working hierarchy remains approximately:

`engine default → Run package → Run → season → category → Tournament Series → Tournament Edition → phase/round → match`

Exact placement/availability of every setting remains open.

If a rule can legitimately vary by Run/season, do not hard-code an Official default as a universal engine constant.

---

# 16. World Event Log, Audit Log, Task Center and Notification Center

**[DECIDED]** These are four separate product layers:

- **World Event Log** — chronological branch history of world facts/events,
- **Audit Log** — changes to data and provenance,
- **Task Center** — running/completed operations,
- **Notification Center** — items requiring Admin attention.

Reading/dismissing a notification must not delete its source World Event, audit record, task or validation result.

**[DECIDED]** Notification Center supports automatic system notifications and user watchlists. Repeated notices may be grouped; critical issues remain individually visible.

**[DECIDED]** Severity contract across Admin:

- blue information — non-blocking,
- orange warning — non-blocking,
- red critical — blocks or safely stops only the affected operation/branch.

Every warning/block should explain cause, impact and repair options.

Viewer does not show technical notifications, internal validation or Audit Log.

Standalone News page, final event taxonomy and `News Importance Score` remain unresolved/provisional at their real statuses.

---

# 17. Save, import/export, storage and recovery

**[DECIDED]** Normal Save stores coherent working changes; advanced save may select safe logical bundles.

Every successful Save creates a recoverable version.

Important mutations are auditable and preserve provenance such as Built-in, Generated/Simulated, Imported, Manual and Regenerated where applicable.

CSV/XLSX and other structured imports use preview/staging and atomic confirmed writes.

Run copy with unsaved changes must not silently choose a source state; the workflow must make clear whether it copies last saved state, saves first, copies working draft or cancels.

Run copy supports full copy and a safe advanced subset with required dependencies; new copy receives a new `run_id` and no live link to the original.

Run export target includes:

- full archive,
- safe custom export,
- compact snapshot.

Version migration must never silently drop unknown data. Older supported schemas migrate safely; unsupported newer schemas fail clearly rather than partially loading.

No artificial storage quota or silent automatic deletion. Admin may show physical usage and block only an operation that truly lacks required space.

Crash recovery distinguishes saved state from Recovery Draft. Undo/Redo is session-local; historical restore uses versions/checkpoints.

Long tasks should expose progress/state and support safe pause/stop/recovery boundaries. Windows tray/background continuation remains part of the broader target where supported.

---

# 18. Major competitions

The product has dedicated systems for:

- World Tour Finals,
- Individual World Championship,
- Team World Championship,
- continental championships,
- national championships,
- possible later league/IFSL-type structures.

Exact formats may be Run configuration/Official defaults or remain open rather than engine invariants.

## 18.1 Team World Championship

**[DECIDED][OFFICIAL RUN]** Men's Team World Championship exists.

**[DECIDED][OFFICIAL RUN]** It occurs every odd calendar year unless a later explicit decision changes that Official schedule.

**[DECIDED]** Each international tie consists of exactly six individual singles matches, each BO5 to 11, win by 2.

**[DECIDED]** At 3–3 in individual matches, tie-break order is:

1. aggregate set difference across all six singles,
2. aggregate point difference,
3. result of the position-1 singles match.

**[DECIDED]** Championship nomination/positioning uses one fixed Team Championship Ranking Snapshot associated with the roster-lock logic; later ranking movement during the event does not reorder the already locked team.

Roster capacity is configurable; do not invent a universal minimum that Master v41 explicitly removed as unsupported.

Overall field, qualification, calendar and exact order of six singles remain open where not separately decided.

---

# 19. Forecast and Future Locks

**[PROVISIONAL STRONG DIRECTION]** Forecast is non-authoritative analysis. Running Forecast does not mutate Run, branch, real future seed or current time.

Direction includes reproducible Forecast Sessions, scalable sampling, conditional analysis, sample reconstruction, pinning/comparison, rare-event tools and explicit branch materialization.

**[PROVISIONAL STRONG DIRECTION]** Future Locks constrain possible futures for Forecast/testing and potentially branch workflows. Feasibility is separate from natural probability. Viewer does not see locks; Admin preserves provenance.

Exact algorithms, sampling thresholds, UI, retention, conflict handling, fulfilled-lock lifecycle and complete deterministic contract remain partially open.

---

# 20. Rivalries, records and tournament prestige

**[DECIDED]** Player rivalries exist as a product concept.

**[PROVISIONAL]** Automatic detection, overlapping/multi-player rivalry groups, scoring, lifecycle, manual insertion from unsimulated junior history and exact Viewer placement remain directions of varying strength.

**[DECIDED]** Viewer/Admin will expose many historically correct records derived from authoritative branch/week data.

**[PROVISIONAL WEAK DIRECTION]** A unified record service and complete succession history of holders remain weaker ideas.

**[PROVISIONAL]** Tournament Prestige is a direction: Tournament Series may carry changing Prestige Score with category defaults and Admin overrides/locks. Individual Tournament Appeal remains a weaker separate direction.

---

# 21. UX and design contract

**[PROVISIONAL STRONG PREFERENCE]** Premium but practical sports-manager / sports-data product:

- high readability,
- clear hierarchy,
- desktop-first,
- no overlapping panels,
- tables optimized for desktop,
- summary first and technical detail lower,
- strong Viewer/Admin distinction,
- explicit preview vs mutation,
- no unnecessary neon/sci-fi styling.

**[DECIDED/TARGET AS SPECIFIED]**

- Czech + English UI target,
- Light / Dark / System appearance target,
- important state is never communicated by color alone,
- Viewer and Admin have distinct visual/textual mode indication,
- appropriate Admin tables support multi-select with only valid bulk actions,
- global search exists with keyboard shortcut,
- current version is desktop-first rather than fully mobile-responsive.

Full final Admin/Viewer navigation, Viewer reveal modes, exact MSA menu and many page layouts remain unresolved.

---

# 22. v41 audit corrections that must remain preserved

Master v41 intentionally corrected several overclaims. New code/docs must not reintroduce them:

- authoritative compact Match Engine log unit is **rally**, not an incorrectly generalized “point” unit,
- there is no proven universal exact three-week jet-lag cut-off,
- there is no proven universal minimum `roster_capacity`,
- exact generation of ordinary between-rally time gap remains open,
- pre-Tour prospects are not silently included in the Official MSA Ranking before their formal Tour entry,
- player rivalries are confirmed to exist as a product concept,
- uncertain details must remain uncertain rather than being promoted for convenience.

---

# 23. Explicitly open/deferred areas — do not invent silently

Examples include:

- final full Global/Run Admin navigation tree,
- final Viewer public-site navigation/reveal modes and exact MSA menu,
- exact Show in Viewer activation timing,
- final branch concurrency/lock matrix,
- complete engine-wide deterministic seed contract,
- exact talent-generation mathematics,
- final attribute/development/health/form/AI calibration,
- exact mapping from player attributes into the three physical stamina bars,
- exact number/mechanics of mental match bars,
- exact Simulation Slot taxonomy/count,
- remaining Entry Freeze/cut-off rules,
- final Category Package seasonal data format,
- Country Ranking formula,
- final Forecast/Future Lock algorithms and lifecycle,
- Match Reconstruction probability architecture, retention and compact-card details,
- advanced referee/review/court-condition systems,
- detailed travel/acclimatization mathematics,
- several competition fields/qualification formats and scheduling details.

---

# 24. Current implementation vs target

This constitution describes **what Squash Engine should be**. The repository remains a beta with mixed implementation maturity and legacy naming/architecture debt.

Implementation work must:

- inspect current code/API/schema before editing,
- preserve working data contracts unless intentionally migrating them,
- distinguish implemented behavior from target behavior,
- add deterministic tests for changed behavior,
- keep migrations backward-safe where saved Runs/data may exist,
- avoid fake data solely to satisfy a mockup,
- preserve historical truth/provenance,
- preserve decision status instead of treating every Master item as final,
- never delete an older still-valid product rule merely because a newer summary focuses on another area.

---

# 25. Product definition in one sentence

**Squash Engine is a long-term deterministic manager and simulator of the men's professional FAX squash world, capable of generating and evolving countries, players, tournaments, matches, rankings and decades of history, safely branching alternative timelines, reconstructing constrained historical matches, and presenting the result through a powerful Admin workspace and historically faithful read-only Viewer websites led by MSA.**
