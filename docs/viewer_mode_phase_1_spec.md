# Viewer Mode Phase 1 Spec

## 1. Goal

Viewer Mode should become the public MSA sports website for the simulated squash world. It is the audience-facing way to browse the current and historical state of the tour, not the place to run the engine.

Viewer Mode should support:

- MSA homepage
- rankings
- tour/calendar/tournaments
- players
- countries
- H2H/rivalries
- statistics
- predictions/odds
- search
- selected Season/Week context

Viewer should feel like:

- an ATP/PSA-style sports website
- Flashscore-style browsing for matches, schedules, and current-week context
- Tennis Explorer-style player/tournament archive browsing
- a sports analytics hub for rankings, form, odds, and records
- NOT an engine/debug/admin screen

Admin Mode remains:

- command center
- simulation control surface
- data management area
- mutation workflow owner
- diagnostics surface
- builder/tools area

The implementation goal for Phase 1 is to define a clean Viewer information architecture before any React, route, API, backend, or CSS changes are made.

## 2. Current Problems

Current repository inspection shows the existing Viewer/Admin split is functional but not yet the final sports-website experience.

Problems to address in future implementation phases:

- Viewer currently has duplicate navigation rows.
- There is top-level Viewer nav and run-scoped Viewer nav, which is confusing.
- Some Viewer top-level pages are thin shells that mostly say “open active run”.
- Viewer currently feels too technical/debug-like.
- Viewer sometimes shares pages/components with Admin.
- Viewer may expose mutating/admin actions in places where it should be read-only.
- Raw/debug payloads should not be primary Viewer UI.
- The word “Engine” should not dominate Viewer branding.
- Viewer needs one clean sports-facing navigation model.

Suspected risky examples discovered during inspection and to be verified/fixed in future implementation:

- Viewer World Tour Finals must not show “Simulate World Tour Finals”. The current Finals page imports and calls a simulation API, so Viewer use of that page needs to be split or made read-only.
- Viewer planned event detail must not show commissioner controls such as wildcard, withdrawal, or late replacement controls. The current planned event detail page imports APIs for those actions, so Viewer use of that page needs a read-only component split.

These notes are not bug fixes in this phase. They are implementation risks to guide the next Viewer refactor.

## 3. Non-Negotiable Global Viewer Rules

Viewer MUST:

- be strictly read-only
- use sports-facing language
- have one clean topbar
- support global Season/Week context
- use selected Season/Week as current world state
- allow browsing/filtering/sorting/searching
- allow opening detail pages
- allow read-only comparison/prediction views
- keep Admin and Viewer route spaces separate

Viewer MUST NOT:

- mutate backend state
- render mutating/admin action buttons
- render admin-only panels
- render raw JSON/debug payloads by default
- rely on CSS `display: none` to hide dangerous controls
- import/render components that include mutating controls unless those controls are removed/split
- show future knowledge beyond selected Season/Week in future phases

Forbidden Viewer action labels/buttons:

- Simulate
- Generate
- Persist
- Apply
- Execute
- Delete
- Edit
- Import
- Rollover
- Rebuild
- Override
- Save changes
- Commit
- Regenerate
- Repair
- Merge
- Overwrite

Clarification:

These words may appear inside explanatory documentation only if not rendered as action buttons or links. Tests should focus on interactive elements and should not fail only because documentation text explains a forbidden word.

## 4. Final Viewer Topbar

Final topbar exactly:

MSA | Rankings | Tour | Players | Countries | H2H | Stats | Predictions | Search | Season/Week selector

Rules:

- MSA has no dropdown.
- MSA links to Viewer homepage.
- Rankings has dropdown.
- Tour has dropdown.
- Players has dropdown.
- Countries has dropdown.
- H2H has dropdown.
- Stats has dropdown.
- Predictions has dropdown.
- Search is a global Viewer search control, not a normal dropdown category.
- Season/Week selector is always visible on the right.
- There must be no second duplicate run navigation row.
- Existing run-scoped Viewer pages should be reachable through the new topbar/context model, not through duplicate nav.

## 5. Final Dropdown Structure

### Rankings

- MSA Rankings
- Race to Finals
- Next Gen Race
- Elo Ranking
- Power Rating
- Form Ranking
- Country Ranking
- No.1 History

### Tour

- Season Hub
- Season Calendar
- Current Week
- All Tournaments
- Match Center
- Tournament Categories
- Past Champions

### Players

- Players Hub
- All Players
- Active Players
- Prospects / Next Gen
- Retired Players
- Compare Players

### Countries

- Countries Hub
- Country Ranking
- All Countries
- Hosting Nations
- Talent Pipeline
- Country Records

### H2H

- H2H Explorer
- Rivalry Rankings
- Most Played Matchups
- Finals Rivalries
- Player Comparison
- Predict Matchup

### Stats

- Records
- Title Leaders
- Weeks at No.1
- Streaks
- Biggest Upsets
- Best Seasons
- Player Stats
- Tournament Stats
- Country Stats
- Awards
- Hall of Fame
- Era Rankings

### Predictions

- Match Predictor
- Match Odds
- Tournament Odds
- Finals Qualification
- Season-End No.1
- Upset Watch
- Futures Markets

These are product/navigation targets. If backend data is not ready, implementation phases may create read-only scaffold pages, but this spec must still define the final intended structure.

## 6. Shared Route Shortcuts

Shared shortcuts:

- Rankings → Country Ranking and Countries → Country Ranking must lead to the same Country Ranking page.
- Players → Compare Players and H2H → Player Comparison must lead to the same Player Comparison page.
- H2H → Predict Matchup and Predictions → Match Predictor must lead to the same Match Predictor page.

These are not duplicate features. They are multiple natural navigation paths to the same tool. The implementation should avoid duplicate components and duplicate state for these shortcuts.

## 7. Global Viewer Current Context

The Viewer current context is the selected Season + Week that defines the Viewer world state.

Compact display:

`Season 2004/05 · W10`

Expanded hover/click display:

- Season: 2004/05
- Season Week: 10 / 61
- Calendar Year: 2005
- Year Week: 3
- Status: selected viewer context

Rules:

- The entire Viewer uses selected Season + Week as current world state.
- Future phases should ensure Viewer does not reveal future knowledge beyond selected Season/Week.
- The selector must support changing season and week.
- The selector may initially use local state if backend support is incomplete.
- Selected context should influence page headings and future data queries.
- It should be accessible by hover and click because hover does not work on mobile.

Past/current/future knowledge model:

- Weeks before selected week: results, champions, completed draws, stats are visible.
- Selected week: current tournaments, current matches, draws, entries, odds/predictions are visible.
- Future weeks: only known information is visible, such as calendar, entries if known, draw if drawn, predictions if available, but no results.

