# Squash Engine / FAX Squash / MSA World Tour

## Active Product Constitution — synchronized from Master Vision v42

**Repository status:** canonical product-level specification for current design and implementation decisions.  
**Source version:** Master Vision **42**.  
**Source updated:** **10. 8. 2026**.  

> This file is a repository-facing constitution distilled from Master Vision v42. The detailed Master is broader and more granular. A rule being specified here does **not** mean it is already implemented.

---

## 0. How to read this document

Decision states:

- **[DECIDED]** — current rule/design; build against it until explicitly changed.
- **[PROVISIONAL]** — working rule or strong direction, not final canon.
- **[TARGET]** — required capability whose exact details may still be open.
- **[OPEN]** — not decided yet.
- **[DEFERRED]** — intentionally postponed.
- **[LATER]** — future-version idea, not current scope.
- **[OLDER IDEA]** — historical context only unless reconfirmed.

Independent scope axis:

- **ENGINE INVARIANT** — universal technical contract for all Runs in the current version.
- **RUN CONFIG** — configurable state of a Run/package/season/category/tournament/etc.
- **OFFICIAL RUN DEFAULT** — FAX/MSA default, not a universal restriction.
- **OVERRIDE** — explicit narrower exception.

### Precedence

When sources disagree:

1. explicit newer user/product decisions,
2. latest audited Master Vision — currently v42,
3. this constitution,
4. subordinate migration guidance such as `docs/ENGINE_UX_SPEC.md`,
5. README/ROADMAP/AGENTS summaries,
6. older docs, handoffs and current beta behavior only as implementation/history evidence.

Do not convert `[PROVISIONAL]`, `[OPEN]`, `[DEFERRED]` or `[LATER]` items into hard product rules without a newer explicit decision.

---

# 1. Product identity and scope

**[TARGET]** Squash Engine is a long-term deterministic manager and simulator of the fictional men's professional FAX squash world. It covers countries and population, player generations/careers, tournaments and entries, match simulation, rankings/statistics/history, alternative timelines, Admin workflows and historically faithful read-only public Viewer websites led by MSA.

**[DECIDED] Current scope:**

- men's squash only,
- singles matches only,
- one-user local product; no accounts/roles/login,
- exactly 50 seasons `2000/01–2049/50`,
- exactly 61 Season Weeks per season,
- team competitions consist of individual singles matches,
- no women's tour, doubles, coaches, support teams, agents or training centers as separate simulated entities in the current version,
- no personal sponsors/contracts, player salaries, detailed travel costs, AI player photos, simulated attendance or standalone junior ranking in the current version.

---

# 2. Viewer and Admin

## 2.1 Viewer

**[DECIDED]** Viewer is always read-only. It cannot edit, simulate, import, regenerate or perform Admin mutations.

Viewer is a historically faithful environment for multiple fictional public websites over the same Run/time context; the main current site is **MSA Squash**.

Viewer must not fabricate unavailable data or leak future information. Public news/messages come from then-public World Events rather than becoming a separate source of truth.

## 2.2 Admin

**[TARGET]** Admin creates, edits, validates, simulates, reconstructs and audits the world.

**[DECIDED]** Global Admin and Run Admin are separate scopes:

- **Global Admin:** no active Run/branch/week; manages Runs and source Packages.
- **Run Admin:** one Run, one active Admin branch and time context.

**[DECIDED]** Run Admin landing page is **Home**, not Dashboard. It is an overview/command center, not the place where every simulation control must live.

**[DECIDED]** Run Home has two fixed segmented progress indicators:

- position in the 50-season Run,
- position in the current 61-week season.

**[PROVISIONAL]** Full Run Admin navigation tree remains a strong direction rather than final canon.

## 2.3 Viewer ↔ Admin mapping

**[DECIDED IN PRINCIPLE]** Mode switching preserves Run, time, object and matching subpage when possible.

Admin → Viewer never silently changes Viewer Branch. If the exact object/time is unavailable in Viewer Branch, use the closest meaningful fallback and explain the context change.

---

# 3. Application shell

**[DECIDED]** Application root is neutral **Squash Engine Home** with current global entries:

- Runs
- Packages

Global pages have no Run/Branch/Time selectors. Viewer is unavailable until a Run is chosen.

Run-scoped upper-right controls remain conceptually:

- Viewer: `Run → Time → Viewer/Admin`
- Admin: `Run → Branch → Time → Viewer/Admin`

Global search/`Ctrl+K` remains part of the shell.

---

# 4. Run and branch model

