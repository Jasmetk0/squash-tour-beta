# R007 — independent data-atlas critique, R008 synthesis, and FAX-world evidence boundary

**Date:** 2026-11-01.  
**Status:** PRELIMINARY SELECTIVE INDEPENDENT AUDIT, not an exhaustive source-by-source legal review or fully reproduced statistical study. Research-only; no source data were imported, no medical/sporting parameters calibrated and no simulator tests executed.  
**Primary user document:** 50-page Gemini DOCX (`Dostupnost a Kalibrace Dat Squashe.docx`), preserved in the research chat and archived here only as [searchable lossy text](GEMINI_R007_FULL_TEXT_EXTRACT.txt). The original DOCX has 5 large tables and 166 inline graphical objects, including mathematical formulas; the binary is NOT committed. Refer to original DOCX when checking formulae.  
**Companion:** R008 independent simulator-validation methodology in Draft **[#1719](https://github.com/Jasmetk0/squash-tour-beta/pull/1719)**; its proposed 15 experiments are not executed validations.  
**Base:** `buuk` verified `a07c51548ef3f398edba3e92551008ab2d61ec61`. Work has not received these reports. Only owner merges.

## Overall assessment

**R007 supplies a useful *catalogue and governance framework*, NOT a set of already-calibratable numeric laws.** Its classification into official competition records, secondary aggregations, tool-generated data, small scientific datasets and proprietary feeds is valuable, especially the data provenance/unit/license inventory and the practical distinction between macro competition outcomes and sparse micro/rally/health observations.

**Correct the following before using R007 as the authority for implementation or a data acquisition plan:**

### Verified and corrected claims

| Claim from R007 / area | Independent evidence and qualification | Project consequence |
| --- | --- | --- |
| SquashInfo has strong restrictions on copying, scraping, downloads, third-party redistribution and extracts. | **Confirmed directly** in [SquashInfo Terms & Conditions](https://www.squashinfo.com/terms-conditions.php). Limited personal single-page viewing/printing exception is described. The practical policy is to **not bulk-scrape or redistribute** without explicit rights. | Do not use an open-source scraper as proof of permission to extract third-party data. Exact legal outcomes depend on jurisdiction and use; do not label every use criminal/automatically unlawful. |
| No meaningful open positional/T-zone dataset exists / only three authentic open squash datasets found in Zenodo/Figshare/Kaggle. | **Important missed open-source counterexample:** [squashai/datasets](https://github.com/squashai/datasets) includes `positions.csv`, `attributes.csv`, `tboxes.csv`, `pboxes.csv`, and annotated JSON. The repository's LICENSE is **Apache-2.0**. The size, subject composition, temporal sampling, annotation accuracy, rights to source video and applicability to elite male PSA are **not established** by repo existence. | List this dataset separately as actual research data to inspect, not a full pro match-level event corpus. Do not blindly import downloaded video/third-party media or assert the samples represent PSA elites. |
| Sportradar Squash API has season, competitor, timeline and probability endpoints; “three seasons maximum” makes all longer historical study impossible. | API/endpoints are **real**. [Sportradar Squash Overview](https://developer.sportradar.com/squash/reference/squash-overview) states a **maximum of three returned seasons for the Seasons/Competition Seasons listing feeds**, not a universal retention guarantee/prohibition on every historical query. [Sport Event Timeline](https://developer.sportradar.com/squash/reference/squash-sport-event-timeline) states timeline content is **coverage-dependent**. Trial/production credentials and rights are separate. | Avoid declaring the whole API historical horizon either 3 seasons or unlimited without authenticated endpoint-level proof. Timeline ≠ guaranteed complete rally-by-rally tracking across all competitions. |
| Historical official men's PSA ranking monthly before weekly start **29 August 2022**. | Date corroborated by [Aug 2022 PSA announcement reportage](https://squashmad.com/breaking-news/psa-announces-switch-to-weekly-ranking-lists/). | Do not interpolate old monthly rankings into invented weekly published snapshots. Use observed publication dates or represent temporal interval uncertainty. |
| Historical PSA ranking “the divisor rises when one plays >11 events”. | **Misstatement in R007 narrative.** [August 2024 PSA Rule Book](https://d2h2jicm4ii9y.cloudfront.net/wp-content/uploads/2024/08/PSA-Squash-Tour-Rule-Book-August-24.25.pdf): **≤15 events → divisor 11; 16→12, 17→13 ... 24→20**, plus +1 thereafter. Historical PSA regimes changed; do not treat this as timeless or FAX. | The S05 empirical example “12th to 16th tournament changes divisor 11→12” must explicitly mark **15→16** as the first such step for that specific rule version. Recheck every season independently. |
| Audio-based squash scientific data released openly in 2018. | **Supported** by [Hajdú-Szücs et al. PLOS ONE](https://doi.org/10.1371/journal.pone.0194394) and linked Figshare source. | Excellent small observational benchmark for ball-hit timing/audio, but cannot turn an isolated short recording into a representative modern pro tour stroke or injury distribution. |
| Peer-reviewed sport papers make numerical hazard/severity and kinematic transition probabilities “exactly calibratable”. | **Overstatement.** R005 audit found that Horsley lacks individual male person-time, Rejeb's 53/34/13 severity and TL/NTL totals are from youth multisport cohorts, and physiological samples are small. Publication of marginal/T-area percentages does not identify the **joint transition matrix** or individual tactical decision weights. | Cite study population/definitions, reconstruct only identified quantities, report underdetermined model parameters as **OPEN / HYPOTHESIS**. |
| An open-source `squashinformr` package permits use of SquashInfo-derived data. | Code licensing and third-party data extraction rights are independent. R007 correctly warns about this distinction; SquashInfo terms corroborate. | Avoid scraping and public re-hosting; seek permission/licensed exports or use separate genuinely open datasets. |

### Ten proposed micro-studies: methodological triage

| Study | Source idea | Correct use / issue |
| --- | --- | --- |
| S01 Rally + rest Gamma/Weibull distribution | **Promising exploratory fit**, but means/SD and a few quantiles do **not uniquely identify** full mixture shapes, heavy tails or contemporary PSA distributions. Report model family assumptions and partial identification. |
| S02 Match duration vs PAR11 points | Descriptive study candidate; account for game intervals, lets/strokes, retired matches, changing eras and player-level repeated observations. The regression does not prove a mechanistic per-point time constant. |
| S03 BO3 vs BO5 upset contrast | Theoretically compare formats at fixed set-win probability; **do not infer format causal effect solely from Tour Finals vs other events**, whose fields, selection, prestige, scheduling and player states differ. |
| S04 Long No.1 dynasty Pareto fit | Small N, ranking observation regime and right/left censoring make a universal Pareto tail inappropriate absent diagnostics; don't set a mandatory FAX dynasty quota. |
| S05 Ranking points/rank vs divisor | Correct 2024 PSA divisor breakpoint **15→16**, not 11→12; version rules and avoid inferring individual event-value dynamics from a single top-100 ranking snapshot. |
| S06 Challenger/Copper entry tradeoff | Official scoring may be explored under a *dated* PSA rule, but rational utility and tournament attendance require real costs, eligibility, fields, available information and probabilities; no numeric Entry AI utility from a prize/points table alone. |
| S07 Walkover/retirement descriptive frequency | Potentially observable in public published draws, but **WO/RET indicators are not injury onsets or cause-specific medical hazard**, can involve illness/administrative events. Coverage and publication bias matter. |
| S08 Lactate and final-game fatigue | Small selected human physiological samples cannot identify an exact speed/stamina-decay ODE for all elite FAX players; risk double-counting existing `Form`/`Stamina`/`Health`. |
| S09 T-zone positional transition matrix | **Marginal T/control aggregates and audio frequency cannot identify** a full Markovian state transition matrix or conditional drive/drop response without actual linked sequences. SquashAI annotated data may offer partial position observations; inspect first. |
| S10 Juniors to senior breakthrough | Construct **complete junior cohorts, including never-breakthrough players**, with right-censoring, participation opportunities and historical nationality; do not fit an Early Prodigy/Late Bloomer mixture from selected champions only. |

The ten studies were **proposed by Gemini, not conducted**. Costs, sample sizes, data licenses and exact numeric fit feasibility remain unverified. Some proposed conclusions require observations that the study itself documents as missing.

## Critical user-world correction: FAX is NOT modern PSA with more players

The owner's established product premise is an **alternate globally popular squash world**, with sport, competitive ecology and potentially sporting/tactical practices evolving through its own history. Real-world PSA (Earth) is an **evidence anchor**, not the target aggregate.

Segment evidence into four categories:

1. **Hard rule/engine invariants within a specified FAX historical regime:** score counting, validity of draws, published ranking snapshots, Save/replay. These are correctness tests against FAX Master and recorded source dates, **not** PSA copying. If FAX policy differs historically, tests should differ accordingly.
2. **Mechanisms plausibly transportable with explicit conditions:** superior relative skill raises win probability at comparable style/load, long rally has physical cost, no future information at Entry closure, ranking/entry link impacts competition. Validate mechanisms and units, not universal coefficients.
3. **Environment/era-dependent evidence:** distribution of pro match length, training load and tactics, global player pool size, turnament calendars, financial incentives, nation-level top player concentration, player age distributions. These depend on FAX world/era; PSA 2026 values cannot be frozen as FAX's evolving future.
4. **Unobserved alternative evolution hypotheses:** new player strategies, coaching and recovery practices, meta adaptation, sport technology, institutional pathways or rule regimes may evolve, **but must not be assumed to happen at a fixed year/rate**. Implementation is a Master/owner product choice and should emerge from allowed actual systems where possible. Never force all athletes always to improve or infer national style/innate talent DNA.

A globalized FAX world could have larger athlete pools and faster diffusion of tactics; it could also retain long dominant eras. **This is not proof of a precise magnitude or direction.** The correct validation question is *whether simulated change has coherent, historically versioned causes and doesn't violate physics/logic*, not whether 2060 FAX matches have PSA 2026 median duration.

R008 explicitly calls for assessing nonstationarity, held-out historical samples, ensembles, orthogonal/mechanism-specific observations and avoiding copying real-world marginals. **Future R009 (if commissioned)** could study the historical evolution of professional squash, skill/tactical diffusion and what alternate-globalization trajectories are identifiable; no new research job authorized here.

## R007 + R008 integrated data-to-validation path (no implementation approval)

**Step 1: Source provenance inventory.** For each dataset, maintain URL, named custodian, acquisition method, rights *for exactly this data*, sex/age/competitive level, format/regime, tournament/ranking-date validity, whether directly observed or reconstructed, missingness, version and population selection.

**Step 2: Scientific observables.** Map each R001–R006 metric to actual available variables/estimands, measurement uncertainty, dependency structure, and explicit `NOT OBSERVED` for unavailable dimensions. Avoid “fitting” from aggregate marginal data that cannot identify interactions.

**Step 3: R008 experiment manifests.** Pin current code/config/fixture, source version, historical rule state, seeds, primary observables, falsification criterion, negative control and actual runtime budget. Only pre-approved current code paths and nonconflicting research work; overlapping integration PRs **#1713/#1718** already cover some Saved/restart checks.

**Step 4: Earth→FAX transfer assessment.** Per candidate target label `MECHANISM_TRANSPORTABLE`, `CONDITIONALLY_TRANSPORTABLE`, `WORLD_SPECIFIC`, `NOT_IDENTIFIABLE`. Require one sentence explaining adaptation to alternative history/population and which Master-era rules apply.

**Step 5: Report limitations.** Record `VERIFIED ALGORITHM`, `STRUCTURAL DIAGNOSTIC PASSED/FAILED`, `EMPIRICAL COMPATIBLE/INCOMPATIBLE`, `NOT OBSERVABLE`, `NOT IMPLEMENTED`, and `PRODUCT DECISION OPEN` rather than outputting a fictitious single "realism" score.

### Suggested immediate investigation (research only)

Smallest useful next independent inquiry: **inspect the actual `squashai/datasets` metadata/coverage** (sample size, period, whether elite professionals, position/time alignment, annotations, error bounds and video/media rights) and compare against published SAGIT T-zone summaries **without downloading unlicensed match footage**. It could provide *limited* paired spatial observations for R006 and R008 but is NOT automatically enough to calibrate FAX tactical probabilities.

Other sensible research: compare original published numbers in R007's S01/S08, check whether S02/S07 can be done with an authorized manual noncommercial sample, and re-evaluate S03 with matched skill/format rather than conflated competitions.

**Governance:** Work/owner decides new product rules, permanent research numbering, experiment budgets and merge. This PR only archives and reviews data-source proposals. No new Play, Health, Gameplan, Ranking, Entry or World-Package mechanics were coded; no source datasets copied into repo.