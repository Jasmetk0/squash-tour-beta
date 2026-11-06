# SQUASH ENGINE — R014 PART B
## Independent synthesis: sport-science evidence × actual player-development architecture × falsifiable tests

**Prepared:** 2026-11-03  
**Baseline read-only check:** `buuk` commit `a07c51548ef3f398edba3e92551008ab2d61ec61`; compare with latest `buuk` before implementation.  
**Purpose:** Complete the **missing project-specific analysis** left by Gemini's 28-page physiological training-monitoring study. This is a critical research/engineering handoff, **NOT a new rulebook, calibrated adaptation model, validation report, or authorization to program**.  
**Companion research:** `GEMINI_R014_SEARCHABLE_TEXT_EXTRACT_LOSSY.txt` (the mathematical/graphic extraction is incomplete; the owner retains the original Word); `INDEPENDENT_CRITICAL_REVIEW_AND_HANDOFF.md` (scientific checks and errors). Source bibliography is in the original Word.  
**Owner / governance:** Master and `AGENTS.md` supersede every recommendation below. Work is lead coordinator. Owner-only merge. Preserve determinism, explicit Save, immutable historical rule source, no invented effects or fixed national player DNA.

### 1. What Gemini actually demonstrates

| Source observation | Evidence strength & design | Defensible FAX interpretation | **Not** justified |
| --- | --- | --- | --- |
| Elite players mix Group/Matchplay/Feeding/Conditioning/Ghosting; session length and heart-rate/load differ. | James et al. 2021, **15 elite athletes (11M/4F), 166 sessions / 2 weeks**, observational; samples not 166 independent player-years. | Training activities need not impose identical **short-term load**; a future source-backed activity layer could distinguish dose types. | A numerical `+Physical` or `+Technical` per session; “Group > Matchplay” for every era/athlete. |
| External Playerload only weakly/moderately aligns with some internal TRIMP/sRPE measures. | Independent 2021 squash paper from overlapping two-week elite cohort, correlations conditional on modality and sensor. | Do not collapse fitness, mechanical work, subjective perceived effort, Form and Fatigue into one scalar. | Claiming 4 independent trainable fatigue dimensions are identified; converting sensor correlations directly to match win chance. |
| Training adaptation and acute fatigue can pull in opposite directions. | General fitness–fatigue conceptual model with sport-specific monitoring, **not longitudinal randomized squash effect**. | In theory long-term ability and short-term readiness are distinct; existing Form/Fatigue/Sharpness partly reflect this separation. | Introducing a second unlabeled fitness, form or adaptation state automatically. |
| ACWR “sweet spot” has mathematical and causal issues. | Methodological literature and general sports consensus. | No universal workload-ratio injury law should be hard-coded. | Claiming absence of any load–risk relationship or prescribing a new injury probability. |
| >10% workload increase is risky. | Running-injury cohort of **5,200 adult runners**, session distance vs longest 30-day run. | MAY motivate a future question on acute overload after separate squash validation. | **Reject as a squash per-session safety threshold.** Runners' kilometres are not squash load units. |
| Specific court tests differ from ordinary lab running tests. | Squash-specific physiological and test/retest studies (small samples). | Sport-specific measurement can better represent the intended capacity than generic run-test proxy. | Treating `VO2max`, lactate or accelerometer Playerload as directly recorded canonical FAX player attributes. |
| Age may shift physical vs technical/experienced performance differently. | Broad indirect sport-age and cross-sectional evidence, strong cohort and selection effects. | Different attribute groups and player trajectories are plausible. | Hardcoding peak at age 27/30/34 because source supports those exact ages; they are **current provisional game constants only**. |
| Bodyweight training / block periodization should always win. | Indirect and insufficient. Small 2019 squash resistance-program study reports lighter **weights G2**, not pure bodyweight **G3**, as better on certain tests. | Candidate approaches for later exploration, not a global superior mechanism. | Mandatory bodyweight-only training, block scheduling or "heavy lifting injury penalty". |

**Evidence-transfer grading:** DIRECT to squash *monitoring* is not DIRECT to years-long *adaptation*, career survival, all nations or FAX history. `Causal identified` / `observational` / `physiology-plausible` / `simulation assumption` must be recorded separately for any coefficient.

### 2. Architectural reality: two genuinely different development paths

These are *not* an indication of two simultaneously authoritative writers inside one Run; they serve **distinct historical/timeline ownership models**. Never merge the semantics just by similar names.

