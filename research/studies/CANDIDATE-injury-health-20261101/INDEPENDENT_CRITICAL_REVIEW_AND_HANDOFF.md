# Gemini injury & health research — first independent scientific and product audit

**Date:** 2026-11-01  
**Status:** FIRST CRITICAL PASS; selected external sources independently checked, not a full 59-page peer review or validated simulation model.  
**Source:** [Gemini searchable text archive](GEMINI_DEEP_RESEARCH_TEXT_EXTRACT.txt) of the user-supplied 59-page original DOCX. **Original Word formulas, charts and table structure can be lost**; access the user-provided DOCX for source-accurate mathematical checks.  
**Program ID:** *candidate R005*, **not formally assigned by Work/owner**.  
**Base:** verified `buuk` `ef529e26b47f0af68cf5741398879d11bce111ec`. No sporting code modified.

## Executive verdict

The paper is a **substantial source of research hypotheses and diagnostic design**, notably (i) exposure denominators cannot be interchanged, (ii) health limitation is not the same as match fatigue or Form, (iii) Return to Participation → Return to Sport → Return to Performance are distinct clinical concepts, and (iv) new RNG, injury, Save and restart must not affect unrelated sporting results.

**Do not directly implement the proposed injury-rate coefficients, semi-Markov/frailty engine, severity mixture or the author's pre-alpha release prescriptions.** Several numerically important claims improperly transfer youth or mixed-sex cohort statistics to elite men, and one executive-summary physiological figure is outright wrong. The 59-page report did not inspect current Master/Health source tree and should not be used to replace existing Health V1.

### Verified original evidence and corrections

