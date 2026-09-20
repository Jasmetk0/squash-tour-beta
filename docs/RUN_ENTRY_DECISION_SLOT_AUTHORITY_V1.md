# Run entry decision slot authority v1

The legacy `SeasonEntryBatchService` already makes overlapping tournament entry
decisions from one shared active-player snapshot. PR #862 preserves every pre-cut
Main/Qualification application decision from that batch.

This slice binds that decision evidence to the canonical Run chronology without
inventing the still-open application-validity policy.

## Run/Branch slot boundary

`RunEntryDecisionSlotAuthority` freezes:

- exact `run_id` and `branch_id`;
- exact FAX `RankingWeek`;
- one global `decision_slot_ordinal >= 1`;
- the persisted source Entry-batch fingerprint;
- the complete pre-cut application-decisions fingerprint;
- the frozen active-player snapshot fingerprint;
- one immutable fingerprint for every preserved Main/Qualification decision.

A dry-run Entry batch cannot become Run authority.

The existing match `SimulationSlotModel` remains match-specific. This adapter does
not pretend that the match-event ledger already persists entry-decision events. It
binds the product-level global slot ordinal explicitly while a later unified slot
ledger remains a separate integration step.

## Validity stays upstream

A preserved decision means **the player chose to apply**. It does not by itself prove
that the application is valid.

`ValidatedApplicationDecision` therefore supplies explicit external evidence:

- stable application ID;
- exact event/player identity;
- Main vs Qualification window;
- fingerprint of the preserved source decision;
- NR tie-break token;
- validation authority ID/fingerprint;
- provenance.

`ValidatedEntryDecisionSlot` accepts only a subset that exactly matches the
preserved slot evidence. Unknown decisions, changed Main/Q targets and changed source
fingerprints fail closed.

Only that validated subset can project to
`TournamentApplicationSubmissionBatchAuthority`.

## Tour-entry path

The resulting path is now:

`SeasonEntryBatchService shared snapshot`
→ complete pre-cut application decisions
→ `RunEntryDecisionSlotAuthority`
→ explicit validation evidence
→ `TournamentApplicationSubmissionBatchAuthority`
→ atomic submission persistence
→ first `PlayerTourEntryTrigger`.

Field capacity remains downstream and cannot erase the fact of a valid submission.

This slice does not implement the missing eligibility/deadline policy itself and does
not infer validity from acceptance into Main, Qualification, alternate or outside-cut
status.
