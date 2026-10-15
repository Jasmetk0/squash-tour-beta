# Full Simulation event and global-slot targets — Master v81

Implementation baseline: `buuk` `0691123aa421395732a5d6fb86eb7a35ba1df4f4`,
merged #1471; no open PR at the initial 15 October 2026 audit. Implements #1472
as one vertical slice above the existing durable server worker. Master §27.23,
§31.7/31.36 and §36 remain authoritative; no product decision or Master label is
changed. This is scoped PR acceptance, not full pre-alpha/50-season acceptance.

## What Admin can do

For one exact original, pending Full Simulation parent, open **Review precise
targets** in Run Admin. Review the current canonical choices, select the exact
edition or global slot, supply operator/reason and explicitly confirm the review.
The current week is the supported horizon. Future, unplanned weeks cannot be
selected by guessing an ordinal or a tournament name.

Supported choices:

- **BEFORE global Simulation Slot #K**: existing immutable match schedule slots,
  including v1 simultaneous groups, or a reserved Entry decision slot. Global
  ordinals include Entry and completed WC reservations; they are not dense
  match-only indices. No selected slot is materialized or played by this parent.
- **BEFORE this edition's final slot**: a final resolved through the validated
  canonical Draw → Match Topology projection's terminal group, or an already
  frozen hybrid knockout bracket's `terminal_match_id`. Qualification sections,
  BYEs and multi-round hybrid topology use their existing validators. Exactly
  one main-draw schedule slot must contain that actual terminal group.
- **AFTER this edition is officially closed**: the exact Run/Branch-owned
  `OwnedTournamentRankingSource` is durably present, validated and bound to the
  chosen edition/current completion week, with matching source/adopting-command
  fingerprints and every event slot fully committed. A played final alone,
  template result, another Branch's source or an already closed edition at
  selection time is insufficient.

The current owned-source contract uses `edition_id == Calendar event_id`.
No broader series/season/name matching is introduced. A v2 scheduled legacy
four-player event may support AFTER through its validated owned source; its
legacy bracket is deliberately insufficient for BEFORE-final selection.

The UI lists unavailable current editions with reasons: missing schedule,
non-executable/unfrozen/ambiguous final, started final or already closed source.
Pure groups do not acquire an invented final. Hybrid BEFORE-final is unavailable
until the real post-group bracket exists; the operator can then review it.
AFTER is unavailable for a hybrid until its executable knockout bracket exists.
It may wait for supported result/points approvals using existing
`awaiting_operator` checkpoints and explicit same-task continuation. An earlier
pending Next Week that froze a different schedule also makes these choices
unavailable (`parent_week_schedule_review_changed`); safely Stop that parent and
review a new operation after preparing the topology. This slice does not rewrite
a wider child's reviewed scope.

The existing absolute and relative week/season target editor remains available.
Applying any such target clears the precise boundary. Resetting to S49 W61
restores the original final-Run path without replacing the original command.
A reached shortened target terminates this parent as `target_reached`, leaves
sporting work in the Working Draft and never Saves or closes the 50-season Run.

## Contracts and immutable review

`GET .../full-simulation/target-options?command_id=<original parent>` returns
`full_simulation_boundary_options.v1`, exact Run/Branch/parent scope, current week,
validated selectors and unavailable reasons. It executes no sport and creates no
parent, task, revision or target.

The existing `POST .../full-simulation/target` accepts exactly one of
`target_week`, `relative_target` or new `boundary_target`. The latter is a
`full_simulation_boundary_target.v1` containing kind/week, global slot ID/ordinal
and groups where applicable, exact event/edition, schedule/Entry fingerprint,
Calendar Event fingerprint, final topology fingerprint where applicable, and a
canonical selector fingerprint. It rejects unknown fields and malformed shapes.

One effective kind exists at a time. `effective_boundary_target` is null for
weekly targets. When a boundary is effective, the old `effective_target_week`
retains the original S49 W61 compatibility value and is **not** the boundary's
meaning. Pending, History, global operations, server tasks and CS/EN presentation
expose the precise selector separately.

Each target revision preserves the control request ID, operator/reason, applied
week, selected immutable selector and fingerprinted review with exact
Run/Branch/original-parent scope. Identical boundary retries return the original
`authoritative_full_simulation_target_result.v2` acknowledgement (with
`replayed=true`), even after newer targets, terminal completion and later work.
They neither resolve again nor reinstate an old target. Changed input under the
same request ID conflicts. Legacy weekly response/replay semantics remain v1.

## Writer ordering and worker integration

The existing execution lease/token/expiry, task claim and
`FullSimulationExecutionGuard` remain mandatory. A callback checks the current
effective boundary **after SQLite BEGIN IMMEDIATE acquired writer ownership**,
before the next parent/child writer. It joins the same Connection for reads and
never commits a separate transaction. It does not run Position's speculative
Week Transition preflight from that hook.

A prior child that owns the writer commits first. Retarget waits, validates the
then-current canonical schedule and rejects a selected slot that has started.
A retarget that commits first fences every subsequent child transaction. No
match, simultaneous group set, slot or closing transaction is truncated. Before
reaching a slot, every earlier match slot must be complete with exact plan,
checkpoint and complete group receipts; earlier Entry validation must match its
reserved authority. Interleaved tournament transit slots remain chronological.

