# Current implementation — Master v83

Audited base `buuk`: `b51d88efba3977eaf14d165f9dd83b5927310c6c`, merged #1506
(16 October 2026). Fresh GitHub and local fetch agree; no open PR at final audit.
Master v83 records the new product decisions, not completed runtime features.

**Implemented:** versioned Run calendar, optional CS/EN creation/Home and immutable
first Save; exact Saved clock reads/target math; annual age/birth helpers;
calendar-owned player preview, reviewed adoption and manual Save/fork/restore;
initial health baseline (#1501), actual calendar-owned Injury/Illness Admin edits
with receipts, Health Save and CS/EN saved-player panel (#1502). Sporting migration
is incomplete and relevant guards remain.

**Horizon status:** #1503 validates plan bounds; #1504 exposes read-only Saved-clock
extension preview; #1505 adds CS/EN Home inspection; #1506 inventories all Branch
Saved heads. These are merged, not open candidates. Actual extension transaction,
all-Branch snapshot migration/Save and Completed continuation are still absent.

**Current checkpoint candidate:** Master v83 + fresh audit/handoff and targeted
extension inspection fixes: stale frontend responses and an explicit SQLite read
snapshot for the all-Branch readiness API, plus independent authority import repair. This candidate is not in the base above
until the owner merges it. Checkpoint PR final-head CI is the verification source.

**New targets:** optional resumable world preparation/readiness, Home guidance and
selected Package export; initial population from the same historical 15-year-old
cohorts as ongoing intake, simplified development to start, retirement filtering,
world-derived count and exact reviewed prestart regeneration. These are not
implemented merely by this checkpoint. Whether initial custom rule edits affect
future intake is explicitly deferred. Calibration/performance require tests.

**Next:** finish one usable reviewed all-Branch horizon extension and explicit Save
flow rather than another inspection-only fragment. Then migrate annual sporting
development, ranking validity, actual transitions and frozen goals as required.
Health fact editing and range planning are not W52 sporting execution.

Authority: [Master](SQUASH_ENGINE_MASTER_VISION.md) 9.8/31.38/35.40;
[audit](docs/PRE_ALPHA_CHECKPOINT_V83_2026_10_16.md);
[complete next task](docs/PRE_ALPHA_NEXT_CHATGPT_TASK_V83_2026_10_16.md).

## Verified boundaries to preserve

- Saved history/Compare/replay remain exact revision-owned reads; no current fallback, pre-fork ownership rewrite or regenerated old matches.
- Full Simulation has durable server tasks, exact controls/targets, immutable terminal summaries and a fenced SQLite lease. Browser close is not process death; process restart requires explicit recovery.
- The first real hybrid parent is terminal at Week 2. The second parent survived restart and crossed the actual Season boundary; only the latter can be continued where nonterminal.
- A82-01 was fixed in merged #1490; no duplicate authoritative work was established. A82-02 is incomplete touched localization. A82-03 is the new calendar integration gap. A82-04 is unfinished populated second-season acceptance. Details/tests are in the v82 checkpoint.
- Exact growth/realism/statistical calibration, the canonical richer attribute migration and the rest of the complete pre-alpha scope are not finished. New calendar targets do not close older deferred/open product questions.

## Working protocol

Implement directly in the ordinary continuation ChatGPT chat unless the owner
explicitly requests paid Codex. Fresh-check base/open PRs; preserve concurrent
work. Deliver one complete usable slice, exact historical state and final-head
green evidence. The owner alone merges. Full populated sporting acceptance and
50-season release gates remain; no realism/release claim from narrow smoke CI.

Earlier evidence remains in Master chapter 35, Git history and the v82 checkpoint.

## V83 all-Branch horizon extension implementation candidate

The implementation branch adds a reviewed cohort fingerprint, explicit CS/EN consent and manual atomic Save across all Branches; per-Branch Saved heads, append-only audit, clean Working Draft baselines and a durable idempotent receipt. Historical population clocks have explicitly validated origin provenance. Existing sporting execution guards and frozen task targets stay unchanged. This is a **candidate until focused final-head CI/acceptance is green**, not a pre-alpha release or simulated future-season execution. Contract: [Run horizon extension](docs/RUN_CALENDAR_HORIZON_EXTENSION_V83.md).

## Post-merge #1508 and V83 Run Home guidance candidate

Owner merged #1508 to `buuk` (verified 2026-10-16); its Run-wide horizon extension transaction, history preservation, CS/EN Save and receipt were verified by 10/10 latest-HEAD workflows. Calendar sporting writers still require FAX reference clock and cannot run W52/W80 merely because a range is saved. Next candidate adds **present-Branch, actual saved-content readiness** across World/Calendar entities, saved player population, Health, published ranking, dirty Working Drafts and durable Full Simulation tasks; actionable CS/EN guidance with refresh. All content statuses are anchored to hash-verified Saved HEAD and a coherent SQLite snapshot. It explicitly does not claim Full Simulation permission or provide a new simulator. Candidate remains unmerged until final-HEAD checks pass. Contract: [Run Home readiness](docs/RUN_HOME_READINESS_V83.md).

## V83 rolling ranking/race point-report calendar migration candidate

Verified merge: #1509 is already on `buuk` (17 October 2026, `d8b71c63`); no open PR at starting audit. The next candidate allows the **existing deterministic ranking/race point-report calculator** to consume an explicit hash-verified RunCalendar v1. It validates exact Run horizon, source times, historical non-future data and W-week rolling expiry for W52/W61/W80, preserves the legacy W61 report JSON/default and returns a separate provenance-bearing calendar report type. This is not the separate Official Ranking writer, not a Full Simulation unlock, and not a completed annual development/transition migration. Contract: [calendar ranking/race point report](docs/RUN_CALENDAR_RANKING_RACE_REPORT_V83.md). Candidate not complete until final HEAD checks pass.

## Post-merge #1510 — versioned calendar Official Ranking candidate

Verified current `buuk` `e852bd74` after owner merged #1510, no competing open PR. The candidate implementation adds a new **independent** W52/W61/W80 Official Ranking calculation schema with Best N, weekly expiry, disciplinary zero slots, Season Week W→next season Week 1 predecessor, deterministic tie-breaking, scoped hashes and a real Saved-Run HEAD read-only bridge. This is **not** a saved Official Ranking publication or a Full Simulation enablement. FAX historical ranking state and frozen tasks remain byte-identical; authoritative Week/Season Transition is still blocked for non-reference Run clocks. Full integration/calibration remain outstanding. See [candidate scope](docs/RUN_CALENDAR_OFFICIAL_RANKING_CANDIDATE_V83.md).


## Post #1511 — calendar ranking source history integration candidate

Verified owner merge #1511 on `buuk` `b8046825` (17 October 2026);
no other open PR at the starting audit. The current *unmerged* candidate
implements typed W52/W61/W80 result-correction and disciplinary-zero version
resolution, immutable as-of source manifests, a real signed-Saved-clock
read-only adapter and strict horizon-extension continuity for ranking
predecessors. It does **not** persist those new source version types, publish
official rankings, migrate legacy source stores or remove sporting guards.
Final HEAD focused tests/CI are required before a merge-ready handoff.
See [scope and limitations](docs/RUN_CALENDAR_OFFICIAL_RANKING_CANDIDATE_V83.md).


## Post #1512 — unpublished SQLite source staging candidate

#1512 merged to `buuk` and no competing open PR at inspection. This candidate
adds real SQLite/restart durability and exact fingerprinted storage for
calendar-aware ranking correction and zero *staging*, with internal
`BEGIN IMMEDIATE` append, scope/Save-clock verification and read-only
as-of replay. It refuses forks and already authoritative sporting branches.
These separate tables are **outside Saved Revision history and real publication**:
there is no matching authoritative source evidence/Save/fork/restore integration,
no UI or sporting W52/W80 enablement. See the revised scoped contract and
focused real SQLite tests. Candidate only becomes merge-ready after final-head CI.
