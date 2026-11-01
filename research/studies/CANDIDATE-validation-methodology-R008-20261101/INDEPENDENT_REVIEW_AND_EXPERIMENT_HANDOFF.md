# R008 — independent methodological review and experiment handoff

**Date:** 2026-11-01  
**Research status:** PROVISIONAL/UNAPPROVED methodology, not a validated release or a newly adopted product rule.  
**Author research:** [23-page ChatGPT R008 report text](CHATGPT_R008_FULL_TEXT_EXTRACT.txt), extracted from the user-provided original DOCX. The original DOCX is not in this PR. Mathematical Word formula/table layout is not guaranteed to survive plain-text extraction.  
**Repo state checked:** `buuk` `a07c51548ef3f398edba3e92551008ab2d61ec61` and the open PR list. No sporting code, tests, Master or acceptance configuration were edited.

## Verdict

**Methodologically strong cross-system research with several important qualifications.** R008's central point is essential: a deterministic implementation may be *verified* yet not be a realistic sports model; a model can reproduce marginal PSA statistics while being causally misspecified. The most valuable suggestions are the four-level hierarchy, explicit falsifiability, scenario/seed manifests, honest aleatoric vs parametric uncertainty, no-lookahead historical assessment, proper survival censoring, and negative controls that demonstrate a test can *detect* a planted defect.

Unlike earlier numerical sport-domain studies, R008 generally **does not claim to have calibrated specific squash coefficients**. It correctly distinguishes Bayesian posterior predictive checks (PPC) and simulation-based calibration (SBC) from a distribution of outputs produced by a **fixed parameter configuration with varied RNG seeds**. The latter does not itself generate a posterior distribution or validate Bayesian computation.

The 15 experiments are **15 hypotheses/plans, not 15 executed tests**. Some need missing production capabilities, some would consume high runtime, and others overlap existing open integration PRs. They should not automatically become new release gates.

## Methodological facts spot-checked