Before-slot/final selectors freeze the complete current schedule/Entry identity.
Changed topology/schedule, moved week or an externally started target produces
`target_boundary_review_required`, with no further sport or fabricated success.
AFTER validates the current frozen hybrid schedule at safe points while retaining
the exact Calendar Edition identity. A changed wider child review is an explicit
unsupported boundary, never silent rebasing of its original scope. Its source is absent at selection and must
subsequently pass the normal owned-source validator. Corrupt selectors, scope,
source ownership, completed slot evidence or audit fail closed.

Completion is re-evaluated under a new terminal writer lock. If an intervening
retarget changed the goal, `target_changed_before_completion` waits for explicit
same-task continuation. A concurrent pause is acknowledged safely; a committed
Stop wins. No optimistic earlier detection can close the newer target falsely.

The worker continues without a browser. Pause/resume, Stop, global exclusion and
explicit expired-lease recovery reuse #1471; startup/GET never restarts tasks.
An unresolved operator checkpoint is not polled into sporting progress. Existing
Save, Entry, WC, standings/points and Season/Final Transition approvals remain
manual. No new slot taxonomy, sporting RNG, ranking rule, World Event,
notification, public knowledge or Viewer publication is introduced.

## Frozen terminal evidence and compatibility

New precise terminal summaries use `full_simulation_terminal_summary.v2`. Alongside
#1469's original command, actual Position, Saved head, child ownership and winners,
they freeze the effective selector and `full_simulation_boundary_evidence.v1`:

- BEFORE: reached week, exact slot ID/global ordinal/groups and schedule fingerprint;
- AFTER: reached week, exact edition/event, owned-source fingerprint and adopting
  command ID, with the current validated schedule fingerprint.

The terminal status, evidence and summary are captured in the same transaction.
Summary reads and terminal replays validate frozen scope/hash/chronology and use
that historical Position, not today's Branch, topology or source. Later explicit
Save does not rewrite it. Existing valid weekly v1 summaries remain valid;
unrecorded old endpoints remain unavailable. A safe Stop with a precise target
also records the selector, while correctly reporting that it did not reach it.

No DB schema migration is needed: versioned fields are additive in the existing
parent's JSON receipt; server-task identity and original reviewed command stay
unchanged.

## Verification and reproducible evidence

`tests/application/test_full_simulation_boundary_targets.py` uses real production
FastAPI over TCP, file-backed SQLite and actual MatchEngine children for:

- retargeting a live durable worker before a slot and after official source closure;
- exact prefix comparison with an uninterrupted copy of the same DB/input/command;
- no post-target sport or automatic Save, original receipts/RNG ownership retained;
- lost-response retry, cross-scope/mismatched-ID denial, later revision/reset,
  passed selection and corrupt effective selector;
- two interleaved tournaments with all earlier transit slots included;
- expired/reclaimed worker recovery after a genuine child and stale-owner fencing;
- a retarget between actual boundary detection and terminal commit, followed by
  explicit continuation to the newer target.

Additional focused contract tests exercise strict selectors, canonical qualification/
BYE final projection, a real two-round hybrid bracket and a reserved Entry prefix.
These isolated topology tests are not described as HTTP integration.

CS/EN component/client tests cover explicit review, scope/shape validation, unavailable
choices, stale errors, identical request retries and frozen v2 source/slot summaries.
Those tests mock the HTTP boundary and do not prove sporting execution.

`scripts/full_simulation_boundary_targets_browser.py` creates the real 64-player
Run, Entry, canonical Draw and schedule through native Admin forms. It starts the
server task, retargets BEFORE the actual final after a genuine match, kills the
actual server process, proves no automatic restart, explicitly recovers the same
task, closes the tab and verifies two matches/no final slot. A separate newly
reviewed parent then targets AFTER the exact owned closure in Czech, commits the
real final/source, closes/reconnects through Task Center and validates its frozen
summary. All Saved Revisions remain unchanged. Native screenshots, JSON and trace
are retained by the dedicated Boundary Targets Browser workflow.

Existing Controls, Server Tasks, Saved Group and applicable Hybrid browser gates
remain independent required regressions. Fast CI, focused backend/frontend checks,
compile/build and all triggered final-head workflows must pass before merge
handoff. The full Master §31 release suite remains separate.

## Deliberate remaining scope

Future-week targets without an adopted current schedule, dynamic hybrid targets
before topology exists or after a wider child froze an incompatible range,
generic event kinds, tracking/stop rules,
notifications and presets remain future work. These selectors cannot claim a
completed season, 50-season Run or full pre-alpha release. Recommended next slice:
versioned, safe extension of an existing Next Week after hybrid bracket
materialization, with native same-parent checkpoint acceptance; then
tracking/stop rules over these proven boundaries.

## Separate adversarial review

The final review checked actual writer/flush boundaries and identified three
material cases addressed in this patch: a retarget between detection and terminal
commit cannot claim the old goal; a `complete` slot flag alone is insufficient
without its whole group ledger/plan/checkpoint; and a frozen wider weekly review
cannot silently absorb a later hybrid schedule. Old receipts, Stop, exact retries,
source-row/payload owner consistency and native process recovery were checked
separately from the initial implementation. Existing Next Week extension remains
explicitly unsupported and is a follow-up, rather than invented behavior.