## 8. Jump to Week

Jump to Week appears in:

- Season Calendar
- Season Hub event cards
- Current Week / tournament cards when relevant
- event cards in Tour pages

Behavior:

- Button/links labeled `Jump to W{week}`
- It updates global Viewer selected Season/Week context.
- It must not mutate backend state.
- It must not merely scroll.
- It changes `selectedSeason` and `selectedWeek` in Viewer context/store.
- After jump, Viewer topbar selector reflects the new week.

Example:

Clicking `Jump to W24` on a Team Championship card sets:

- Season = same season
- Season Week = 24

## 9. MSA Homepage

MSA homepage is a sports landing dashboard for the selected Season/Week.

It must include the sections below.

### 9.1 Featured Tournament Hero

Full-width top hero for the biggest/current most important tournament of selected week.

Show where available:

- tournament name
- category
- country/city if available
- season/week
- status
- top seed
- favorite
- biggest match
- defending champion if available
- champion if completed

Navigation links only:

- Tournament Detail
- Draw
- Matches
- Predictions

No mutating actions.

### 9.2 Other Tournaments This Week

Smaller cards ordered/grouped by category.

Each card should show:

- tournament
- category
- country
- week
- status
- winner if completed
- quick links to detail/draw/matches/predictions if available

### 9.3 Top 10 Rankings + Race to Finals

Two side-by-side panels:

- MSA Rankings Top 10
- Race to Finals Top 10

Show:

- rank
- player
- country
- points/race points
- small change indicator if available

### 9.4 Featured Matches

Sports-facing cards:

- Match of the Week
- Closest Odds
- Rivalry Match
- Upset Potential

### 9.5 Predictions & Upset Watch

Cards:

- tournament favorites
- season-end No.1 watch
- Finals qualification watch
- biggest upset alerts

### 9.6 Storylines

Short sports-style storyline cards.

Examples:

- “Paris can reclaim No.1 this week.”
- “Macky needs a semifinal to protect his Race lead.”
- “Francica has five players in the Top 20.”
- “Silva enters his first Diamond as a top seed.”

No raw/debug text.

## 10. Rankings Pages

### 10.1 MSA Rankings

Official weekly ranking for selected Season/Week.

Main table columns:

- Rank
- Player
- Country
- Age
- Points
- Points change vs previous week
- Tournaments counted / tournaments played in last 61 weeks

Important:

- Do NOT show Previous Week Rank as a main column.
- Rank movement can be a small visual indicator if needed, but previous week rank is not a primary column.

Expanded future view:

- Dropping
- Next Best
- best-count breakdown
- tournament points breakdown

Filters:

- Season
- Week
- Top 100
- 101–200
- All
- custom from/to range
- Country
- Age
- Active/retired/all
- Sort by columns

Concept:

- Official ranking uses 61-week window.
- Count display should be: “counted tournaments / tournaments played in last 61 weeks”.

### 10.2 Race to Finals

Season race.

Rules:

- Best 11 tournaments of current season count.
- World Championship winner and Diamond winners get auto-qualified marker.
- Full Finals qualification status becomes more prominent near cutoff week.

Columns/scaffold:

- Rank
- Player
- Country
- Age
- Race points
- Points change
- Events counted
- Next max points possible
- Qualification marker

Do not show “titles this season” as main column.

Qualification marker states:

- Auto-qualified
- In position
- Bubble
- Outside
- Unknown/not calculated

### 10.3 Next Gen Race

Default age concept:

- U23

Rules:

- Same basic idea as Race to Finals.
- A player who plays World Tour Finals cannot play Next Gen Finals.
- Next Gen does not grant World Championship/Diamond entry by itself unless future rules say so.

Columns similar to Race:

- Rank
- Player
- Country
- Age
- Next Gen race points
- Points change
- Events counted
- Next max points possible
- Eligibility marker

### 10.4 Elo Ranking

Scaffold now, details later.

Initial concept:

- Rank
- Player
- Country
- Elo
- Elo change
- Peak Elo
- Recent Elo
- Matches counted

Filters:

- Season/Week
- Country
- Age
- active only
- minimum matches

### 10.5 Power Rating

Viewer-facing name for OVR.

Do not call it OVR in primary Viewer UI. Use:

Power Rating

Main view:

- Rank
- Player
- Country
- Power Rating

Expanded future view:

- Technical
- Movement
- Tactical
- Mental
- Physical
- Creativity
- Form modifier

### 10.6 Form Ranking

Weighted recent form.

Future formula concept may include:

- recent wins
- opponent strength
- score dominance
- upset value
- loss severity
- tournament importance
- recency weighting

Initial columns/scaffold:

- Rank
- Player
- Country
- Form score
- Last 5
- Last 10
- Best recent win
- Momentum

### 10.7 Country Ranking

Shared page with Countries section.

Concept:

- rank countries by player ranking/race/points strength for selected Season/Week.

Support selected range:

- Top 10
- Top 50
- Top 100
- Top 200
- custom range

Columns/scaffold:

- Rank
- Country
- Total points
- Players in selected range
- Top player
- Top 10 players
- Top 50 players
- Top 100 players
- Average points
- Season titles
- Average Elo top X if available

### 10.8 No.1 History

Historical No.1 archive.

Columns/scaffold:

- Player
- Country
- Total weeks No.1
- Longest streak
- First week No.1
- Last week No.1
- Year-end No.1 count

## 11. Tour Pages

### 11.1 Season Hub

Main page for one season.

Show:

- season overview
- selected current week
- major events
- champions so far
- ranking leader
- race leader
- top storylines
- featured matches
- upsets
- year-end No.1 prediction if available

Major event cards:

- World Championship
- World Tour Finals
- Team Championship if present that season

Important:

World Championship, World Tour Finals, and Team Championship should not require separate isolated topbar items. They should be highlighted in Season Hub and link to normal tournament/event detail pages.

### 11.2 Season Calendar

Week-by-week calendar.

Show:

- Week 1 to Week 61
- tournaments in each week
- category
- country
- status
- winner if completed
- draw/entry/results links if available

Each week/event card:

- Jump to W{week}

Filters:

- category
- country
- status
- week range

### 11.3 Current Week

Detailed selected-week page.

Show:

- all tournaments in selected week
- matches in selected week
- featured matches
- upset alerts
- probability cards if available
- status of each tournament

### 11.4 All Tournaments

Filterable tournament database.

Filters:

- season
- category
- country
- region
- status
- week

Fields:

- Tournament
- Category
- Season
- Week
- Country
- Status
- Winner if completed
- Prize money if available
- Points if available

### 11.5 Match Center

Keep under Tour, not H2H.