| Concern | Legacy authoritative sporting Week Transition | Native calendar sporting-week path |
| --- | --- | --- |
| Core entry | `src/beta_engine/infrastructure/db/player_sporting_state.py::stage_sporting_transition` → `src/beta_engine/domain/players/sporting.py::weekly_player_development_update` | `src/beta_engine/application/calendar_sporting_week_service.py::_preview` → `src/beta_engine/domain/players/calendar_sporting_week.py::develop_and_recover` |
| Effective policy | `PlayerDevelopmentPolicy`: `weekly_change_basis_points=18`, `form_influence_basis_points=4`, frozen historically. | `CalendarAnnualDevelopmentPolicy`: `annual_change_basis_points=1098` and `annual_form_influence_basis_points=244` (=61×18, 61×4); frozen in native event. |
| Calendar denominator | 18 basis points is applied as **per-week** probability without `1/W` inside this kernel. Its *production* authoritative entry is **guarded to legacy reference FAX W61** by `require_supported_legacy_sporting_calendar`; unsupported W52/W80 must not silently use it. | Normalizes by **current Run W** via `_roll(..., modulus=10000*W)`, with whole/remainder draws. Tested for W1/W52/W61/W80. |
| Age input | Integer `lifecycle.players[*].age` supplied by the lifecycle owner, adjusted by Early/Standard/Late timing ±3 years. | Exact `Fraction` derived from stored **birth year + birth week**, current Run year/offset and W; also ±3 timing. |
| Positive-growth eligibility | If age <= provisional `growth_end_age=27`, attempts +1 with probability threshold. **No check against potential** in this function; hard clamp only attribute 0..200. | Requires **both** age <= growth end AND current OVR **below** `potential_ovr`. This is a *soft-potential growth-gating rule*, not an absolute OVR clamp; historical records may still be above potential. |
| Decline & groups | If age beyond Physical/Move 30 or other 34, attempts -1, else hold; group × age mapping. | Similar Physical/Move vs other age thresholds but applies fractional age and different positive-growth predicate. |
| Form | Uses completed-week pre-regression Form for threshold, then separate `between_week_state_update` regresses to personal norm. | Uses completed checkpoint Form for threshold, then in same pure function constructs separate developed and recovered records. |
| Sharpness/Fatigue | If no actual competitive matches in completed week: weekly Sharpness -2; weekly Fatigue recovery -8 (default), Form divisor 8. | Same policy's explicit **weekly** recovery and inactivity semantics; **not normalized by W**. |
| Source & replay | Completed-week Run/Branch-owned tournament result manifest, exact roster, frozen source fingerprints, deterministic hash rolls; policy effective on completed week. | Exact source checkpoint, immutable native scheduled/played history, explicit preview/consent and manual Save, source-scoped seed, stored annual policy, original calendar. |
| Lifecycle/slot | Full legacy authoritative week path via `infrastructure/db/authoritative_week_transition.py`; season path via `application/season_transition_sporting.py`, stage before new 15-year-old prospects. | Native sporting checkpoint on its native timeline (and related native authority); **do not** present an exhibition week event as the complete Official Week Transition. |
| Test evidence (existing, **not rerun** here) | `tests/domain/test_player_sporting_week_state.py`; `tests/application/test_ordinary_season_transition.py`; immutable revision/fork boundaries. | `tests/domain/test_calendar_sporting_week.py` asserts W1/52/61/80 annual exposure, fractional age, source/preview and weekly recovery; `docs/CALENDAR_NATIVE_SPORTING_WEEK_V1.md` describes scoped acceptance. |

**Critical reconciliation item P0: POTENTIAL SEMANTICS.** `docs/AUTHORITATIVE_PLAYER_SPORTING_WEEK_STATE_V1.md` explicitly describes `potential_ovr` as a hidden soft indicator, **not an upper cap** to development. Legacy kernel follows this by not checking potential; native kernel stops *positive growth* at `ovr >= potential_ovr`. This is a **material path-level semantic difference** in player trajectories, not proof of a runtime corruption. Both rules can be programmed consistently; **which semantics are intended for future common canonical FAX runs requires authoritative owner/Work review**, not this paper's choice. Prioritize a comparative trace over a new physical model.

