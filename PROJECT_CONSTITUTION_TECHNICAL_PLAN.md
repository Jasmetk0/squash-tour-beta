# Beta_Engine — Active Product & Technical Blueprint

## 1. Product Identity
Beta_Engine is a deterministic, data-driven, long-term FAX men’s professional squash world simulator.

It is not just a match generator.
It is not just an academy manager.
It should eventually generate and preserve a whole professional squash history.

The simulator should support a fictional FAX timeline roughly from:
- 2000/2001 to 2039/2040

The early development mode may simulate many seasons in bulk to test realism.
The final usage mode should allow detailed simulation and browsing match by match, tournament by tournament, week by week.

## 2. Two Main App Modes

### 2.1 Admin / Engine Mode
Admin Mode is for building, editing, regenerating, validating, and simulating the world.

It should eventually contain:
- Engine Dashboard
- World
- Tournament Categories / Templates
- Seasons
- Players
- Simulate
- Settings / Diagnostics

Admin Mode must be allowed to edit world data.
All serious edits must be explicit.
Important edits should create audit/history records when they affect simulated history.

### 2.2 Viewer / MSA Website Mode
Viewer Mode is for browsing the generated world as if it were a real professional squash association website.

It should eventually contain:
- Home
- Rankings
- Tournaments
- Players
- Countries
- History
- Records

Viewer Mode should not feel like an editor.
It should feel like a public sports database / MSA official website.

### 2.3 Separation Principle
Do not mix Admin Mode and Viewer Mode too much.

Admin Mode = create/edit/regenerate/simulate.
Viewer Mode = browse/read/analyze the generated world.

## 3. Time Model

### 3.1 Season
A season is identified by a label such as:
- 2000/2001
- 2001/2002
- ...
- 2039/2040

### 3.2 Season Week
Every season has exactly:
- 61 Season Weeks

Season Week is the main internal simulation index for tournaments, ranking updates, simulation commands, and season progression.

Use:
- season_week = 1..61

Even if a season starts in autumn, it still starts at Season Week 1.

### 3.3 Year Week
The engine must also support calendar positioning.

Use:
- calendar_year
- year_week = 1..52/53

A tournament/event can therefore have:
- season = "2000/2001"
- season_week = 7
- calendar_year = 2000
- year_week = 48

Season Week is for simulation structure.
Year Week is for real calendar timing, ages, birthdays, and historical browsing.

### 3.4 Player Birth Timing
Players should eventually store:
- birth_year
- birth_year_week

This allows player age to be calculated relative to the current calendar year/week.

Suggested derived fields:
- age_at_season_start
- current_age_years
- current_age_weeks

Players should not all age at one abstract global moment if better precision is available.

## 4. Admin Mode Pages

### 4.1 Engine Dashboard
Purpose:
Show current simulation/world status.

Should include:
- active world
- active season
- current season week
- current calendar year/week
- number of countries
- number of players
- number of tournament templates
- number of scheduled events
- simulation status
- stale/invalid future-history warnings
- last simulation actions
- validation issues

### 4.2 World
Purpose:
Add, delete, edit, import, export, and validate countries.

Country fields should include or be designed to later include:
- country code
- country name
- region/continent
- population
- squash culture
- access/infrastructure
- development pipeline
- competition density
- richness/wealth
- federation quality
- court count
- style DNA
- travel/regional metadata
- optional country momentum / era modifiers

Country parameters influence:
- initial player pool generation
- annual junior intake
- average potential
- player style distribution
- long-term country strength

Population must not be the only driver.
Small squash nations must be able to produce elite players if their culture/system/pipeline is strong.

### 4.3 Country Momentum / Era Modifiers
Countries should not have to be static across 40 seasons.

Each country may optionally define time-based modifiers.

If no country momentum curve is defined, use default modifier 1.00 across all seasons.

Possible era modifier fields:
- from_season
- to_season
- talent_quantity_modifier
- talent_quality_modifier
- infrastructure_modifier
- federation_stability_modifier
- golden_generation_chance_modifier
- decline_risk_modifier
- style_dna_modifier