Purpose:

Database of matches across the tour.

Filters:

- season
- week
- player
- country
- tournament
- round
- finished/upcoming
- category
- upset probability if available

Fields:

- Match
- Tournament
- Round
- Score or scheduled time/status
- Win probability if available
- Odds if available
- Status

### 11.6 Tournament Categories

Overview of tour category structure.

Categories:

- World Championship
- Diamond
- Emerald
- Platinum
- Gold
- Silver
- Bronze
- Elite
- Challenger
- Development

Show where available:

- points
- draw size
- prize money
- number of events
- notable events

### 11.7 Past Champions

Archive of tournament champions.

Filters:

- season
- tournament
- category
- country
- player

Columns/scaffold:

- Season
- Tournament
- Category
- Champion
- Finalist
- Score
- Country
- Week

Important:

Past champions must also appear in:

- completed tournaments in Season Calendar
- tournament detail pages
- player profiles
- Season Hub champions so far

## 12. Players Pages

### 12.1 Players Hub

Not just a database. It is a player news/spotlight hub.

Sections:

- Player of the Week / Featured Player
- Recent Winners
- Breakthrough Players
- Upset Makers
- Current Stars / Favorites
- link/button to All Players

No editing.

### 12.2 All Players

Filterable player database.

Filters:

- country
- age
- status
- ranking range
- race range
- Elo
- Power Rating
- form
- active/retired/prospect
- titles
- generation

Fields/scaffold:

- Player
- Country
- Age
- Status
- Ranking
- Race
- Elo
- Power Rating
- Form
- Titles

### 12.3 Active Players

Players active in selected Season/Week.

### 12.4 Prospects / Next Gen

Young players.

Default concept:

- U23

Potential fields:

- player
- country
- age
- Next Gen Race rank
- Power Rating
- Elo
- potential/talent marker if available

### 12.5 Retired Players

Historical player archive.

### 12.6 Compare Players

Shared route with H2H → Player Comparison.

Purpose:

Compare career/profile, not only direct H2H.

Compare:

- rankings
- titles
- finals
- World Championship titles
- Diamond titles
- weeks No.1
- Elo
- Power Rating
- form
- win rate
- best season
- H2H summary
- age milestones

Player timelines:

- Do not make Player Timelines a topbar dropdown item in Phase 1.
- Timeline should be a future tab inside each player profile.

## 13. Countries Pages

### 13.1 Countries Hub

World/national squash overview.

Sections:

- world squash stats
- top countries this week
- countries rising
- countries falling
- most titles this season
- most players in Top 100
- recent Team Championship winners
- best young nations
- major hosting nations

### 13.2 Country Ranking

Shared route with Rankings → Country Ranking.

Concept:

- rank countries by selected range and selected Season/Week

Metrics:

- total points for selected ranking range
- players in Top 10 / Top 50 / Top 100 / custom range
- top player
- average points
- season titles
- average Elo top X if available

### 13.3 All Countries

Filterable country database.

Filters:

- region
- population
- number of players
- top player ranking
- top 100 players
- titles
- hosted tournaments
- squash strength
- talent pipeline

Fields/scaffold:

- Country
- Region
- Population
- Players
- Top player
- Best ranking
- Titles
- Hosted tournaments
- Squash strength

### 13.4 Hosting Nations

Countries by hosting role.

Show:

- events hosted
- major events hosted
- categories hosted
- recent hosted tournaments

### 13.5 Talent Pipeline

Countries by young player strength.

Show:

- U23 players
- prospects
- Next Gen Race representation
- future strength indicators if available

### 13.6 Country Records

National records.

Examples:

- most titles by country
- most No.1 weeks by country
- most Top 100 players
- best Team Championship records

### 13.7 Future Country Detail

Future country profile should include:

- Overview
- Top Players
- All Players
- Ranking History
- Titles
- Hosted Tournaments
- Team Championship History
- Talent Pipeline
- Records

## 14. H2H Pages

### 14.1 H2H Explorer

Select Player A + Player B.

Show:

- overall H2H
- by season
- by tournament category
- by round
- recent matches
- biggest wins
- biggest upsets
- average score
- Elo/ranking at time if available

### 14.2 Rivalry Rankings

Ranking of rivalries by selected period.

Periods/filters:

- all-time
- current season
- last 3 seasons
- selected season/week range
- era
- minimum matches
- only finals
- only World Tour
- majors/Diamonds
- country
- generation
- active rivalries only

Rivalry score concept:

- number of matches
- balance of H2H
- importance of matches
- finals count
- five-set matches
- upsets
- No.1 stakes
- top-10 stakes
- recent relevance

### 14.3 Most Played Matchups

Count-based matchup database.

Fields:

- Player A
- Player B
- Matches
- H2H
- Finals
- Last match
- Biggest match

Difference from Rivalry Rankings:

- Most Played Matchups = quantity
- Rivalry Rankings = quality/drama/importance score

### 14.4 Finals Rivalries

Finals-specific rivalry page.

Show:

- most common finals matchups
- finals H2H
- World Championship finals
- Diamond finals
- World Tour Finals matches
- most dramatic finals if available

### 14.5 Player Comparison

Shared route with Players → Compare Players.

### 14.6 Predict Matchup

Shortcut to Predictions → Match Predictor.

## 15. Stats Pages

Stats is a broad statistical library.

Do not over-specify every metric now. Create scaffold concepts for:

### 15.1 Records

General record book:

- youngest winner
- oldest winner
- longest match
- biggest comeback
- most titles in a season
- most finals in a row

### 15.2 Title Leaders

- total titles
- World Championship titles
- Diamond titles
- World Tour titles
- category titles
- titles by country
- titles by era

### 15.3 Weeks at No.1

- total weeks No.1
- longest streak
- year-end No.1
- returns to No.1
- youngest No.1

### 15.4 Streaks

- win streak
- finals streak
- semifinal streak
- top 10 streak
- top 100 streak
- unbeaten run

### 15.5 Biggest Upsets

- by ranking difference
- by Elo difference
- by win probability
- by tournament importance

### 15.6 Best Seasons

- best individual seasons
- most dominant seasons
- best Race seasons
- most titles in one season
- best comeback season

### 15.7 Player Stats

- win rate
- matches played
- finals reached
- top 10 wins
- clutch score
- five-set record
- form score

### 15.8 Tournament Stats

- strongest fields
- most upsets
- most frequent champions
- best finals
- most prestigious events

### 15.9 Country Stats

- titles by country
- Top 100 players by country
- No.1 weeks by country
- country dominance eras
- Team Championship history

### 15.10 Awards

- Player of the Year
- Most Improved
- Rookie of the Year
- Comeback of the Year
- Match of the Year
- Upset of the Year

