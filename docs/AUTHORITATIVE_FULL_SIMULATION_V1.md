# Authoritative Full Simulation v1

## Purpose

`Full Simulation` is the canonical long-range Run parent from the current
Run/Branch Position through the final 2049/50 closure. It replaces the legacy
full-season/full-range wrapper as the product path without introducing a second
sporting engine.

The parent is **progressive, reviewed and resumable**. It composes the narrower
canonical authorities already responsible for matches, weeks, seasons, Saved
Revisions and final Run closure.

## Preview

`POST .../authoritative-simulation/full-simulation/preview` is read-only.

The preview freezes:

- current Ranking Week and final 2049/50 Week 61 boundary;
- remaining weeks and seasons including the current one;
- current Position fingerprint and Saved Revision head;
- the first orchestration mode;
- current blockers;
- the invariant that ordinary seasons are owned by canonical `Next Season`;
- the invariant that the final season ends through canonical final Run closure;
- the invariant that Saves and season/final transition confirmations remain explicit.

No future season is simulated by preview.

## Seasons 2000/01–2048/49

Every non-final season receives one deterministic child command ID and is delegated
to the existing canonical `Next Season` parent.

A child may itself stop at Entry/process, Save or Season Transition review. Full
Simulation surfaces that checkpoint and leaves its own receipt pending. After the
explicit prerequisite is resolved, retrying the same Full Simulation command reuses
the same frozen Next Season child.

A completed season index is recorded exactly once before the parent proceeds to the
next season.

## Final 2049/50 season

The final season is intentionally **not** represented by `Next Season`, because
there is no 2050/51 Week 1.

For Weeks 1–60 the parent composes the existing canonical `Next Week` boundary or,
when the Calendar proves that no competitive work exists, the existing audited
empty-week authority.

Week 61 uses authoritative `Next Slot` children for remaining competitive work or
the same audited empty-week proof. No synthetic next-season publication is created.

## Explicit final boundary

If Full Simulation produced final-season sporting state, it pauses at
`final_run_save_required`. Admin must use the existing canonical Save surface.

After a new Saved Revision exists, the parent reads the existing final Season
Transition preflight:

- unresolved prerequisites return `final_run_closure_prerequisite`;
- a ready 2049/50 preflight returns `final_run_closure_review_required`.

Admin then commits the already-existing final Run closure. Full Simulation does not
create a second Closing Ranking, Season Closure Marker, Saved Revision writer or Run
status transition.

## Completed Run observation

The canonical final closure changes the Run to `completed`, so the pending Full
Simulation parent has a special read-only completion path.

On retry it requires:

- Run status `completed`;
- the selected Branch head to be a final-season closure Saved Revision;
- valid embedded Season Closure evidence;
- closure marker boundary exactly 2049/50 Week 61.

Only then is the Full Simulation parent marked complete. This finalization performs no
sporting mutation and does not require the Run to remain writable.

## Durable retry and reopen

A pending parent now persists its exact reviewed command and preview contract inside
the durable Full Simulation operation receipt. The Run/Branch inspection endpoint
returns resumable pending parents after browser or process state loss, including the
original Command ID, operator/audit metadata, reviewed start contract and accumulated
completed-season/final-week counters. The Admin Simulation surface can therefore
restore the exact parent after reload instead of manufacturing a replacement command.
Older pending receipts created before this metadata existed remain backend-resumable
only when the original command payload is still available and are reported separately.

Only one pending Full Simulation parent is permitted per Run/Branch. A new preview or
new parent start fails closed while another Full Simulation parent is pending; Admin
must resume or finish the existing parent first. This prevents two long-range
orchestrations from racing through the same canonical Branch while preserving exact
retry for the already-existing parent.

A pending parent may also be explicitly abandoned. Abandon is an audited control-plane
action, not rollback: the operator must provide a label and reason and explicitly
acknowledge that already committed child work remains canonical. The durable parent
receipt changes from `pending` to `abandoned` and preserves its frozen operation,
progress and abandonment audit metadata. The old parent cannot be resumed after
abandonment; a replacement Full Simulation may be reviewed from the current canonical
Run/Branch state.


Full Simulation parent receipts are also inspectable as durable Run/Branch history.
The history surface includes pending, abandoned and completed parents with Command ID,
start/final range, completed-season/final-week counters and available operator/audit
metadata. Abandoned parents expose the abandonment actor/reason separately. Newly
completed parents persist the original operator and audit reason in the terminal
result receipt; older completed receipts may legitimately show those fields as
unknown rather than reconstructing or guessing them.

The parent freezes deterministic identities for:

- every ordinary-season `Next Season` child;
- every final-season `Next Week` child;
- every audited final-season empty-week child;
- every final Week-61 authoritative slot child.

Already-completed work is never rerolled. One parent identity survives process reopen,
Saved Revision changes at explicit checkpoints, ordinary Season Transitions and final
Run closure.

## Admin UI

The canonical Simulation panel exposes:

1. operator label + audit reason;
2. **Review authoritative Full Simulation**;
3. start/final boundary and remaining week/season counts;
4. exact ordinary/final orchestration modes and explicit-boundary policy;
5. **Simulate reviewed authoritative Full Simulation**;
6. current progressive checkpoint, blockers and completed-range counters;
7. **Retry reviewed authoritative Full Simulation** with the same parent command ID.

When the parent pauses, the Admin surface keeps the durable parent Command ID visible,
shows completed-season and final-season-week counters, renders a season-boundary
progress indicator, and gives checkpoint-specific next-action guidance. Discarding the
review intentionally abandons that in-memory operator handle; normal prerequisite
resolution must keep the review and retry the same parent identity so already-committed
child work is observed rather than rerolled.

The UI points to the existing Save, ordinary Season Transition and final Run closure
controls instead of duplicating those authorities.

## Acceptance

PR-critical coverage proves two complementary paths:

- a real Official Run season is driven through the outer Full Simulation parent,
  including process reopen, explicit Save and reviewed ordinary Season Transition;
- the final 2049/50 edge observes an externally committed final Run closure and turns
  the same pending Full Simulation parent into an exact-retry-safe completed result.

## Scope limits

- Full Simulation does not invent Entry/WC or other explicit authored decisions.
- It does not auto-confirm ordinary Season Transitions or final Run closure.
- Live progress streaming, immediate pause/cancel and background-job UX remain a
  separate execution-surface layer above this deterministic resumable kernel.
- Full Simulation is canonical orchestration, not a claim that every deeper future
  feature planned beyond pre-alpha already exists.