**Critical reconciliation item P0: TIME UNITS.** Master requires annual development anchored in elapsed fractions `1/W`; native path explicitly does this, but legacy authoritative kernel has weekly probability and is guarded to **W61** in production by `src/beta_engine/application/run_calendar_read_authority.py::require_supported_legacy_sporting_calendar`. Do NOT claim all existing native seasons and full simulation already support arbitrary W; the same file separately blocks Full Simulation when W/offset/horizon differ from legacy reference. The correct issue is migration/equivalence **before reuse on arbitrary W**; guarded legacy W61 is not itself evidence of current W52 simulation defect.

**Critical reconciliation item P1: AGE DISCRETISATION.** Birth-week fractional age in native vs integer lifecycle age in authoritative kernel can differ around birthdays/27/30/34. The correct acceptance check is *intended age policy per timeline owner*, not blindly matching the same rounding across unrelated schema versions.

**Causal observation:** neither inspected long-term attribute update consumes a scheduled `Group`, `Feeding`, `Ghosting`, `Conditioning` activity dosage or human HR/sRPE/Playerload. These two functions cannot be described as training-specific physical adaptivity. This local statement is **not** a repository-wide proof that no training feature, AI schedule or preparation pipeline exists elsewhere. Their present changes are age/Form-driven (with provenance); per-session dose-response remains not established.

### 3. Causal graph and non-duplication contract

Plausible future `TrainingOpportunity / ActivityDose` → separate `short-term workload` → `stamina/fatigue readiness` AND possibly `long-term attribute adaptation`, with mediators `recovery, health, age, development environment, training history, individual response`. This is **hypothesis topology**, not validated fitted weights.

Current consumed constructs are already distinct:
- **57 canonical attributes / OVR** represent persistent realized skill/capacity and are stored with history.
- **Potential OVR / timing** are hidden player developmental descriptors, not a hard genetic nationality bucket.
- **Form vs personal long-term Form norm** are bounded historical/current performance states.
- **Match Sharpness** changes with inactivity.
- **Long-term Fatigue** recovers through defined weekly rules.
- **Match Stamina** exists at a different per-rally/physical-work timescale and must not be replaced by human wearable metrics.
- **Health** records/Match effects and career availability have separate technical limits (R005); physiological dose→injury hazard is not calibrated.
- **Development Quality / Access / Competition / Elite Support** among six Country ratings express **opportunity context**, not direct innate talent/mentality gain.
- **Entry AI (R004), travel (R011), psychology (R010), economy (R012)** can influence competitive/training opportunity in future models, but the same causal effect must not be imposed once as a direct +rating and again via participation/results.

Avoid translating descriptive training-load differences into arbitrary +rating; avoid double-counting `match physical workload → fatigue → Form drop` *and* a separate uncalibrated penalty; avoid using rank as both an input to and confirmation of innate improvement.

### 4. Exactly 15 falsifiable scientific/technical diagnostics

**All are proposed, NOT run here.** These are **not** 15 new PRs or mandatory pre-alpha gates. Before execution, Work must check actual branch, existing test coverage, ownership and run budget. Test results must report exact source state, policy IDs, W, seed/sample space, event type, code SHA and whether measurement is a technical contract or external sport fit. For multi-seed results, report uncertainty/bounds and computational budget; an unobserved rare bug is not proven impossible.