### 15.11 Hall of Fame

- legends
- active candidates
- historical generations
- GOAT tier list concept

### 15.12 Era Rankings

- best players by era
- best peaks
- best careers
- dominance
- longevity

## 16. Predictions Pages

Predictions is read-only. No simulations from Viewer.

### 16.1 Match Predictor

Inputs:

- Player A
- Player B
- Season
- Week
- Tournament / neutral context
- Round

Outputs/scaffold:

- win probability
- fair odds
- bookmaker odds with margin
- expected score
- upset probability
- key factors
- Elo difference
- Power Rating difference
- form comparison
- H2H influence

Special case:

If same player is selected twice, future concept is Player Version Comparison, not a normal match.

Example:

Paris 2004 W10 vs Paris 2008 W30

### 16.2 Match Odds

Current/selected week match odds.

Filters:

- season
- week
- tournament
- round
- player
- upset potential

### 16.3 Tournament Odds

For tournament:

- win tournament
- reach final
- reach semifinal
- reach quarterfinal

### 16.4 Finals Qualification

Chances for:

- World Tour Finals
- Next Gen Finals

### 16.5 Season-End No.1

Probability of finishing season as No.1.

### 16.6 Upset Watch

Show vulnerable favorites and high-upset-potential matches.

### 16.7 Futures Markets

Long-term predictions:

- World Champion
- Diamond winner
- most titles this season
- country with most titles
- player to enter Top 10
- breakthrough player

## 17. Search

Global Viewer search.

Search across:

- players
- tournaments
- countries
- matches
- seasons

Initial implementation may be a frontend shell if backend search does not exist.

Expected UX:

- search input in topbar
- results grouped by type
- clicking a result opens detail page
- no mutation

## 18. Context-Aware Admin/Viewer Switcher

When user clicks Admin/Engine from Viewer, send them to closest Admin equivalent. When user clicks Viewer/MSA from Admin, send them to closest Viewer equivalent.

Fallback:

- `/admin`
- `/viewer`

Mappings:

- `/viewer` → `/admin`
- `/admin` → `/viewer`
- `/viewer/players` → `/admin/players`
- `/admin/players` → `/viewer/players`
- `/viewer/countries` → `/admin/world/countries`
- `/admin/world/countries` → `/viewer/countries`
- `/viewer/tour` → `/admin/tour-seasons`
- `/admin/tour-seasons` → `/viewer/tour`
- `/viewer/runs/:runId/calendar` → `/admin/runs/:runId/calendar`
- `/admin/runs/:runId/calendar` → `/viewer/runs/:runId/calendar`
- `/viewer/runs/:runId/players` → `/admin/runs/:runId/players`
- `/admin/runs/:runId/players` → `/viewer/runs/:runId/players`
- unknown Viewer route → `/admin`
- unknown Admin route → `/viewer`

## 19. Proposed Viewer Route Map

Status type values are limited to:

- `existing_reused`
- `existing_needs_cleanup`
- `new_placeholder`
- `new_data_page`
- `shared_shortcut`
- `future_detail_page`

