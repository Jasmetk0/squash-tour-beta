# R001 — reviewed synthesis and handoff to ChatGPT Work

**Date:** 2026-10-31  
**Research status:** **RESEARCHED**, **not VERIFIED** and **not owner-decided**  
**Scope:** design/evidence review of globally popular fictional men's squash; relevant beyond pre-alpha  
**Implementation:** none; no tests run, no parameter calibration performed, no Master change

## Source provenance and limitations

This synthesis is based on three user-supplied Gemini research artefacts archived in this folder:

1. [Original Deep Research text extraction](GEMINI_ORIGINAL_REPORT_TEXT_EXTRACT.txt): from the 38-page DOCX `Plán výzkumu talentů ve squashi.docx`. **Not a faithful mathematical facsimile** — embedded equation images are missing or degraded in the text-only extract; consult the original DOCX for equations.
2. [Gemini self-audit](GEMINI_SELF_AUDIT_01.txt): first critical revision, identifying empirical, mathematical and validation issues.
3. [Gemini Master-alignment review](GEMINI_MASTER_ALIGNMENT_02.txt): alignment with provided `AGENTS.md` and `docs/COUNTRY_ATTRIBUTES_V1.md`.

All three are **AI-authored source material**, not independently verified scientific evidence. Cross-sport transfer claims and primary literature links remain to be independently checked. The Gemini report initially lacked reliable access to the Master; its last alignment exercise used only a subset of canonical documentation. Nothing here proves an existing runtime implementation or successful simulation test.

Repository design context:
- [AGENTS.md](../../../AGENTS.md): authority precedence, deterministic replay and strict product status distinctions.
- [Country Attributes V1](../../../docs/COUNTRY_ATTRIBUTES_V1.md): **decided** model; six authored environmental ratings (target 1–10, 0.1 increments), not national innate-talent bonuses; runtime migration may differ.
- [Master](../../../SQUASH_ENGINE_MASTER_VISION.md): highest canonical design authority subject to newer owner decisions.
- [Current state](../../../CURRENT_STATE.md): dated implementation evidence, not whole-product proof.

## Useful existing rules reaffirmed by research, not new decisions

- Global innate potential and quality-band rarity must not be conditioned by nationality.
- Effective cohort volume may depend on factual population and authored participation/access with diminishing returns at very high population; exact formula remains calibration.
- Country development/competition/support/tradition affect potential realization rather than genetically shifting the potential distribution.
- The fictional squash world is globally popular, so a narrow historical PSA country mix is **not** a hard national distribution target.
- Dominance, unusual careers and small-country champions can be realistic; avoid artificial results/ratings caps and the disallowed innate-quality Recent Greatness Dampener.
- Current weekly calendar/15-year-old cohort, authored World Package history/interpolation and deterministic seeds are part of product integration constraints.

## Four candidate improvements (NOT DECIDED)

| ID | Candidate design hypothesis | Value if validated | Key confound / risk | Evidence strength | Suggested handling |
| --- | --- | --- | --- | --- | --- |
| R001-C1 | **Complementary development factors:** use a partially multiplicative relationship among `development_quality`, `competition_quality`, `elite_support`, `squash_tradition` rather than only an additive average | Poor elite support can bottleneck otherwise strong junior development / professional conversion | Strongest bottleneck may be double counted; zero/near-zero numerics; weighting not empirically identified | Plausible modelling hypothesis from broad talent-development frameworks, **not directly validated for FAX** | Compare baseline versus candidate with held-out scenarios and diagnostic outputs; no fixed weights yet |
| R001-C2 | **Competitive-depth developmental opportunity:** use *derived real competition/sparring availability*, not nationality alone, to influence realization of some young players' potential | Supports organically strong generations and elite training ecosystems | Nationality does not imply geographic proximity or shared training; positive-feedback lock-in possible | Plausible cross-sport analogy; causal magnitude **unverified** | First measure `Competitive Depth` correctly; test weak/absent impact versus bounded alternatives |
| R001-C3 | **Professional conversion congestion:** elite support availability per prospect may produce diminishing marginal conversion when the eligible pool overwhelms available support | Models the distinction between top juniors and supported professionals | May secretly penalize large countries and act as anti-dominance rubber band; support capacity needs grounding | Hypothesis; no calibrated causal coefficient | Test only if it follows actual resource capacity, not national Top 10 quotas; never alter innate potential |
| R001-C4 | **International exposure for an exceptional player:** access to international-level competition/training could improve development for a talented player from a weak domestic system | Makes individual exceptions and small-country champions plausible | Must not grant a free bonus based only on nationality; explicit migration/academies may be later-version scope | Plausible scenario with real-world exemplars; mechanism/size **unverified** | Distinguish support from actual world-tour participation; model later only if owner approves and runtime has evidence |

