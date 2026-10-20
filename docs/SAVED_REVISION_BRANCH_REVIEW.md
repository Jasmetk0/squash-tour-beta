# Saved Revision Branch creation review v1

This candidate adds review/confirmation/retry safety to the existing writer. It
**does not implement match-bearing native Branch forks**. Those remain blocked
by real coverage and historical-authority guards. It is not the completion of
the native branching task or a pre-alpha release.

## Existing production path

`POST /run-containers/{run_id}/branches/preview` accepts the same source Branch,
Saved Revision and optional display name as ordinary Branch creation. It reads
one SQLite snapshot, authenticates reachable Saved lineage, validates auxiliary
lifecycle/Health/prospect components, and returns:

- the selected source's hash, actual historical owner and current source head;
- the current Viewer Branch and exact proposed unique Branch name;
- historical player, played-match and ranking counts and sporting week;
- known component/source-authority blockers and `can_create` eligibility;
- a fingerprint binding that review plus the Run metadata/status and reserved names.

The fingerprint is an optimistic concurrency token, not authorization to rewrite
history. The complete existing writer still validates/remaps/installs all
supported content after confirmation; review eligibility does not bypass any
later guard or guarantee persistence success. No preview creates a Branch,
revision, checkpoint, draft, receipt or simulation event.

`POST /run-containers/{run_id}/branches` keeps its original source fields and
accepts an optional `review` containing `command_id`,
`expected_preview_fingerprint` and `explicit_confirmation: true`. The CS/EN
Admin uses this reviewed path. Legacy callers may omit it and continue through
the original complete safety checks.

A reviewed create serializes inventory validation and the existing writer in
one `BEGIN IMMEDIATE` SQLite transaction. Stale source head, Viewer selection,
metadata, proposed name or inventory rejects before writes. A new
`saved_revision_branch_commands` table records the request digest, created Branch
and original response in the same transaction. Startup adds the table using the
existing schema bootstrap. Exact retries return the same original response,
even after a subsequent Branch Save or physical backend restart. Different
inputs with that Run-scoped command id conflict. Receipt failure rolls back all
Branch/draft/revision/receipt writes. Ordinary generated-identity and name
collisions retain their existing rejection behavior.

The Admin freezes the exact token with the submitted command. An uncertain
response offers an explicit retry of that same request. The result links into
the created Branch after refreshing both history-page and Admin-shell Branch
inventories. Read-only history navigation and immediate fork parameter/review
controls do not become unsaved Run edits. Unrelated actual Working Draft and
form safeguards remain active. Viewer selection and Manual Save remain separate.

## Reproduced native gap

A real saved population, Health baseline, three original MatchEngine knockout
matches, population checkpoint, weekly development and initialized Tour produce
HTTP 409 on the original Branch endpoint. Unsupported component coverage is:

- `calendar_standalone_match`;
- `calendar_player_sporting_checkpoint`;
- `calendar_tour_authority`.

After actual admission, the existing v4 lifecycle and v3 Health guards also
require authenticated fork source/Entry/transition authority. The new review
reports these guards without relaxing them. Run-shared prospect epochs remain
immutable historical sources; no Run prospect row is copied or rewritten.

A future implementation must authenticate the shared source revision and keep
original match logs/inputs/results, ranking and effective configurations. It
must establish target-owned mutable state and new command authority without
presenting recomputed hashes as permission to change historical sources. Both
Branches must then independently play, Save, reopen, replay and restore after
restart. This is the remaining work, not a claim made by this candidate.

## Verification boundary

`test_saved_revision_branch_review_api.py` uses a running production HTTP server
and actual SQLite. It covers read-only review, explicit confirmation, late-write
rollback, concurrent duplicate submit, exact/conflicting retry, stale review,
foreign/unreachable/corrupt sources, separate Manual Save and restart.

`test_native_saved_branch_review.py` uses actual production population, original
MatchEngine matches, native admission, future cohort materialization and source
epoch Save, historical review/refusal, immutable source equality, original match
replay and source restore after restart. It asserts refusal, not native fork
success. The original native Tour/birth/post-admission/season acceptance gates
remain required for changes to shared persistence.

`saved_revision_branch_review_browser.py` uses real Chromium and the production
backend. It tests review/cancel/explicit create, Viewer isolation, opening the
created supported Branch and native blockers in CS/EN. Mocked component tests
are separate UI contracts. The dedicated workflow runs actual HTTP/SQLite and
browser cases; it does not replace existing gates or certify the full pre-alpha.
