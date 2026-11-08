# R001-C5 — Baseline career-path diagnostics (research follow-up)

**Prepared:** 2026-10-31  
**Status:** PROPOSED DIAGNOSTIC PLAN — not a new product requirement, not executed, not scientifically calibrated  
**Authority:** Master v86 plus newer owner decisions; `AGENTS.md` and `docs/COUNTRY_ATTRIBUTES_V1.md`. In case of disagreement, this document yields to canonical product decisions.  
**Source:** [R001 independent review](INDEPENDENT_REVIEW_FINDINGS.md) and the Work coordinator's subsequent code-level assessment of `buuk` `fb9fd790635956ff1f4eee155482f02c7289ef74`. The latest base checked when this document was prepared was `7a08ff441dd185189638c05dfc3bd33401407b7d`.

## Decision and motivation

**Measure the current model before designing another career-growth mechanism.** Existing design and code include Early/Standard/Late Bloomer profiles, different growth timings, individual potential and reproducible variation. That does not establish that the *combined* junior-to-senior paths resemble convincing career histories.

The independent report introduces **C5: heterogeneous youth-to-senior outcomes**, including late developers, early plateaus, rare exceptional careers and non-elite senior outcomes. Do **not** turn this into a generic pre-Tour dropout rule.

### Evidence boundary

- Güllich et al. (2023) reported low overlap between international U17/U18 junior and senior elite populations across multiple sports. The quoted **89.2%** and **82.0%** use different denominators and are NOT the percentage of FAX prospects who should be removed. Source: <https://pubmed.ncbi.nlm.nih.gov/37022588/>.
- Güllich & Barth (2026) reported **36.3% annual turnover** in selected sports talent-promotion programmes, which concerns programme membership entries and exits; it is **not** annual retirement, disability or pre-Tour dropout. Source: <https://pubmed.ncbi.nlm.nih.gov/42380538/>.
- Neither number is an FAX acceptance threshold. Cross-sport results motivate investigation, not direct formula coefficients.

### Canonical compatibility boundaries identified by Work

1. Master §9.2: an automatically generated prospect is ultimately eligible to enter the professional Tour, subject to the specified severe-medical-termination exception. Do **not** randomly eliminate most generated prospects or silently redefine this rule.
2. Master §11.4: plateau, more than one peak, comeback and unrealized potential are already part of the intended design; existing labels alone are not proof of their runtime frequency.
3. No general played junior tour is currently simulated. **Young OVR/potential is a youth skill proxy, not a published junior ranking/result.** Any chart labelled “junior elite → senior elite” requires explicit caveat or separately sourced junior results.
4. Actual Top N status must be computed from a valid contemporaneous saved/published **ranking source** where available, not derived by calling the highest young OVR “Top 10”.
5. Distinguish end of an observed simulation window from player retirement, dropout, inactivity and eventual non-achievement. Missing future seasons must be classified as **right-censored** observations, never as career failure.

## Two implementation-contract discrepancies to review BEFORE changing equations

### A. Soft potential versus native growth condition

The reviewed production path is [`src/beta_engine/domain/players/calendar_sporting_week.py`](../../../src/beta_engine/domain/players/calendar_sporting_week.py) in `develop_and_recover`:

```python
below_potential = player.ovr < player.potential_ovr
direction = (
    1 if age <= old.growth_end_age and below_potential
    else (-1 if age >= decline else 0)
)
```

Under this **specific native weekly path**, positive growth is blocked at or above current Potential OVR. Work reports that Master §11.2 permits exceptionally rare growth beyond the ordinary soft potential, while a legacy path differs. The next auditor must verify the **complete actual active path**, semantics of Potential OVR (soft vs hard ceilings), attribute caps, effect of decline/recovery, and possible elsewhere-defined exceptions. Do not assume a one-line change is correct or merge a sporting rule without its owner-approved contract.

### B. Retirement / inactivity / comeback ownership

Work reports the native lifecycle validation is presently focused on automatic retirement by age and does not provide a complete inactivation, voluntary retirement and comeback pathway from Master chapter 12. Verify actual event, status, age, historical projection and Save/restart rules before designating a feature “missing”. The development path also references `automatic_retirement_age`; this is **not** proof of a complete retirement event system.

**Scope:** this PR only records these review findings. It does not change code or rule interpretation.

## Minimal read-only cohort diagnostic specification

Choose a bounded representative saved Run/Branch with unambiguous historical provenance. The initial diagnostic must inspect **existing immutable snapshots/events**, without writing into player, branch, ranking, match, tournament or lifecycle state. If necessary data does not exist, report that measurement as `unobservable` rather than inventing history.

**Identity / reproducibility metadata** (for every report):
- source Run/Branch identifiers; full seed hierarchy or reproducibility identifiers; immutable Saved Revision/checkpoint fingerprints; package/config versions; Run's fixed weeks-per-year `W` and effective dates;
- analysis tool/report version; observed season/week range; whether history is complete or partial; cohort-selection rule, denominator and exclusions.

**Per-player observations**, subject to actual recorded source availability:

