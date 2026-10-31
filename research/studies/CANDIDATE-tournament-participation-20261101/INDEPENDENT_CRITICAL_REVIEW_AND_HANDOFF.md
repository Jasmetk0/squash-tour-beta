# Gemini Tournament Participation Deep Research — Independent Critical Review

**Prepared:** 2026-11-01  
**Status:** `RESEARCHED / UNVERIFIED` — independently reviewed *select claims only*. Not verified/calibrated, not product-approved, not a new pre-alpha requirement.  
**Source:** owner-provided **42-page Gemini DOCX**, "Výzkum Turnajové Účasti ve Squashi.docx". See [searchable text archive](GEMINI_DEEP_RESEARCH_TEXT_EXTRACT.txt); original DOCX **not committed**, text extraction can lose equation objects, tables and the process timeline diagram.  
**Research ID:** *provisional candidate R004*, permanent ID must be coordinated by Work/owner.  
**Base checked:** `buuk` `7a08ff441dd185189638c05dfc3bd33401407b7d`. All previous owner decisions and Master v86 retain precedence.

## Overall assessment

**Useful research question, meaningful methodology, several material scientific and rules errors.**

The report's strongest contribution is an *information-correct, testable* explanation of **why AI players choose a tournament before its draw is known**: legal entry cutoffs, publicly available competition information, travel and calendar conflicts, possible fatigue, and differing opportunities across skill and career levels. The proposed *available-choice-set*, **no-lookahead** and **same-seed reproducibility** diagnostics are potentially high-value for Squash Engine.

However, the report **incorrectly promotes external PSA mechanisms and cross-sport laboratory findings to near-authoritative and sometimes precise FAX recommendations**. It did not establish actual squash-tour-wide participant-level behavioral choice coefficients or a calibrated attendance model; the author's §10 notes that it could not directly inspect all repository content. Many numerical “expectations” in its 16 proposed experiments are assertions, not validated PSA distributions. Do not implement its preferred MNL + Gumbel model on research authority alone.

## Material errors — separately identified and source checked

### E1 — Nonexistent special discontinuity at the 24th tournament

The report repeatedly calls moving to **24 tournaments → divisor 20** a “jump”, “penalization threshold”, or a major strategic cliff, and proposes a 25-event penalty test with that premise.

The historical PSA Squash Tour **August 2024** rulebook §7.4 says:

| Tournaments played in rolling 52 weeks | ≤15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Counting tournaments | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 |

This is a **smooth +1 step** on every event from the 15→16 boundary onward, **not a new discontinuity at 23→24**, and 24→25 likewise increases the divisor by one. Earlier events before 15 have a flat minimum, so **15→16 is the actual discrete breakpoint** in event count. The study's phrase “dramatic 24th-tournament penalty” is unsupported. The recommendation to suppress all players beyond a magic `24` threshold is not justified.

