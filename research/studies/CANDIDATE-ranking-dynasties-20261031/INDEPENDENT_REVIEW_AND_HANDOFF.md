# Ranking dynamics, dynasties and competitive balance — initial independent review

**Prepared:** 2026-10-31  
**Status:** user-supplied AI Deep Research received / selectively source-checked; **NOT scientifically VERIFIED**, not owner-approved and not implemented.  
**Research ID:** provisional next study, **not assigned R003** until Work/owner coordinates the research programme.  
**Source fidelity:** [searchable text archive](CHATGPT_DEEP_RESEARCH_TEXT_EXTRACT.txt) is from a 22-page user-supplied DOCX; Word equation objects, some cross-reference layout and table formatting can be lost in conversion. Original DOCX is not committed.  
**Authority:** Master v86 + newer owner decisions, `AGENTS.md`, current technical constitution. Research findings do not override these.

## Core judgment

The research presents a strong **observation/validation concept** for the *emergent* long-run FAX universe: measure individual ranking persistence and rare No.1 reigns, country-level Top-N depth, age-structured generations, titles and outcomes as distinct dimensions, and between-seed diversity; do not embed a national turnover timer, automatic catch-up or compulsory equal representation.

This is not evidence that the current runtime is wrong. The author had **incomplete access to the full Master and code** and did **not obtain a comprehensive licenced 1975–2026 raw ranking dataset**. Its quantified historical aggregates come mostly from updated secondary Squash Stats analyses of SquashInfo (the authors cite the latter as source). Its **16 named experiments are unexecuted proposals**, not new pre-alpha release gates.

## Selective independent source checks and methodological constraints