| Gemini statement | Status / necessary correction | Primary support |
| --- | --- | --- |
| McCartney et al. (2026) meta-analysis: 12 included studies, 8 pooled, ≈2.01 injuries / 1,000 athlete-days, I² ≈99.65%. | **Confirmed as reported**, but this is an aggregate of very different definitions/designs/populations. Do **not** set 0.00201 daily injury chance or claim it describes elite male PSA players. The source's computed denominator multiplies cohort size by observation days, which for some clinical case-only studies fails to represent an at-risk population. | [McCartney et al. full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12944960/) |
| “Core body temperature 86% of critical maximum” in the Executive Summary. | **False / major variable confusion.** The 86 ± 9% figure in Girard et al. (2007) refers to measured oxygen uptake as a percentage of **VO₂max**, *not body/core temperature*. The 92 ± 3% figure is **HRmax**. The relevant study does not support a temperature-percent figure. | [Girard et al., PMID 17685699](https://pubmed.ncbi.nlm.nih.gov/17685699/) |
| Horsley et al. (2020): 67 elite England Squash players, 592 injuries, mean 8.83 over 11 years, 76.48% lower-extremity injuries. | Reported aggregate values are supported, **but 67 players included 45 men and 22 women**, so the rates and distributions are **not male-only observations**. The report repeatedly implicitly treats them as the adult male FAX benchmark. Moreover participants need not have been observed for all 11 years; 8.83/11=.803 is NOT a reliable person-year incidence for truly exposed active players. | [Horsley et al., PMID 32823248](https://pubmed.ncbi.nlm.nih.gov/32823248/), [McCartney et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12944960/) |
| Estimated 1.2–1.8 medically recorded injuries per *active male professional per year* from Horsley. | **Not established**. The report infers this by asserting fewer actual player-years but provides no individual follow-up/exposure person-time. The inferred interval is a hypothesis, not a trustworthy calibration target or an original study estimate. | [Horsley](https://pubmed.ncbi.nlm.nih.gov/32823248/) |
| Rejeb et al. (2017): ≈8.5 injuries/1,000 exposure hours for the squash subgroup. | The squash subgroup is from a **youth multisport sport-academy cohort** (166 athletes across sports, a small squash subgroup). It is not an adult professional men baseline. Its injuries/overuse and recovery response cannot be copied wholesale to FAX. | [Rejeb et al. PMID 28100124](https://pubmed.ncbi.nlm.nih.gov/28100124/), [McCartney et al. table](https://pmc.ncbi.nlm.nih.gov/articles/PMC12944960/) |
| Minor 53%, moderate 34.4%, severe 13%; time-loss 87% and non-time-loss rates 4.8 vs 0.7/1,000h are “in squash”. | These severity and time-loss fractions/rates appear to be **the entire 166-person multisport cohort**, not adult professional men or necessarily the tiny squash-only subgroup. Such a mistaken denominator would compromise the proposed pre-alpha 53/34/13% injury-duration mixture. **Original paper's sport-stratified tables must be examined before even calling them squash-specific.** | [Rejeb et al. publication/abstract](https://onlinelibrary.wiley.com/doi/10.1080/17461391.2016.1275820), [PMID 28100124](https://pubmed.ncbi.nlm.nih.gov/28100124/) |
| 2–7 / 8–28 / 29–240 days as minor/moderate/severe absences, directly weighted 53/34/13. | The numerical bounds and fitted *time-loss* mixture are **proposals**, not established population-specific PSA severity/duration empirical bins. A prospective youth “injury-severity” variable cannot without source confirmation be translated into that exact elite-player healing distribution. |
| 700–1000h annual exposure, 45–65 matches, 1.5–2.5/1,000h and match hazard several times training hazard. | **Derived/assumed scenario**, not a directly measured male PSA exposure/injury hazard panel. Indicate assumptions and sensitivity bands; never freeze as a calibrated law. |
| Injury-based retirement, protected rankings, 3-state pre-alpha Health, hard cap on match retirements, frailty parameter, “no lasting skill effect of minor injuries.” | **Product hypotheses**, not binding medical findings or approved FAX mechanics. Master and current Health V1 contracts have precedence. Document any proposed new rule separately for owner decision. |
| 2016 Bern consensus distinguishes Return to Participation, Return to Sport, Return to Performance. | **Correct as a clinical decision framework**; the three labels do not provide exact squash healing durations, post-return win-rate penalties, mandatory attrition or number of comeback tournaments. | [Ardern et al. (2016) consensus](https://bjsm.bmj.com/content/50/14/853) |
| ACWR mathematical coupling and spurious associations. | **A relevant methodological warning**, but criticism of a single ratio does not validate any specific alternative nonlinear tissue-hazard formula or frailty prior. | [Impellizzeri et al. conceptual review](https://pubmed.ncbi.nlm.nih.gov/?term=Impellizzeri+Acute%3AChronic+Workload+Ratio+Conceptual+Issues+Fundamental+Pitfalls) |

### Additional red flags

1. **Unjustified medical determinism:** no clinical evidence warrants compulsory 100% return to preinjury performance after 2–4 tournaments or universal non-impact of all minor/moderate injuries. Keep these as model questions.
2. **Overinterpretation of heterogeneity:** the primary meta-analysis has extreme methodological differences and even misleading person-time reconstructions in case-only records. That is important, but do not claim that 100% of between-study variance was *mathematically proven* to be a denominator artefact alone, or that heterogeneity is *not biological*, without reconstructed data and model.
3. **Epidemiological outcome definitions:** injury ≠ illness; medical attention ≠ time-loss ≠ no-time-loss ≠ match retirement; incidence vs prevalence vs exposure vs calendar time must be explicitly distinguished. Never infer a professional per-match retirement probability from general injury incidence.
4. **Selection/censoring:** players entering/exiting an 11-year registry, unscheduled care visits, training load, repeated injuries, careers not yet complete and survivorship bias all affect proposed hazard estimates.
5. **Over-engineering:** a 6-state semi-Markov process + competing risks + time-decaying local frailty + renewal hazards + disease processes can be useful in future research, but the report supplies no elite-male data capable of identifying all parameters. Complexity will not compensate for lack of observation.
6. **Cross-PR scope:** health↔Entry/career/ranking interactions touch #1700/#1705 and code owned by other pending PRs; this study alone does not authorize changes.

## Cross-check with existing current Health V1 (actual code)

The original Gemini author **could not read the live GitHub code** (their section 8 says so), and thus its “new health module” proposal starts from a partially incorrect premise.

**Already present, read-only verified on `buuk` `ef529e26...`:**

- `src/beta_engine/domain/players/health.py`: `PlayerHealthRecord` distinguishes `Injury` / `Illness`; lifecycle `At Risk`, `Active`, `Recovering`, `Recovered`; severity (0–100); affected domains, onset/recovery weeks, recurrence links, recovery windows, immutable historical identity/provenance and separate permanent health consequences.
- `PlayerHealthProfile`, `PlayerHealthWeekState`, explicit Run/Branch/Week identity, deterministic bootstrap and no-op historical carry-forward already exist.
- `src/beta_engine/domain/matches/health.py`: a hash-protected `EffectiveMatchHealthSnapshot` projects those health records into a Match, including permanent consequences.
- The Match health projection explicitly declares **`numeric_effect_applied=False`** and lists unsupported components including numeric limitation effects and Health Check / match decisions. Current probability/healing calibration is unresolved, **not already done**.

**Interpretation:** A new `PlayerHealthState` and 3-state architecture must **not** replace the existing canonical record/history system. The scientifically useful next step is to inspect the gap between the current **documented health-state authority** and the existing Match/lifecycle/Entry consumers, *not* to drop in the paper's novel clinical state machine and random hazards.

Master's fixed per-Run calendar weeks `W`, immutable Saved revisions and current chronological Simulation Slots must be respected. The report's independently proposed “day_index”, exact healing *days* and “new day” state clock need explicit feasibility analysis rather than silent insertion into a W-based model.

## Prioritized no-code / minimal-code research diagnostics (proposals, not tasks)

1. **H0 — Evidence inventory:** exact Master Health + retirement + ranking + Entry contract; current health model/stored events; what is active versus no-op/projection only. Mark each item DECIDED/TARGET/IMPLEMENTED/OPEN and current-data observability.
2. **H1 — Health fact consistency:** negative/schema tests for Injury vs Illness, At Risk/Active/Recovering/Recovered, recurrence links, recovery windows, historical lineage and permanent-consequence source requirements. Verify Save/Load/replay already preserves them; no new random model.
3. **H2 — Match integration boundary:** verify which projected health facts are consumed in actual match simulation, and that a purely descriptive projection does not cause hidden numeric changes. Characterize open owner/calibration questions without inventing coefficients.
4. **H3 — Data coverage:** search for legally and methodologically valid adult male squash injury and true exposure/recovery data; separate mixed-sex elite registry from youth subgroup and general club populations. Report "not measurable" rather than fit invented targets.
5. **H4 — Optional future causal candidate tests:** only after owner consent, compare simple exposure-dependent hazard (with appropriate denominator and medically reasonable admissible outcomes) against null model; report sensitivity, per-player overdispersion, outcome and restart consistency.
6. **H5 — Sport-integrity invariants:** medical event logging, immutable history, ability to resume after restart and unrelated-random-stream isolation only once events are truly implemented. Do not claim a 50-season health acceptance run completed.

The study offers **16 experiment ideas** (EXP-01..EXP-16), not 16 execution results. The most defensible invariant candidates in current pre-alpha context are the anti-double-counting and integrity themes of **EXP-06, EXP-15 and EXP-16**, preceded by actual-data observability. Proposed numerical calibration tests **EXP-01/02/03** cannot inherit targets wholesale without corrected denominators and sexes.

## Recommendation to Work (when available)

- Treat Gemini as a creative scientific hypothesis generator. **Keep study and correction file alongside each other** so that later reviewers cannot silently use its spurious numeric parameters.
- Obtain a truly independent audit of the original 59-page DOCX before selecting specific injury rates, severity duration distributions, state transitions or epidemiological calibration.
- Coordinate with the **already decided and partially implemented Health V1** before allocating any implementation task.
- Do not change Master, implement a new Health subsystem, impose a retirement cap, introduce protected ranking or medical retirement probabilities, commission costly empirical runs, or merge this research as a gameplay approval.
- Owner alone decides merger/numbering; Work is not contacted by this PR.

**No product code, Master or health data changed; no simulations or tests executed.**