| ID / priority | Test / controlled comparison | Measure & falsifier | Feasible now? |
| --- | --- | --- | --- |
| **D01 P0 — Path inventory** | Enumerate production writer → state/policy producer → kernel → Saved/replay consumer for legacy and native. | A writer with ambiguous or incorrectly labelled calendar authority, stale policy, or cross-domain reinterpretation violates provenance. | **Read-only now**; partial mapping above. |
| **D02 P0 — W-normalisation** | Same age/skill/Form, no time-dependent fatigue; W1/52/61/80 using **native annual policy**, matched seed ensembles. | Expected **annual** change exposure must not multiply with W (conditional on age threshold, attr cap and changing Form); stronger claim of identical per-seed paths is unnecessary. Existing `test_annual_exposure_is_inverse_W_and_weekly_recovery_is_not_rescaled` establishes a **scoped formula invariant**, not a full 50-season acceptance. | **Existing domain test + future sampled scenarios**. |
| **D03 P0 — Potential divergence** | Player aged 20 at `current OVR = potential` vs one just below, identical attrs otherwise; compare legacy vs native source-specific predicates. | Expect legacy may still grow, native cannot grow at/above potential; if both were intended to share one canonical contract, detected divergence is a **decision-required semantic mismatch**, not a sporting-statistical falsehood. | **Direct code/frozen fixture**; choose policy first. |
| **D04 P0 — Age boundary** | Same frozen player at birth-week adjacent `26.99/27.00/27.01`, `29.99/30`, `33.99/34`, for W52/61/80 native; integer lifecycle comparator isolated. | Group growth/hold/decline must match **documented chosen** boundary; no phantom growth jump from calendar remap or use of target-week future age. | **Domain fixture**, needs declared boundary contract. |
| **D05 P1 — Development timing** | Early/Standard/Late variants with identical initial attrs and matched source but recorded timing ±3 years. | Shift development timing/age only; it must not mutate `potential_ovr`, nationality or hidden bootstrap; no forced champion outcome. | **Existing domain tests**; extend only if gap. |
| **D06 P0 — Causality fence** | Identical completed-week snapshot and source fingerprints; modify target/future-week match, ranking, training or event sources without effective retrospective change. | Prior completed-week development and replay must remain identical; future leak is a technical failure. | **Existing source-boundary tests + scoped additions**. |
| **D07 P1 — Form sensitivity** | Vary completed-week Form with other latent traits fixed; compare baseline effective strength, growth threshold and post-regression Form. | Trace two mechanisms separately; high pre-regression Form affects threshold but subsequent regression should not retroactively change this week. No empirical fitness–fatigue claim from deterministic response alone. | **Existing unit tests**, isolated component trace. |
| **D08 P1 — Sharpness inactivity** | 0 vs >0 actual completed-week competitive matches (not guessed matches). | Exactly explicit weekly inactive Sharpness decay, no invented activity-specific skill loss; fabricated match counts violate source contract. | **Existing fixtures**, historical source check. |
| **D09 P1 — Fatigue and workload** | Same terminal player long-term Fatigue with and without prior physical Match load, then one weekly recovery step; separately inspect per-rally Stamina. | Exactly one documented recovery step, no negative/unbounded states or double application; distinguish weekly fatigue rule from changes attributable to played rallies. | **Current domain + cross-boundary fixtures**. |
| **D10 P1 — Attribute limits** | Player near 0/200 with growth/decline timing; source-owned policy extremes; soft potential above/below. | Never leave allowed attribute space; no unexplained hard clamp to potential in legacy; no unnoticed float drift or positive growth beyond intended native predicate. | **Unit tests exist for hard caps**; inspect missing edge cases. |
| **D11 P0 — Save/replay/policy change** | Compare saved old policy and future policy change, restore/fork/restart identical historical input. | No old state recomputation with modern constants; same source+policy+seed produces identical historical byte/hash, no duplicate update on retry. | **Existing transaction/fixture gates**, recheck real integration owner. |
| **D12 P1 — Training dosage evidence** | Trace actual recorded training type, duration, effort and mutable activity if present: input→historical snapshot→player attribute and fatigue consumers. | If absent, label `UNSUPPORTED` rather than infer Gym/Group effects from existing athlete growth. If present, no future data or provenance-less effect. | **Read-only now**; new training module later-only. |
| **D13 P2 — Country opportunity invariance** | Reassign a country identity label while keeping actual objective opportunity/age/history/source attributes identical; then separately vary true Development Quality or Access. | Label-only permutation cannot directly change innate potential; genuine environment may legitimately affect opportunities or development. Do not demand identical outcomes after modifying real pathways. | **Partial code/provider audit**, future paired Run. |
| **D14 P2 — Long-run careers** | Frozen representative cohorts for multiple decades, multiple seeds with source-correct W, age at entry, potential, timing, match activity. | Report ability changes by *separate* attribute groups, age, survival and career status; high-level rank alone cannot validate physiology; assess abrupt thresholds/plateaus, not require artificial dynasty or one peak age. | **Requires coordinated real simulation**; overlap R001/R009/R008. |
| **D15 P2 — Causal fitness–fatigue / skill learning** | Treat `no additional activity-dependent adaptation` as null; compare future proposed dose-response only when true training activity and outcome data exist. | A complex model must improve held-out conditional sport observables, not just generate desired narratives; reject if added parameters are non-identifiable, duplicate current Form/Fatigue or break replay. | **Future experiment only; no active training feature presumed**. |

#### Experiment design traps to avoid