- [Sargent, Verification and validation of simulation models (2013)](https://doi.org/10.1057/jos.2012.20) explicitly distinguishes model verification, conceptual, data and operational validity.
- [Stan User's Guide: Simulation-based calibration](https://mc-stan.org/docs/stan-users-guide/simulation-based-calibration.html) confirms that SBC tests a Bayesian posterior sampler using prior, likelihood and posterior draws; merely varying world seeds is not SBC.
- [Glasserman & Yao, Common Random Numbers (1992)](https://doi.org/10.1287/mnsc.38.6.884) discusses conditions under which CRN benefits are guaranteed and why event timing/recursions matter. Same-seed coupling of unequal rally/season event sequences is not automatically statistically efficient or causally well matched.
- Current **AGENTS.md** confirms explicit RNG, versioned historical facts, owner-only merge and separation of product status; the test policy/full pre-alpha acceptance constraints remain distinct.

Only selected references and current technical claims were independently checked, not all cited statistical papers or the original equations. These are methodological spot-checks, not peer review of the whole 23-page report.

## Corrections and cautions before engineering

### C1. Parameter interaction is NOT equivalent to duplicate counting

R008's §Sensitivity section illustrates large Sobol total-effect vs first-order-effect indices as a signal for mechanism interactions and possible double counting. **That difference measures interactions under an assumed input distribution, not that the same biological/sport effect was applied twice.** Two genuinely distinct causes can strongly interact legitimately. Double counting requires an explicit causal/implementation path, correctly defined interventions, and checking whether separate terms duplicate the *same* intended process.

Likewise the text's suggestion that a sum of individually reported mediated path effects exceeding the total effect proves over-counting is **not generally valid** for non-additive outcomes, mediating interactions, cross-world dependencies or correlated mediators. Define a causal diagram and scale, then use a principled decomposition or report interaction residual; do not demand naive additive path sums.

**Use Sobol/Morris for sensitivity and prioritization, not as a direct 'double-counted = YES' flag.**

### C2. Identical seeds do not guarantee perfectly paired events

The report itself acknowledges this important limit. Semantic RNG namespaces are a sound **candidate design pattern**, but a per-rally event under gameplan B may not exist under A. Pair only exogenous quantities at the same semantic event identity. Distinguish non-descendant from descendant events; legitimate future ranking/entry consequences may diverge after a causal change. Do not demand full-world bitwise identity after an intentional sporting treatment.

### C3. Verification pass conditions vs realism diagnostic outcomes

Exact Save/Load/replay equality can properly be a **hard invariant** with zero tolerance. Skill monotonicity, game length CDF, upset rates, national dynasties and career distributions generally need *conditional data, uncertainty and specified comparison windows*; an aesthetically appealing deviation or single-seed long dominance is not automatic failure.

Synthetic no-op and planted-error (negative-control) tests can verify a diagnostic's *ability to detect an error*, but a planted failure is not evidence of correct empirical calibration.

### C4. Conditional FAX world transfer, not aggregate PSA targets

FAX's variable `W` weeks/year (Earth 52, FAX reference 61), tour population, country inputs and historic ranking policies differ from PSA. Match mechanism conditionals may be transferable with caveats, not raw Top-10 country shares, seasonal event counts or one universal ranking churn baseline. Prevent learning and validation on the same reference targets.

### C5. Missing/unimplemented domains cannot pass a realism gate

The actual `Health V1` has record/history/projection, but numeric health effect and stochastic health checks are declared unsupported (`numeric_effect_applied=False`). A full health causal-chain test (**EXP-07**) cannot currently be treated as an executable production-calibration test. Likewise 50/100-season population and career ensembles depend on complete long-run system integrations. Record tests as `NOT APPLICABLE / NOT IMPLEMENTED / NOT OBSERVABLE` when needed, never fabricate a pass.

### C6. Proposed budgets are not accepted pre-alpha obligations

The R008 budgets (examples: 500–1000 paired matches; 30–50 × 10-year worlds; 30 × 50-year and 10–20 × 100-year worlds) are **suggested experimental sizes**, not runtime-proven affordable runs, calibrated statistical power calculations or Master release requirements. First measure wall-clock, memory, source provenance and test utility; preregister bounded seed sets and stop rules. Do not run a multi-thousand season experiment just because a research document printed it.

## Proposed prioritization of R008's 15 experiments

| ID | Domain / report heading | Current action | Boundary |
| --- | --- | --- | --- |
| 01 | Exact Save/restart/replay invariance | **Coordinate existing tests first** | PR **#1713** already covers real one-Edition Saved/physical SQLite restart; **#1718** covers two sequential Editions; do NOT duplicate. Neither equals the 1,000-player/80-Edition/50-season release evidence. |
| 02 | RNG namespace isolation | **High-priority narrow diagnostic if uncovered** | Distinguish true non-descendants from treatment descendants; inspect current seed hierarchy before proposing code. |
| 03 | Gameplan paired counterfactual | **High-priority R006 candidate** | See tactical study **#1714**; compare control/pace/workload mediators and legacy archetype/momentum effects. No permanent effect removal without decision. |
| 04 | Match skill monotonicity / upset | **High-priority cheap baseline** | Stratify skill, Form, fatigue, opponent, match format; no invented PSA-wide win-rate target. |
| 05 | Rally-to-match outcome aggregation | **Medium/high local diagnostic** | Compare conditional distributions and strength-specific tails, not a single blended percentage. |
| 06 | Fatigue/recovery conservation | **High-priority cheap invariant** | One match impulse, zero load, recovery paths; avoid pretending it proves match realism. |
| 07 | Health causal-chain ablation | **Deferred / partially not executable** | Health numeric sporting effects and health checks not implemented/approved. Validate existing fact/projection integrity first, using R005 **#1709**. |
| 08 | Ranking-policy invariance | **High-priority source-scoped test** | Frozen sporting results must not be silently modified by a ranking rule variant. |
| 09 | Entry/ranking feedback | **Later: requires actual longer native continuity** | May be a genuine positive feedback of chosen ranking rules, not necessarily a bug. Need conditional threshold and alternative controls. |
| 10 | Career survival and censoring | **Later: cohort evidence prerequisite** | Left truncation, right censoring, correct lifecycle; coordinate C5 Draft **#1700** and merged R001. |
| 11 | Parameter identifiability ridges | **Screen after observability inventory** | Perturb only valid, currently effective sporting parameters; avoid fitting undeclared/deferred parameters. |
| 12 | Global sensitivity interactions | **Phase 2 reduced screening only** | Input distributions/uncertainty ranges must be grounded; interaction ≠ double counting. |
| 13 | Held-out historical mechanisms | **Requires R007 corpus and licence review** | Chronology, scoring regimes, missingness, support for exact observables. |
| 14 | National/generational dynasty | **Later ensemble / R003** | No nationality→innate talent shortcut; historical country/time and censoring; no fixed parity targets. |
| 15 | 1/10/50/100 season validation ladder | **A staged future science programme** | 1-season narrow now when valid; 50/100 only after runtime, memory and full-flow evidence. Owner alone sets actual release gates. |

## Minimum viable scientific-validation package for Work to consider

If Work later chooses a single small research-to-engineering slice, evaluate **only unaddressed gaps** in this order:

1. **Inventory existing tests, Saved observability, versioned source/baseline contracts and exact overlaps with PR #1713/#1718 and other concurrent work.** A currently open, not-yet-merged test is not 'release verified'.
2. **Write a nonmutating validation-manifest proposal** (engine commit, source package fingerprints, settings, fixed seed set, independent vs shared random namespaces, supported observables, primary hypothesis, negative control, actual runtime budget). Do not make it a global mandatory schema without owner approval.
3. **First independent checks**: no-op vs deliberate mutation diagnostics; one-step fatigue conservation; effective-strength decomposition / skill monotonicity; no-lookahead & ranking-source boundaries where current state is actually available.
4. **Keep failures explanatory**: distinctions `RULE/IMPLEMENTATION`, `STRUCTURAL`, `EMPIRICAL`, `NOT OBSERVABLE`, `NOT IMPLEMENTED`, `UNDECIDED PRODUCT POLICY`. Do not return `REALISTIC=true` as a single scalar.
5. After R007's source-data atlas arrives, evaluate which local distributions can be compared to held-out PSA data without legal or temporal issues, and which FAX aggregates are intrinsically incomparable.

## R001–R008 integration

- R001 career C5 Draft **#1700**: survival cohorts/censoring; do not use youth OVR as observed junior PSA ranking.
- R002 match realism Draft **#1702**: rally/skill/score/duration conditionals.
- R003 ranking/dynasty Draft **#1703**: ranking-policy frozen histories, generational and national diversity.
- R004 Entry Draft **#1705**: entry decision time, no-lookahead and source-ranked published snapshot.
- R005 Health Draft **#1709**: fact/projection, fatigue separation, RNG and Save/Load; no adult male injury hazard derived from mixed/youth studies.
- R006 tactics Draft **#1714**: axes, adaptation, archetype/momentum ablations without inventing new gameplan bonuses.
- R007 Gemini **pending**: corpus/data provenance; do not assume available yet.
- R008 this archive: common testing methodology across the ecosystem; avoid duplicating existing integration PRs.

**Handoff governance:** Research is not a product decision, task authorization, code patch or release gate. Work has not been sent this handoff. Owner alone merges; no branch merges made and no simulations run.
