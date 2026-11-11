# AI repair handoff — 11 November 2026

This is an implementation handoff for a one-month Claude experiment, not product
canon or a promise of continued subscription. Radim owns merge and subscription
decisions. Approved Master/owner decisions take precedence over this file.

## Confirmed owner clarification

On 11 November, Radim selected **an estimate from available information** for
Turn Pro strength assessment. The weekly player-AI decision must not directly
read hidden true OVR of opponents to know that a prospect exceeds, for example,
70% of professionals. The exact estimator/calibration remains a design question.
An explicit unknown-information case is better than invented observations.
This does not prohibit internal attributes in population generation itself.

Do not reopen the already recorded principle that new-policy association entry
requires a separate Turn Pro event, including definitive wild cards. However,
review the complete proposed Master #1765 separately: accepting that principle
does not automatically approve every provisional timing/calibration detail.

## Prompt to paste into Claude Code

You are the autonomous implementation partner for Squash Engine during Radim's
one-month trial. Work remains technical lead and an active developer. Design your
technical solution; do not start another broad subsystem before stabilising the
existing Turn Pro chain. Read `CLAUDE.md`, `AGENTS.md`, the approved Master and
the current evidence map. Your first deliverable is the following repair.

**Goal:** a clean, independently reviewable Turn Pro candidate with correct
production configuration, genuine final-head acceptance and historically safe
Saved/replay/fork behaviour. Keep the ATP work (#1763/#1780) separate.

**1. Restore production Entry configuration and stop test leakage.**

- At reviewed baseline `buuk` `04c9879c49921865e35240cbcf411426d84ef68d`,
  `config/balance/entry_tuning.json` has Git blob
  `02fd58856ca05ca248c20373fa8a296c72d4c797`.
- Commit `041ecfab8bf0172e36a400f704342783e1283961` in #1777 replaces it
  with the test override; #1778/#1779 inherit the same blob
  `f3ec4101a8fd93308f2c51e61b5a567bb0175df0`.
  In particular `baseline_bias=-0.22` became `10.0`, quality thresholds became
  zero and production weights/tour/category maps disappeared.
- Restore the exact reviewed baseline unless an intentional separately reviewed
  calibration change is required. Do not tune around a test failure.
- Preserve the isolation repair from #1769. Find other writes to shared config
  and built-ins, use temporary copies, and inspect the entire final staged diff.
  A test comparing a config file to its pre-test bytes cannot detect pollution
  already committed in HEAD; compare the PR's config diff to its trusted base too.

**2. Repair the actual #1769 failure, preserving the Health guard.**

- Head `8aa0b4d8944fa56b5f2aaa31680268cd13115de7`, Fast CI run
  `42918982448`, job `130188747990` fails
  `tests/application/test_authoritative_simulation_api.py` in
  `test_match_reconstruction_http_preview_is_read_only_and_commit_is_exact`.
- Independently reproduced response from the real HTTP route:
  `GET .../match-reconstruction/state?group_id=...` → 409,
  `match_reconstruction_state_conflict`,
  **`Simulation Slot requires authoritative Health state`**.
- The same isolated test fails at baseline `04c9879...` too. This is evidence of
  an existing incomplete fixture exposed by current test selection, not evidence
  that the new isolated Entry tuning caused the failure.
- Determine which owned/Saved Health baseline the positive reconstruction
  fixture needs. Establish it through existing supported setup/commands; keep
  the genuine missing-Health case rejected. Do not replace the production stack
  with mocked success, arbitrary fingerprints or a weakened 200 assertion.
- Prove preview/read non-mutation, exact selected-candidate commit, retry and
  actual rollback/error behaviour. Keep the config override isolated.

**3. Bring Turn Pro inputs into line with the owner clarification.**

- The current native caller in
  `src/beta_engine/domain/tournaments/calendar_native_tour_week.py`
  passes `{p.player_id: p.ovr for p in checkpoint.players}` to the candidate
  builder. This is actual engine strength, not an observed AI estimate.
- Design a small, versioned input boundary for then-known observations/estimates.
  Show what happens before anyone has public results. Do not build a large scouting
  subsystem as a prerequisite, invent observations or silently keep true-OVR
  knowledge as a production shortcut. Submit unresolved estimator/product choices
  with concrete examples before activating a new default.
- Keep annual/weekly timing consistent for W52/W61/W80. Validate the stated
  eventual-entry rule: a capped chance or a sample with no non-entrants is not a
  proof that every healthy generated prospect enters before career end. Preserve
  the owner's no-fixed-forced-age rule; present a conflict rather than silently
  changing either requirement.
- Audit the opening-population approximation separately from real weekly AI,
  no-future-leak, birth weeks, native fork decisions and historical v57 policy.
  Do not re-run old history through today's model or change older Saved bytes.

**4. Stabilise the stack and demonstrate integration.**

- Actual chain: #1767 → #1768 → #1770 → #1771 → #1772 → #1773 → #1774 →
  #1775 → #1776 → #1777 → #1778 → #1779. The PRs currently target `buuk`
  despite including predecessors' commits. #1765 is the separate proposed
  product document; #1769 is a separate test-isolation repair.
- Repair the existing chain without force-rewriting another author's work or
  spawning more unverified stacked features. Explain how each correction reaches
  every affected descendant. Propose a safe consolidation/retarget plan for
  owner/Work review; do not close or merge other PRs unilaterally.
- Re-run relevant focused tests and actual configured Ready acceptance on the
  final heads: native Turn Pro, genuine Entry/WC, Health, actual matches and
  ranking, explicit Save, SQLite restart/restore, birth and fork/replay. Keep
  corruption, stale ownership, rollback and no-future-leak cases intact.
- Demonstrate at least one genuine prospect becoming professional, then entering
  and playing an association Edition through normal Saved commands, with its
  historical decision reproduced after restart/default changes. State remaining
  unsupported pre-Tour, FAX materializer and older-replay paths separately.

**Handoff:** final head(s), own delta versus parent and `buuk`, exact config diff,
test commands/results/artifacts, failures/skips, a working-tree-after-tests check,
known limitations and remaining owner choices. Never label skipped/pending/failed
required checks passed. No merge/auto-merge or direct `buuk` write.

## Reusable task brief and review checklist

A task brief needs: problem/result; approved Master clauses; owned files and
shared boundaries; explicit non-goals; supported inputs/failure cases; actual
acceptance commands; final-head evidence; next dependency.

Before a merge recommendation:

- Verify exact head/base, ancestry, own delta and complete `buuk` diff.
- Inspect configuration/data changes against the trusted base, including changes
  inherited from a predecessor; inspect unstaged and staged changes after tests.
- Check immutable Saved/schema/hash compatibility, source ownership, explicit
  Save, exact retry, rollback and genuinely exercised restart/replay/fork paths.
- Check simultaneous inputs, chronology and then-public AI knowledge.
- Require the relevant final-head checks to execute successfully. Keep local,
  component, HTTP/SQLite, Chromium and full-season evidence distinct.
- Record an author's adversarial pass honestly; do not call it an independent
  second-AI review. Use an actual independent reviewer when available/justified.
- Merge belongs to Radim. Sonar/CodeQL are evidence, not product authority;
  document a validated false positive rather than hiding a real finding.

Fast CI adds a final tracked-worktree guard to its backend, Python-3.12 security
and frontend jobs, including failed test runs after a successful checkout. It
checks the repository root even from `web/`, and catches staged/unstaged writes.
It does not detect a bad value already committed in HEAD, audit untracked outputs,
or cover the separate acceptance workflows; it complements review and isolation.

## Work allocation and light trial ledger

Claude owns the existing Turn Pro/lifecycle/fork repair. Work owns ATP source and
scheduled-knockout integration plus this review/CI guard. Coordinate changes to
`calendar_tour_service.py`, Tour models and shared persistence with one active
writer; do not implement competing versions concurrently. Claude's private chat
is not controlled by this environment: Radim pastes the prompt above.

Coordination baseline: 11 November 2026. Earlier Claude work is included as
pre-coordination work. Actual subscription expiry, effort and cost were not
provided; no estimate of those values or automatic renewal is assumed.

| Work item | Developer | Evidence / integration state | Review or repair cost |
| --- | --- | --- | --- |
| Turn Pro stack #1767–#1779 | Claude | Modular versioned implementation; acceptance incomplete; knowledge-input correction required; config pollution in #1777–#1779 | One confirmed config incident propagated to three PRs; elapsed effort/cost unknown |
| Config isolation #1769 | Claude | Useful isolation change; failing positive reconstruction fixture also fails on baseline; real Health error reproduced by Work | Repair required; do not attribute the baseline failure as a new Claude regression |
| ATP #1763 | Work | Current head, 20 successful applicable workflows; documented Sonar false positive | Full public ATP knockout lifecycle remains unfinished |
| Horizon repair #1780 | Work | 105 local focused tests; hosted Fast CI; full combined-head acceptance tracked in the evidence map | Review included original-result byte comparison and 43-match controls |
| This coordination/CI change | Work | Minimal handoff + existing map; tracked-write guard behaviour/YAML verified | Draft until its own final checks/review are complete |

At actual trial end, compare completed accepted functionality, regressions,
integration/review effort and independently verified discoveries on similarly
risky tasks. PR/line/test counts are evidence, not productivity scores. Record
unknowns instead of inventing hours or savings. Radim decides whether to renew,
use Claude only for selected months/tasks, or stop.
