# R012 — Independent critical review: professional squash economics, career sustainability and FAX incentives

**Reviewed:** 2026-11-02.  
**Status:** SELECTIVE SCIENTIFIC / PRIMARY-SOURCE / IMPLEMENTATION AUDIT ONLY. No economics was fitted, no simulation/experimental test was run, no new gameplay or funding policy is approved.  
**Owner-supplied primary document:** [ChatGPT R012 13-page source, searchable text](CHATGPT_R012_ECONOMICS_TEXT_EXTRACT.txt), original DOCX held by owner; extracted source citation markers such as `【8†L49-L54】` are NOT standalone external citations.  
**Code checked:** `buuk` `a07c51548ef3f398edba3e92551008ab2d61ec61` as of review, especially `src/beta_engine/domain/tournaments/prize_money_award_authority.py`, `src/beta_engine/application/player_prize_money_history.py`, `src/beta_engine/application/season_entry_batch_service.py`, `src/beta_engine/domain/players/sporting.py`, and `docs/PRE_ALPHA_INTEGRATION_2026_10_30.md`. Work/owner authority remains independent of research.

## Verdict

**Useful economic causal map, but neither a fully verified empirical economic model nor a true audit of the financial code.** Most useful hypothesis: elite sport growth can increase **aggregate prize money and tournament opportunities while leaving many individuals with insufficient net income**. That is highly relevant to a global FAX ecosystem with potentially different professional funding, regional networks, prestige and calendar structure.

**Do not import** Princeton senior-thesis coefficients, athlete income quotas, arbitrary `poor/medium/rich` brackets, hard-budget retirement, direct national-money bonuses, athlete bank accounts or prize redistribution into pre-alpha from this paper. Economic realism is **not proof of any required version-1 mechanism**.

## High-priority evidence check

