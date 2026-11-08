# R010 — Critical review: mental traits, situational pressure, clutch and momentum

**Date:** 2026-11-01.  
**Status:** FIRST INDEPENDENT RESEARCH/CODE AUDIT; selected papers spot-checked, no full systematic literature review or actual numerical experiments.  
**Original:** owner-uploaded 9-page DOCX "Psychika elitního squashisty – vlastnosti a momentální stavy.docx", available in this PR only as [text extraction](CHATGPT_R010_FULL_TEXT_EXTRACT.txt).  
**Code baseline:** `buuk` commit `a07c51548ef3f398edba3e92551008ab2d61ec61`. Re-check latest HEAD before any further engineering.  
**Authority:** Master/AGENTS and owner decisions supersede this study. No PR overlap or code mutation authorised. **Research candidate R010** pending Work/owner. 

## Verdict

**Useful topic and sound broad conceptual separation, but substantially WEAKER evidence than a complete 2026 Deep Research.** The nine-page report does not do the requested line-by-line Match Engine audit and offers **unresolved citation markers only** rather than a usable full bibliography/URLs. The DOCX has no actual external hyperlink relationships. Its primary advice to implement a simple score-based psychological modifier for pre-alpha is **premature**, because the current code **already** includes an endgame pressure modifier. Several experiments are constructed so that the model is considered wrong if it *doesn't* display a chosen effect; this is circular and would artificially engineer drama.

Do **not** treat this as permission to add Mental/Clutch/Choking bars, pressure multipliers, heroic comeback boosts or a gameball bonus, or to change the existing `+0.035` momentum without an approved, falsifiable diagnostic.

## Current implementation (READ ONLY, actually verified)

**File:** `src/beta_engine/domain/matches/match_engine.py` on checked `buuk`.

- **Base effective strength (§ `_base_strength`, ~lines 1789–1805):** weighted `technique*0.21 + movement*0.18 + physical*0.14 + mental*0.14 + consistency*0.12 + clutch*0.11 + recovery*0.10`, divided by 99, plus Form/Sharpness/Fatigue/Health/Travel input modifiers. Thus **Mental and Clutch affect all rallies via base strength**; they are not merely pressure-only traits.
- **Late-score term (§ ~3197–3213):** `close_phase = games_a >= games_to-2 and games_b >= games_to-2`; when true, `pressure_shift = ((clutch_a+mental_a)-(clutch_b+mental_b))*0.18` is added to both baseline and stamina-adjusted rally probability. `Consistency` also adds a separate `consistency_delta * 0.06` across rallies.
- **Interpretation:** for PAR11, `9:9` triggers this specific close-phase adjustment but `10:8` (a gameball) **does not** because both players are not ≥9. This is an important semantics/documentation question, **not by itself proof of a bug**: the intended policy may be 'both-near-finish deuce-like phase', not 'every gameball/matchball'.
- **Momentum:** `momentum_adjustment = 0.035` adds to prior set winner's **internal strength** both in step and full-set execution paths (approx. lines 331–338 and 1053–1060). It is not +3.5 percentage points to point-winning probability. The method uses the set's own prior winner, not a measured transient psychological state; needs controlled ablation to distinguish sporting feature vs dramatic history bonus.
- **Mental opponent estimate / risk/effort:** separate code paths use `mental` for perception noise (around line 2114), tactical effort selection (around line 2829), and serve execution (around line 2747). This increases the importance of a causal map: Mental is not a single only-psychology modifier.
- **Mental stamina:** actual post-rally snapshots label `unsupported_dynamic_state=("mental_stamina",)`. The existence of attributes or other pressure terms does not mean a dynamic mental fatigue bar is implemented.
- `pressure` also names a **court-control/workload** mechanism in the simulation. Never conflate spatial control pressure with **perceived psychological stakes**, nor assume that the word's presence implies an emotional state in player data.

**What is still unknown:** whether the overlapping base/late-score/serve/perception effects are intentionally orthogonal, their intended calibration and whether observed scoring behaviors can separate them. The overlap is a **risk**, not an empirically demonstrated 'double count'. Master may already mandate certain pressure/gameplan semantics.

## Selected external science checks