Use cases:
- a country rises because squash becomes popular
- a country declines because its federation/system weakens
- a golden generation appears
- a formerly strong country loses depth

### 4.4 Tournament Categories / Templates
Purpose:
Define reusable tournament categories/templates.

These are not individual season events yet.
They are reusable types from which season events are created.

Examples:
- World Championship
- Diamond
- Emerald
- Platinum
- Gold
- Silver
- Bronze
- Elite
- Challenger
- Future / Development

Template fields should include:
- template_id
- category name
- tour level
- draw size
- qualification draw size
- number of seeds
- wildcard slots
- qualifier spots
- lucky loser rules
- byes rules
- points distribution
- prize money
- prestige
- duration in season weeks
- optional host requirements
- optional category-specific rules

Every serious tournament should support:
- qualification
- main draw
- seeds
- wildcards
- lucky losers
- withdrawals
- walkovers
- retirements

### 4.5 Seasons
Purpose:
Build actual season calendars from tournament templates.

Each season has 61 Season Weeks.

Season features:
- create season from a base template
- copy previous season
- edit individual season events
- assign tournament templates to season weeks
- allow tournaments lasting more than one season week
- allow multiple parallel tournaments in the same week
- prevent a player from playing more than one tournament in the same week
- detect impossible calendars
- detect overlaps
- allow event-level overrides from template values

Season event fields should include:
- event_id
- season
- season_week
- calendar_year
- year_week
- template_id
- host country
- host city
- duration
- event-level draw override
- event-level points override
- event-level prize money override
- status

### 4.6 Players
Purpose:
Generate, preview, edit, lock, delete, and regenerate players.

Before the first simulated season, the engine must generate an Initial Player Pool.

Initial Player Pool:
- generated before season 2000/2001
- should include players across all age groups
- approximate age range: 15–38
- must avoid a world where everyone starts as a 15-year-old
- should produce initial rankings and career stages

Initial player career stages:
- junior
- developing player
- breakthrough player
- prime player
- veteran
- late-career player

Annual intake:
At the end of each season, generate new young talents.
Default new intake age:
- mostly 15 years old

Later, optional late-discovered players may appear at:
- 16–17 years old

Player fields should include or be designed to later include:
- player_id
- name
- country
- birth_year
- birth_year_week
- current age
- current ability
- potential ability
- potential tier
- career stage
- play style
- archetype
- attributes
- hidden traits
- injury risk
- development speed
- consistency
- locked/unlocked
- generation source
- manual override marker

Player editing/regeneration:
- regenerate all unlocked players
- regenerate players by country
- regenerate players by region
- regenerate annual intake
- add custom player
- edit generated player
- delete player if allowed
- lock player
- unlock player

Locked players:
- must never be changed by automatic regeneration
- may only change through explicit manual edit
- are important for custom stars, story players, and historical anchors

### 4.7 Simulate
Purpose:
Run the simulation at different levels of detail.

Simulation commands:
- simulate next match
- simulate next round
- simulate next tournament
- simulate next week
- simulate full season
- simulate from season X to season Y
- simulate full history from 2000/2001 to 2039/2040

Early development priority:
Allow bulk simulation of many seasons to test realism.

Final usage priority:
Allow careful detailed simulation of the “real” FAX timeline.

End-of-season lifecycle:
At the end of each season:
1. process final rankings/race
2. process player aging
3. process player progression/regression
4. process injuries/recovery
5. process retirement decisions
6. generate new 15-year-old talent intake
7. prepare next season baseline
8. create season archive/snapshot

Retirement:
- players of any age may retire
- older players retire more often
- young players may retire if they fail badly, drop too low, suffer severe injuries, or lose motivation
- retirement probability should depend on age, ranking, decline, injuries, motivation, career success, hidden traits, and role in the sport

### 4.8 Editing the Past and Regeneration
If the user edits something in the past, every later simulated result must be considered stale/invalid.

Example:
If the user edits season 2005/2006:
- seasons before 2005/2006 may remain valid
- season 2005/2006 must be regenerated
- all later seasons must be regenerated

