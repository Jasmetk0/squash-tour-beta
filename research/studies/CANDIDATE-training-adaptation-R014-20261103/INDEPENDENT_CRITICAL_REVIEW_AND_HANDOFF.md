# R014 — Independent critical audit of Gemini's physiology, training load and periodisation paper

**Date reviewed:** 2026-11-03.  
**Scope:** Independent research/code *spot-check*, **NOT** a complete systematic review, verified model calibration, performed experiments or owner-approved R014 implementation.  
**Original owner DOCX:** `Vypracování Výzkumného Dokumentu R014.docx`, visually formatted at ~28 pages; underlying Word has **5 tables and 478 inline shapes** (mostly equations/notation and embedded media). See [searchable lossy text](GEMINI_R014_SEARCHABLE_TEXT_EXTRACT_LOSSY.txt); **original Word is NOT committed**. Critical numerical equations, Greek symbols, plot labels and table values may be missing or corrupted in the text. Always consult the original DOCX for formula fidelity, figures, and exact quantitative claims.  
**Repo baseline inspected:** `buuk` `a07c51548ef3f398edba3e92551008ab2d61ec61`, particularly `AGENTS.md`, `src/beta_engine/domain/players/sporting.py`.  
**Research status:** **PARTIAL candidate R014 sports-science literature source**, not a completed R014 deliverable. Do not merge facts into the Master or new runtime policy.

## Executive determination

The document is **much better as a scientific source collection** than R010/R011, but **does not follow the main project-specific R014 deliverable**: zero sections on the real Squash Engine and alternate FAX, no crosscheck of 57 player attributes/actual development function, no `W` time semantics, no current State/Save/seed audit, **none of the requested 15 falsifiable engine experiments**, no CLEAR IMPLEMENTED/TARGET/DEFERRED matrix. The author has produced a self-contained human performance/training-monitoring narrative, **not a validated player-career development model**.

The strongest data: in-season monitoring (only 15 elite players, 166 training sessions across **two weeks**), group session vs matchplay/conditioning differences, poor interchangeability of mechanical and internal load, and statistical/measurement warnings. These support treating **effective workload, immediate fatigue, long-term adaptation and performance** as distinct phenomena and avoiding naive “training hours → linear rating gain” assumptions.

**NOT supported:** one universal squash adaptation equation, a per-training-session attribute growth coefficient, a safe injury threshold for squash from recreational running, one universally best periodisation scheme, physiological performance peaks at fixed birthdays, an intrinsic left/right injury pattern or mandatory nutrition/hydration game mechanic.

## Original science checks, reconciled with first-party studies

