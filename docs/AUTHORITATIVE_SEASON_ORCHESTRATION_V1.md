# Authoritative Next Season v1

## Purpose

`Next Season` is the first canonical long-range simulation parent. It progresses from
the current Ranking Week to the next Season's Week 1 without replacing the narrower
authorities that already own matches, weeks, Saves or Season Transition.

The operation is **progressive and resumable**. It only performs work that can be
proven from current canonical state, and it stops at explicit Admin boundaries rather
than inventing policy or silently approving a transition.

The final 2049/50 closure remains owned by the dedicated final Season Transition and
is deliberately outside this V1 action.

## Preview

`POST .../authoritative-simulation/next-season/preview` is read-only. The Admin
supplies one durable parent command ID plus operator/audit provenance.

The preview freezes:

- current Ranking Week and next Season Week 1 target;
- current Position fingerprint and Saved Revision head;
- number of weeks remaining including the current week;
- the current first action;
- current canonical blockers;
- the long-range policies:
  - empty weeks may only be auto-closed through the existing audited
    Calendar-proven empty-week authority;
  - Season Transition still requires an explicit Save and the existing reviewed
    transition surface.

The preview does not simulate future weeks.

## Progressive children

The durable parent composes existing canonical operations instead of creating a second
simulation engine.

### Ordinary weeks

When the current week has competitive work or terminal sporting evidence, the parent
freezes one deterministic child `Next Week` command and executes that existing
orchestration. A blocked child becomes a blocked Next Season checkpoint while the
parent receipt remains pending.

### Calendar-proven empty weeks

If a week has no sporting evidence yet, the parent may create one deterministic
`AuthoritativeEmptyWeekCompletionCommand` using the reviewed parent operator/reason.
That child still runs the complete production proof: Calendar, packages, adopted
authority, schedules, Entry/WC slots, historical match rows, owned tournament sources,
lifecycle and sporting state must all prove that zero competitive matches are valid.

If the week cannot be proved empty, the parent stops at
`week_preparation_required`. It never treats missing data as an empty week.

### Explicit Entry/process boundaries

A current Entry process returns `entry_process_required`. The parent does not choose
application validity, tournament preference, Wild Cards or other explicit Admin
decisions.

## Week 61

Week 61 never uses ordinary `Next Week`.

Remaining competitive slots are executed through deterministic authoritative
`Next Slot` children. If no competitive work exists yet, the same audited
Calendar-proven empty-week command is used.

Once Week 61 sporting evidence is complete, the parent records that it reached the
season boundary.

### Explicit Save checkpoint

If the parent produced any season work, it returns
`season_transition_save_required`. The Admin must use the existing canonical Save
surface. The parent never creates a hidden Saved Revision.

Retry before that Save returns the same checkpoint.

### Existing Season Transition review

After a new Saved Revision exists, the parent evaluates the existing canonical Season
Transition preflight.

- unresolved prerequisites return `season_transition_prerequisite`;
- a ready preflight returns `season_transition_review_required` and exposes the exact
  preflight.

The Admin then reviews/commits the existing Season Transition. The Next Season parent
does not select incoming policies, create a second Closing Ranking writer or bypass
the normal atomic rollover command.

Once the world has actually reached next Season Week 1, retrying the exact same parent
marks it complete.

## Durable retry and reopen

The parent receipt freezes deterministic IDs for:

- every contained Next Week child;
- every audited empty-week child;
- every Week-61 Next Slot child.

Completed children are never rerolled. The parent can survive process reopen, a manual
Save, and the external reviewed Season Transition while retaining one identity.

The production PR-critical acceptance now drives the real Official Run from Season 0
Week 1 through Week 61, process reopen, explicit Save, ordinary Season Transition and
Season 1 Week 1 through this parent.

## Admin UI

The canonical Simulation Admin panel provides:

1. operator label + audit reason;
2. **Review authoritative Next Season**;
3. start/target boundary, remaining-week count, first action and policies;
4. **Simulate reviewed authoritative Next Season**;
5. blocked checkpoint, completed-week count, blocker/detail explanation;
6. **Retry reviewed authoritative Next Season** using the same parent command ID.

The Next Season review intentionally survives Saved Revision head changes on the same
Run/Branch, because the W61 Save checkpoint requires that change. Switching Run or
Branch discards the review.

Existing Save and Season Transition sections remain the actual authorities for those
explicit checkpoints.

## Scope limits

- Final 2049/50 closure remains the dedicated final Season Transition.
- `Full Simulation` remains compatibility-only.
- Entry/WC and other authored process decisions are never automated by the long-range
  parent.
- Live progress streaming, immediate pause/cancel and background-job UX remain a
  separate execution-surface layer above this deterministic resumable kernel.
