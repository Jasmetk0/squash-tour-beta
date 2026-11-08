# R004 — Tournament participation: Gemini vs independent ChatGPT audit

**Date:** 2026-11-01  
**Research status:** Original Gemini + independent ChatGPT audits archived. Not an approved product mechanic, official study numbering or calibration.  
**Sources:** [Gemini 42-page report text](GEMINI_DEEP_RESEARCH_TEXT_EXTRACT.txt), [ChatGPT independent 26-page audit text](CHATGPT_INDEPENDENT_SCIENTIFIC_AUDIT_TEXT_EXTRACT.txt), [initial critical review](INDEPENDENT_CRITICAL_REVIEW_AND_HANDOFF.md). Both original DOCX binaries are **not** in Git; exact Word equations/tables may be corrupted by text extraction, and ChatGPT independently assessed a text extract of Gemini rather than the original source DOCX.

## Independent conclusion

Gemini proposed potentially useful tournament player-choice ideas but overstated numerical certainty and sometimes read historical PSA rules incorrectly. ChatGPT's research audit independently agreed with multiple critical errors and produced an **eight-test, existing-Entry-AI-first validation plan**. Neither report proves a new MNL/Gumbel choice model is necessary or that the existing Entry AI behaves incorrectly.

## Claims and disposition

| Claim / approach | Gemini | ChatGPT verification | Safe disposition |
| --- | --- | --- | --- |
| PSA 52-week average/divisor | Treats historical scheme as general | 2024/25 had minimum 11 counting tournaments for up to 15 starts, then +1 per start; **earlier years had materially different rules**, and 2026 needs separately dated verification | Never overwrite FAX's historically versioned ranking rules |
| Sudden performance penalty for **24th** event | Large divisor cliff at 24 | False: divisor **19→20** at 23→24, same +1 step as other starts beyond 15 | Reject the 24-event threshold, its proposed mandatory suppressor and its empirical target |
| All squash tournaments allow one match per day | Absolute one-day rule | 2024/25 PSA explicitly permits two same-day matches under specified minimum rest/format constraints | Preserve competition-specific FAX schedule policy; verify dated PSA sources |
| **+430.1% creatine kinase** after competition | Implies squash recovery relevance | Original figure from youth badminton, not adult professional squash | Reject as squash-specific load/injury hazard multiplier |
| Medical, disciplinary and tournament zeros | Overly uniform 52-week counting scheme | PSA policies distinguish zero types, event count, counting score, timing and first/second/third medical zero | No imported penalty logic without versioned, explicit owner decision |
| Three annual 100% performance peaks, remainder 80% | Proposed hard preparedness pattern | Coaching/conceptual guidance, not demonstrated squash biological limit | Reject as a universal coefficient |
| Break-even around world rank 150 | Applies a ranking cut-off | Tennis findings, without valid squash income/cost panel | No player-economy/retirement threshold based on this |
| 75% player overconfidence | Proposed behavioural parameter | Laboratory choice study outside squash, not a PSA player finding | Do not create a universal self-confidence coefficient |
| MNL / Gumbel decision-making | Preferred next architecture | Valid mathematical option, but uncalibrated; IIA can be especially problematic for closely substitutable nearby tournaments. Mixed Logit adds complexity/identifiability burden | Compare existing simple AI and actual observations first |

## Valuable principles that survive independent review

1. **No-lookahead / source-of-information ownership:** a player must choose using only the calendar, ranking snapshot, event rules and public information available at the actual decision deadline, never future outcomes or secret states.
2. **Explicit available choice set:** alternative available events, overlaps, eligibility and a legitimate rest/no-entry option are distinct; a later final draw does not describe everyone who could apply.
3. **Entry history and provenance:** preserve never-applied, applied, confirmed, reserved, wildcard, rejected, withdrawn, with authoritative source/time and deterministic key where the code supports it.
4. **Non-causal observational caution:** final draw is selection-biased; participation by ranking segment and season is a measurement target, not permission to require chosen quota.
5. **Deterministic replay:** if seed, frozen input and slot identity are unchanged, repeat commands should produce equivalent recorded decisions with no future-leak.
6. **Keep agent policy bounded:** a simple transparent heuristic is a valid baseline; complex MNL/MDP/rolling-horizon and travel/finance mechanisms must earn their complexity through measured shortfalls and product authorization.

## ChatGPT's revised eight bounded diagnostics (proposed only)

1. **Decision-time information/no-lookahead** — alter post-deadline facts and show prior decisions remain unchanged.
2. **Same-input deterministic replay** — immutable decision inputs, seed, ranking source and application results.
3. **Entry-state history & provenance** — verify stage transitions and source identities, no post-hoc invention of applicant history.
4. **Historical ranking-rule regime fixtures** — test policies separately; don't apply PSA historical formulas to FAX.
5. **Feasible choice-set sanity** — simultaneous tournaments, rest, non-overlap and eligibility constraints.
6. **Entry cutoff distribution** — measure accepted/reserved/wildcard/rejected by event segment without hard monotonic targets.
7. **Geographic substitution** — only where location/travel exists; measure response, not enforce universal international travel penalties.
8. **Existing AI sensitivity/ablation** — remove one supported term at a time and measure changes; report unobservable/unsupported terms as such.

None of the eight experiments were run by this archive. Actual latest Master, code, open PRs and persisted sources must be checked before translating any of them to a test task. The study originally proposed 16 experiments, not 16 independently demonstrated results.

## Cross-study boundaries

- R001 career C5: don't infer lack of talent or Tour dropout from not entering an individual event.
- Match-realism and injury research: Form, fatigue and Health state should not be counted multiple times in Entry score.
- Ranking-dynasty R003: ranking publication used at Entry Closing must come from actual historical source, not current/player-power proxies.
- Health R005: an injury record alone does not authorize automatic withdrawal, match retirement or a PSA Protected Ranking policy.
- Tactics/Gameplan research: not a reason to make agent choice perfectly optimize future draws.

## Handoff decision for Work (when available)

**Recommended first technical inquiry** is not a new utility model. Work should verify latest `buuk`, Master, current Entry slots, published snapshots and current Saved source evidence, and then **propose** a minimal read-only/no-lookahead validation. Do not automatically commission programming, change Master, approve new PSA penalty rules, run expensive tests or merge research. Owner/Work decides priority and permanent research ID.

**No production code, rules, tests, simulation runs or external services were changed by this research-only update.**