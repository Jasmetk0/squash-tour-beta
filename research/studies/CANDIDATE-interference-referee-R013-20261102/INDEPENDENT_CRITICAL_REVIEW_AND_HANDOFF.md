# R013 — Independent critical review: WSF interference rules, officiating, actual Match Engine and measured decisions

**Reviewed:** 2026-11-02.  
**Status:** SELECTIVE PRIMARY-SOURCE AND CURRENT REPOSITORY AUDIT ONLY. No full end-to-end simulated Match regression or scientific parameter estimation executed.  
**Source:** Owner-supplied 21-page ChatGPT document "Výzkumná zpráva_ SQUASH ENGINE – R013_ Interference, rozhodčí a realismus.docx". Its searchable [text archive](CHATGPT_R013_INTERFERENCE_TEXT_EXTRACT.txt) is **not** the original DOCX; citation markers like `【25†L68-L75】` are source-snippet references, not directly usable bibliography.  
**GitHub snapshot:** `buuk` commit `a07c51548ef3f398edba3e92551008ab2d61ec61`; re-check branch and PR overlap before any later programming.  
**Authority:** `AGENTS.md`, Master, `docs/RALLY_RULES_RESOLVER_V1.md`, actual domain Match files. No new rules/coefficients accepted here.

## Overall verdict

**The research cites valuable official World Squash Officiating (WSO) sources and outlines useful experimental questions, but the 'audit of current Match Engine' is mostly speculative and misses significant already implemented functionality.** Its recommendation to build a conditional probability model instead of an allegedly constant random model is largely redundant with the current engine. Its “decision density” paragraph mixes **points, played rallies and hypothetical match counts**, invalidating the numerical inference about percentage of rallies needing a decision.

The most useful next activity is a **bounded no-code/only-if-authorized test of current rules semantics and reporting**, not replacing the existing Match resolver or copying 2026 WSO statistics as the mandatory FAX global history.

## Primary-rule evidence

