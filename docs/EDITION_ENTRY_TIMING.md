# Run-owned Edition Entry timing and ranking preparation

This backend/API slice implements decided timing preparation from Master §15.1,
§18 and §31.29. It does not resolve automatic sporting eligibility, create fields
or draws, choose FAX awards, or complete the reference season. The Admin form and
automatic-validator consumer remain follow-ups. No Master decision is changed.

## Ownership and commands

The existing Run Calendar Package event owns
`event_level_overrides.entry_timing` (`edition_entry_timing.v1`). The global source
Calendar is untouched. Unrelated event overrides, Run-local identity and source
baseline/provenance survive the edit. There is no new registry/table or alternate
Save mechanism. Historical JSON without this override retains its original shape.

Under `/admin/runs/{run_id}/branches/{branch_id}/packages/calendar/{package_id}/editions/{event_id}/entry-timing`:

- `GET` inspects the current Working Draft plan and scoped prerequisites.
- `POST /preview` accepts `{ "timing": ... }`, validates and returns the frozen
  before/after plan, Saved head, Draft/Package identity, exact ranking source,
  blockers and `preview_fingerprint`. It writes nothing.
- `POST /confirm` additionally requires `command_id`, the reviewed
  `expected_preview_fingerprint`, `operator_label` and `audit_reason`. One
  `BEGIN IMMEDIATE` transaction recomputes the review, stages the ordinary local
  Package edit and, when available, adopts the existing Tournament Ranking
  Snapshot authority. The normal Working Draft Save remains a separate action.

The local `entry_timing_review` annotation records the explicit command/operator/
reason. It is provenance, not a ranking authority. This effective local review
also makes a later ranking-only preparation visible to the existing Package Save,
which captures both the Calendar and ranking components. Exact retry returns the
authenticated original receipt after Save/restart; reusing an ID with a different
request fails. A failure at the ranking boundary rolls back Package, Draft and
receipt changes together. Two reviewers cannot confirm the same old preview twice.

## Timing and ranking labels

`main_open` is an explicit `RunWeekPosition` including its Run calendar.
`main_duration_weeks` defaults to 2; `qualification_duration_weeks` defaults to 1.
The windows are consecutive, inclusive whole-week ranges and finish before play.
`final_commitment` defaults to the end of the Qualification window; an explicit
pre-play override is supported. No play-to-opening lead is inferred. Ordinals
handle year/season crossings using the actual W; durations are not rescaled.

Master §15.1 selects ranking data **after Main Closing Week − 1**. Master §18
publishes that data when the next week opens, labelled with that next week.
The API exposes both `default_ranking_completed_week` and
`ranking_publication_week`: Main 13–14 / Q 15 selects data through 13, the Official
publication labelled 14. Selecting publication 13 would lose a week of data.
This is an explicit mapping of the two existing rules, not a new timing default.

`ranking_publication_override` explicitly selects another existing publication.
Only the exact Run/Branch-scoped, hash-validated Official snapshot is usable;
neither a candidate nor the latest available ranking substitutes for it. A
missing predecessor at Run start is reported, never synthesized as Week 0 or
silently replaced with the initial ranking. Already bound Editions cannot replace
their snapshot through this command. Reopening/postponement requires its separate
historical process and is outside this slice.

A valid future plan can be confirmed/Saved before its publication exists.
Missing publication and readiness remain visible. The unchanged saved plan can
later be explicitly confirmed again to bind the newly available exact snapshot.
Once a known authoritative clock reaches the old or proposed opening, retiming is
blocked; unchanged configuration may still acquire its exact ranking. The world
head must agree with its latest authenticated publication before binding.

## Honest boundaries

- `ranking_binding_status` separates missing prerequisites, a candidate ready for
  explicit confirmation, and an installed authority.
- `timing_and_ranking_ready` is scoped to the installed plan/binding in the current
  Working Draft, never a claim that Save, eligibility, field or sporting execution
  is complete. `configuration_state` explicitly identifies the Working Draft.
- `automatic_eligibility_status` remains `not_implemented`. The existing global
  unresolved-policy gate is not weakened or removed by this preparation API.
- Missing content, blocked edits and unsupported execution remain distinct. W52/
  W80 timing math is supported, but a custom/native clock does not gain permission
  to use the legacy 61-week ranking store. Valid Package planning may still Save;
  binding is withheld. Native fork aggregate ownership fences remain intact.
- Missing, null/corrupt, foreign or hash-invalid stored inputs are not interchangeable.
  No unrelated points/health/identity gap is approved by a successful timing review.
- No new UI, process-slot count, late cut-off, pre-start history or automatic
  acceptance policy is invented.

## Validation and distinct adversarial pass

Pure domain checks cover W4/W52/W61/W80 crossings, Main/Q/closed boundaries,
explicit lengths/commitment/ranking selection, missing predecessor and invalid
clocks/ranges. Real HTTP/SQLite scenarios use constructed Calendar content and
production-calculated publication fixtures, not a claimed Week Transition or
whole season. They cover Preview non-mutation, explicit confirm/normal Save,
both Saved components, physical runtime reopen, original exact retry, scoped
identities, stale position, opened-plan locks, missing exact source, explicit
override, conflicting immutable authority, corruption, rollback and two writers.

Separate review traced false-ready and recovery paths: publication versus
completed-week labels, no latest-ranking fallback, no overwrite of an existing
binding, no writer borrowing a custom/native clock, no loss of unrelated Package
content, no receipt retarget and atomic late failure. The established Package
snapshot/review/source adapter and Tournament Ranking Snapshot regressions remain
required. Hosted Saved Branch gates also run because the existing Package edit
transaction boundary was extracted for reuse; no path filter/test was weakened.
Full regression, browser use of this new API and 50-season release proof are not
claimed by these scoped tests.
