# R011 — independent scientific and engine audit: global Tour travel, jet lag and recovery

**Date:** 2026-11-01  
**Status:** SELECTIVE INDEPENDENT PRIMARY-SOURCE CHECK AND TECHNICAL REVIEW, not a systematic review of all travel evidence, finished hazard/Match model, numerical validation or owner-approved functionality.  
**Original document:** user-supplied DOCX **"Vědecké důkazy o cestovní únavě a jet lagu.docx"**, 10 pages, 70 paragraphs, no Word tables or shapes; [searchable archival text](CHATGPT_R011_FULL_TEXT_EXTRACT.txt), original DOCX **not** committed. Source contains unresolved snippet citations (e.g. `【44†L171-L179】`) without usable direct hyperlinks; source-level references recovered independently only for selected major studies.  
**Repository snapshot checked:** `buuk` `a07c51548ef3f398edba3e92551008ab2d61ec61`. No production code changed.  
**Research programme:** candidate R011 only, pending Work/owner review; previous psychology R010 [#1730](https://github.com/Jasmetk0/squash-tour-beta/pull/1730), tournament Entry R004 [#1705](https://github.com/Jasmetk0/squash-tour-beta/pull/1705), Health R005 [#1709](https://github.com/Jasmetk0/squash-tour-beta/pull/1709), validation R008 [#1719](https://github.com/Jasmetk0/squash-tour-beta/pull/1719), evidence atlas R007 [#1722](https://github.com/Jasmetk0/squash-tour-beta/pull/1722).

## Decision-relevant verdict

**Useful topical overview and 15 experiment ideas, but not a production-ready Deep Research or actual code audit.** Best supported proposition: **physical travel fatigue and circadian jet lag are distinct, can coexist, and should not be reduced to the same geographic flag**. The study identifies important global FAX calendar/Entry questions and the risk that different systems double-count the same sleep/fatigue consequence.

**Reject immediate implementation advice** in the report to apply linear performance penalties by time zone/distance (example “one week after five zones”), add automatic Health effects, individual travel tolerance, flight records or a new day clock. These are uncalibrated and have not been approved in Master; data supporting **sleep disturbance** do NOT directly determine **male professional squash match-win probability**.

## Evidence and important corrections

| Study statement | Independent verification and correction | Required interpretation |
| --- | --- | --- |
| Janse van Rensburg et al. (2021) consensus describes travel fatigue distinct from jet lag; scientific evidence for precise sporting performance impact is limited. | **Confirmed.** Expert panel of 26 and explicit distinctions: travel fatigue from a journey regardless of zones/direction; jet lag from circadian misalignment after rapid crossing of roughly ≥3 zones. Recommendations mostly physiology/opinion/intervention consensus with major research gaps. [Original full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC8279034/) DOI `10.1007/s40279-021-01502-0`. | Good basis for distinct explanatory concepts, **not** numeric performance penalty. |
| Maynard et al. “2025 WHOOP WTA” 52 players: first-night sleep decreases roughly 11 min per crossed time zone. | **Confirmed** for **52 female professional tennis players**; data are observational from 2022–2023, paper online **21 Nov 2025** and final issue **Jan/Feb 2026**. `-11.3 ± 0.96 min` per **hour of absolute time-zone difference** was an estimated **first-night sleep duration association**, not a squash performance effect. [Full study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12640278/), [PubMed](https://pubmed.ncbi.nlm.nih.gov/41272436/), DOI `10.1177/19417381251387717`. | No transfer of this minute-sleep coefficient to professional men or FAX percent ability. |
| Study says eastern effect **−24.5 min/time zone**, western **+30 min/time zone**. | **Mathematical/model interpretation error.** The per-zone slope is approximately **−11.3 min/zone**. Eastward additional **−24.5 ± 4.2 min** and westward additional **+30.0 ± 4.2 min** are *travel-direction effects in the multivariable mixed model*, **NOT additional per-zone slopes**. This difference can massively inflate modeled consequences. | Reject original directional *per-zone* statement. Future research must reproduce actual source model covariates/interactions. |
| WTA sleep disruption did not translate to lower player performance. | Their multivariable analysis found **no statistically significant link** between the tested sleep/recovery and match-performance metrics; about **81.3% of matches occurred ≥3 nights after arrival**, and even an early-match subgroup was null in that study. Lack of statistical detection is **not proof of zero performance influence** and selection/logistical preparation may help explain the null. | Report outcome and limits; do not claim all athletes are immune to sleep disruption, or that the null establishes FAX penalty=0. |
| WTA program “regulating travel extended player careers from median 12.1 to 14.2 years”. | **Major causal misattribution.** The original study [WTA Age Eligibility Rule and Player Development Programmes](https://pubmed.ncbi.nlm.nih.gov/35396204/) compared **811 players who at some point reached singles ranking 1–150** between pre/post-1995 entry eras, examining AER/PDP package effects. It did not isolate travel limits nor randomly test travel strategies. The observed medians are genuine but cannot be attributed to travel management. | Absolutely no “travel extends lifespan +2.1 years” calibrator or claim. |
| Schwellnus et al. (2012) travel >5 zones increases illness 2–3×. | **Supported observational association** in **259 professional rugby union players**, 8 teams, 16-week 2010 Super 14 competition (22,676 player-days); abroad >5h time difference illness incidence **32.6/1,000 player-days** versus home baseline **15.4/1,000** (and return **10.6/1,000**). [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/22875910/). The ratio is about **2.12** for that cohort; exposure, destinations, climate and cohort context may confound. | **Illness** ≠ injury, match fatigue, or squash-specific hazard. Do not encode automatic 2–3x FAX Health risk on any trip. |
| Fowler et al. (2015) simulated international travel impairs sleep and intermittent endurance. | **Supported in an experiment with just 10 physically active men** in simulated 24h vs 5h travel/control, not elite male squash professionals or real tournament itinerary. [Primary paper](https://pubmed.ncbi.nlm.nih.gov/24750359/). | Mechanism plausibility only; no universal per-match decline or exact duration. |
| Adaptation rates “0.5 day west/1 day east per zone”. | Common practical heuristic, but individual circadian phase, direction, travel schedule, light exposure, time zone magnitude and sleep schedule vary. The consensus does not validate a hard fixed biological law applicable to every player. | Treat as possible scenario sensitivity, not fixed simulation decay. |

## Technical contract vs actual implementation

**Master/AGENTS.md / Country V1:**
- `travel_region` and `timezone_area` are distinct **factual metadata/geography layers**, not interchangeable fields or active per-player travel effects. A timezone registry/assignment exists; this is **not evidence** of a working physiological jet-lag simulation.
- A Run uses **its own fixed positive W weeks per year**, configurable at creation and frozen after active start. Earth **defaults** to W52, FAX **defaults** to W61 (Season Week 1 from Year Week 37); the uploaded study incorrectly describes every FAX simulation as universally **fixed 61-week implemented clock**. An actual W61 simulation is not a real-world 365-day calendar. Never assume physical days per FAX week or normalize durations as calendar days silently.
- The Master expressly warns against inventing **deferred travel mechanics** or collapsing geography layers.
- Simultaneous Simulation Slots use a shared pre-slot snapshot; historical facts, Save and replay need exact provenance.

**Actually verified Match path** (`src/beta_engine/domain/matches/match_engine.py`, `_base_strength`): `participant.travel_modifier * 0.1` is added to effective internal strength alongside Form, Sharpness, Fatigue, Health. That confirms a **consumed input field**, **not its automatic derivation** from actual itinerary, Timezone Area delta, calendar, flight hours or a travel history. No source data or producer function in the uploaded paper was actually verified. Do not assert the simulator automatically enforces per-zone travel penalties.

**Other currently unproven functionality:**
- `Travel Region` metadata does not prove actual travel route records, player home base, flight itineraries, day-of-arrival nor personal jet-lag recovery clocks are present and persisted.
- `Health V1` currently contains injury/illness records and projected Match snapshots; its `numeric_effect_applied=False` is an explicit lack of completed automatic health outcome effects, **not an implemented health↔travel causal chain**.
- `Form` and `Stamina` exist, but claims that a specific travel fatigue is already written into Form/Stamina or that an actual athlete is located at an event are **unverified**.
- The model should distinguish structural access to geographically distributed tournaments (Entry option availability) from a hypothetical **performance penalty** after travel.

## Critique of all 15 proposal scenarios

| ID | Original test (condensed) | Valid current treatment |
| --- | --- | --- |
| T01 | Equal time zones, east vs west | **Future physiological model**; directional effect requires real route/time/arrival information and owner-approved model. Distinguish geometry-only fixture from sports result. |
| T02 | Long journey, no time-zone change | **Good contract separation test** once travel facts/producer exist. Without real duration data, currently only negative metadata check. |
| T03 | Short journey, many zones | **Compare independent axes** if real assignments/route possible. Do not infer 6h/5-zone physical itinerary solely from geography. |
| T04 | Arrival 5 vs 1 day before | **Not currently executable as proposed** on weekly Run/Scheduling alone; needs authorized finer timing layer. |
| T05 | Repeated travel over weeks | Future event/participant history and real location needed; no present quantitative cumulative model proved. |
| T06 | Match on day of arrival vs +1 | Same limitation as T04. |
| T07 | Rest between tournaments | Can inspect supported weekly stamina/recovery separately. Don't label output a travel effect absent source. |
| T08 | Local vs distant field advantage | Structural exposure potentially measurable; no compulsory performance disadvantage for distance. |
| T09 | Same nationality, different bases | Useful anti-nationality test only if different **player base/location** exists in current schema; otherwise future data modeling. |
| T10 | No nation-based home advantage | **High-value direct invariant:** swapping nationality label without changing true geography/itinerary should not change travel costs. Actual local environment may legitimately differ. |
| T11 | Cross Form/Stamina/Health | **High-value conceptual code trace**, not proof of double-counting absent identified duplicated causal pathway. No implemented travel-to-health hazard identified. |
| T12 | Entry AI reaction to long travel | **Read-only current path check** first; not require a new rational-choice model. No-lookahead and choice set; coordinate R004 **#1705**. |
| T13 | Deterministic replay | **High-value existing hard invariant**; check overlap with native Tour Saved/restart PRs, avoid duplicate fixtures. |
| T14 | Historical Earth PSA comparison | **Do not enforce PSA historical aggregate** on evolving FAX. Need licensed/time-scoped data and matched scoring/rule regimes. |
| T15 | Regional vs alternating global calendars | Legitimate **scenario design** with identical players/competition source, but only measure currently supported outcomes; no compulsory fatigue or country-quota target. |

**None of T01–T15 have been executed** in this review or source study. Several are **future-feature design questions**, not valid current acceptance tests; “we don't see an effect” is NOT a defect when no corresponding feature is approved.

## Smallest useful science-to-engineering diagnostic path (no action authorised yet)

1. **Travel source/consumer map (read-only):** actual fields and producer of `MatchParticipantContext.travel_modifier`; `travel_region` and `timezone_area` registry/assignment and historical source; Entry availability consumption; actual player home base/location; precision of time/slot. Label `IMPLEMENTED` vs `PLACEHOLDER` vs `UNSUPPORTED`.
2. **Data neutralities:** pure country-label permutation vs true home location, region metadata, timezone and route; absent route must not be guessed from nationality.
3. **One mechanism at a time:** track current travel strength modifier in effective Match probability only where *actually supplied*; avoid fake travel penalties in Form/Stamina/Health.
4. **Shared invariants with R004/R005/R008:** historical source/time ownership, no-lookahead, Save/replay, independent RNG, no double count on health/fatigue; coordinate with existing pending implementation PRs.
5. Only after an explicit owner choice, evidence and storage model, evaluate a **minimal separated travel-fatigue / jet-lag model** against a **null travel penalty**, with declared uncertainty and actual performance outcomes. Do not bring default “linear per zone” into pre-alpha without data.

## Important FAX-specific nuance

FAX is a **globally popular alternate historical squash world** with possibly denser regional events, different long-haul travel frequency and different logistics; not just real PSA Tour. Geography, travel demands and competition effects may evolve over decades. More world tournaments could **decrease** average elite travel if regionally dense, or **increase** it if concentrated in intercontinental Premier series. Neither should be hardcoded as world-law or tied to innate nationality.

The current calendar W changes the *sporting time discretisation*, not a proven real-time day/hour mapping. A detailed circadian rhythm model requires supported local time-of-day data and an explicit owner decision; do not substitute fractional or full FAX weeks arbitrarily for Earth hours.

## Governance and next step

The paper is useful as a **hypothesis list and sources to retrieve** but no direct performance coefficient or illness risk is validated for male pro squash. Work is unavailable and has not been notified. Once available, Work should evaluate a narrow, no-calibration **data-lineage and consumer-map** audit, avoiding parallel PRs and false release gates. Owner alone decides Master/rule changes and merges.

**Scope:** research-only; no Match/Health/Entry code, World Package, time model, Master, tests, agents or external data were modified; no simulations run.
