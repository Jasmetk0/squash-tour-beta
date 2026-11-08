# R005 — Gemini original vs ChatGPT independent audit: scientific synthesis and guarded handoff

**Date:** 2026-11-01  
**Status:** TWO RESEARCH DOCUMENTS ARCHIVED; selective independent third-party source checks; **NOT a numerical health calibration, release certification or product approval**.  
**Authority:** Squash Engine Master, current owner decisions and active branch/contracts supersede all research.  
**Repo/base verified:** `buuk` `ef529e26b47f0af68cf5741398879d11bce111ec`. The source PR was open Draft #1709 at audit archiving.  
**Studies:**
- [59-page original Gemini research, lossy text extraction](GEMINI_DEEP_RESEARCH_TEXT_EXTRACT.txt)
- [44-page independent ChatGPT scientific audit, lossy text extraction](CHATGPT_INDEPENDENT_SCIENTIFIC_AUDIT_TEXT_EXTRACT.txt)
- [Earlier focused pre-audit](INDEPENDENT_CRITICAL_REVIEW_AND_HANDOFF.md)

**Source fidelity limitation:** Both original documents were DOCX. Neither binary DOCX is included in this PR. **ChatGPT specifically did not have direct access to the original Gemini DOCX during its audit**, so extracted Word equations, figure captions and complex table layout could not all be checked against source pixels. This limitation is important whenever numeric formula transcription is disputed. The original documents were supplied to the research coordination conversation and should be consulted for graphical/equation-level questions.

## Synthesis in one sentence

**Gemini generated useful epidemiological/mechanistic hypotheses; ChatGPT more rigorously separated clinical observations, wrong denominators, assumptions, and product rules. Preserve the existing Health V1 record system; prioritize integrity/observability checks, not an unvalidated injury-rate generator.**

## Major disputed claims and current disposition

