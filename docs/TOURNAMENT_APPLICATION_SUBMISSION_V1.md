# Tournament application submission authority v1

This authority freezes the exact moment of a **valid** MSA Tour tournament
application, which Master Vision §9.2 defines as one formal Tour-entry trigger.

The contract records Run/Branch, player and event identity, requested Main/Q entry
window, FAX submission week, global decision-slot ordinal, stable NR tie-break token,
and the ID/fingerprint of the upstream validation authority that established the
submission as valid.

It does not decide the validation policy itself. Eligibility/deadline/AI rules remain
upstream. It also does not claim that the player is accepted into Main Draw or
Qualification: capacity rejection is downstream and does not erase a valid
submission.

The authority can project directly into the existing `TournamentEntryApplication`
field-cut payload. That projection intentionally drops only the submission week and
validation provenance that the downstream field cut does not need; player/event,
entry window, decision slot and NR tie-break identity remain identical.

This slice does not persist submissions or emit a Tour-entry trigger yet. Those are
separate integration boundaries so a future command can validate the exact current
week/slot and commit submission evidence plus first-entry trigger atomically.
