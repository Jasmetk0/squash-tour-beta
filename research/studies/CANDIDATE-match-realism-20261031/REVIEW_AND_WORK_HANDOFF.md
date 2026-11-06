# Squash match realism — first independent research review

**Date:** 2026-10-31  
**Status:** research received; **NOT scientifically VERIFIED**, **NOT owner-approved**, **NOT implemented**  
**Study ID:** unassigned; **candidate for R002**, pending Work's prioritization and owner's confirmation  
**Source:** [ChatGPT Deep Research searchable text-only extract](CHATGPT_DEEP_RESEARCH_TEXT_EXTRACT.txt), from user-provided 25-page DOCX. Original DOCX, mathematical formula objects and formatted tables are not faithfully included in this Git text archive.
**Scope:** realistic male professional rally-by-rally squash and empirical benchmark design; research only.

## Executive judgement

This research is useful **mainly as a measurement/calibration plan, not a new match-engine specification**. It supports a simple, reproducible rally outcome based on current skill/state and controlled variation, physical workload related to rally intensity, appropriately timed recovery, and joint realism diagnostics over multiple matchup strengths and seeds.

It **does not** demonstrate that the current Squash Engine implementation lacks any proposed mechanism or that its existing numerical coefficients are incorrect. Its author explicitly could not read the entire Master or all rally-probability code. Work must audit actual existing support before assigning implementation tasks.

No gameplay rule, ranking rule, Master text, performance target or test gate is changed by this document.

## Strong findings with selective independent checks