**[DECIDED][ENGINE INVARIANT]** Every Run spans exactly 50 seasons `2000/01–2049/50`; each contains exactly 61 Season Weeks.

**[DECIDED]** Run lifecycle is `Working / Completed / Archived`. `Built-in/Local`, `Read-only/Editable` and `Valid/Warnings/Errors` are independent properties, not lifecycle states.

**[DECIDED]** No blocking global Setup phase exists. Validation is operation-scoped: unrelated incomplete data must not block an otherwise valid operation.

**[DECIDED]** Branches are equal alternative timelines inside one Run. There is no privileged Main/Official branch concept.

**[DECIDED]** Each Run has exactly one **Viewer Branch**. It selects which saved timeline Viewer displays and does not make that branch more authoritative than others.

**[OPEN]** Exact save/activation moment of the explicit Show in Viewer operation remains unresolved.

History target includes recoverable saves, versions, checkpoints, branch map/timeline and shared pre-divergence storage rather than duplicating common history.

---

# 5. Packages and world data

**[DECIDED]** Every Run selects exactly one World Package and one Category Package during creation.

Selected versions are copied into the Run as independent versioned snapshots. Source identity/version remains provenance only; later source edits never silently rewrite existing Runs.

Built-in GitHub source Packages are read-only. Custom/local source Packages can be editable.

**[PROVISIONAL]** Future Package types such as Player Packages remain possible but are not canonized.

Population, talent quantity/quality and country strength are separate concepts; exact generation formulas remain open.

**[DECIDED IN PRINCIPLE]** Travel Regions and Timezone Areas exist as coarse independent geographic systems for first-version travel/jet-lag handling. Exact networks, distances and acclimatization mathematics remain open/deferred.

---

# 6. Players, state and AI

Player identity uses stable `player_id`; time-varying state belongs to Run/branch/week history.

Current player state target includes attributes, potential/OVR, physical profile, form, fatigue, health, stamina, style/gameplan and decision AI.

**[DECIDED]** Each player uses an individual AI; different players may choose differently in the same external situation. Exact behavior is calibrated later over a working simulation.

**[DECIDED]** Player AI does not get hidden omniscient access to Admin-only truth or Forecast output.

## 6.1 Form

**[DECIDED FOR V1]** Each player has one current Form.

- updates after each actually played match,
- considers performance quality relative to opponent/expectation rather than only win/loss,
- affects the next match immediately, including within the same tournament,
- regresses gradually toward the player's individual long-term norm during Week Transition,
- never hard-resets,
- does not overwrite long-term attributes or stamina capacity.

W/O and pre-start DQ do not change Form. RET/post-start DQ use only actually played performance with reduced evidence weight. Abnormal/No Contest cases postpone or constrain recalculation according to final resolution.

Exact formulas, scale and reversion speed remain open.

---

# 7. Time progression, Week Transition and Simulation Slots

**[DECIDED FOR V1]** Moving into a new week uses an explicit automatic **Week Transition**. It is not a Simulation Slot.

Week Transition prepares the next week's initial state and may include ranking activation, birthdays/prospect intake and other boundary processes.

**[DECIDED FOR V1]** `Weekly Player Development Update` uses only state/history known through the end of the completed week. It cannot read information from the newly opened or future week.

Continuous states such as fatigue/health are not automatically reset by week change.

**[DECIDED FOR V1]** Every week has one global chronological sequence with a variable number of **Simulation Slots**.

- events inside one slot are simultaneous,
- all use the same pre-slot snapshot,
- technical execution order must not change their inputs,
- the next slot starts only after the current slot is validly resolved.

**[DECIDED]** `Simulate Next Slot` resolves the nearest unresolved slot.

**[DECIDED]** Split `Simulate Next Match` may resolve one stable-order match or a selected unresolved match inside the current slot without changing inputs of other simultaneous matches.

Exact number/taxonomy of slot types remains open.

---

# 8. Season Transition and future planning

**[DECIDED FOR V1]** **Season Transition** is the special Week 61 → Week 1 extension of Week Transition, not a normal slot.

It requires the closing season's mandatory events to be terminally resolved. Blocking problems are operation-scoped and identify their cause.

New seasonal policies activate atomically. Only explicitly season-scoped state resets; continuous player/history state continues.

A lightweight **Season Closure Marker** records the boundary without copying the entire world.

**[DECIDED]** Future seasons may use efficient **Inherited Plans**; Drafts/Tournament Editions need not be eagerly materialized until editing, confirmation or simulation requires them.

