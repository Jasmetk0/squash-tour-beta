# Pre-alpha copied-FAX Entry validation policy gate

## Purpose

Make the remaining unattended-release blocker explicit and machine-readable instead of hiding it inside a generic Entry-process pause.

The current Master/technical plan leaves automatic tournament-application eligibility and deadline policy open. Existing infrastructure can already generate shared-snapshot Entry decisions, freeze their Run/Branch slot authority, accept explicit validation outcomes, persist valid application submissions and build Entry Fields. What is missing is the automatic policy that decides those validation outcomes without Admin intervention.

## Gate contract

The gate reports:

- fixed policy identity `automatic_application_eligibility_deadline.v1`,
- `policy_status=unresolved`,
- `master_status=open`,
- `blocks_unattended_release=true`,
- current authoritative Week/slot/Position fingerprint,
- whether the current Entry decision slot is frozen,
- its fingerprint and frozen decision count,
- whether validation has already been explicitly resolved,
- a precise current blocker code.

When frozen Entry decisions exist without validation, the blocker is `application_validation_policy_unresolved`.

## Long-acceptance integration

When the real Full Simulation parent pauses at `entry_process_required`, the copied-FAX long-acceptance probe now inspects this policy gate. If the current Entry slot is frozen but unresolved, the report carries the specific release-policy blocker and gate fingerprint.

## Admin

Authoritative Simulation shows this policy gate separately from the FAX input-readiness gate. This distinguishes missing/invalid data from a consciously unresolved sporting-policy decision.

## Next

Resolve the product rule for automatic application eligibility/deadline behavior, version that policy, implement it as validation authority, and then feed resulting valid submissions into the existing Entry Field builder.