| Route | Page name | Topbar category | Status type | Notes |
| --- | --- | --- | --- | --- |
| `/viewer` | MSA Homepage | MSA | existing_needs_cleanup | Existing Viewer home exists, but should become sports landing dashboard rather than active-run shell. |
| `/viewer/rankings` | MSA Rankings | Rankings | existing_needs_cleanup | Existing run ranking pages can inform data needs; final page should use selected context. |
| `/viewer/rankings/race` | Race to Finals | Rankings | new_data_page | Race rules and qualification markers need read-only presentation. |
| `/viewer/rankings/next-gen` | Next Gen Race | Rankings | new_placeholder | U23 concept until backend data is ready. |
| `/viewer/rankings/elo` | Elo Ranking | Rankings | new_placeholder | Scaffold until Elo formulas/APIs exist. |
| `/viewer/rankings/power` | Power Rating | Rankings | new_placeholder | Viewer-facing OVR presentation; do not call primary label OVR. |
| `/viewer/rankings/form` | Form Ranking | Rankings | new_placeholder | Scaffold until form score is specified. |
| `/viewer/countries/ranking` | Country Ranking | Rankings / Countries | shared_shortcut | Shared destination from Rankings and Countries. |
| `/viewer/rankings/no1-history` | No.1 History | Rankings | new_data_page | Historical archive; may require history/read model support. |
| `/viewer/tour` | Season Hub | Tour | existing_needs_cleanup | Existing tour/runs pages can inform data but need sports hub layout. |
| `/viewer/tour/calendar` | Season Calendar | Tour | existing_needs_cleanup | Existing calendar route/data can be reused after removing duplicate run nav. |
| `/viewer/tour/current-week` | Current Week | Tour | new_data_page | Context-driven page for selected week. |
| `/viewer/tour/tournaments` | All Tournaments | Tour | existing_needs_cleanup | Existing tournament surfaces need database-style filters. |
| `/viewer/tour/matches` | Match Center | Tour | new_data_page | Match database belongs under Tour, not H2H. |
| `/viewer/tour/categories` | Tournament Categories | Tour | new_placeholder | Product explainer/scaffold can be read-only. |
| `/viewer/tour/champions` | Past Champions | Tour | new_data_page | Champion archive; also surfaced in calendar/player/tournament pages. |
| `/viewer/players` | Players Hub | Players | existing_needs_cleanup | Existing top-level players page should become player spotlight hub. |
| `/viewer/players/all` | All Players | Players | existing_needs_cleanup | Existing run player list can inform fields. |
| `/viewer/players/active` | Active Players | Players | new_data_page | Selected-context active player list. |
| `/viewer/players/next-gen` | Prospects / Next Gen | Players | new_placeholder | U23/prospect scaffold. |
| `/viewer/players/retired` | Retired Players | Players | new_placeholder | Historical archive scaffold. |
| `/viewer/players/compare` | Compare Players | Players / H2H | shared_shortcut | Shared destination from Players and H2H. |
| `/viewer/countries` | Countries Hub | Countries | existing_needs_cleanup | Existing countries/world data needs sports-facing hub. |
| `/viewer/countries/all` | All Countries | Countries | existing_needs_cleanup | Existing country data can inform database page. |
| `/viewer/countries/hosting` | Hosting Nations | Countries | new_data_page | Hosting/tournament relationship page. |
| `/viewer/countries/talent-pipeline` | Talent Pipeline | Countries | new_placeholder | Prospect strength scaffold. |
| `/viewer/countries/records` | Country Records | Countries | new_placeholder | National records scaffold. |
| `/viewer/h2h` | H2H Explorer | H2H | new_data_page | Direct player matchup explorer. |
| `/viewer/h2h/rivalries` | Rivalry Rankings | H2H | new_placeholder | Rivalry score formula later. |
| `/viewer/h2h/most-played` | Most Played Matchups | H2H | new_data_page | Count-based matchups. |
| `/viewer/h2h/finals-rivalries` | Finals Rivalries | H2H | new_data_page | Finals-specific rivalry view. |
| `/viewer/predictions/match-predictor` | Match Predictor | H2H / Predictions | shared_shortcut | Shared destination from H2H and Predictions. |
| `/viewer/stats` | Records | Stats | new_placeholder | General record book landing page. |
| `/viewer/stats/title-leaders` | Title Leaders | Stats | new_data_page | Title leader archive. |
| `/viewer/stats/no1-weeks` | Weeks at No.1 | Stats | new_data_page | No.1 week stats. |
| `/viewer/stats/streaks` | Streaks | Stats | new_placeholder | Streak library scaffold. |
| `/viewer/stats/upsets` | Biggest Upsets | Stats | new_placeholder | Upset metrics depend on rankings/Elo/odds. |
| `/viewer/stats/best-seasons` | Best Seasons | Stats | new_placeholder | Season scoring formula later. |
| `/viewer/stats/player-stats` | Player Stats | Stats | new_data_page | Player statistical table. |
| `/viewer/stats/tournament-stats` | Tournament Stats | Stats | new_data_page | Tournament statistical table. |
| `/viewer/stats/country-stats` | Country Stats | Stats | new_data_page | Country statistical table. |
| `/viewer/stats/awards` | Awards | Stats | new_placeholder | Awards concept scaffold. |
| `/viewer/stats/hall-of-fame` | Hall of Fame | Stats | new_placeholder | Hall of fame concept scaffold. |
| `/viewer/stats/era-rankings` | Era Rankings | Stats | new_placeholder | Era ranking formula later. |
| `/viewer/predictions` | Match Predictor | Predictions | shared_shortcut | Category landing may redirect/render match predictor. |
| `/viewer/predictions/match-odds` | Match Odds | Predictions | new_data_page | Selected-week odds table. |
| `/viewer/predictions/tournament-odds` | Tournament Odds | Predictions | new_data_page | Tournament futures/progression odds. |
| `/viewer/predictions/finals-qualification` | Finals Qualification | Predictions | new_data_page | World Tour Finals and Next Gen Finals chances. |
| `/viewer/predictions/season-end-no1` | Season-End No.1 | Predictions | new_placeholder | Probability model later. |
| `/viewer/predictions/upset-watch` | Upset Watch | Predictions | new_data_page | Selected-week upset alerts. |
| `/viewer/predictions/futures` | Futures Markets | Predictions | new_placeholder | Long-term predictions scaffold. |
| `/viewer/search` | Search | Search | new_placeholder | Global grouped search shell if backend search is not ready. |
| `/viewer/players/:playerId` | Player Detail | Future detail | future_detail_page | Future tabs include overview, results, ranking history, timelines, H2H. |
| `/viewer/countries/:countryCode` | Country Detail | Future detail | future_detail_page | Future tabs specified in section 13.7. |
| `/viewer/tournaments/:eventId` | Tournament Detail | Future detail | future_detail_page | Read-only event detail/draw/matches/predictions. |
| `/viewer/matches/:matchId` | Match Detail | Future detail | future_detail_page | Read-only score, context, odds, factors. |
| `/viewer/seasons/:seasonLabel` | Season Detail | Future detail | future_detail_page | Season archive page. |
| `/viewer/seasons/:seasonLabel/weeks/:week` | Season Week Detail | Future detail | future_detail_page | Week archive/context page. |
| `/viewer/h2h/:playerAId/:playerBId` | H2H Detail | Future detail | future_detail_page | Deep link to player matchup. |

## 20. Component Plan

Reusable components proposed for future implementation:

- `ViewerTopNav`: one primary Viewer topbar containing MSA, dropdown categories, Search, and Season/Week selector.
- `ViewerDropdownNav`: reusable dropdown menu primitive for Rankings, Tour, Players, Countries, H2H, Stats, and Predictions.
- `ViewerCurrentContextSelector`: compact and expanded Season/Week selector with hover and click behavior.
- `ViewerContextProvider` or equivalent local state/store: owns selected season/week and exposes context update actions.
- `ViewerModeSwitchLink` helper: maps Admin/Viewer equivalents using the route mapping in this spec.
- `ViewerPlaceholderPage`: sports-facing scaffold for pages whose backend data is not ready.
- `ViewerSectionHeader`: consistent sports-style section heading/subheading.
- `ViewerCardGrid`: responsive grid for tournament/storyline/stat cards.
- `ViewerHeroTournamentCard`: homepage hero card for featured tournament.
- `ViewerTournamentCard`: reusable read-only event card.
- `ViewerTopTenPanel`: compact ranking/race Top 10 panel.
- `ViewerStorylineCard`: sports-style narrative card.
- `ViewerReadOnlyEventDetail`: tournament/event detail without commissioner controls.
- `ViewerJumpToWeekButton`: local/context-only control that updates selected Viewer context.
- `ViewerDataTableShell`: consistent table wrapper with sorting/filter affordances.
- `ViewerFilterBar`: reusable filter layout.
- `ViewerSearchBox`: global Viewer search input/results entry point.

Important:

Components must be read-only unless explicitly pure local UI state. Local UI state includes dropdown open/closed state, selected filters before query execution, selected Season/Week context, and search input text. Local state must not persist, generate, simulate, apply, delete, import, rebuild, override, or execute engine commands.

## 21. Read-Only Safety Split Plan

If existing components are shared between Admin and Viewer and contain mutating controls, they must be split.

Examples:

- Planned event detail with wildcard/withdrawal/late replacement controls must not be rendered in Viewer.
- World Tour Finals viewer page must not render simulation button.
- Viewer must get read-only components such as `ViewerReadOnlyEventDetail`.
- Admin can keep mutating panels separately.

Implementation rule:

- Do not hide dangerous controls with CSS only.
- Do not pass a simple prop and trust that forever if the component is structurally admin-focused.
- Prefer separate read-only Viewer component and Admin control component.
- Viewer components may call read-only APIs only.
- If a page needs both Admin and Viewer variants, route them to separate components even when they share presentational subcomponents.

## 22. Implementation Checklist

Allowed statuses: `not_started`, `in_progress`, `done`, `blocked`, `deferred`.