1. [ESSA position statement (Schweickle et al., 2026)](https://doi.org/10.1007/s40279-026-02472-x): pressure may facilitate OR impair performance. This is a general position statement, not a squash-specific rally probability, individual Clutch coefficient or gameball-specific effect size.
2. [Counteracting choking under pressure, 2026 meta-analysis](https://pubmed.ncbi.nlm.nih.gov/41951087/): **21 studies**, broadly beneficial interventions but effects are **less robust in open-skill** sports after publication-bias adjustment. Squash's dynamic opponent-dependent play is not equivalent to a closed target-accuracy task. This review does NOT estimate an automatic performance bump in late squash points.
3. [Meier et al. (2020) professional men's tennis](https://doi.org/10.1016/j.joep.2020.102269): **4,930 game observations from 141 men's Grand Slam tennis matches**, using service breaks and exogenous rest interruptions to distinguish strategic vs psychological momentum. It provides research evidence **in tennis**, not a meta-analysis, not a fixed squash momentum strength term, and not proof that winning a set directly improves the next one.
4. [Murray et al. (2019) elite squash situation-awareness](https://pmc.ncbi.nlm.nih.gov/articles/PMC6527813/): descriptions of 'pressure' principally concern **on-court spatial/tactical control**, not psychological choking. Don't relabel pressure position as a measured mental-state variable.

This spot-check does not exhaustively verify every placeholder citation in the original document; without complete references, provenance for those claims is not auditable from the document.

## Specific logical problems in the proposed R010 experiments

| Proposed diagnostic | Issue | Safer revision |
| --- | --- | --- |
| “9:9 vs 5:5 should have same match outcome under no psychology” | Score changes **mechanical set win probability** even if future per-rally chance is identical. Score-conditional performance can only be compared on the **next rally's conditional probability** after controlling effective strength/serve, not final set win chance. | Freeze players, stamina, gameplan and other states, compare **next-rally** probabilities and break down separate score-based terms. |
| “Same Mental/Clutch on each side, changed score should produce an effect if implemented” | Existing endgame term is a **difference between players' (Mental+Clutch)** and vanishes for exactly equal mental profiles; no observed difference does not imply the mechanism is missing. | Use **asymmetric, independently varied** Mental and Clutch profiles and separate baseline strength differences. |
| “Same raw total rating, higher Mental/Clutch should auto-win under pressure” | Changing Mental or Clutch also changes base strength. Equal OVR is not equal effective pre-pressure strength; the test confounds baseline and late-score terms. | Construct controlled effective-strength-matched contrasts or instrument the probability components. |
| “If no effect, pressure/choking/momentum missing, so implement it” | Model validity does NOT require an extra psychological bonus in every stressful state, particularly if no squash data identify its size. | Start with a null baseline; assess whether data **support** a residual pressure effect after quality, strategy, service and fatigue controls. |
| Momentum vs winning streaks | Pure independent Bernoulli draws generate substantial streaks, and heterogeneous player ability/tempo further creates apparent persistence. | Compare streak/run-length distributions and conditional outcome dependence with calibrated null models, not 'does a streak occur'. |
| Winning previous set → next set | Prior set winners are likely stronger or in better shape; simple `P(next set win | last set win)` is confounded. | Use pre-specified matched states, source-known skills, exogenous interruptions if supported, or an intentionally isolated simulation ablation. |
| Favored player 0–2 down necessarily chokes | The result could be tactics, poor play, selective data, underdog performance and fatigue. | Don't force panic just because a favorite loses. |
| Suggested 1,000 match iterations | Arbitrary count without power/variance assumptions; not a fixed pre-alpha release mandate. | Pilot bounded deterministic seed ensembles with runtime measurement and confidence intervals. |
| Score pressure 9:10 vs 9:9 | Different states include different probability of game termination; a feature might correctly represent stakes without an immediate strength bonus. | Measure score-derivative of *conditional rally performance* separately from mathematical leverage, not aggregate win odds. |
| “No empirical divergence means baseline is validated” | A fit to pooled statistics is not unique identification of underlying mechanisms. | Cross-check multiple conditional quantities, held-out matches if access is legal and source data exist, negative controls and implementation provenance. |

**Crucial:** a statistical 'null' is not proof that mental traits don't exist; lack of data can make parameters unidentifiable. Conversely a designed forced pressure effect is not evidence of real psychology.

## Minimal high-value future diagnostics, proposed only

**Read-only instrumentation / existing-unit-boundary checks first; don't issue duplicate PRs until test ownership is checked.**

1. **P1 — Actual pressure coefficient map:** enumerate every `mental/clutch/consistency/momentum` code path, expected source semantics and where it enters per-rally probability, including Gameplan/adaptation/serve; distinguish spatial 'pressure'.
2. **P2 — Endgame boundary policy:** compare identical states near `8:9`, `9:9`, `10:8`, `10:9`, `10:10`, `11:10` under correct terminal-state validity. Explicitly ask whether close-phase policy means deuce-like, every gameball, every matchball, or stakes-weighted expectation. No semantics change without decision.
3. **P3 — Mental vs Clutch orthogonality:** isolate base strength, chance adjustment and estimate/effort pathways. Compare controlled players whose **nonpressure effective strength** is equal, then vary one candidate trait at a time.
4. **P4 — `+0.035` momentum ablation:** distinguish prior-set winner strength shift from direct score math, fatigue, previous-set strength selection and RNG alignment. Never interpret `0.035` as 3.5 percentage-point win-rate shift.
5. **P5 — Null streak and conditional pressure model:** compare observed seeded sequences to a per-player/format/strength-conditional no-momentum model, avoiding naive run-count inference.
6. **P6 — deterministic replay and logging:** preserve canonical seed hierarchy, per-rally score, actual source availability and Saved/Restart; coordinate existing integration PRs instead of duplicating them.

Design each as falsifiable **model/contract** audit with result labels IMPLEMENTED/PARTIAL/UNSUPPORTED/UNKNOWN; do not declare `REALISTIC=true` without independent empirical calibration.

## Relation to R002, R006 and R008

- R002: game and match outcome distributions can reveal odd scoring tails, but can't identify a particular psychological cause from margins alone.
- R006 **[#1714](https://github.com/Jasmetk0/squash-tour-beta/pull/1714)**: Gameplan/Archetype/Momentum are already identified as potentially overlapping; combine future Gameplan × Mental/Clutch ablations under one experiment owner.
- R008 **[#1719](https://github.com/Jasmetk0/squash-tour-beta/pull/1719)**: distinguish exact algorithmic/Save invariants, structural response and externally calibrated sport evidence.
- R009 **[#1728](https://github.com/Jasmetk0/squash-tour-beta/pull/1728)**: alternative globally popular FAX can differ from PSA psychology/culture; don't encode national innate mental strength or winner personality by nationality. Source-known historical context still matters.

## Governance

This is a **research-only archive** with a selective critical review, not approval to add a mental-state model, stage pressure bonus or change Match code. No tests, simulations or model ablations actually ran. Work not contacted. Owner alone merges. No Master or game code modified.