**Primary source:** [PSA Squash Tour Rule Book August 2024, §7.4](https://d2h2jicm4ii9y.cloudfront.net/wp-content/uploads/2024/08/PSA-Squash-Tour-Rule-Book-August-24.25.pdf). (A 2025 or 2026 revision would require its own dated verification.)

### E2 — The purported one-match-per-day absolute rule has exceptions

The report says PSA athletes may play **at most one match per day** and points to its schedule/18-hour rule as if universal. The 2024 PSA §4.4.3 expressly specifies **4 hours 45 minutes between starts of two same-day matches**, and **18 hours between starts on consecutive days**, with some PSA discretion. Official PSA event registration also allows **Challenger 3** two rounds in one day. It is incorrect to make “max one match per day” a universal global sport constant.

**Sources:** [PSA Rule Book §4.4.3](https://d2h2jicm4ii9y.cloudfront.net/wp-content/uploads/2024/08/PSA-Squash-Tour-Rule-Book-August-24.25.pdf), [PSA event registration](https://form.jotform.com/250123377819055).

### E3 — Quoting +430.1% CK and +160.4% at 24 hours as squash physiology

The exact `430.1%` and `160.4%` increases in creatine kinase come from **Moreno-Pérez et al. (2020), twenty elite JUNIOR BADMINTON players after TWO badminton matches on the same day**. The report frames these values repeatedly beside male professional squash, sometimes generically “racket sports”; if read as squash-specific evidence, that is incorrect. The *general* proposition that strenuous matches may produce fatigue remains plausible. Exact badminton CK changes are **not a calibratable FAX recovery coefficient**.

**Primary source:** [The influence of a badminton competition with two matches in a day ... (PubMed PMID 32508387)](https://pubmed.ncbi.nlm.nih.gov/32508387/). See also [Nosaka & Chen 2024 review](https://pubmed.ncbi.nlm.nih.gov/39086854/), which compares badminton and tennis, **not squash match telemetry**.

### E4 — “All 52-week Medical/Penalty zeros fill counting slots” is wrong

Gemini's Executive Summary and §9 describe **52-week Medical Zero and Penalty Zero penalty slots** as if they all continuously occupy a counting-tournament place. §4.6 of the dated primary PSA 2024 rulebook distinguishes:
- First Medical Zero: **does NOT** count as a tournament played or counting score.
- Second Medical Zero: **counts as tournament played** but does **NOT** enter counting scores.
- Third or later medical zeros in 52 weeks: treatment differs and counting inclusion can last a **maximum 26 weeks**, not blanket 52.
- Disciplinary / penalty zeros have their **own treatment and timing**, not the same as medical.
- Tournament Zero Score is another distinct type.

The study cannot be copied into the FAX ranking or withdrawal subsystem even if the owner were to authorize PSA-like rules; first reconstruct the exact *historically effective* FAX Master and PSA policy separately.

**Primary source:** [PSA Rule Book 2024 §4.6 and §7.4](https://d2h2jicm4ii9y.cloudfront.net/wp-content/uploads/2024/08/PSA-Squash-Tour-Rule-Book-August-24.25.pdf).

## Unsupported or weakly supported inferences

| Claim or proposal | Why caution is required |
| --- | --- |
| **MNL with Gumbel shocks is the “optimal” and evidence-based pre-alpha design** | Random utility/discrete choice is a *plausible technique*, not an empirically identified squash player-choice model. A simpler auditable deterministic heuristic / bounded stochastic choice may meet the existing Master. It must be compared to actual currently implemented Entry AI and to real alternatives before selecting architecture. |
| **Player Top 20 should rationally prefer Gold/Silver over Platinum/Diamond** | Specific PSA points and draw sizes are real rule context, not proof of universal player choices. Registration requirements, qualification, actual field strength, prizes, contracts, points expiration, desire for major wins and individual sponsorship are omitted. No matched empirical participation study was demonstrated. |
| **Elite player can be 100% ready exactly 3 times/year, others 80%** | Attributed to a 2003 WSF coaching conference: coaching guidance/periodization opinion, not experimentally established biological ceiling. Never implement a 3-event cap or 80% rating multiplier. |
| **“Break-even around world rank 150” for professional squash** | The report repeatedly draws on economic studies of **professional tennis** and general racket sports; it does not show a squash-specific income/cost panel with travel, federation support, sponsorship and taxes. EXP-14's “100–160 break-even” is not a validated squash threshold. |
| **75% of squash athletes overconfident about being in the top quartile** | A generalized behavioral-economics result is not shown to measure professional squash players. Avoid applying a universal psychological correction to their tournament choices. |
| **EXP-01 target ≤5% of players exceed 24 events; Top 10 mostly 11–15 events** | These are *hypothesized* metrics, not actual measured tour-wide distributions. Divisor rules create incentives; cannot determine empirical participation frequency without data. |
| **EXP-06 ranks of entry cutoff must strictly order by tournament tier and 0% World Event unfilled** | Field strength may vary by venue, date, region, calendar conflicts, event restrictions and cancellations; forcing universal strict monotonicity or zero unfilled draws would be artificial. |
| **EXP-05 near-certain ranking loss after 25 tournaments** | Depends on points/performance, actual format, FAX policy and competition; false step-change premise E1. |
| **Apply a 52-week average divisor in the FAX world** | The historical official PSA average-based system is distinct from FAX's authored historically versioned Best-N policies. Never map PSA ranking rules into FAX automatically. |
| **Experiment claims immediately executable in pre-alpha** | Product intent and available schemas do not prove actual production support for late medical withdrawals, travel location, bankroll, U23 event pyramid, all season-time intervals or a comprehensive batch runner. Audit runtime and Saved provenance first. |

### A source-quality note

The bibliography mixes PSA rulebooks and sport-science studies with Wikipedia, consumer blogs, non-peer-reviewed economic projects and a **2003 coaching-conference transcript**. The stronger normative assertions are verifiable from dated PSA policy, but **individual player preference weights, income thresholds and precise physiological response rates are not empirically established for male squash players in this study**.

The study has a valuable 4-stage idea for future external corpus acquisition (historic published rankings, entry lists, main draws, late withdrawals and confounders), but legal/technical access and completeness must be checked before scraping, copying or deriving calibration products. “Only aggregate output” does not automatically establish data-licence permission.

## What remains useful after correction

**1. Canonical information-state audit:** a player deciding at a real Entry Closing Week must not see future draws, outcomes, never-published entry lists, opponents' hidden health or RNG outcomes. Same-time decisions must not accidentally reveal other simultaneous agents' future results. Preserve Master slot semantics, saved source snapshots and audit trails.

**2. Feasible-choice-set diagnostics:** at the decision time, which tournaments are actually known, calendar-compatible and eligible for that specific player? Explicitly distinguish **did not apply / applied but not accepted / reserved / withdrew / unavailable** before modeling preferences.

**3. Behavioral diversity only if observed:** test existing AI player Entry behavior by ranking/career group, location (if supported), competing events, age, previous physical load, and recorded available information. Do not invent evidence or forcibly equalize every choice.

**4. Determinism and chronology:** repeat identical state/seed/config/command; validate no lookahead; preserve published ranking source and historical decision ownership; reject retroactive update to confirmed entry after draw. A hash alone is not a substitute for semantic proof if serialization includes nondeterministic or irrelevant fields.

**5. Distinguish PSA / FAX authority:** maintain current FAX Main/Qualification Entry windows and ranking source rules; external PSA discipline, zero scores, payday policy, protected ranking and WC hierarchy are research analogies only, unless separately approved.

## Proposed *staged* audit for Work (NOT an automatic task)

- **Stage 0:** verify latest `buuk`, AGENTS, entire Master Entry & Player AI chapters, current open PRs, and implemented active Entry path; identify data actually stored at application time and for historical replay. Prioritize current pre-alpha Entry→Draw→Match blockers.
- **Stage 1 (smallest read-only slice):** from existing authoritative Saved Entry events or available state, report who could enter, who applied, who was accepted / reserve, what source ranking was known and why; detect future-state leak and rank source mismatch. If historical decisions are not persisted, report `unobservable` instead of fabricated probabilities.
- **Stage 2:** use a few counterfactual synthetic tournaments only with currently supported fields; compare alternative candidate fields under identical observed seeds. Separate structural entry eligibility from a preference model.
- **Stage 3:** after real per-player participation history and legally reusable corpus exist, estimate optional player decision heterogeneity. Compare simple policy and MNL on held-out events; no unverified coefficients or artificial activity targets.
- **Stage 4:** if future explicit product decision authorizes more realism, investigate travel/finance, exact withdrawal and ranking penalties. Do not expand pre-alpha scope solely because PSA has those mechanisms.

## Relationship to existing drafts and research

- **Merged #1695 / R001**: talent-pipeline and generational models. This study should not inject nationality into innate potential or force early exit from Tour.
- **Draft #1700**: C5 youth–senior career tests. Shared event history/censoring definitions only; avoid duplicate player cohorts.
- **Draft #1702**: match realism. Use measured fatigue/physical state, not imported badminton CK constants.
- **Draft #1703**: ranking dynamics. Distinguish player ranking versus skill and actual historical entry from present-day rank.
- **Draft #1701**: Windows preview launcher, unrelated. **PR #1704** Cross-Run Saved Comparison (observed open on 2026-11-01), unrelated operational scope. No files overlap.
- One research archive = one Draft PR. Do not merge; owner alone merges. No Master/rules/code changes.

## Verdict / recommendation

Keep the original Gemini research visible, with **explicit unverified tags**. Its procedural-entry, no-lookahead and decision-heterogeneity sections deserve future independent research audit. **Reject direct adoption** of the “24-event cliff”, universal one-per-day rule, squash CK +430.1%, blanket medical zeros, fixed 3 peaks/year or top-150 break-even economics.

The next step after archive is **independent factual validation and a narrow existing-Entry AI observational audit**, subject to Work coordination. Do not create a mandatory new sophisticated MNL decision engine or an R004 release gate.

No source code, Master, ranking policy, package config or game outcomes were edited. No sim/test pipeline ran for this documentation-only review.
