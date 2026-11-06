# Tactical/Gameplan Deep Research — technical verification and scientific-program handoff

**Date:** 2026-11-01  
**Status:** first critical review and bounded scientific synthesis. Not an external replication of all cited sport studies; no tests executed, no sporting changes approved.  
**Source:** [23-page ChatGPT Deep Research text archive](CHATGPT_TACTICS_DEEP_RESEARCH_TEXT_EXTRACT.txt); original DOCX not committed; mathematical Word formatting may be lossy.  
**Program label:** candidate R006, **not assigned by Work/owner**.  
**Latest branch checked for key production facts:** `buuk` `a07c51548ef3f398edba3e92551008ab2d61ec61`.

## Summary

This study does not show that squash needs a shot-by-shot/POMDP implementation. It supplies a credible research direction: play style should affect **space, time, control, pace, risk and workload**, with outcomes emerging downstream; adaptive strategies should be limited by observation and uncertainty rather than clairvoyant hidden opponent attributes.

The **highest immediate engineering/research value** is auditing the current Match Engine's overlapping pathways before adding another model. Existing four-axis Gameplan V1 / hidden-control abstraction is an appropriate pre-alpha *candidate*, but current coefficients and effect isolation are not empirically validated.

The paper lists **24 experiments**; treat them as research suggestions, NOT 24 pre-alpha acceptance gates.

## Fresh code cross-check (read-only)

Current `src/beta_engine/domain/matches/match_engine.py`:

1. Uses `_style_and_archetype_adjustment(..., include_style=not gameplan_applied)`: the legacy `STYLE_MATCHUP_EDGES` term is disabled when `stamina.within_rally_effort_applied` signals Gameplan-style play, **but `ARCHETYPE_MATCHUP_EDGES` remains applied independently**. Thus direct archetype strength edges can coexist with new Gameplan effects; whether they *duplicate* a sporting effect is not yet empirically demonstrated.
2. Maintains `momentum_adjustment = 0.035` and adds this to the **internal strength** of the prior set's `momentum_owner`; this is **not** a direct +3.5 percentage point win chance. Test whether this legacy influence reproduces a legitimate short-run effect or introduces a narrative bonus beyond the physical/form/gameplan paths.
3. Match/score processing and seed usage are nontrivial; ablation/paired-seed tests need **counterfactual RNG care** because gameplans can change rally count/order and thereby which random draws are consumed. Same seed only is not automatically a causally paired alternative.
4. Gameplan adaptation may be score-sensitive; the study's proposal for finer awareness of accumulated pressure/energy is a **new hypothesis**. Do not infer a broken implementation just because every plausible signal is not used.

**No claim of a confirmed defect or an automatic fix:** direct modifiers could be deliberate author-approved mechanics. Any weakening/removal requires Master/owner review after controlled observations.

## Science boundary

- Studies of T-area control and elite situation-awareness support the role of spatial/time pressure as a **descriptive or associational correlate**, not an experimentally identified universal % point bonus.
- Stable long-term styles and context-sensitive tactics can coexist; inter-player differences and opponent specificity invalidate simplistic universal rock-paper-scissors style matrices.
- Empirically reliable context-specific coefficient amplitudes are scarce; do not promote an attractive mechanistic explanation to calibrated probability law.
- Behavioral signatures should be measured conditionally on player skill, opponent, format and recorded physical state, to distinguish tactic from quality.
- Four axes `Risk`, `Tempo`, `Court Positioning`, `Variation` may not have equally strong observable effects; the tentative weak-VARIATION claim requires an ablation, not source-code intuition.
- Distinguish **implemented/stored** data from inferred physical outcomes and from truly observed rally metrics. A hidden-control abstraction cannot be claimed validated by real T-position coordinates unless its proxy is independently justified.

