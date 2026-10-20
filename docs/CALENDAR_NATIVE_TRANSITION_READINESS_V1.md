# Native transition readiness and honest Admin capability

This candidate depends on the confirmed birth writer in #1565. It does not add
sporting rules or unlock post-birth competition, source epochs or Full Simulation.

## Read-only actual runtime contract

`GET .../calendar-tour/prospect-intake/transition-readiness` authenticates the
actual Run/Branch Saved lineage and live owners through the same Tour context
used by commands. Its `native_tour_transition_readiness.v1` binds current HEAD,
Tour/checkpoint, Health/source, frozen completed week and current Run calendar.
It reports the correct Week/Season action, exact next target (or terminal null),
actual due birthdays, admitted population, blockers and current/target scope.

This endpoint is not the older read-only component proposal. A valid native
identity is not an unknown foreign InitialWorld player. A staged birth requires
manual Save before another command. Reaching the Run horizon is a normal blocked
capability response, not a fabricated future date or a server exception.
No request executes, Saves, starts simulation or pre-authorizes a later command:
actual execution still requires its own exact seed/HEAD preview and confirmation.

## Admin behavior

The CS/EN panel loads capability only on explicit request. It validates HEAD,
Run/Branch, Tour/checkpoint, completed/target clocks and operational flags before
displaying a result. Scope/generation tokens and abort signals reject delayed or
completed stale results across A→B→A, commands and Save. It contains no Execute or
Save button. Unsupported post-birth Edition/Entry/match actions remain disabled;
confirmed birth review lists admitted identities. Normal Week/Season command and
separate manual Save remain authoritative. The older component-only preflight is
hidden after birth and no longer claims that the coupled writer does not exist.

## Explicit source limitation

Until historical source epochs are implemented, a changed Run-shared prospect
source cannot be Saved while any Branch has an activated native v4 birthday.
Source Save preview now reports `native_prospect_source_epochs_required` and
`can_save: false`; the transactional writer independently rejects a forced POST.
This is the existing technical limitation made explicit, not a permanent product
ban on annual generation. Detection is Run-scoped, includes other Branches and
checks physical lifecycle identity/hash before trusting a native row.

## Evidence and remaining gates

- Production HTTP/SQLite: W2/O2 birth, read-only database dumps, unsaved/Saved
  states, physical API restart, foreign scope and actual terminal horizon.
- Existing real birthday/recovery case: activated metadata protection, incompatible
  future-source preview refusal and forced Save rollback.
- Real SQLite guard component: another Branch, foreign Run isolation and corrupt
  physical row rejection. Its pure lifecycle fixture is not a complete Tour test.
- Frontend component/validator tests cover no automatic request, CS/EN, forged
  source/clock/capability, stale response rejection and disabled competition.
- TypeScript/Vite build remains required. Full native API/season/browser gates
  remain mandatory; the new real Chromium birth-readiness scenario separately
  checks readiness, explicit birth confirmation, 57 attributes, manual Save and
  unchanged pre-Save Viewer. Local Chromium is unavailable in this workspace,
  so that scenario is not claimed passed until its actual final-head CI is green.

These are bounded development checks, not the full Master pre-alpha release gate.
