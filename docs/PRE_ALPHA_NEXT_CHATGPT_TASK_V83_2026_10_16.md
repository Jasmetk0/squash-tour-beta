# Continue pre-alpha directly — Master v83

Repo `Jasmetk0/squash-tour-beta`, integration branch `buuk`. The owner alone merges.
Implement directly in the ordinary ChatGPT chat with available tools. Do not
launch paid Codex or other paid agents. Never claim unavailable tools or tests.

First verify current buuk, all open PRs, merge of the Master v83 checkpoint and
any active horizon/health work. The audited pre-checkpoint base was
`b51d88efba3977eaf14d165f9dd83b5927310c6c` after #1506; it is not a permanent pin.
Continue existing work rather than opening a competing implementation. If v83 is
not merged, read the checkpoint PR for new decisions; avoid overlapping docs.

Read AGENTS.md, CURRENT_STATE.md, ROADMAP.md, Master v83 6.9–6.12/9.8/31.38,
docs/PRE_ALPHA_TEST_POLICY.md, docs/PRE_ALPHA_CHECKPOINT_V83_2026_10_16.md and the
scoped health contract. Preserve all existing still-valid canon.

## Next complete usable slice

Finish actual Run horizon extension through reviewed confirmation and explicit
Save, across all Branches, with usable CS/EN Admin controls. #1503–1506 only add
bounds/planning/inspection; another read-only helper alone is not completion.

Before implementation briefly explain what the operator will be able to do,
which invariants make the change safe, and how overlap is avoided. Then implement,
verify and open one coherent PR. Do not stop at a plan or request a Codex prompt.

Trace actual authority in run_calendar_read_authority, Run metadata/timeline
columns, Branch Saved heads and full payloads, Working Drafts, calendar-owned
population/lifecycle/health states, historical reads/restore/forks, task leases and
frozen targets. Equality currently includes season_count: changing one Run row
alone will invalidate current state. Do not hide this with a weak equality check.

Required outcomes:
- Strictly increase the horizon while preserving W, offset and start basis.
- Inventory/review the complete Branch cohort and Saved heads. Bind confirmation
  to all relevant hashes, draft versions and cohort membership; reject late new
  Branches, head changes, dirty incompatible drafts and task conflicts.
- One writer transaction atomically records the coherent Run/all-Branch change,
  audit/receipt and the explicit Save outcome. Fit existing manual Save semantics
  without auto-saving unrelated user work. Use the actual established domain
  rules for eligibility; disclose concrete blockers instead of silently dropping
  branches or forcing data.
- Preserve every old Saved Revision's payload/hash and historical meaning.
  Materialize/reconcile new current snapshots with exact provenance where needed;
  never redate old records, regenerate players/matches or rebuild old rankings.
- Do not change frozen task goals/targets, restart terminal tasks, simulate or
  generate future cohorts merely by extending. Completed Run continuation and
  any new task/resume stay explicit. Sporting writers remain guarded if their
  W/horizon migration is incomplete; extending a range does not itself prove
  sporting support.
- Exact retry, response loss and concurrent conflicting requests are safe.
  Review invalidates on input/source changes, including changing away and back.
- Usable CS/EN preview, affected Branches/blockers, explicit consent/Save, success
  receipt and reload. Avoid a UI that promises unsupported time progression.

Test actual SQLite/API with multiple Branches, W52/W61/W80 where relevant,
completed and unstarted Runs, new Branch/head/draft between review and commit,
concurrency, injected partial-write failure/rollback, retry, restart, historical
reads, backward/forward restore and fork. Verify task frozen targets and source
Packages unchanged. Add meaningful UI regressions and extend an existing actual
browser acceptance for the operator flow; do not create repetitive workflows.

Perform a separate adversarial pass on snapshot ownership, old/new horizon
compatibility, command identity, transaction boundaries and recoverability.
Follow focused PR gates, not an unnecessary full historical suite. Update
CURRENT_STATE/ROADMAP/contract to distinguish implemented behavior from targets.

Open PR base=buuk and never merge. Hand it off only after all required checks on
final HEAD succeed, with link, usable result, actual evidence and limitations.
If credits/tools interrupt work, checkpoint the same branch/commit and give exact
remaining steps; do not duplicate the task or reset existing work.

New product decisions 9.8/31.38 are subsequent work. Do not independently invent
retirement/growth curves or implement the explicitly deferred initial-rule to
future-intake inheritance policy. Finish calendar integration before claiming
realistic history-based world generation or full pre-alpha readiness.