Selected sources cited in the research:
- [Vučković et al. on T-area control](https://pubmed.ncbi.nlm.nih.gov/19551552/)
- [Murray et al. on situation awareness](https://pmc.ncbi.nlm.nih.gov/articles/PMC6527813/)
- [Squash tactical decision-making](https://pubmed.ncbi.nlm.nih.gov/29599875/)

These are candidates for later independent literature verification. The present document's **code** claims were spot-checked at the branch listed above; full literature and code audit remains incomplete.

## Smallest non-implementation diagnostic proposal

| Order | Test | What to measure | Data/approval note |
| --- | --- | --- | --- |
| 0 | Observable current state | Actual post-rally/game Gameplan, control, workload and effective-score logs; versioned seed/timing | Do not derive invented hidden values from final box scores |
| 1 | Gameplan active / legacy-archetype effect isolated | Controlled strength or outcome decomposition with and without archetype edges in a **test fixture only** | Requires authorized experimental toggle, **not** permanent code removal |
| 2 | Legacy momentum `+0.035` isolated | Set-to-set transition and outcome contrast while controlling original state and scoring amplification | The effect is an internal-strength delta, not a direct win-rate delta |
| 3 | `Variation` and other axis ablation | Effect on control/pace/duration/workload and true result; compare all axes | Isolate actual existing controls and opponent context; avoid forcing equal axis power |
| 4 | Opponent estimate and adaptation | Compare correct/noisy estimates and STICK/ADAPT in controlled contexts; determine whether adaptive selection is excessively accurate | No magic access to hidden attributes/future rally outcomes |
| 5 | Invariants | Same-state/seed replay, no double counting Form/effort/health; equivalent Save/Load sporting results | Separate architecture test from realism calibration |

No empirical target/win percentage is accepted here. Work should first determine whether these diagnostics are already covered by tests and Saved history and choose the smallest no-conflict slice; owner must approve changes.

## Cross-study research programme synthesis (for Work; not product canon)

| Study | Primary observable research question | Relevant shared integration boundary | Risk to prevent |
| --- | --- | --- | --- |
| **R001** merged talent pipeline, Draft **#1700** C5 diagnostic | Which youth-skill cohorts produce observed late Top-N senior paths? | Stable player age/cohort ID, ranking history, career Save completeness | Youth OVR is **not** a played junior ranking; right censoring/late entry |
| Candidate **R002** Draft **#1702** match realism | Do rally/score/duration distributions respond appropriately to strength gaps and fatigue? | Shared Match seeds, effective-skill composition and source history | A population-wide 3:0 mix from PSA is not a required FAX constant |
| Candidate **R003** Draft **#1703** rankings/dynasties | Are Top-N mobility and national eras emergent across long seeded histories? | Historical **published** Official Ranking snapshots, date/country at event | Hardcoded national balancing, sampled vs interpolated PSA history |
| Candidate **R004** Draft **#1705** Entry AI | Do players select eligible tournaments from **known at the deadline** alternatives? | Entry snapshots, source ranking, application/reserve/withdrawal provenance | Lookahead, applying PSA historical scoring to FAX, unsupported MNL weights |
| Candidate **R005** Draft **#1709** Injury/Health | Are current Health facts valid/replayable, and do we avoid duplicate Form/fatigue impact? | Health V1 record history → frozen Match → Entry/Ranking/Career | Misusing youth/mixed-sex injury rates as male professional hazard |
| Candidate **R006** this study | Does real Gameplan V1 produce observable tactical variation without duplicate legacy archetype/momentum effects? | Match strength, style axes, hidden-control, fatigue/form, RNG | Hidden strength bonuses presented as “tactics”, or arbitrary match-up counters |

### Shared diagnostic infrastructure before new mechanics

**Tier A — integrity, no sporting calibration required:** historical source identity; deterministic seed/restart; immutable events and snapshots; player-knowledge timing; no unintended RNG bleed; signed provenance. Prioritize the narrowest currently uncovered tests rather than duplicating functionality across PRs.

**Tier B — existing-model ablations:** health no-op vs Form/Stamina; gameplan vs archetype/momentum; Entry ranking/source deadlines; talent career early/late outcomes. Interpret result distributions with versioned source data and explicit observation limits.

**Tier C — empirical realism:** legally available professional squash raw data, population definitions, longitudinal exposure, compatible competition format/ranking cadence, confidence intervals and multi-seed simulation. No guessed numerical pass/fail bands.

**Guardrails:** no Master rewrite; no assumed 50-season validation; no health injury rates from McCartney/Horsley/Rejeb without adult-male person-time; no new random career dropout; no automatic tournament finance penalties; no national parity timer; no artificial momentum “fix” by intuition; no POMDP/shot-by-shot expansion before proof of need.

**Work handoff when available:** review state of research PRs, select at most one high-value, already-authorized, nonconflicting diagnostic slice, and return a fact-based feasibility/implementation proposal. Until then, do not automatically launch agents, edits, heavy simulations or merges. Only the owner decides the PR merges.

**Scope:** research documentation only; no code, Master, tests, ranking or sporting configuration modified.