Future calendar editing distinguishes narrower Edition-specific changes from forward-inherited changes while protecting explicit overrides.

---

# 9. Tournament Editions, publication and entries

Tournament Series is persistent identity; Tournament Edition is a season-specific occurrence with its own `edition_id`, season/weeks, parameters and edition number.

**[DECIDED]** Tournament Edition has derived lifecycle/component states and a public `Public Stage` rather than one disconnected manually maintained status.

**[DECIDED]** Incomplete Drafts may exist. Missing fields block only dependent operations such as scheduling, entries, draw or simulation.

## 9.1 Public knowledge

**[DECIDED]** Each Tournament Edition has historical `announcement_week`.

Before that week is activated and the public World Event exists:

- Admin may know the Edition,
- Viewer must not know it,
- player AI must not use it.

For first version, all players and Viewer share the same public announcement time.

Normal announcement must precede the earliest operational event by at least one full week. Later public changes use explicit update events; emergency handling is a separate exceptional path.

## 9.2 Entries

**[DECIDED]** Entry decisions that belong to one Simulation Slot read from the same snapshot and commit transactionally.

Retries must not arbitrarily reshuffle unrelated successful decisions.

An application/entry is historical state rather than an ephemeral UI choice.

Exact Entry Freeze/cut-off rules remain open where not explicitly resolved.

---

# 10. Match Engine v1

Official Run default individual format is BO5 to 11, win by 2 unless narrower stored configuration overrides it.

**[DECIDED FOR V1]** Matches are simulated **rally-by-rally**, not shot-by-shot.

Each rally uses a hidden multi-phase process with control/pressure states, individual physical load and separate sporting/officiating resolution.

**[DECIDED]** V1 has three distinct trainable stamina systems, each with capacity, current state and recovery. Their state updates after every rally.

**[DECIDED]** Player AI perceives its own fatigue imperfectly and estimates the opponent's fatigue from observable signals rather than hidden exact numbers.

AI selects an effort level before a rally and may change effort during hidden rally-state transitions.

**[DECIDED]** Serve has a weaker initial influence appropriate to squash rather than tennis-like dominance.

**[DECIDED FOR V1]** Interference uses simplified correct squash semantics:

- No Let
- Yes Let
- Stroke

Referee errors, detailed reviews, edge interference cases and deliberate delay are later scope.

**[DECIDED]** Authoritative rally log stores compact sporting cause, official decision, duration, estimated shot count and relevant stamina state.

Exact probability formulas, transition values and detailed calibration remain open.

---

# 11. Match timing and health breaks

**[DECIDED FOR V1]** Match history includes authoritative timing events, not only scores.

Official Run defaults currently include:

- 2-minute interval between games,
- 3-minute simplified health break where the configured health-break workflow applies.

Recovery during actual elapsed time is continuous; these breaks do not hard-reset stamina/form/health state.

Precise broader medical/injury mathematics remains open beyond the decided simplified first-version contract.

---

# 12. Match Reconstruction

**[DECIDED FOR V1]** Admin supports **Match Reconstruction** for matches where some historical facts are known but the detailed rally history is not.

- manually supplied facts are constraints,
- Admin chooses candidate count,
- engine generates candidate histories consistent with those constraints,
- candidate cards provide compact comparison,
- each candidate has complete read-only detail,
- candidates remain non-authoritative merely by existing,
- only an explicitly selected candidate becomes authoritative history.

Selection/commit must be validated and auditable with provenance.

**[PROVISIONAL/OPEN]** Default of ten candidates, remembering last count, exact probability/statistical architecture, session retention and exact compact-card content are not all fixed canon.

---

# 13. Rankings

Ranking policies and snapshots are historically versioned/configurable rather than globally hard-coded.

**[DECIDED][OFFICIAL RUN DEFAULT]** Season `2000/01` starts with **Best 15**.

**[DECIDED]** Each later season uses the immediately previous season's effective Best N as its initial inherited proposal, while remaining independently configurable.

Changing future policy must never silently recompute already historical ranking results from new defaults.

Country Ranking formula remains deferred until base simulation is mature enough to calibrate it.

---

# 14. World Event Log, Audit Log, Task Center and Notification Center

**[DECIDED]** These are four separate product layers:

- **World Event Log** — chronological branch history of world facts/events,
- **Audit Log** — changes to data and their provenance,
- **Task Center** — running/completed operations,
- **Notification Center** — items requiring Admin attention.

Reading/dismissing a notification must not delete its source World Event, audit record, task or validation result.