| Topic | Report's claim | Independent check / caveat |
| --- | --- | --- |
| PAR-11 scoring amplifies small rally advantages | Constant point-win chance `p=0.52` yields P(game)≈0.577, P(BO5 win)≈0.642; `p=0.55` yields 0.687 and 0.819. | **Independently recomputed mathematically**, assuming i.i.d. point outcomes and win-by-two deuce. Correct to three decimals; this is a scoring **model** and not measured PSA outcomes. |
| Typical men's professional match ≈42–43 min | Squash Stats article describes an updated corpus of 67,034 timed matches since 2005, through 2026-10-27; older 2000–2020 comparison gives ~43 min mean. | The source [Squash Stats](https://squashstats.com/category/psa/) confirms 67,034 timed matches and typical men's 42 min; the older [duration analysis](https://squashstats.com/2021/02/07/match-durations/) describes match format/context. **Secondary database statistics**, requiring sampling, period, scoreline and segment control. Not all 67,034 cases are male-only. |
| Outcome mix varies by draw stage and tour | The older Squash Stats analysis shows World Tour men's 3:0 ≈45% and men's L16 54% 3:0, 30% 3:1, 16% 3:2 in the stated historical window. | Checked against the [source narrative](https://squashstats.com/2021/02/07/match-durations/). It also contains a **contradictory 3:2 text example** and overall approximations. Do not use inconsistent prose as precise calibration; reconstruct from real scored matches if access/licensing permits. |
| Men's rally durations are skewed | Murray et al. (2016) report PAR-11 rally median 13.2s; percentiles 7.0 / 22.7 / 46.4s and maximum 146.5s. | Matched peer-reviewed [publication](https://pubmed.ncbi.nlm.nih.gov/27494689/) and reported article table; small historical match sample (2010/2011), not full contemporary tour. Validate *quantiles and tail*, not only mean. |
| High physiological strain, incomplete elite literature | Original Girard et al. (2007) found 86±9% VO2max, 92±3% HRmax and blood lactate 8.3±3.4 mmol/L in seven elite squashists. 2024 meta-review comprises 35 studies, 14 elite/world-class. | Checked original [Girard abstract](https://pubmed.ncbi.nlm.nih.gov/17685699/) and [2024 systematic review](https://doi.org/10.1007/s42978-024-00313-9). Caveat: the review's prose apparently misreports the Girard relative VO2 as 92%; **the source report correctly uses the primary article's 86%**. Physiological percentages must never be copied as point-win penalties. |
| Serve advantage is modest | Carboch & Strnad (2017) studied 15 PSA matches and 1072 rallies, recording service outcome and many lets. | Verified the [2017 publication](https://doi.org/10.7752/jpes.2017.04268) / [accessible article text](https://1library.net/document/zw5d90n0-original-article-analysis-serve-serve-return-squash-carboch.html). Raw “server scores ~40%” includes lets and varied serves; **not directly P(server wins a resolved rally)** or a uniquely calibrated serve coefficient. |

**Verification scope:** these are selected independent spot-checks, not validation of all cited studies or numerical claims in the research. The paper's named research and factual sport conclusions are distinct from an inferred model.

## Distilled methodology that fits the pre-alpha direction

1. **Do not introduce automatic momentum, clutch, upset or comeback bonuses.** A sequence of winners or a dramatic comeback does not establish a causal streak effect. Existing skill, form, state, uncertainty and PAR-11 scoring may generate these outcomes without artificial correction.
2. **Calibrate scoring before fatigue.** First verify deterministic point/game/BO5 structure for fixed `p`; then skill-gap mapping and upset results; then duration/workload; then within-match recovery and across-tournament propagation. Otherwise one wrong coefficient can conceal another.
3. **Condition statistics on matchup and tournament segment.** A globally popular fictional FAX with a different player-quality distribution need not reproduce present-day PSA's *unconditional* 3:0 proportion. Compare physically transferable quantities and **conditional** score distributions, and document periods, rounds, World Tour/Challenger scope, BO3 exclusions, and empirical sample sizes.
4. **Preserve replay and source integrity.** Same saved history, effective version/configuration, hierarchical seed and command must reproduce exact accepted sporting outcomes and authoritative logs; a diagnostic must not write to a Run, invent rally times, or leak information into Viewer.
5. **Do not prematurely expand match modelling** to shot-by-shot, advanced psychophysiology, hydration/nutrition or free-floating latent variables. More complexity needs evidence of measurable shortcomings and explicit owner scope.

## Candidate diagnostics (the document contains **19 named experiments**)

The document proposes 6 mechanistic checks, 7 outcome/duration checks, 3 tournament-load checks and 3 determinism/restart checks. This is a **research checklist**, not 19 newly mandated release gates.

**Group A — first baseline feasibility (proposed high priority):**
- Fixed-`p` PAR-11 game and BO5 *analytical oracle* (including p=0.5, 0.52, 0.55 and deuce).
- Skill-gap monotonicity, identical-player symmetry, correct seed/replay comparison.
- Scoreline frequencies `3:0/3:1/3:2` *conditioned on matchup-strength bins*, not only global averages.
- Rally duration percentiles (25/50/75/95) and game/match duration percentiles, **only if historically authoritative timestamps are available**.
- Determine observational coverage: do we have exact skill, seed, event-time, scorer, rally and physical snapshots for the exact dataset version?

**Group B — after first baseline, if evidence is adequate:**
- Server/receiver outcome after resolving lets; returner and server strength confounding.
- Scoring margin/tiebreak and comeback transition frequencies, empirical PSA targets still unknown.
- Upset curve by strength proxy with reliability calibration, contextual Brier score/log-loss when pre-match forecast probability exists.
- Physical dose-response to short/long rallies and rest interval order; no instantly vanishing or runaway fatigue.
- Between-match finalist workload, 8/24/48h recovery scenarios and over-punishing deep-run checks.
- Seed-locality and Save/restart invariants.

**No numeric pass/fail thresholds** should be invented from today's means or from a few published top-tour samples. Work should first record whether a metric can actually be measured and collect a versioned, legal, machine-readable corpus where useful.

## Specific technical review questions for Work (not an implementation assignment)

1. What is *actually present* in `src/beta_engine/domain/matches/match_engine.py` and related control/rally/stamina/timing/health/gameplan packages (rules may already be implemented)? What is only a Master target?
2. Does the current engine have actual logged rally durations and the correct distinction between ball-in-play time and elapsed match time? Are lets, rest and timeout timing counted consistently with the external reference data?
3. Does the skill-to-rally-probability function reproduce the fixed-`p` oracle when state-changing effects are frozen? Avoid comparing an arbitrary special case to actual full-engine behavior.
4. Are both per-rally and between-match fatigue updates already accounted for, and would a new separate per-match variance double-count existing Form / sharpness / matchup effects?
5. Can we re-use **existing tests and logs** for a no-code or read-only diagnostic before adding an entirely new analytics subsystem?
6. How does this compare in urgency to C5 career baseline, pre-alpha sporting integration, Windows local-preview PR and current acceptance gaps?
7. Is any PSA/SquashInfo dataset legally reusable, sufficiently complete and comparable in scoring era, tour level and match format? No blind web-scraping task authorized.
8. Would a small, bounded read-only evidence project give meaningful value before the complete FAX reference season/50-season run, or would it distract from a stronger integration blocker?

## Proposed review disposition

- Accept the **research archive** as non-authoritative evidence if source fidelity notes are acceptable.
- Do **not** install new rally mechanics, override match-form or gameplan canon, add coefficients, claim a new calibration is correct, or launch extra paid AI agents.
- If Work sees a feasible non-overlapping next slice, propose only the **smallest existing-logs-first comparison** with a verifiable output and the user's explicit approval before code.
- Do not assign a permanent R002 number until the owner/Work agrees the scoped match realism research is the programme's next numbered study.

Research value resides in testability and identifying data gaps, not in the page count of its report.