1. [Official WSO/World Squash Rules of Singles Squash (Sep 2025)](https://worldsquashofficiating.com/rules-of-squash/) confirm Rule 8 Interference has multiple independent conditions: fair view, access, reasonable swing and front-wall freedom; general conditions for `NO_LET`, `YES_LET` and `STROKE` depend on ability to make a good/winning return, striker effort, actual obstruction, contact and decisions. A **No Let for an already stopped appeal** is not the same as “an ordinary interference-free rally ended with a No Let”: ordinary scoring remains `POINT_AWARDED`. For a genuinely prevented swing (8.9.2), a stroke may be awarded to the striker.
2. [2026 Officiating Standards Framework](https://worldsquashofficiating.com/officiating-standards-framework/) applies from **30 Aug 2026**. The **Guiding Let** is a practical referee-management practice (Yes Let + instruction in an early/repeated pattern) and **not a new formal Rule 8 outcome**. Historical FAX cannot automatically use 2026 Earth officiating policy.
3. [WSO Palm Hills PSA World Championships 2025/26 report, 21 May 2026](https://worldsquashofficiating.com/behind-the-decisions-cib-palm-hills-psa-world-championships-2025-2026/) gives **1,960 decisions / 124 matches = 15.806 decisions per match**, split **813 Strokes (41.48%), 738 Yes Lets (37.65%), 409 No Lets (20.87%)**, across men's and women's draw. WSO describes approximately **one decision per four *scored points***; this is not '4 total abstract rally attempts' and WSO's three-way percentage is **conditional on decisions**.
4. **Key denominator/arithmetic error in R013:** the paper says ~15–16 decisions per match and assumes **120 rally attempts/match**, then calls that **25% of rallies**. In that hypothetical, `15.8/120 = 13.17%`, NOT 25%. A one-decision-per-four-*points* ratio can be ~25% decisions per scored points, but **does not identify** fraction of all played rally attempts (lets add unscored attempts). Nor can 120 rally attempts be derived from match length 46 minutes without a sourced count/time model.
5. **Selection/coverage problem:** 1960 decisions includes the entire tournament (both sexes and differing rounds), while elite individual 3.5 vs 6.4 *points per decision* are selected quarterfinal cohort. A high-count player's identity does not prove an intrinsic “aggressive style → 20% more interference” or “better movement → fewer strokes”; tactical game length, player/situation selection and official interventions are confounders.
6. **Unwarranted effect prescriptions:** “20–40% decision density of rallies” as a calibration target in EXP-15 is not a sourced universal male PSA rate. WSO's sample is a selected current elite event and uses a different denominator. The most immediate result from the 2026 report is **relative proportions of issued decisions** under that regime and cohort, not a validated universal per-rally generator.
7. **Terminology warning:** Source R013 sometimes conflates 'striker' (player currently attempting to strike ball), 'outgoing player', 'attacker' and 'defender' and states `STROKE` always belongs to the 'attacker'. This is dangerous, especially in cases of turning/ball hitting opponent, where rule-specific award recipient may differ. Names need stable role semantics.

## Actual engine reality — verified current files

**`src/beta_engine/domain/matches/rally_rules.py`**
- `OfficialRallyCall` supports `POINT_AWARDED`, `NO_LET`, `YES_LET`, and `STROKE`.
- Typed `InterferenceRuleContext` records actual abstract **fair_view, direct_access, reasonable_swing, front_wall_freedom, good_return_possible, winning_return, clearing_effort, striker_effort, wrong_footed_recovery, self_created_path, swing_prevented, excessive_swing, turning, further attempt, front-wall path** and related flags, with validation.
- `_interference_verdict` is a **deterministic branch-by-branch rules resolver** with decision codes for general conditions, blocked swing, inadequate clearing, intentional turning, wrong-footed access, winning returns and front wall cases. It is not merely choosing No Let/Yes Let/Stroke at random once interference occurs.
- `EffectiveRallyRulesSnapshot` freezes named version `world_squash_singles_2025_v1_2_2`, resolver `pre_alpha_rules_v1`, separate `pre_alpha_rule_situations_v1` generation profile with base `interference_probability=0.04` (and `ball_hit_probability=0.004`, `external_interruption_probability=0.001`). These are explicitly **provisional, uncalibrated**, *not* universal 4% of rallies or a direct WSO observation.

**`src/beta_engine/domain/matches/match_engine.py`**
- At an abstract terminal attempt, `interference_probability` scales by **court-control pressure and a movement proxy**. E.g. `rules.interference_probability * (0.75 + 0.35*pressure + 0.4*movement_deficit)`; not the paper's alleged constant p=0.3 for all equal players.
- Separate seeded `rule-situation-v1` facts are sampled (including `VIEW / ACCESS / SWING / FRONT_WALL`) and passed to deterministic `RallyRulesResolver.resolve`. Score, timeline, workload and replay semantics have separate data paths; there is a guard after eight consecutive lets that suppresses further incident *generation*, not an override of a real adjudication.
- Court control is an abstract modeled **state**, not a fully observed continuous geometric trajectory; this distinction does not mean court-control signals are absent.
- `STROKE` is an award under a fact-specific rule, `YES_LET` a neutral replay, `NO_LET` denial yielding point for opposing player who requested let; `POINT_AWARDED` ordinary rally finish. Replay does **not** refund physical work. Rule outcome and score lineage are stored/protected for historical read.

**`docs/RALLY_RULES_RESOLVER_V1.md`** explicitly documents score mutations:
`POINT_AWARDED` one ordinary point, `NO_LET` one point to opponent of requesting striker, `YES_LET` zero points and **same server + service box**, `STROKE` one point to relevant rule-selected player. Every `YES_LET` still consumes the actual modeled physical workload; after interruption recovery only once. This is consistent with separate scoring/rally logs and exact immutable replay.

**`tests/domain/test_rally_rules.py`** covers decision/fact contracts. Existing Match/history scoped tests documented in the same contract cover selected scoring, incident, determinism, facts and tamper behavior. These are stated in repository evidence, **not a comprehensive newly executed test suite by this reviewer**.

### Important corrections to R013 code claims

| Original research claim | Correction |
| --- | --- |
| Model likely constant interference p=0.3, only general movement | False for checked code. p=0.04 base provisional, changed by abstract court-control pressure/movement and guard, then multi-fact resolver. |
| Probably no types of obstruction | False: explicit 4 generator families + many Rule 8 resolution conditions. |
| Possibly not storing referee decisions, ruleset source or replay | False: typed Rally events capture rule facts, rule codes and identities, plus historical ruleset version, via strict schema and source hashes. |
| “More detailed shot geometry cannot be deterministic” | False as a mathematical/computer science claim. Geometry **can** be deterministic under controlled inputs/seeds; it is likely costlier and outside **current** rally-by-rally scope. |
| Must calibrate directly to 2026 PSA decision distribution to make FAX realistic | Wrong for evolving alternate FAX, different rules/eras and unknown conditional event denominators; treat Earth as source-typed external comparison only. |
| Detailed Video Review is required now | No. Official Master explicitly keeps referee-error/review depth as **later** scope. |
| No Let should be treated as no-interference normal rally finish | No: normal point is `POINT_AWARDED`. A No Let is a distinct official call following an appeal/stop and awards the opponent the point. |

## Triage of R013's fifteen suggested experiments

| Experiment | Critical action |
| --- | --- |
| 1 (Movement) | Current movement proxy is actually present. Measure source coefficient with frozen Match inputs, but *direction of stroke incidence* is not necessarily monotone; increased movement can also change rally length/contest. |
| 2 (Court Control) | Current pressure proxy present. Track incident generation vs final adjudication separately; can't infer intentional fouls from high CC. |
| 3 (Style) | Style effect specifically in incident generation not established by the paper; inspect actual live pathways and separate mediated effects via control/rally length. |
| 4 (Parity) | Match parity and average rally attempts/confounders influence *per-match* decisions; compare per-attempt, per-scored-point and per-case rates separately. |
| 5 (Long rallies) | Incident generation contains a guard for <=2 shots, but may be flat past that threshold; don't force linear rise with rally length unless evidence supports it. |
| 6 (Blocked swing) | **Strong bounded deterministic resolver test**: given consistent facts with `swing_prevented`, expected stroke to striker under Rule 8.9.2. Check if existing tests already cover. |
| 7 (No interference) | **Strong invariant**: regular unimpeded rally should finish `POINT_AWARDED`, not `NO_LET`. |
| 8 (Intentional blocking) | Requires real intentional intent/context not mere CC; don't substitute “better T control” for foul intent. |
| 9 (Repeat Yes Lets) | **Strong invariant**: no scoring/serve/box change, physical effort remains, guard is generation-only. Check existing tests. |
| 10 (Borderline No Let vs Stroke) | Typed factual rule variations can be tested today; precise centimeters not represented. |
| 11 (Score continuity) | **Strong invariant**: award codes, scorer, serve and Saved replay. Already documented; seek gap, not duplicate tests. |
| 12 (Elapsed time/workload) | **Good path**: Yes Let workload not refunded; external delay counted once; no arbitrary every-let time penalty beyond trace. |
| 13 (Historical rule versions) | Current named version/provenance exists; **new** historical alternate FAX rule effects require owner decision. Stored old events must not be reinterpreted. |
| 14 (Replay) | **Hard existing invariant**; compare actual immutable log and same-seed generation; coordinate with existing matches/science PRs. |
| 15 (WSO fit) | **Reject 20–40% of all rallies target** absent real denominator. Stratify by event sex, round, time, scoring points and unscored attempts, rule era, match length and player pairing. |

No test was run in the uploaded paper or this PR. The 15 experiments are **suggestions**, most not demonstrations that a module is currently missing.

## FAX-specific boundary

FAX is an **alternative historically evolving global professional squash world**. It may have its own accepted rules/version timelines, referee practices and style ecosystems. Contemporary Earth WSO data (mixed men/women across elite events) cannot be forced as universal FAX incident frequency or every-era adjudication ratio. The current package/ruleset must remain historically source-owned; expansion should be based on **demonstrated gaps, approved product choices and falsifiability**, not invented country or referee DNA and not narratives that prescribe controversy frequency.

### Suggested future scientific slice (requires Work/owner selection)

**R13-A — Frozen decision-boundary truth table**: use existing typed Rule 8 facts and cases, inspect source-issued `decision_code` and actual scorer/serve/box, assert no future lookups. Coordinate with `tests/domain/test_rally_rules.py`, existing match labs and any overlapping tests, do not duplicate passing gates.

**R13-B — Decision denominator report**: a read-only observer that separates `all_played_rally_attempts`, `scoring_rallies`, `replayed_lets`, `actual_decision_calls` and `source-fact interferences`, by event/time/rule version. No tuned rates until actual source and synthetic matching protocol exist.

**R13-C — Movement/control conditional sensitivity**: isolate event-generation probability, verdict conditional on facts, and final scoring outcome; use paired seed strategy that avoids RNG-consumption coupling when control branching changes. Compare original provisional parameters to null without claiming external validation.

## Governance and external-source rights

Research-only files; no modifications to `src/`, `tests/`, `docs/RALLY_RULES_RESOLVER_V1.md`, Master, World Packages, competition results, runtime constants, user Saved data or PR merge queue. No WSO PDFs copied, video assets scraped, simulations run, Work messages sent, paid services invoked or concrete product decisions issued. Owner alone merges.