| Gemini claim or proposed parameter | ChatGPT independent finding | Additional source spot-check | Disposition |
| --- | --- | --- | --- |
| McCartney et al. (2026) pooled **2.01 injuries / 1,000 athlete-days** can ground a professional men's daily/annual event hazard | 12 studies, 8 pooled, I²=99.65%; heterogeneous definitions and epidemiological population denominators. 2.01/1,000 is the reported **pooled constructed rate**, not a validated adult-male hazard or chance. | [McCartney original full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12944960/) agrees on rate, k, I², populations and study-design heterogeneity. | Reject as direct calibration. Label outcome and denominator in every metric. |
| Horsley: **592 events among 67 players across 11 years** implies **1.2–1.8 injuries per active professional/year** | 67 included **45 men, 22 women**, and roster membership/person-years are not given. Observed 592 events (363 male, 229 female) cannot identify a professional male annual injury rate. | [Horsley abstract](https://pubmed.ncbi.nlm.nih.gov/32823248/), [published article](https://www.sciencedirect.com/science/article/pii/S1466853X20304831) confirm sample and event splits. | Reject numeric 1.2–1.8/year claim; lower limb distribution ≈76.48% is useful as a **broad mixed-sex elite anatomical plausibility** diagnostic, not male-specific universal quota. |
| Rejeb: **53% minor, 34.4% moderate, 13% severe**, **87% TL / 13% NTL** can drive elite male squash duration distributions | Source studied **166 male adolescents** in multiple sports; squash subgroup **n=18**, its event rate ≈8.5/1000 exposure-hours. Broad severity/time-loss proportions concern the **whole youth multisport cohort**. Gemini's proposed injury-duration bin endpoints also do not fully preserve original severity definitions. | Source context described in [McCartney review](https://pmc.ncbi.nlm.nih.gov/articles/PMC12944960/) and [Rejeb DOI](https://doi.org/10.1080/17461391.2016.1275820). This secondary spot-check does not validate each original Rejeb stratification; original publication still owns its own tables. | Do not turn 53/34/13 into FAX severity weights or assume fixed minor/moderate/severe treatment lengths. |
| “86% of critical body/core temperature maximum” during squash | **Plain physiological variable error:** **86 ± 9% VO₂max**, **92 ± 3% HRmax** in Girard et al. (2007). | [Girard abstract](https://pubmed.ncbi.nlm.nih.gov/17685699/) explicitly reports these units. | Reject temperature-percent claim. Neither value is injury probability. |
| Bern 2016 gives exact time to regain Form (e.g. 2–4 tournaments) | The consensus distinguishes **Return to Participation**, **Return to Sport**, **Return to Performance** as clinical stages, NOT fixed periods or a guarantee of full recovery. | [Ardern et al.](https://bjsm.bmj.com/content/50/14/853) | Retain terminology; do not code fixed tournament or success probabilities. |
| Multi-state/frailty/tissue-vulnerability/semi-Markov model is required in pre-alpha | Models can be mathematically legitimate but their *numeric parameters* are not identified by available adult male squash longitudinal data. Complex frailty risks double-counting existing predisposition/fatigue and Form. | Current `src/beta_engine/domain/players/health.py` already has structured Health V1 records and recovery windows. | Defer model replacement/complexity; make all new numeric effects explicit decisions. |
| RNG isolation, Save/Load and non-duplication of Health vs Form/fatigue | Strong engineering requirements independent of injury-risk calibration. | Already compatible with game's deterministic ownership and existing historical Health projections. | High-value integrity/diagnostic candidates (NOT empirical validation of injury rates). |

## Engine status (checked against live branch, not assumed from Gemini)

- `src/beta_engine/domain/players/health.py` defines `PlayerHealthRecord` (`Injury`|`Illness`, `At Risk`|`Active`|`Recovering`|`Recovered`), severity, affected domains, onset/recovery week, recovery window, recurrence link, provenance, and separately recorded `PermanentHealthConsequence`; the canonical player/Run/Branch/week facts carry forward deterministically.
- `src/beta_engine/domain/matches/health.py` projects these facts into a frozen `EffectiveMatchHealthSnapshot`. The projection expressly has `numeric_effect_applied=False`; `numeric_limitation_effects`, `health_check`, `start_wo_ret_decision` and `medical_timeout_effect` are marked unsupported.
- The existence of Health facts in Save / Match inputs **does not establish** automatic injury onset, healing probability, fatigue conversion, player withdrawal/RET or calibrated performance penalty.
- Health should not introduce a separate hidden decline in *potential* simply because a player missed training or matches; first measure indirect consequences through existing calendar, form, competition, opportunities and career systems.
- Current Master policy and the Run's fixed weeks-per-year calendar `W` remain binding; do not silently add a medical `day_index`, PSA Protected Ranking or new eligibility policy.

## Diagnostics justified before extra sporting code

**Priority 1 — no new numerical parameters necessary:**
1. **Health lifecycle and recurrence graph** (valid states, chronology, links, unique identity, permanent-consequence provenance).
2. **Healthy Match projection no-op:** a healthy projected player must not silently acquire a sporting penalty.
3. **Health vs Form/Stamina separation:** healthy fatigue alone must not be reclassified as injury; no double-counting across layers.
4. **Frozen Match Health and Save/Load/replay** equivalence for real supported flows.
5. **Run/Branch identity and RNG stream isolation** under controlled non-impacting changes.
6. **Consumer boundary / future-state integrity:** Entry, Match, ranking and career must not act on unapproved numeric Health effects.

**Priority 2 — data-quality/provenance before calibration:**
7. Source table for every proposed injury metric: study, sex, age, competitive level, injury definition, event count, exposure-time definition, actual person-time, follow-up, exclusions, censoring and interval/uncertainty.
8. Identify which adult professional male data are missing; report `unobservable`, not a fitted 1.2–1.8 injuries/year.

**Deferred until evidence, a fitting model comparison and an owner product choice:**
9. Simple exposure hazard vs no calibrated hazard; prospective exposure/recovery data and outcome-specific probabilities required.
10. Recurrence/frailty/tissue-specific disease/health-driven retirement or protected ranking complexity only if existing model fails a specified test and authoritative rules approve changes.

## The audit's treatment of Gemini EXP-01..EXP-16

The 44-page ChatGPT report reviews all 16. Most important reclassifications:
- **EXP-01** fix: preserve exposure monotonicity, remove 1.2–1.8 injuries/year target.
- **EXP-02** reject 53/34/13% as calibrated *professional squash* recovery distribution.
- **EXP-03** retain anatomic pattern as a broad plausibility check, not a precise male quota.
- **EXP-06** retain Health vs fatigue/Form orthogonality; critical before numerical Health is activated.
- **EXP-07** verify recurrence *record integrity* now; postpone numerical recurrence multipliers.
- **EXP-08** reject fixed 2–4 tournament Form recovery benchmark.
- **EXP-10** treat Protected Ranking as a separate FAX ranking/entry policy decision, not an outcome of injury science.
- **EXP-11/12/13** defer specific peak-delay, age/style, automatic medical retirement numeric models.
- **EXP-14** preserve long-run stability stress tests without invented expected prevalence bands.
- **EXP-15/16** preserve deterministic PRNG isolation and Save/Load replay integrity.

None of these tests were executed by Gemini, ChatGPT scientific reviewer, or this archiving update. The project has not passed any new release gate by virtue of including this research.

## Honest remaining limitations

- This is **not** a third independent replication of every figure in the 59-page paper. Key epidemiology and original article facts have been spot-checked; the ChatGPT 44-page audit is stronger than Gemini on methodological reasoning but still an AI-generated secondary analysis.
- The audit reviewer did **not** inspect the original Gemini DOCX. Word equations/tables may be altered in text extraction and require original-file visual verification before engineering any numeric law.
- No dataset of individual adult male professional player injury risk, actual follow-up, injury/illness incidence by match/training hours, and time to recovery was assembled; numerical science remains incomplete.
- Historical source versions, sex/age/level specificity and the distinction between *event rates* and *risk of at least one event* should be pinned in any future data acquisition.
- These studies do not decide which stylized Health events might still be useful for a fictional game when empirical calibration is impossible; that would be an **explicit product choice with declared assumptions**, not a scientifically estimated coefficient.

## Safe handoff when Work is available

Work should first verify current Master + actual active Health consumers, the pending research PR landscape and baseline acceptance dependencies. Then **propose** the smallest deterministic, read-only / no-calibration Health V1 test slice: schema/recurrence, healthy projection invariance, frozen snapshot, Save/restart and RNG isolation. Do not touch injury probabilities, state machine replacement, Product Master, Protected Ranking, automatic medical retirement, or any published FAX ranking rule until separately authorized. No implementation or merge is delegated by this research PR.

**Research files only. No production code, Master, tests or simulations changed. Owner-only merge.**