| ID | Area | Task | Status | Notes | Test needed |
| --- | --- | --- | --- | --- | --- |
| A1 | Viewer shell/navigation | remove duplicate Viewer run nav | done | Current layout has top-level nav plus run-scoped nav. | Viewer one nav test |
| A2 | Viewer shell/navigation | create one Viewer topbar | done | Use exact topbar from section 4. | Topbar render test |
| A3 | Viewer shell/navigation | add dropdowns | done | Dropdown items must match section 5. | Dropdown items test |
| A4 | Viewer shell/navigation | keep MSA as no-dropdown homepage link | done | MSA links to `/viewer`. | MSA link test |
| A5 | Viewer shell/navigation | sports-facing Viewer branding | done | Reduce Engine/debug language in Viewer. | Copy/smoke test |
| B1 | Dropdown routing | Rankings routes | done | Implement rankings route group. | Route tests |
| B2 | Dropdown routing | Tour routes | done | Implement tour route group. | Route tests |
| B3 | Dropdown routing | Players routes | done | Implement players route group. | Route tests |
| B4 | Dropdown routing | Countries routes | done | Implement countries route group. | Route tests |
| B5 | Dropdown routing | H2H routes | done | Implement H2H route group. | Route tests |
| B6 | Dropdown routing | Stats routes | done | Implement stats route group. | Route tests |
| B7 | Dropdown routing | Predictions routes | done | Implement predictions route group. | Route tests |
| B8 | Dropdown routing | shared shortcut routes | done | Country Ranking, Compare Players, Match Predictor. | Shared shortcut route tests |
| C1 | Season/week context selector | compact selector | done | Display `Season 2004/05 · W10`. | Selector render test |
| C2 | Season/week context selector | expanded hover/click panel | done | Must support click for mobile. | Expansion test |
| C3 | Season/week context selector | local/global Viewer context state | done | Local state acceptable initially. | Context state test |
| C4 | Season/week context selector | selected context reflected in page headings | done | Page headings should include selected context where useful. | Heading test |
| C5 | Season/week context selector | future no-future-knowledge rules documented | not_started | Rules documented here; enforcement later. | Future backend/data tests later |
| D1 | Jump to Week | add concept to calendar cards | in_progress | Cards show `Jump to W{week}`. | Calendar card test |
| D2 | Jump to Week | update Viewer context on click | done | Updates selected season/week locally. | Jump click test |
| D3 | Jump to Week | no backend mutation | done | No POST/PUT/PATCH/DELETE. | API call negative test |
| D4 | Jump to Week | tests for local context update | done | Verify selector changes. | Context update test |
| E1 | MSA homepage | Featured Tournament Hero | done | Full-width hero for biggest/current event. | Homepage section test |
| E2 | MSA homepage | Other Tournaments This Week | done | Group/order cards by category. | Homepage section test |
| E3 | MSA homepage | Top 10 Rankings panel | done | Side-by-side rankings panel. | Homepage section test |
| E4 | MSA homepage | Race to Finals Top 10 panel | done | Side-by-side race panel. | Homepage section test |
| E5 | MSA homepage | Featured Matches | done | Match of Week, Closest Odds, Rivalry, Upset Potential. | Homepage section test |
| E6 | MSA homepage | Predictions & Upset Watch | done | Read-only cards only. | Homepage section test |
| E7 | MSA homepage | Storylines | done | Sports-style narrative cards. | Homepage section test |
| F1 | Rankings scaffolds | MSA Rankings | done | Official weekly ranking page. | Page smoke test |
| F2 | Rankings scaffolds | Race to Finals | done | Best 11/auto qualification markers. | Page smoke test |
| F3 | Rankings scaffolds | Next Gen Race | done | U23 default concept. | Page smoke test |
| F4 | Rankings scaffolds | Elo Ranking | done | Scaffold until formula/API exists. | Page smoke test |
| F5 | Rankings scaffolds | Power Rating | done | Viewer-facing OVR name. | Copy test |
| F6 | Rankings scaffolds | Form Ranking | done | Weighted recent form scaffold. | Page smoke test |
| F7 | Rankings scaffolds | Country Ranking shared page | done | Shared with Countries. | Shared route test |
| F8 | Rankings scaffolds | No.1 History | done | Historical No.1 archive. | Page smoke test |
| G1 | Tour scaffolds | Season Hub | done | Main season page. | Page smoke test |
| G2 | Tour scaffolds | Season Calendar | done | `/viewer/tour/calendar` scaffold is done; Phase 1B reconfirmed run-scoped `/viewer/runs/:runId/calendar` preserves the existing real read-only calendar. | Page smoke test |
| G3 | Tour scaffolds | Current Week | done | Selected-week page. | Page smoke test |
| G4 | Tour scaffolds | All Tournaments | done | Filterable tournament database. | Page smoke test |
| G5 | Tour scaffolds | Match Center | done | Match database under Tour. | Page smoke test |
| G6 | Tour scaffolds | Tournament Categories | done | Category explainer/scaffold. | Page smoke test |
| G7 | Tour scaffolds | Past Champions | done | Champion archive. | Page smoke test |
| H1 | Players scaffolds | Players Hub | done | Spotlight/news hub. | Page smoke test |
| H2 | Players scaffolds | All Players | done | Filterable player database. | Page smoke test |
| H3 | Players scaffolds | Active Players | done | Active in selected context. | Page smoke test |
| H4 | Players scaffolds | Prospects / Next Gen | done | Young players/U23. | Page smoke test |
| H5 | Players scaffolds | Retired Players | done | Historical player archive. | Page smoke test |
| H6 | Players scaffolds | Compare Players | done | Career/profile comparison. | Shared route test |
| I1 | Countries scaffolds | Countries Hub | done | World/national overview. | Page smoke test |
| I2 | Countries scaffolds | Country Ranking shared page | done | Shared ranking page. | Shared route test |
| I3 | Countries scaffolds | All Countries | done | Filterable country database. | Page smoke test |
| I4 | Countries scaffolds | Hosting Nations | done | Hosting role page. | Page smoke test |
| I5 | Countries scaffolds | Talent Pipeline | done | Young country strength. | Page smoke test |
| I6 | Countries scaffolds | Country Records | done | National records. | Page smoke test |
| J1 | H2H scaffolds | H2H Explorer | done | Select Player A/B. | Page smoke test |
| J2 | H2H scaffolds | Rivalry Rankings | done | Rivalry score later. | Page smoke test |
| J3 | H2H scaffolds | Most Played Matchups | done | Count-based matchups. | Page smoke test |
| J4 | H2H scaffolds | Finals Rivalries | done | Finals-specific page. | Page smoke test |
| J5 | H2H scaffolds | Player Comparison shared page | done | Same route as Players compare. | Shared route test |
| J6 | H2H scaffolds | Predict Matchup shared shortcut | done | Same route as Match Predictor. | Shared route test |
| K1 | Stats scaffolds | Records | done | General record book. | Page smoke test |
| K2 | Stats scaffolds | Title Leaders | done | Title leader pages. | Page smoke test |
| K3 | Stats scaffolds | Weeks at No.1 | done | No.1 weeks stats. | Page smoke test |
| K4 | Stats scaffolds | Streaks | done | Streak library. | Page smoke test |
| K5 | Stats scaffolds | Biggest Upsets | done | Upset library. | Page smoke test |
| K6 | Stats scaffolds | Best Seasons | done | Season rankings. | Page smoke test |
| K7 | Stats scaffolds | Player Stats | done | Player stats table. | Page smoke test |
| K8 | Stats scaffolds | Tournament Stats | done | Tournament stats table. | Page smoke test |
| K9 | Stats scaffolds | Country Stats | done | Country stats table. | Page smoke test |
| K10 | Stats scaffolds | Awards | done | Awards scaffold. | Page smoke test |
| K11 | Stats scaffolds | Hall of Fame | done | Hall of Fame scaffold. | Page smoke test |
| K12 | Stats scaffolds | Era Rankings | done | Era ranking scaffold. | Page smoke test |
| L1 | Predictions scaffolds | Match Predictor | done | Read-only predictor. | Page smoke/no mutation test |
| L2 | Predictions scaffolds | Match Odds | done | Selected-week odds. | Page smoke test |
| L3 | Predictions scaffolds | Tournament Odds | done | Tournament progression odds. | Page smoke test |
| L4 | Predictions scaffolds | Finals Qualification | done | Finals chances. | Page smoke test |
| L5 | Predictions scaffolds | Season-End No.1 | done | Season-end probability. | Page smoke test |
| L6 | Predictions scaffolds | Upset Watch | done | Upset alerts. | Page smoke test |
| L7 | Predictions scaffolds | Futures Markets | done | Long-term predictions. | Page smoke test |
| M1 | Search shell | topbar search UI | done | Search control in topbar. | Search render test |
| M2 | Search shell | search page | done | `/viewer/search`. | Route/page test |
| M3 | Search shell | grouped result concept | deferred | Group by players/tournaments/countries/matches/seasons. | Search result test |
| M4 | Search shell | detail navigation concept | deferred | Result opens detail page. | Navigation test |
| N1 | Read-only safety | remove Viewer simulate buttons | done | Especially World Tour Finals. | Forbidden actions test |
| N2 | Read-only safety | remove Viewer commissioner controls | done | Wildcard/withdrawal/late replacement. | Forbidden actions test |
| N3 | Read-only safety | hide raw/debug payloads from primary UI | done | Use sports-facing summaries by default. | Copy/UI test |
| N4 | Read-only safety | split shared mutating components | done | Structural split preferred over prop/CSS. | Component/import test |
| N5 | Read-only safety | tests for forbidden Viewer actions | done | Phase 1B expanded checks to top-level Viewer shell buttons/links and preserved run-scoped Viewer pages. | Forbidden actions test |
| O1 | Context-aware mode switcher | Viewer to Admin equivalents | done | Mapping in section 18. | Switcher route test |
| O2 | Context-aware mode switcher | Admin to Viewer equivalents | done | Mapping in section 18. | Switcher route test |
| O3 | Context-aware mode switcher | fallback behavior | done | Unknown Viewer → `/admin`; unknown Admin → `/viewer`. | Fallback test |
| O4 | Context-aware mode switcher | route mapping tests | done | Phase 1B reconfirmed common top-level and run-scoped calendar/player mappings. | Route mapping test |
| P1 | Tests | Viewer one nav test | done | Verifies one primary nav. | Required |
| P2 | Tests | dropdown items test | done | Verifies dropdown items match spec. | Required |
| P3 | Tests | Season/Week selector test | done | Render/expand/change. | Required |
| P4 | Tests | Jump to Week test | done | Updates local context. | Required |
| P5 | Tests | MSA homepage sections test | done | Verifies required homepage sections. | Required |
| P6 | Tests | no forbidden actions in Viewer test | done | Interactive action labels only; Phase 1B scopes this to buttons/links/actions. | Required |
| P7 | Tests | shared shortcut route tests | done | Shared destinations. | Required |
| P8 | Tests | Admin still works smoke test | done | Ensure Admin routes unaffected. | Required |
| Q1 | Cleanup/visual polish | sports-style page headers | done | Phase 1B polished copy to sports-facing read-only language and removed Phase 1A placeholder wording. | Visual/smoke test |
| Q2 | Cleanup/visual polish | card layout | done | Responsive sports cards. | Visual/smoke test |
| Q3 | Cleanup/visual polish | reduce debug look | done | No raw JSON primary UI. | Copy/UI test |
| Q4 | Cleanup/visual polish | responsive topbar | done | Desktop/tablet/mobile. | Responsive test |
| Q5 | Cleanup/visual polish | mobile dropdown behavior | done | Hover cannot be required. | Mobile interaction test |