**[DECIDED]** Notification Center supports automatic system notifications and user watchlists. Repeated notices may be grouped; critical issues remain individually visible.

**[DECIDED]** Severity contract across Admin:

- blue information — non-blocking,
- orange warning — non-blocking,
- red critical — blocks or safely stops only the affected operation/branch.

Every blocking/warning state should explain cause, impact and repair options.

Viewer does not show technical alerts, internal validation or Audit Log.

**[DECIDED]** Historical MSA homepage public messages derive only from then-public structured World Events and must not create future leaks.

Standalone News page and News Importance Score remain unresolved/provisional at their actual status.

---

# 15. Forecast and Future Locks

**[PROVISIONAL STRONG DIRECTION]** Forecast is non-authoritative analysis. Running it does not mutate Run, branch, real future seed or current time.

Strong direction includes reproducible Forecast Sessions, scalable sampling, conditional analysis, sample reconstruction, pinning/comparison and explicit branch materialization.

**[PROVISIONAL STRONG DIRECTION]** Future Locks can constrain possible future outcomes for Forecast/testing and potentially real branch workflows. Feasibility is separate from natural probability. Viewer does not see locks; Admin preserves provenance.

Exact algorithms, sampling thresholds, rare-event methods, UI, retention, conflict handling and fulfilled-lock lifecycle remain partially open.

---

# 16. Rivalries, records and tournament prestige

**[DECIDED]** Player rivalries exist as a product concept.

**[PROVISIONAL]** Automatic detection, multi-player/overlapping rivalry groups, scoring, lifecycle, manual insertion from unsimulated junior history and exact Viewer placement remain directions of varying strength.

**[DECIDED]** Viewer/Admin will expose many historically correct records from authoritative branch/week data.

**[PROVISIONAL]** A unified record service and complete holder succession history remain weaker directions.

**[PROVISIONAL]** Tournament Prestige is a direction: Tournament Series may carry changing Prestige Score with category defaults and Admin overrides/locks. Tournament Appeal remains a weaker separate direction.

---

# 17. Save, audit, import/export and storage

- every successful Save creates a recoverable version,
- important mutations are auditable,
- imports use staging/preview/validation and atomic commit,
- meaning-changing corrections require explicit approval,
- valid independent rows may be selectively imported only when referential consistency remains valid,
- Run export/import must not silently lose data during version migration,
- no artificial silent deletion/storage quota behavior,
- crash recovery distinguishes saved state from Recovery Draft.

---

# 18. UX contract

Desktop-first, highly readable, practical sports-manager/data product.

- Viewer/Admin are visually and semantically distinct,
- important state is never communicated by color alone,
- Czech + English UI target,
- Light/Dark/System appearance target,
- preview must be distinct from mutation,
- user-facing terminology follows current canon even where backend adapters still use legacy names.

Full final Admin/Viewer navigation, Viewer reveal modes, exact MSA menu and many page-level layouts remain unresolved.

---

# 19. Explicitly open/deferred areas

Do not silently invent:

- final full Admin navigation tree,
- final Viewer public-site navigation/reveal modes,
- exact Show in Viewer activation timing,
- final branch concurrency/lock matrix,
- full engine-wide deterministic seed contract,
- exact talent-generation mathematics,
- detailed development/health/form/AI calibration,
- exact Simulation Slot taxonomy/count,
- unresolved Entry Freeze/cut-off rules,
- final Category Package seasonal format,
- Country Ranking formula,
- final Forecast/Future Lock algorithms and lifecycle,
- exact Match Reconstruction probability architecture and retention,
- advanced referee/review/court-condition systems,
- deep travel/acclimatization mathematics.

---

# 20. Current implementation vs target

This constitution describes **what Squash Engine should be**. The repository is a beta with mixed implementation maturity and legacy naming/architecture debt.

Implementation work must:

- inspect current code/API/schema before editing,
- preserve working contracts unless intentionally migrating them,
- distinguish implemented behavior from target behavior,
- add deterministic tests for changed behavior,
- keep migrations backward-safe where saved Runs/data can exist,
- avoid fake data merely to satisfy a target mockup,
- preserve decision status instead of treating every Master item as final.

---

# 21. Product definition in one sentence

**Squash Engine is a long-term deterministic manager and simulator of the men's professional FAX squash world, capable of generating and evolving countries, players, tournaments, matches, rankings and decades of history, safely branching alternative timelines, reconstructing constrained historical matches, and presenting the result through a powerful Admin workspace and historically faithful read-only Viewer websites led by MSA.**