| Topic and source | Confirmed | Limitation / correction |
| --- | --- | --- |
| [James et al. (2021) `Quantifying Training Demands`](https://pubmed.ncbi.nlm.nih.gov/33547264/), DOI `10.1123/ijspp.2020-0306` | **15** professional squash participants (**11 men, 4 women**) measured over **2 weeks**. Group on-court sessions longest (79 ± 12 min), Matchplay 46 ± 17, Conditioning 37 ± 9, Ghosting 35 ± 6; off-court conditioning produced highest mean relative Playerload, and Group highest on-court Playerload and selected internal load. | This is a **descriptive 2-week monitoring study**, not a longitudinal randomized comparison of which training makes players win more matches, how much each attribute develops or lifelong adaptation. Repeated sessions are **not 166 independent players**. The group/matchplay contrasts should not be mandated for every player/country/era. |
| [James et al. (2021) `Minimal Agreement`](https://pmc.ncbi.nlm.nih.gov/articles/PMC7919364/), DOI `10.52082/jssm.2021.101` | Same-type elite sample: **134 on-court + 32 off-court = 166 sessions**. Overall Playerload vs TRIMP Banister r=0.43; vs TRIMP Edwards r=0.50; vs TEAM r=0.24; vs sRPE TL r=0.46. Global sRPE vs HR TRIMP metrics substantially correlated; differential legs/breathing RPE highly collinear with global. | **Monitoring markers, not a causal dose–fitness–injury mapping.** Paper itself calls for future investigation of *how load associates with changes in squash-specific fitness*. The Gemini claim that separate RPE dimensions bring *no additional value universally* overstates a finding from a small, context-specific sample. Five sessions with erroneous HR data were excluded from relevant analysis. |
| [IOC 2016 training load / injury and illness statements](https://pubmed.ncbi.nlm.nih.gov/27535989/) | Widely cited framework linking workload change, recovery, health and injury risk in complex sporting contexts. | Consensus statements are not validated FAX simulator coefficients or causal player-specific hazard functions. Risk depends on exposure, personal history, ascertainment and confounding. |
| [ACWR methodological critique (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7485291/) | The ACWR `acute/chronic` ratio and proposed universal 'sweet spot' have **mathematical coupling, denominator and sensitivity** issues. | Correct conclusion is **don't hardcode a magic ACWR safe zone**; not that every alternative workload-risk predictive measure is reliable. |
| [2025 cohort of 5,200 adult runners](https://pmc.ncbi.nlm.nih.gov/articles/PMC12421110/), DOI `10.1136/bjsports-2024-109380` | Session-specific >10% increase **in running distance** vs the longest run in prior 30 days associated with increased **lower-extremity running-related injury risk**, not an established universal safe workload threshold. | **MAJOR TRANSFER ERROR:** Gemini advises that **no squash training session** should exceed the largest previous session by >10%. Runners' linear distance and mixed squash workload (technical drills, acceleration, turns, strength, court control) are **different exposure units**. Even the original runner study says increases below 10% are not guaranteed safe. Reject as FAX rule. |
| [2019 comparison of squash resistance training programs, 15 participants](https://www.em-consulte.com/article/1284895/comparaison-de-trois-programmes-de-musculation-che), DOI `10.1016/j.scispo.2019.01.001` | A **small preliminary** 3-program comparison found better improvements in reported test endpoints under a *particular* lighter-load protocol (G2), with limited individual testing. | **INTERNAL MISLABEL / OVERGENERALISATION:** Source summary lists G1 heavier, **G2 lighter weights**, **G3 bodyweight**; the largest test gain was **G2**, **NOT** universal proof that bodyweight training outperforms heavy weights or that heavy training harms all elite squashists. The document conflates 'lower load' with 'bodyweight' in §Periodization and generalises to all squash players. Must validate source design and injury outcomes before even discussing a health risk mechanism. |
| [2026 network meta-analysis of resistance methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13457283/) | Broad comparison in healthy adults found **no consistent superiority** of advanced over traditional methods for strength/power across relevant networks; external to squash. | Supports caution against the paper's “block periodization is highest effectiveness universally” and compulsory bodyweight-only prescription, but neither paper identifies FAX physiological coefficient. |
| Age/peak examples from tennis, padel, Olympic sport | Age trajectories may have multidimensional components (physical vs motor/tactical experience). | Highly confounded with selection, historical cohort, rankings, workload and rules; **cross-sport peak ages are not fixed squash training milestones**. Claim that 'cognitive abilities grow at least to age 60' is an unbounded transfer; no physical/form rule or age 60 player skill bonus. |
| Left/right high-intensity steps and ileopsoas association | An asymmetry was **observed** in a particular 2-week cohort (14/15 right-handed) and a separate musculoskeletal association is cited. | **Causal overreach:** observed direction counts and a cross-sectional muscle finding do not establish that left-turn load *causes* an individual player's chronic injury. No nationality/handedness fixed injury genetics or mandatory lower-limb lesion model. |

**Measurement vs simulation warning:** `Playerload` from a particular trunk-mounted accelerometer is **not a game player attribute**, and `TRIMP`, `sRPE`, `VO2max` measured in physical humans are not automatically obtainable for generated FAX players. Research must distinguish actual observable quantities and internal latent variables.

## Actual engineering boundary: inspected code vs paper's omissions

**Real implementation, not a full repo-wide audit:**

- `src/beta_engine/domain/players/sporting.py` has `PlayerSportingRecord` with canonical **57 attributes** on a 0–200 scale, `current_form`, `long_term_form_norm`, `match_sharpness`, `long_term_fatigue`, `development_timing` and frozen development-policy provenance.
- `PlayerDevelopmentPolicy` currently contains **explicitly provisional** ages/coefficients: `growth_end_age=27`, `physical_decline_age=30`, `other_decline_age=34`, early/late shifts ±3 years, `weekly_change_basis_points=18`, `form_influence_basis_points=4`, `inactive_sharpness_decay=2`, `fatigue_recovery=8`. They are historical named defaults **not evidence that sports-science sources calibrated these numbers**. Distinguish observed performance from latent realized player ability.
- `weekly_player_development_update` consumes **completed-week** source context and player ages; loops across all canonical attributes, chooses direction from shifted age + attribute group; uses a deterministic state/source/seed-derived roll for bounded discrete ±1/0 changes. That function does **NOT** consume training modality, athlete wearables, session load, true individual VO2max, personal annual budget or an empirical fitness–fatigue convolution. This local observation is not proof that *no training system anywhere in the repo* exists.
- `between_week_state_update` separately **regresses Form** toward `long_term_form_norm`, reduces Sharpness after inactive weeks, recovers long-term fatigue. There is no demonstrated independent exercise-type dose-response in this routine. Other match-specific physical stamina mechanisms remain distinct.
- `AGENTS.md`/Master define **each Run's own W** positive weeks/year: FAX default W61; Earth default W52. Long-term age/growth uses elapsed **1/W** fractions of the Run year; some **weekly** rules remain weekly. A real '7-day acute/28-day chronic' human ACWR cannot be blindly ported to 61 abstract FAX weeks, nor can natural ages be shifted by raw number of week calls. The Gemini document does **not** address this mandatory constraint.
- Country V1's six authored attributes affect accessibility/development/conversion, **not innate athletic/mental/technical potential by nationality**. The research offers no allowable evidence for intrinsic national training DNA.
- Master/AGENTS mark **exact growth calibration, detailed training/deload scheduling** as OPEN/DEFERRED or otherwise scoped, not approved release blockers. Deterministic saved replay, source-versioning and user explicit Save cannot be sacrificed for a finer time-based simulator.
- Health state is independently incomplete/not calibrated in historical slices: do not invent a biological injury response merely to make load tracking look realistic.

## Critical omissions compared with the original R014 assignment

| Required section | Status in Gemini report |
| --- | --- |
| Physiological demands and training load across different modes | **Substantial**, with limited source populations |
| Adaptation, fitness–fatigue, fatigue/recovery, ACWR | **Conceptual**, no fitted squash-specific coefficients |
| Skills/technical and tactical motor learning | **Largely missing as a causal development model** |
| Individual non-response, delayed breakthroughs, plateau/detraining | **Insufficient** for R001 career mechanism |
| Long-run skill/physical trajectories / multi-generation FAX | **Not modelled** |
| FAX country opportunities and 6 attributes / nationality invariance | **Absent** |
| Actual code / implementation status mapping | **Absent**; this addendum supplies a *limited* check |
| Actual configurable W52/W61 and Save/seed design | **Absent** |
| Mathematical model comparison with identifiability and numerical alternatives | **Partial** (fitness–fatigue and ACWR) |
| **15 precise falsifiable simulator experiments** | **Missing** |
| Evidence/implementation/phase/release-priority matrix | **Missing** |

**Interpretation:** Accept this source into R014 literature archive as **PARTIAL** and request a second R014 synthesis/engineering/experiment deliverable before declaring R014 complete; do not rerun the same broad physiology search.

## Proposed follow-up R014 science test set (THIS REVIEW'S 15 CANDIDATES — NOT executed or in Gemini paper)

Each proposed test requires checking existing PR/test ownership first; no extra programming is authorized by this archive.

| ID | Diagnostic or scientific question; falsifying signal | Current feasibility |
| --- | --- | --- |
| D01 | **Source-only coefficient inventory:** all `PlayerDevelopmentPolicy` effective settings, source versions and consumers; untraceable historical coefficient fails provenance contract. | Inspect/test existing code |
| D02 | **Age trajectory:** one 57-attribute player across ages 17–40 under frozen seed/model; assess age threshold discontinuities; note no external empirical squash curve. | Existing deterministic domain fixtures |
| D03 | **Attribute-group contrast:** same player physical/move vs technical/mental group across physical vs other decline ages; mismatch to intended policy violates technical contract. | Existing domain fixtures |
| D04 | **Early/late timing:** same ability, development_timing ±3 under matched progression; no pre-assigned eventual superstar story. | Existing fixture possible |
| D05 | **Same elapsed-year W52/W61/W80:** 1/W normalized age/maturation comparison across different W, preserving only declared week-specific state. Unexpected W-dependent annual growth calls for audit, not automatic coefficient re-scaling. | Need exact context and existing W test ownership |
| D06 | **Completed-week knowledge:** no newly opened/future training/match results influence prior weekly development; any leak violates invariant. | Existing source-guard tests |
| D07 | **Form vs growth:** change only Form while fixing age, seed/source; verify actual coefficient sensitivity; a correlation is not measured training adaptation. | Existing deterministic domain fixtures |
| D08 | **Inactivity vs sharpness:** no matches only affects explicit sharpness decay through state update; follow-up separate test of match ability consumption. | Existing domain fixtures |
| D09 | **Long-term fatigue recovery:** test terminal fatigue boundaries and time-step semantics without inventing medical hazards. | Existing domain fixture |
| D10 | **Attribute saturation:** exactly 0/200 boundaries and bounded changes; no unrealistic overflow or guaranteed infinite OVR growth. | Existing domain fixture |
| D11 | **Quality of opportunity / country label:** given same actual environment, arbitrary country name change must not create innate potential differences; opportunity inputs may differ. | Partial existing governance check |
| D12 | **Training dose producer trace:** is a factual exercise schedule/effort already versioned? Is there evidence of per-modality adaptation? If none, classify unsupported instead of making direct coefficients. | Read-only map; new mechanics future-only |
| D13 | **Null model vs fitness–fatigue:** a no-new-training-feature baseline; identify which observations would require extra latent state beyond Form, Fatigue and Sharpness. | Science design only until data |
| D14 | **Career outcomes:** study late bloomers, plateaus, interrupted careers and attr-specific peaks with R001/R009 diagnostics; don't require fixed target-age or percentile shape. | Requires coordinated long-run runs; do not duplicate PR |
| D15 | **Save, Replay and source-version:** identical saved state + historically effective policy + seed yields identical update, with no mutated earlier history after policy changes. | Existing contract; coordinate full release suite |

**Do not turn D01–D15 into 15 new PRs, 15 mandatory pre-alpha gates or 15 new game mechanisms.** Most are hypothesis/contract checks, some already exercised elsewhere. For all tests, report actual run conditions, code version, fixtures and any source-data limitations, rather than “realism proven” merely because a built-in response fires.

## Highest-value next work if authorised

**First:** reconcile Gemini paper with R001 (player development/late bloomers), R005 (health), R006 (Gameplan/skill learning), R008 (validation), R009 (long-run alternate FAX), R010 (psychology), R011 (travel) and R012 (financial support). Produce ONE approved evidence registry with confidence, contradictions, implementability and present coverage, not seven overlapping game-model add-ons.

**Second:** inspect actual long-run 57-attribute progression under identical source-known conditions, frozen policy and seed hierarchy; quantify W-normalised annual change/variance and age thresholds *before* choosing new training adaptivity. Do not label a simulated change 'caused by training' if the source function only sees age/Form.

**Third:** if and only if owner/Work chooses a future feature, study one minimal input-source-backed training type/dose (e.g. **one existing canonical activity**), with deterministic historical evidence, bounded recovery, no duplication of Form/Fatigue, and a clear comparison to null baseline; no physiological parameters copied from 2-week cohorts without power/identifiability.

## No-change declaration

Research-only PR. Only this review and the Gemini lossy text archive were added. No player/match/health/calendar code, algorithms, Master, effective Country policies, World Packages, tests, CI, agents, external datasets, user Run or simulation were modified. No Work contact. No merge. Owner decides policy and merger.
