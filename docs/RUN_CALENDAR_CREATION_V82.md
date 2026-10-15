# New-Run calendar choice — v82 implementation slice

This implements optional calendar input at **creation**, not a mutable calendar
editor, horizon extension or W52 sporting execution. Existing Run rows, Saved
Revisions, packages and task goals are never rewritten.

`POST /run-containers` still accepts just `display_name` with the same explicit
FAX default. An optional `calendar` object has `weeks_per_year`,
`season_start_year_week`, `start_year`, and **either** `season_count` **or**
`last_season_start_year`. The latter means the calendar year in which the last
season starts, not its displayed ending year. Offset 1 produces a single-year
season label. The server validates strict integers, offset/horizon consistency
and finite storage/exact-JSON bounds before generating identities or writing.
Null, incomplete/unknown metadata and conflicting horizon inputs are rejected;
they never silently select FAX. Explicit legacy schema labels cannot be submitted
as a new calendar.

`POST /run-containers/calendar/creation-preview` accepts the same calendar object
and returns its exact first and last week, normalized versioned clock and
`sporting_calendar_supported`. It creates no Run, players, draft or task.
This compatibility flag is about the clock only, not overall sporting readiness.
Non-default calendars are currently **planning-only**: the existing Week/Season/
Full Simulation writer gates remain in force until the clock/ranking migration
is complete. Creating a W52 Run is not a claim of W52 sporting support.

The atomic bootstrap persists the chosen calendar and matching timeline columns
in the new Run and its immutable first Saved Revision. Ordinary explicit Save,
shared-ancestor Branch creation and runtime restart preserve the same calendar
without rewriting the original payload/hash. Duplicate-name creation rolls back
the complete aggregate.

Verification: real HTTP/SQLite tests in
`tests/api/test_run_calendar_creation_api.py`, including W52/O1 and W52/O35,
count/end-year equivalence, read-only preview, invalid-input non-mutation, Save,
fork, original hash preservation and complete service restart. Existing creation,
target-preview, calendar-authority and execution-gate tests remain relevant.

The CS/EN Admin creation form keeps name-only creation and optionally exposes
FAX/Earth/custom W, offset, start year and either horizon input. It requires an
explicit server preview before creation. Editing/unmounting invalidates the
review and late responses cannot restore stale consent. The create response must
match the reviewed clock before navigation. The Home progress uses the stored
Run calendar, keeps absent legacy metadata distinct from corrupt explicit data,
and bounds rendering for large valid horizons. Unsupported clocks retain package
planning but Home explicitly withholds legacy year-2000 player/ranking/tournament
setup panels instead of advertising those as ready.

New explicit-clock Runs also fail closed at InitialWorld adoption, ranking
candidate staging, standalone simulation and authoritative match slot/group
writes. The checks run in the writer transaction after exact completed replay.
Verified historical fork materialization/restoration retains its prior meaning;
it is not a new sporting calculation. Package planning remains independent.
Focused integration covers no partial writes and preserved ordinary default FAX
adoption/ranking/replay. The existing empty-Run/two-player standalone acceptance
also exposed a missing initial Health bootstrap; the flow now installs the same
canonical initial Health used by ordinary adoption before actual match execution.

Additional verification: CS/EN component/DTO/Home tests and the existing real
Shell Browser acceptance extended with custom creation, non-mutating preview,
edit invalidation, exact initial Saved clock, reload and correct 3/52 tracks.
Browser evidence is produced by its existing CI workflow; component mocks are
not described as full sporting integration.

Next: remaining authoritative sporting clock, annual age/development/ranking
units, safe edits/extension and calendar import compatibility. Keep the writer
gates until actual W52 sporting acceptance justifies removing each one.