1. **Different W and exact RNG draws:** preserve annual expectations and ages, **not** identical random histories for W52 and W80 with different event counts/call structure.
2. **Soft potential:** passing a 0..200 cap test does not prove the player development model behaves consistently around `potential_ovr`.
3. **One session is not years of adaptation:** a 2-week study measuring HR/accelerometer values cannot identify a 50-year player development coefficient.
4. **Selection bias:** early elite cohorts and long careers condition on survival/opportunity; high rank may be a consequence, not a cause.
5. **Country/nationality neutrality:** environment paths may be asymmetric, intrinsic ability must not arise from nationality labels.
6. **No pretend execution:** a proposed diagnostic with a defined expected response is **not an experiment that has been run**.

### 5. Prioritised decision matrix

| Candidate / concern | Evidence | Current coverage | Decision / phase |
| --- | --- | --- | --- |
| Distinguish long-term attributes vs Form/Fatigue | Strong conceptual, limited direct squash causality | **IMPLEMENTED structural separation** | Preserve for pre-alpha; check overlap only. |
| W-aware age and annual growth | Strong product/time invariant, no claim about physiological effect | **IMPLEMENTED native**, legacy path **guarded W61** | **P0 product parity/migration diagnostic**, do not change legacy snapshots. |
| Potential growth condition | **Product semantics**, not empirical squash law | **DIFFERENT in legacy/native** | **P0 Work/owner decision before unifying kernels**. |
| Birth-week age vs integer age | Mathematical/calendar rule | **Different pathways** | P1 boundary check, retain historical paths. |
| Early/late development shifting | Plausible heterogeneity, no measured ±3-y squash effect | **IMPLEMENTED provisional ±3** | Preserve as provisional; no new coefficient for release. |
| Training modalities to attribute growth | Descriptive 15-player squash load data, **no longitudinal dose** | **NOT ESTABLISHED** in inspected kernels | LATER, needs owner scope + data + source model. |
| ACWR / >10% injury threshold | Transfer **unsupported** for squash | No quantified calibration verified | **REJECT** mandatory formula. |
| Block periodization / bodyweight superiority | Weak/indirect | No training model requirement confirmed | LATER research question only. |
| Sport-specific physical tests | Small direct squash cohorts | No wearables/VO2 performance sources mapped | LATER validation context, not UI requirement. |
| Country-supported development | Product opportunity constraints / R001/R009 | Six authored country attributes, implementation across provider paths not fully traced | Preserve source-owned opportunity and label-invariant potential. |
| Detailed 15-experiment long-run validation | R008 experimental methodology, not executed for R014 | Various scoped tests; no full campaign in this PR | Only after Work selects non-overlapping bounded tests. |

### 6. Handoff to coordinator / proposed next authorised work

**Now (docs done):** archive R014 Part A (Gemini scientific review) + this Part B (repo-specific causal and implementation synthesis). No further generic literature search is needed merely to increase page count.

**First decision:** Determine canonical future meaning of `potential_ovr` in growth (especially legacy vs native) and confirm whether owner wants equivalence of developmental *distributions* across W/time pathways or just a preserved historical legacy adapter. The Master/authoritative owner can decide; a separate research study cannot.

**First engineering diagnostic if selected:** bounded *read-only* kernel parity evidence with synthetic values around potential and 27/30/34 birthdays, separate native W52/W61/W80 annual expected changes and policy identifiers. **One small evidence test package if tests prove a gap**; don't overlap #1700/#1736 or other active PRs.

**Second diagnostic:** authoritative existing-long-run run or source-owned cohort checks of physical vs technique/movement trajectories, Form/Fatigue/Sharpness, 1/W time basis and survival. Preserve reference 50-season gate and source history. An external 'realism fit' requires actual age/athlete performance observation with rights/quality, not just 57 numbers.

**Future feature only:** minimal, causally measured and historical activity evidence if individual training decisions become a product target. Baseline zero new mechanism is valid. Do not make W61 FAX a 365-day physiological calendar or add wearable sensors/player diets to pre-alpha as unapproved requirements.

### 7. Provenance / limitations

This Part B is based on direct inspection of selected `buuk` paths/docs/tests, plus source scientific notes in R014 and prior R001/R005/R008/R009/R010/R011/R012. It **does not claim complete all-repository producer coverage, full end-to-end runtime tests, external peer review, actual FAX calibration, currently approved physiology parameters, or proof any runtime bug exists**. All row outcomes above are static inspections or proposals, never observed simulation output.

No Master, rules, tests, implementation, country packages, match state, saved Run or PR ownership modified. Work has not been contacted. One existing Draft PR is updated; owner merges if desired.