Reason:
A past edit can affect:
- tournament results
- rankings
- entries
- seeds
- injuries
- retirements
- development
- junior intake
- future history

The UI should warn:
"This change affects future simulated history. Regenerate from this point forward?"

The engine should track stale future history explicitly.

## 5. Viewer / MSA Website Mode

### 5.1 Viewer Home
Should show:
- current week
- latest tournament winner
- ranking top 10
- race top 10
- upcoming tournaments
- featured players
- country leaderboard
- recent highlights/headlines

### 5.2 Rankings
Should show:
- official weekly rankings
- race standings
- historical ranking by week
- player ranking charts
- country ranking summaries

### 5.3 Tournaments
Should show:
- calendar
- tournament pages
- qualification draw
- main draw
- results
- match list
- champions history

### 5.4 Players
Should show:
- player profile
- attributes
- career titles
- ranking history
- match history
- rivalries
- season stats
- injuries if appropriate
- career timeline

### 5.5 Countries
Should show:
- country profile
- top players
- titles by country
- talent output
- historical strength
- country momentum/era history if available

### 5.6 History
Should show:
- season archive
- year-end rankings
- all champions
- records
- GOAT-style statistics
- top rivalries
- nation records

## 6. Determinism Rules
Keep the existing project rule:

(world_state_snapshot + config_version + RNG seed + command) => identical result

All random behavior must go through injected deterministic RNG.
No direct ambient randomness.

Seed hierarchy should support at least:
- global
- season
- season_week
- tournament
- draw
- match
- player_generation
- annual_intake
- retirement
- injury
- progression

Manual overrides must be explicit and audited.
Manual overrides must not silently break replayability.

## 7. Historical State and Snapshots
History is a product feature.

The engine must preserve:
- weekly ranking snapshots
- race snapshots
- tournament results
- match results
- player history
- country history
- season archives
- end-of-season summaries
- records and milestones

Long-term goal:
The user should be able to browse any season/week from 2000/2001 to 2039/2040.

## 8. Regeneration Philosophy
The app should support generation, preview, edit, lock, confirm, simulate, and regenerate workflows.

Important workflows:
- Generate world preview
- Edit world parameters
- Regenerate player pool
- Lock important players
- Confirm initial world
- Simulate history
- Edit past world/event/player data
- Mark future history as stale
- Regenerate from that point

Regeneration must respect locked players.

## 9. Comparison to Tennis Manager
The project is partly inspired by Tennis Manager-style logic:
- countries have different talent probabilities
- players have current ability and potential
- players age, improve, decline, and retire
- tours, tournaments, rankings, and seasons evolve over time

But this project is not an academy manager.

Beta_Engine should simulate the whole FAX professional squash world.

Tennis Manager inspiration:
- youth/talent generation
- player progression
- scouting-like country differences
- tournament/ranking career flow

FAX Beta_Engine difference:
- user controls the whole world
- full country/tournament/season editor
- long-term historical simulation
- Admin Mode + Viewer Mode separation
- ability to regenerate history from a selected point

## 10. Implementation Priorities
Current next implementation direction should be:

1. Documentation alignment.
2. Clear Admin/Viewer navigation structure.
3. World editor improvements.
4. Tournament template editor improvements.
5. Season calendar model with Season Week + Year Week.
6. Player generation preview + lock/regenerate system.
7. Initial Player Pool generation for 2000/2001.
8. Annual intake at season end.
9. Retirement logic at season end.
10. Stale-history detection when past data changes.
11. Bulk simulation 2000/2001 → 2039/2040.
12. Viewer Mode pages for browsing generated history.

## 11. Non-Negotiables
- Determinism must not be weakened.
- Editable world content must not be hardcoded in business logic.
- Admin Mode and Viewer Mode must remain conceptually separate.
- History/snapshots are required, not optional.
- Ranking model remains rolling 61 weeks / best 12 unless explicitly changed.
- Match results must be rule-based and deterministic, not AI-decided.
- Locked players must survive regeneration.
- Editing the past must mark future results stale/invalid.
- UI is a client over backend commands, not the owner of simulation logic.