| Claim or assumption | What is supported | Required caveat |
| --- | --- | --- |
| PSA 2025/26 total award pool about **USD 13.54 million** with 1,297 sanctioned events across 81 countries. | Supported by the PSA figures reported [6 Aug 2026 by Squash Mad](https://squashmad.com/breaking-news/mostafa-asal-on-track-for-1m-in-psa-squash-tour-prize-money-in-under-three-years/) and PSA's own 2026 public announcement. | Total comprises **USD 7,049,082 men's and USD 6,490,253 women's** prize pools; FAX reference is men's professional world. Do not treat combined-sex total as total available to FAX males, or gross prize purses as actual athlete net income. |
| “1,297 tournaments” represents the direct equivalent of 227 PSA tournaments 2017/18. | **False comparability unless classifications are harmonized.** PSA 2025/26 includes **78 World Tour, 252 Challenger, 967 Satellite/Federation** events, plus men's/women's event accounting. | Do not compute raw growth or median payout across incomparable event taxonomies and years as a causal change in elite opportunities. Normalize dates, event tiers, sexes and counts. |
| Khalil (2026) proves rising aggregate prize pool and falling welfare. | [Princeton thesis catalog record](https://theses-dissertations.princeton.edu/entities/publication/bd8e1656-a719-4953-850a-460258da8cac) confirms author **Hassan Khalil**, date **2026-04-09**, senior undergraduate thesis, studied **2018–2025** with proposed nine-variable Economic Welfare Score and five models. | Thesis abstract presents its empirical results, but this reviewer did not reproduce the underlying data, wage thresholds, season fixed-effects, ATP cross-sport measurement invariance, missing sponsorship, or numerical EWS robustness. **Unverified external thesis conclusions must not become mandatory FAX targets**, even if thesis says “five econometric models confirm”. |
| PSA ranking almost deterministically predicts ability to earn “living wage”. | Association in published prize money can be strong because prize tournaments and seeding are mediated by rank, but ranking is **endogenous** to results/entry and opportunity. | Correlation/rank coefficient does not prove that a change in rank *causally creates* money or sufficiency of cashflow. Sponsorship, federation grants, jobs, taxes and expenses are not necessarily observed. |
| Player net revenue can be measured from prize-money table. | **No**. Published prize earnings are an incomplete revenue stream; player-specific costs, taxes, third-party funding and currency/time effects matter. | **Gross awarded prize money ≠ earnings received ≠ after-tax take-home ≠ profit/net cashflow.** Avoid a false “economic career end” decision solely from prize amounts. |
| More tournaments necessarily make per-player incomes worse. | **Conditional** depending on new prize pools, field size, participants, how many events each player can enter, ranking policies, source sex/tier and entry barriers. | The paper's E01 experiment partly assumes the answer through fixed money budget and enlarged opportunity. A different expansion can raise individual net income and accessibility. |
| Pure cash-maximizing tour decisions fully explain entry / retirements. | **Not proven.** Time, sporting points, cost, tournament field, qualification, opportunity cost, injury/recovery, sponsor obligations, country context and preferences are jointly relevant. | Entry AI may rationally attend low-return events for ranking/experience; early career may be financed by families/grants; late retirement need not equal “bankruptcy”. |
| Fixed national support to “Egypt and England” should boost players. | **Product/world assumption, not causal evidence.** Countries have specified **six authored game ratings** and separate factual population; no innate nationality-linked potential/style/mentality bonuses permitted. | If future institutional economics is authorized, it must rely on historically effective, source-owned institution/grant opportunities and the player's actual access, not nationality-as-wealth template or fixed country dynasty. |
| PSA policies should become FAX economic optimization targets. | The research's alternative scenarios are useful **conditional hypotheses**. | FAX is a separately evolving **globally popular squash**, not PSA+more players; cannot prescribe ATP wealth distribution, 2026 Earth purses, rich-country participation, or anti-equality 'fixes' as canonical output. |

## Verified actual repository capability (not inferred from the R012 paper)

1. **Payout authority exists now:** `src/beta_engine/domain/tournaments/prize_money_award_authority.py` defines `TournamentPrizeMoneyAwardAuthority`, per-player `TournamentPlayerPrizeMoneyAwardAuthority`, stage payout tables, currency, `not_configured/unknown/known`, source fingerprints, and consistency checks. Known total status is distinct from missing/unconfigured.
2. **Historical prize history exists now:** `src/beta_engine/application/player_prize_money_history.py` uses frozen Owned Tournament sources, exposes branch/player/year reporting, currencies and `known/unknown/not_configured/historical_unavailable` distinctions. Its model explicitly says cross-currency totals need historical FX provenance (`reporting_currency_status="requires_historical_fx_authority"`).
3. **API and tests also exist:** `src/beta_engine/api/routers/admin_player_prize_money.py`, `tests/api/test_admin_player_prize_money_api.py`, `tests/application/test_player_prize_money_history.py`, and domain tests for prize money are present in current repository.
4. **Not proved implemented here:** player personal cash-on-hand, debt, wages/contract/sponsorship, travel expenses, coach salaries, full financial breakdown, direct integration of **actual financial solvency** into Entry AI/retirement, or all financial-level authority. The inspected `season_entry_batch_service.py` did not establish a full financial consumer; absence from a sampled file is **not proof of absence throughout repo**. A separate exact producer/consumer map is needed.
5. The 2026-10-30 pre-alpha evidence map flags **PAQ-101 prize money and separate Live Ranking as not required** for reference first release. This is a release-scope statement, not proof that optional payout code is absent. The existence of historical prize records is **not** evidence for a working budget/financial career system.

The uploaded paper says the engine “probably” assumes all players financially unlimited and “perhaps” has prize pools. It did not trace actual authority files; therefore the paper's IMPLEMENTED/TARGET classifications are **not reliable**.

## Triage of all fifteen proposed economic experiments

| Original | Main risk | Scientific disposition |
| --- | --- | --- |
| E01 calendar expansion | Assumes denominator/total budget; redefines sample; other tiers included | Future controlled tournament supply study; no forced median decline |
| E02 guaranteed stipend outside Top10 | A new finance/retirement mechanism, grants, selection and funding eligibility | Owner product decision + synthetic sensitivity only, not ready gate |
| E03 rich-country budget | Nationality conflated with actual institutions/geographical access | Reject blanket country wealth/DNA; if studied, condition on real source-owned opportunity |
| E04 concentrated prize events | Could alter both access/entry and money distributions | Descriptive static payout scenario only unless full income network exists |
| E05 expected financial ROI in Entry | Overlaps R004 Entry source-known decision and R011 travel | Future finance/no-lookahead hypothesis; do not build extra Entry AI before prioritization |
| E06 double travel cost | No verified travel expense consumer and historical routes | Scenario only; no inference from travel region to fabricated exact airline fare |
| E07 coaching budget | Exact coach/contract costs unavailable | Future economics, not near-term pre-alpha requirement |
| E08 junior public investment | Access/development pathways already partially modeled through Country; no separate monetary state | Use intake/source-lineage observation before proposing bonus |
| E09 Top5 bonuses | Income distribution mechanically changes if directly granting bonuses; tautology | Numeric descriptive redistribution, not causal psychological/career validation |
| E10 prize crash → mass retirement | Imposes retirement mechanism not currently evidenced | Do not calibrate forced mass exit; later carefully bounded hypothetical shock |
| E11 EWS / “two tiers” | Thesis EWS not independently reproduced and gross earnings ≠ welfare | Data provenance/reproduction study, not FAX calibration target |
| E12 small vs big prize events | Depends on fields, same budget, event counts, payout tiers and field heterogeneity | Static same-budget sensitivity; no universal Gini direction |
| E13 development opportunity | Confounded by talent selection and accessible resources | Cohort with selected/nonselected controls, future causal model |
| E14 financial bankruptcy | Needs new debt persistence and survival/censoring models | Do not add until independently approved |
| E15 sponsor elite support | Often tautological if added only to top cohort | Requires prospective pathways and realistic eligible support, not mandated elite-vs-rest outcome |

**None of the 15 experiments was actually run** in the submitted document or this review. The report often calls hypotheticals “proven” and labels future model edits “easy”; the correct current label is **CANDIDATE / UNVERIFIED**.

## Recommended smallest bounded diagnostics for future Work review

- **E-A — Evidence inventory**: map Stage payout input → frozen award → historical player view; verify units, currency, source dates, unknown vs zero and non-recalculation from future ranking. Already implemented pieces may only need targeted read-only assertions.
- **E-B — Award arithmetic**: within one completed official Edition, compare sum of player awards with recorded totals and stage-eligibility, including non-configured/unknown. This tests a hard **technical invariant**, not economic realism. Check existing tests before new PR.
- **E-C — Entry AI source map**: list the real currently consumed `Financial Level`, if any, expected prize, athlete cost, and known-at-deadline status; do not presume inputs are present because they appear in Master.
- **E-D — External data audit**: harmonize PSA 2018/19 vs 2025/26 by tour tier, gender, inflation, number of entrants, exchange-rate reporting and prize vs personal actual net cost. Reproduce the nine EWS source components only if source data and license permit; note small-thesis academic status.
- **E-E — FAX alternate environment**: only after Work authorizes a new economic model, test no-money baseline vs **clearly versioned** funding/region scenarios without fixed national genetic or sporting advantages.

## Integration with research series

- R001: career sustainability can constrain observable opportunities for promising juniors; no direct “financial DNA” or fixed early/late probability.
- R003: ranking and earned money may jointly respond to skill, seeding and tour hierarchy; do not use observed correlation as causal effect.
- R004: financial opportunity cost can be a future Entry signal only if known at application deadline; no hindsight.
- R005: treatment funding and dropout are conceptually related, but Health V1 has no calibrated male-pro injury hazard to convert into finance-based career termination.
- R007/R008: external data quality, provenance, valid inferential design and synthetic negative controls before macro economic conclusions.
- R009: historically varying country opportunity and professionalization make **FAX separate** from actual PSA.
- R011: travel logistics (energy/jet lag) and **cash cost** are distinct; do not interpret Travel Region as monetary bills or triple-count performance/Entry penalties.

## Governance

Read-only scientific/product boundary review only. No code, Master, country packages, source statistics, economic coefficient, calendar or Match/Entry modifications. This does not declare a full pre-alpha release gate, correctness of all payout tests, validated athlete incomes, or proof of thesis causality. Work not contacted. Owner-only merge.
