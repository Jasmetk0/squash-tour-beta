# Full Simulation task calendar read contract

Base: `buuk` `26e679035c5cb5456f9afe666d2dc8f47ff8427e` (owner-merged
#1632, #1633 and #1634). This change is a read-contract migration, not a new
sporting execution engine. Only the owner merges.

## Implemented boundary

The task collection envelope stays `full_simulation_tasks.v1`; each projected
item is now `full_simulation_task_view.v2`, with:

- `execution_calendar`: the original Saved clock (schema, weeks per year,
  season start year-week, start year and season count);
- `calendar_revision_id`: exactly the immutable original command's
  `expected_revision_id`;
- `full_simulation_task_progress_evidence.v2`, whose week validation and elapsed
  arithmetic use that clock rather than implicit W61/50-season limits.

The server selects this source only after validating the durable task and its
original parent command. It verifies the original Saved Revision's content hash
using the stored schema, identity, owner and payload. Explicit malformed calendar
metadata fails closed. Only an absent historical calendar field means legacy
FAX. A fork's shared original revision retains its original hash identity.

The current Run or current Branch head does not replace this historical source.
A normal all-Branch horizon extension creates new Saved heads; old source bytes,
commands, task v1 storage, audit events and idempotency keys remain unchanged.
Distinct calendars are authenticated once per inventory request/transaction,
never cached across requests.

Live evidence counts actual committed Branch receipts at the original-clock
ordinal. These are all receipts in that Branch/week, not task-exclusive work.
Terminal endpoints remain frozen in the original terminal result/summary; current
Branch movement cannot change them. Historical missing summaries stay unavailable.

The frontend accepts both old v1 responses (explicit legacy FAX contract) and
v2 responses (mandatory clock/revision/version checks). Broken v2 never falls
back to v1. W52/W61/W80, a one-week year, long horizons and numeric overflow
boundaries have focused read-contract tests.

Task rows show the original season label, calendar year and year-week in CS/EN.
For v2 season-preparation handoffs, `calendarSeason` uses the actual season start
year from this original clock, including a season that crosses a calendar year.
Old v1 responses retain Branch-only links.

## Preserved execution limits

The existing authoritative Full Simulation driver still explicitly rejects
non-reference clocks until its sporting/transition/target writers are migrated.
RankingWeek, boundary selectors, original terminal-summary contracts and legacy
retarget request limits have NOT been relaxed. An accepted arbitrary-clock task
DTO or arithmetic unit test is **not** evidence of a W52/W80 Full Simulation.

W52/W80 Saved authority tests use normal Run creation, fork and extension Save,
including SQLite reopen. Progress arithmetic tests use explicit minimal command
stand-ins and do not fabricate accepted sporting outcomes. Real HTTP worker,
lease, replay and restart/browser acceptance continue using supported FAX.
The broad pre-alpha/50-season release gate and realism calibration remain open.

## Verification

Focused frontend tests cover new/legacy schema boundaries, required source
identity, wrong progress versions, safe integer limits, no mutable Run lookup,
CS/EN year rollover and exact-season links without invoking a simulation.
Backend tests cover hash corruption, wrong/missing Saved source, rollover,
original-clock persistence after fork/extension, immutable historical bytes,
terminal endpoints, scope and unchanged unsupported-execution guards.
The existing actual HTTP task acceptance also checks the new DTO against the
real Saved row, unchanged v1 task storage and read rejection of a damaged source.

Run the applicable existing Ready/manual real-browser workflows on the final
head. Draft skips and mocked UI tests do not satisfy those acceptance gates.

The `fullSimulationTasksCalendar*` helper/test filenames deliberately match the
existing `fullSimulationTasks*` browser path selectors. No gate or assertion was
disabled, and future helper-only edits retain the same acceptance selection.