All four are research proposals; **no automatic pre-alpha requirement, Master edit or implementation task** is authorized.

## Explicit non-adoptions and corrections

1. **Do not adopt GPD/CES/HMM/club agent simulations merely because they appear sophisticated.** A simpler fitted baseline may be more robust. GPD-heavy tails do not, by themselves, remove the effect of sample size on rare champions; the self-audit identified further sign/domain issues.
2. **No hard cap on country dominance.** The self-audit explicitly corrected the HHI inconsistency: six players from one country in a Top 10 require HHI at least 0.40, while seven require at least 0.52. Alternative-world target intervals (e.g. 32–48 countries in Top 100) are **illustrative conjectures**, not established constants.
3. **Do not auto-modify six authored country factors using stochastic OU / hero effects in V1.** Country history is supplied by World Package anchors and interpolated per the existing rules. Any automatic evolution is a candidate for later versions only if approved.
4. **No `court_count` as new active pre-alpha input; no nationality-induced `style_dna`.** Both are outside current Country V1 scope.
5. **Do not replace actual match/ranking computation with probabilistic HMM ranking tiers.** The world ranking comes from played competition and governed points; Form already exists conceptually.
6. **Do not transfer women's PSA age/title statistics into direct men's FAX calibration without separation.**
7. **Reject unsupported numerical precision** in the AI outputs, including claims such as model success percentages (65/90/95), specific global-sport HHI bounds, and exact effects for popularity, population or coaching.
8. **Preserve weekly time semantics and age-15 cohort logic.** Earlier research assumed annual updates and age 14; both require alignment.
9. **Source verification is pending.** Some empirical assertions combine outdated ranking snapshots, mixed measurement periods and secondary citations. Historical causality (Egypt clubs, college drain, heroic feedback) is not conclusively established by those examples.

## Proposed non-binding validation work

Before any code or canon change, Work should review actual current data sources, code paths and existing diagnostic capabilities. Candidate checks (proposal, **NOT executed**):

1. Compare generated 15-year-old cohort size and country mix under representative populations and country factors.
2. Test that innate quality-band distribution stays nationality invariant when environment parameters vary.
3. Run multi-seed sensitivity for small-country rare talents without guaranteeing champions.
4. Check the transition from junior potential to pro participation under strongly mismatched support/development factors.
5. Test whether Competitive Depth causes runaway national feedback; vary coefficient including zero.
6. Check country concentration (HHI of Top 10), countries represented in Top 50/100 and elite nationality diversity as **diagnostics**, not pass/fail caps.
7. Inspect career age distributions, early outliers, peak ages, retirement and extreme title counts using **men's** data as reference (with era differences).
8. Check deterministic rerun and Save/restart reproducibility for the same package/config/seed and command sequence.
9. Compare World Package histories at explicit anchors, interpolation years and out-of-range fallbacks.
10. Stress 50-season reference lifecycle, then optionally 100-season diagnostics, including age/time integration with 52/61 or variable weeks per season.
11. Distinguish authored nationality from actual physical training opportunities before adding sparring or international-training assumptions.
12. Check effects on performance and storage; introducing a model must not silently bypass existing release gates.

Numerical acceptance bands should be derived and reviewed separately; no universal empirical "correct" concentration for a fictional global squash world has been demonstrated.

## Hand-off to ChatGPT Work: review only, no work automatically launched

1. Confirm latest `buuk`, Master sections (country attributes, player generation/15-year-old cohorts, player development/Form, weekly calendar, match/ranking, pre-alpha inclusion) and relevant actual implementations.
2. Classify C1–C4 as: already implemented, conceptually covered but not implemented, genuinely new candidate, conflict with canon, or deferred/later.
3. Check each key external empirical source, numerical statement and transferable causal mechanism against primary data. Reject claims that fail.
4. Decide whether any bounded experimental calibration/diagnostic task is worth recommending to the owner. Do **not** create tasks, launch agents, edit Master or write simulation code based only on this research.
5. If the owner approves, prepare a separate, testable and version-scoped implementation/validation proposal under normal review and PR policy.
6. If no candidate improves current goals, archive R001 without adding complexity. Research value includes justified **non-adoption**.

**R001 conclusion:** first analytic stage complete; scientific verification and product decisions **not complete**. It supports a cautious design review, not an immediate engine rewrite.