| Research claim | Verification / interpretation |
| --- | --- |
| **23 different male No.1s since 1975; Jansher Khan 422 weeks, Jahangir Khan 409 weeks** | Consistent with the [updated Squash Stats ranking index](https://squashstats.com/category/ranking/) reflecting results through Oct 26, 2026. These are secondary archival calculations rather than an independent reconstruction. Do not infer expected FAX reign durations or forced minimum/maximum. |
| **57 different men's Top 10 players since January 2000; 18 became No.1; median cumulative Top 10 time 2.8y** | Matches the [updated Squash Stats ranking/category index](https://squashstats.com/category/psa/). However the older body of its [2020 article](https://squashstats.com/2020/10/11/analysis-10-psa-ranks-00-20/) still describes the **historical 2000–2020 subset (50 men, 15 No.1s)** in some cached views. Always pin snapshot date (Oct 26, 2026), retrieved edition and precise denominator. 18/57≈31.6% describes those *ever reaching Top 10* and is **not** an independent athlete's chance to become No.1. Active careers are right-censored. |
| **Country Top-10 occupancy: Egypt 1,392, Australia 1,193, England 1,139, Pakistan 878 player-months since 1975** | Exact figures and 23/23/23 versus 12 unique national Top-10 representatives corroborated in [Squash: A Game of Thrones](https://squashstats.com/2026/10/14/squash-a-game-of-thrones/), updated with results through Oct 26, 2026. Method is an estimated player-month metric from complete available Top-10 ranking snapshots; **before c. 2000 only several full lists/year**. Do not read this as full equally sampled monthly raw measurements for 1975 onward. |
| **National dynasties coincide with youth-generation clusters** | Historical narrative is consistent with the above source; **association only**, not a controlled causal estimate of coaching/tradition/elite support. A nationality bonus or scheduled national decline is not supported. Store nationality **at the time of ranking**; e.g. Mohamed and Marwan ElShorbagy switched Egypt→England in 2022. |
| **Median 92-month rise to No.1; Asal 57 months** | In [The Fastest Rise to World No.1](https://squashstats.com/2026/10/12/the-fastest-rise-to-world-no-1/), only **14 identifiable No.1s with an observable complete selected climb**; starting line men Top 250, and the clock is deliberately reset on re-entry after a prolonged break. **Not** typical or expected professional-to-No.1 time, nor an age-15 cohort statistic. |
| **Tarek Momen long Top-10 career without No.1** | [The Best Never to Be World No.1](https://squashstats.com/2026/10/22/the-best-never-to-be-world-no-1/) corroborates **10.7 years** and the **2019 world championship**. The analysis uses an author-defined descriptive ranking score, not a peer-reviewed latent-skill estimate. Don't confuse it with an objective permanent player quality rank. |
| **Official monthly vs weekly ranking cadence** | Contemporary [23 Aug 2022 announcement](https://squashmad.com/breaking-news/psa-announces-switch-to-weekly-ranking-lists/) explicitly dates first weekly publication to **29 Aug 2022** (formerly monthly). Some updated Squash Stats descriptions claim weekly records back to **2017**. This is a real **data provenance/definition discrepancy**. Pre-2022 high-frequency reconstructed entries must be labelled and not treated as official weekly published snapshots without separate proof. |
| **HHI on Oct 26 Top 10 example** | With country counts `[4,2,1,1,1,1]`, HHI=(16+4+4)/100=**0.24**, `1/HHI≈4.17` effective countries. The calculation checks out. It is a **single-date arithmetic illustration**, not a longitudinal benchmark or a target. |

**Verification scope:** these are selected external confirmations of key reported aggregates and one mathematical check. This is **not** an exhaustive line-by-line scientific fact-check of all 22 pages or all cited sources. Historical coverage gaps and amended source pages must remain visible.

## Scientific evaluation and risks

**Strengths:**
1. Treats real history as **one observational realization**, not a reproducible generative probability law. Proposes cross-seed distribution, sensitivity and uncertainty.
2. Correctly distinguishes **world No.1 persistence**, **Top 10/50 breadth**, **titles** and **match-outcome strength**. A country may dominate Top 10 without owning No.1; a great player may never hold No.1.
3. Correctly separates official **rolling ranking** from **latent skill** and recognizes ranking time lag, tournament selection, seeding and activity effects.
4. Covers attrition/re-entry and right-censoring instead of labeling active or incomplete cohorts as failed.
5. Recognizes multidecade structural drift and feedback loops as measurement targets rather than pre-planned nationality corrections.

**Interpretation caveats:**
- Pre-2000 Top-10 lists are **sparse**; naively comparing player-weeks to intermittently observed player-months is misleading. Any imputation should be explicitly versioned and excluded in a raw-only sensitivity case.
- A long No.1 reign is not necessarily extreme skill; observed reign depends on schedule, rules, competitors, ranking inertia and measurement cadence.
- Current real PSA ranking policy must **not** silently replace historical, versioned FAX Best-N policy. A realistic FAX may have different national shares and Top-N turnover because its player pool and ranking inputs differ.
- No enforced minimum number of nations in Top 10, no predictable country-dynasty timer, no hard cap on a champion's reign, no direct nationality→innate potential bonus.
- A post-hoc analytical Elo/Glicko/Bradley-Terry comparator is **not** an authoritative replacement for official ranking; an external rating may be poorly identified with sparse matches or confounded by opponent sampling.
- Period-to-period diversity should be measured with common observation cadence and fixed definitions; beware burn-in, incomplete horizons, changing population size, ranking model versions and source switching.
- The study's 16 proposed diagnostics cannot be declared runnable *today* merely because the Master requires persistence: locate actual **saved, time-stamped ranking publications, titles, age/cohort records and country-at-event** in the current branch.

## Relationship to existing research and PR work

- **R001 (merged #1695):** talent pipeline, effective squash pool, national development environment, and C5 junior-to-senior heterogeneity. National dynasties/Top-N turnover are downstream *outcome measures* for R001, not a separate cause requiring new country rules.
- **Draft #1700:** C5 career diagnostics. Overlap: age-at-milestone, Top-N survival and active-cohort censoring. **Do not duplicate its player cohort analytics implementation or create a second inconsistent cohort definition.** This ranking study could consume shared read-only milestone outputs after source validity is proven.
- **Draft #1702:** single-match realism and conditional win/score distributions. Overlap: emergent dominance and upset/rivalry strength; do not create additional match mechanics as part of ranking research.
- **Draft #1701:** Windows local-preview launcher; unrelated operational scope. Do not touch.

## Recommendation for the main Work coordinator (once available)

A. **First, verify** current `buuk`, open PRs, Master, actual stored Official Ranking publications, Saved histories, tournament title records, player IDs and historical country affiliations. Keep `[TARGET]` vs `IMPLEMENTED` clear.

B. Select the *smallest read-only observability slice*, ideally from existing saved ranking publication history: measure **Top-10 first entry vs re-entry, exact cohort coverage and year/season count**, with actual snapshot timestamps, not every week if snapshots are missing. Calculate time-weighted vs snapshot-count metrics separately. Potentially add longest continuous No.1 reign and country Top-10 HHI as **optional** additional metrics only when enough history is present. Use actual published ranking events; do not infer them from present OVR.

C. If #1700 already owns age/cohort metrics, coordinate to share definitions and avoid parallel work. Do not launch heavy 50–100-season batches, new Elo computations or new ranking policies as part of this initial observation.

D. Propose a future 50-season multiseed **research-only** calibration dataset after the pre-alpha acceptance flow is proven. Do not claim it is covered by ordinary green unit tests. No arbitrary pass/fail target from published historical Top-10 shares.

E. Work should determine whether this study becomes the programme's formal next ID (**provisional R003**). Owner decides its inclusion and merge; research archive approval is not approval of a sporting mechanism.

## Scope / exclusions

Only research documents added. No code, Master, Country V1, ranking policy, simulation, calibration, new release gate or package values modified. No additional Work, Codex, Jules or paid Deep Research launched. No tests run or performance established by this documentation PR.