### Phase 1B Structural QA Notes

Viewer Phase 1B completed a focused post-1A route preservation and shell-polish pass:

- Confirmed `/viewer/runs/:runId/calendar` remains the real read-only `SeasonCalendarPage`.
- Confirmed `/viewer/runs/:runId/tournaments`, `/viewer/runs/:runId/players`, `/viewer/runs/:runId/countries`, and `/viewer/runs/:runId/history` remain real read-only run-scoped pages instead of top-level scaffolds.
- Confirmed `/viewer/runs/:runId/calendar/:eventId` and `/viewer/runs/:runId/finals` remain Viewer-specific read-only split pages without commissioner or simulation controls.
- Polished top-level Viewer scaffold copy and homepage cards to use sports-facing Phase 1B language without fake authoritative data.
- Strengthened frontend route/safety tests for preserved run-scoped pages, context-aware mode switcher mappings, and forbidden interactive Viewer action labels.

These notes do not mark full Viewer Phase 1 complete; they only document the Phase 1B structural QA pass.

### Phase 1C Active Run Wiring Notes

Viewer Phase 1C adds active-run bridging for top-level Viewer routes without marking full Viewer Phase 1 complete:

- Top-level Viewer pages now bridge to active run read-only routes where safe.
- No active run state remains sports-facing and asks the viewer to select a Viewer run.
- No duplicate navigation was reintroduced; active-run destinations are content CTAs, not a second nav row.
- Full real data read models for homepage cards, statistics, predictions, Elo, Power Rating, H2H, and odds remain deferred.

These notes do not mark full Viewer Phase 1 complete; they only document the Phase 1C active-run wiring slice.

## 23. Testing Checklist

Frontend tests must verify:

- Viewer has one primary nav.
- No duplicate run nav is visible in Viewer.
- Viewer topbar contains MSA, Rankings, Tour, Players, Countries, H2H, Stats, Predictions.
- Viewer dropdown menu items match spec.
- Season/Week selector exists.
- Season/Week selector expands.
- Jump to Week updates local Viewer context.
- MSA homepage sections render.
- Viewer does not render forbidden mutating action buttons.
- Viewer World Tour Finals does not show Simulate World Tour Finals.
- Viewer planned event detail does not render wildcard/withdrawal/late replacement controls.
- Shared shortcuts route to same pages.
- Context-aware Admin/Viewer switcher maps common routes.
- Admin routes still render.

Backend tests:

- Not required for this docs-only phase.
- Future implementation should avoid backend changes unless read-only APIs are needed.

## 24. Acceptance Criteria For This Docs Phase

The docs-only phase is complete if:

- `docs/viewer_mode_phase_1_spec.md` exists.
- It contains all required sections.
- It captures every agreed Viewer decision.
- It includes exact topbar/dropdown structure.
- It includes read-only safety rules.
- It includes route map.
- It includes component plan.
- It includes implementation checklist with statuses.
- It includes testing checklist.
- No implementation files changed.
- No React/backend/test/CSS files changed.
- git status only shows `docs/viewer_mode_phase_1_spec.md` as changed before commit, or a clean tree after committing the docs-only change.

## 25. Future Implementation Instructions

Future Codex phases must use this file as the Viewer Mode Phase 1 source of truth.

Rules for future implementation:

- Before implementation, read this spec.
- Implement only a defined checklist subset or phase.
- Update checklist statuses after implementation.
- Do not silently change product decisions.
- If implementation requires changing the spec, update the spec explicitly and explain why.
- If a requested feature is not supported by backend yet, create sports-facing placeholder/scaffold rather than inventing fake backend data.
- Keep Viewer read-only.
- Keep Admin functionality stable.
- Do not mix Viewer and Admin route spaces.
- Do not render Admin-only mutation controls in Viewer.
- Add tests for every implemented checklist subset.

## 26. Open Questions

Open questions for future product/implementation discussion:

- Exact route naming can be adjusted during implementation if React routing constraints require it.
- Exact backend APIs for future predictions/statistics may not exist yet.
- Exact formulas for Elo, Form, Power Rating, and rivalry score will be specified later.
- Detailed player/country/tournament detail tabs will be specified later.
- Mobile topbar behavior needs implementation design.
- No-future-knowledge enforcement will need backend/data support in later phases.
- Should Season/Week context persist in URL query parameters, local storage, or only in memory for Phase 1?
- Should `/viewer/predictions` render Match Predictor directly or redirect to `/viewer/predictions/match-predictor`?
- Which Viewer pages must be real data pages in the first implementation slice versus sports-facing placeholders?
- Should the topbar search open an overlay first, or route immediately to `/viewer/search?q=...`?

## 27. Commands Run

Commands run before writing this document:

```text
$ git status --short

$ git branch --show-current
work

$ git log --oneline -n 20
a03c48a Merge pull request #387 from Jasmetk0/codex/conduct-season-builder-ui/ux-audit
cc8d2e3 fix: refine season builder danger-zone copy
658918a feat: clarify season builder apply danger zone UI
aa2936a Merge pull request #386 from Jasmetk0/codex/audit-durable-audit-trail-for-apply-command
48fe5a9 fix: repair create-only apply audit fingerprint syntax
25f637d feat: persist create-only apply audit records
f7db14d Merge pull request #385 from Jasmetk0/codex/conduct-candidate-identity-reference-audit
f49490b feat: enforce candidate identity alignment for create-only apply
6f5775d Merge pull request #384 from Jasmetk0/codex/add-negative-api-tests-for-create-only-command
9cb74ca test: add real create-only apply negative API coverage
86959ce Merge pull request #383 from Jasmetk0/codex/conduct-project-coverage-audit
6441fef docs: plan real create-only apply hardening
e8d7225 Merge pull request #382 from Jasmetk0/codex/add-link-to-future-apply-pre-execution-docs
ec2f245 docs: link future apply pre-execution stack
a013bad Merge pull request #381 from Jasmetk0/codex/perform-phase-22-milestone-audit
d31e83f docs: summarize future apply pre-execution stack
6754246 Merge pull request #380 from Jasmetk0/codex/document-and-test-phase-22e-closure
aae1c76 Phase 22E: clarify decision summary non-authorization invariant
eb80e02 Merge pull request #379 from Jasmetk0/codex/strengthen-frontend-tests-for-decision-summary
9b5157f test: harden future apply execution decision summary safety assertions
```

Additional discovery commands run:

```text
$ find web/src -maxdepth 4 -type f | sort
```

Result summary: listed current frontend files under `web/src`, including `web/src/App.tsx`, `web/src/api/client.ts`, `web/src/components/Layout.tsx`, page components under `web/src/pages`, styles, and frontend tests.

```text
$ find docs -maxdepth 3 -type f | sort
```

Result summary: listed existing project documentation under `docs`, including recent future-apply and project audit documents.

```text
$ rg -n "viewer|Viewer|admin|Admin|NavLink|Link|Routes|Route|run nav|ranking|tournament|players|countries|history|records|finals|simulate|wildcard|withdrawal|late replacement" web/src docs tests -S
```

Result summary: found existing Admin/Viewer route and nav structure, run-scoped nav, Viewer/Admin route reuse, ranking/tournament/player/country/finals references, and safety-sensitive terms around simulation, wildcards, withdrawals, and late replacements.

Supplemental inspection commands run:

```text
$ find src/beta_engine/api/routers -maxdepth 1 -type f | sort
$ rg -n "path=\"viewer|path=\"admin|viewerNav|adminNav|runNavFor|simulateWorldTourFinals|assignEventWildcards|applyEventPreDrawWithdrawal|applyEventLateReplacement" web/src/App.tsx web/src/components/Layout.tsx web/src/pages/ModePages.tsx web/src/pages/FinalsPage.tsx web/src/pages/PlannedEventDetailPage.tsx web/src/api/client.ts -S
$ for f in src/beta_engine/api/routers/*.py; do echo "### $f"; rg -n "@(router)\.(get|post|put|patch|delete)|APIRouter" "$f"; done
```

Result summary: confirmed backend router files and endpoints exist for health, players, rankings, runs, seasons, simulation, snapshots, tournaments, world data, and history; also confirmed the current frontend has Admin/Viewer routes, run navigation, a Finals simulation call, and planned event commissioner-style API calls.

Tests were not required or run because this is a docs-only phase and no React, backend, API client, CSS, or test files were changed.