| Field family | Source / definition | Missingness or caveat |
| --- | --- | --- |
| Cohort | stable player identity and age-15 cohort year, country at cohort creation and observed environment | If initial population reconstructed from history, do not pretend the prospect was observed at age 15 unless that prior state is retained |
| Youth baseline | earliest **observed** OVR, Potential OVR and development-timing class; age/time of measurement | No fabricated “junior ranking”; potential is a design variable, not measurable innate biology |
| Tour entry | observed first Tour-active week/date, age, route/known exception | If first event predates available history, label left-truncated; never infer precise entry age |
| Trajectory | OVR / attributable skill at reliable observation times; age at observed peak, stagnation intervals, late improvement | Do not infer unrecorded trajectories from final current attributes |
| Competition outcomes | first *actual* historical Top 100 / Top 50 / Top 10 appearance, best rank and ages from valid ranking data | Use rankings only after relevant published sporting events and proper history; "not found" != never achieved |
| Lifecycle | observed active/inactive/retired status, event timing, typed reason where recorded, comeback events | Do not treat cohort end or missing records as retirement; report unsupported events explicitly |
| Observation completeness | last observation, eligible observation length, right-censored vs completed follow-up | Mandatory for cohort comparisons |

**Aggregate outputs**:
- counts and denominators for *observed* age-15 cohort classes and late/standard/early timings, with data-quality coverage;
- cross-tab of youth skill quantiles versus later **observed** Top 100/50/10 (not percentage from speculative junior rankings);
- time-to-first-Top-N with appropriately marked right-censored and left-truncated cases; cohort age curve and late-developer examples;
- distribution of observed peak skill, age, sustained stagnation and outliers; do not enforce a fixed allowable number of peaks;
- retirement/inactivity/comeback evidence and **unknown/unobservable** reasons separately;
- between-seed variation and long-run country concentration as diagnostics, not imposed country caps.

## A staged, falsifiable test plan (no tests executed by this PR)

| Stage | Test / comparison | What would reveal a problem |
| --- | --- | --- |
| **0 — observability** | Determine which time-stamped snapshots, player state, ranking publications, Tour-entry events and lifecycle events are actually persisted. | A requested measurement has no valid historical data source; report a coverage gap, do **not** approximate from present-day OVR. |
| **1 — focused rule contract** | For native vs legacy development, test under/past Potential OVR with same reproducible seed and completed week. Compare to approved Master §11.2 without assuming a fix. | Native growth behaves like a hard potential cap where canon requires reachable rare over-cap events, or path-specific semantics unexpectedly differ. |
| **2 — lifecycle contract** | Inspect retire/inactive/comeback representations, age automation, restart retention and past/future visibility. | An approved lifecycle transition cannot be represented or is reconstructed from unsupported data. |
| **3 — cohort descriptives** | On a feasible fixture/saved historical Run, profile young OVR quantiles and development timings against later real ranking outcomes. | Almost monotonic path from early OVR to adult rank, lack of meaningful late development, impossible ages or untraceable outcomes. None is automatic failure without agreed targets. |
| **4 — multi-seed and counterexamples** | Run paired comparable deterministic seeds with fixed model versions and consistent country input; report distributions, rare cases and uncertainty. | All populations collapse into identical trajectories; seed changes cause uncontrolled drift; outputs cannot replay. |
| **5 — reference acceptance** | When release test prerequisites exist, instrument the genuine **50-season FAX reference** (1,000-player minimum / relevant competition coverage), with W-aware timing and Save/restart. | Historical data loss, unbounded drift, broken cohorts or systematic loss of traceability. This is future work, not a claim that acceptance ran. |

### Precision, privacy and bias rules

- Use **fixed, named cohorts** and report sample sizes at each age/follow-up threshold; otherwise misleading comparisons emerge because younger cohorts have not had time to reach late career.
- Separate **selection to Tour** from **selection to elite Top N**, and observed performance from inferred future potential.
- Use complete observed ranking events for historical Top N; never query an unrestricted current ranking to label past cohorts.
- Do not leak unpublished prospect data into public Viewer or change Save authority by adding an Admin-only diagnostic.
- Observational associations cannot by themselves establish causality of country environment, growth class or exposure.
- Same source/config/seed/command must reproduce the same sporting outcome; the diagnostic is read-only and deterministic over retained history.
- Keep quick feasibility tests distinct from expensive W52/W61/W80 and 50-season acceptance claims. No fixed target intervals from PSA women's careers or whole-population junior dropout percentages.

## Recommended handoff (proposal only; Work owns scheduling)

1. Work verifies latest `buuk`, all open PR scopes and the Master/canonical lifecycle sections.
2. Work locates exact player-creation/intake, weekly/native/legacy development, ranking history, retire/inactive/comeback and persistence paths and records **what is demonstrably implemented**.
3. Work identifies the smallest feasible **read-only diagnostic** and its existing fixtures. If enough history is absent, recommend a non-invasive instrumentation proposal rather than inventing the data.
4. Separately evaluate the soft-potential and lifecycle discrepancies for existing approved behaviour. Do **not** combine a rule-changing fix with the first C5 diagnostic PR.
5. Seek owner approval before launching a code PR or any new empirical calibration; report measured results and decision options before C1/C4 experiments.

## Non-goals

No direct edit to the Master, constitution, Country V1, Country Talent Model, sporting engine, RNG or official Run. No new growth formula, GPD/CES/HMM, nationality-dependent innate potential, hard caps, new dropout mechanic, manual Tour-entry exclusion, training-location system, or R002 research commission. This document adds neither a production schema nor a release criterion; it only makes next validation work explicit.
