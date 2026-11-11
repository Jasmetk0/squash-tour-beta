# Squash Engine — Claude Code entry point

Build a deterministic professional squash manager/simulator. The integration
branch is `buuk`; Radim owns product decisions and every merge.

Read these sources before selecting work:

1. `AGENTS.md` — authority, implementation rules and test discipline.
2. `SQUASH_ENGINE_MASTER_VISION.md` — approved product rules, retaining each
   DECIDED / PROVISIONAL / OPEN / DEFERRED label.
3. `CURRENT_STATE.md` and `ROADMAP.md` — implementation evidence and dependency path.
4. `docs/AI_REVIEW_HANDOFF.md` — current repair assignment, owner clarification,
   review checklist and the one-month experiment ledger.
5. `docs/PRE_ALPHA_INTEGRATION_2026_10_30.md` — dated PR/evidence map.
6. `docs/PRE_ALPHA_TEST_POLICY.md` — exact-head acceptance and release requirements.

This file is an entry point, not a second Master. A proposed Master in an open
PR does not approve its own product decisions.

## Working agreement

- Choose technical implementation autonomously inside the agreed task. Prefer a
  completed, verifiable integration boundary to another disconnected subsystem.
- Use an isolated branch/worktree and one coherent Draft PR per task. Inspect
  actual ancestry: `base=buuk` does not make a cumulative stack independent.
- Keep shared built-ins and production configuration read-only during tests;
  use temporary copies. Review unstaged AND staged changes after running tests.
- Restore the reviewed production baseline after accidental test pollution.
  Deliberate calibration changes need their own explained review; do not hide them
  inside a lifecycle, fork or test commit.
- Preserve deterministic seeds, exact Saved ownership, immutable historical
  schemas/fingerprints, explicit Save, replay, restart and fork independence.
- Player AI consumes then-available information. Radim confirmed on 11 November
  2026 that Turn Pro strength decisions use an estimate, not hidden exact OVR.
  Internal population generation and an AI's observable inputs are distinct.
- Missing authority blocks the affected operation. Fix a stale positive fixture
  without removing the production rejection of genuinely missing authority.
- Record unsupported paths and distinguish component tests from actual
  HTTP/SQLite/browser execution. Draft skips are not passes.
- Test the final head, inspect its complete diff and provide a concise handoff:
  result, commit, files, actual tests, limitations and next dependency.
- Never merge, enable auto-merge, push to `buuk`, rewrite another author's branch,
  change approved sporting rules or re-sign historical Saved data without the
  owner's explicit instruction.

Work continues as technical lead and active implementer. Claude has autonomy over
the assigned area; shared files have one active writer. An actually independent
review is different from an author's second review pass. Additional paid tools or
a permanent AI organisation are not prerequisites for this month-long trial.
