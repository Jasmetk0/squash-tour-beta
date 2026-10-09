# Completed standard-tournament Saved Revision Branch fork — acceptance boundary

## Scope

A materialized Branch created from a Saved Revision after Week Transition may
inherit **at most one** completed, standard, canonical Run-owned tournament
across its confirmed historical Week Transitions. No Season Transition,
ranking correction, disciplinary-zero version, unsupported tournament format or
second completed tournament is implicitly enabled.

Ranking's existing remapper must independently reconstruct the target-Branch
tournament result and point/prize authority, its ranking result-version chain,
Official Ranking inputs/snapshots, publication and transition authorities.
The audit binder then validates the exact source and target tournament bindings,
chronology, original World Event/receipt, saved ranking authority and Saved
Revision lineage before re-issuing target-owned transition receipts/events.

A completed tournament also requires evidence of real saved Simulation Slot
results: every competitive match fingerprint in the canonical tournament result
must exist in the original Slot history and have a target-local remapped result.
Existing player lifecycle, sporting/health and Slot remappers remain mandatory.
The installer runs inside the original atomic SQLite Branch transaction, captures
the complete target ranking after installation and aborts on mismatch.

Source revision history remains immutable, with the target fork revision as a
new historically linked child; original match fingerprints in the frozen
canonical result may serve as historical sporting provenance, while the target
owns independently remapped Slot result records. Cross-layer reference
consistency must be verified by the end-to-end acceptance before this capability
is considered supported.

## Focused PR acceptance

`tests/application/test_single_tournament_saved_revision_fork.py` reuses
the full-season acceptance's canonical four-player Week-1 setup but does not
execute the remaining 60 weeks:

1. Create a real HTTP/SQLite Run, apply World/Calendar package snapshots,
   adopt the initial players and Official Ranking.
2. Perform explicit audited Admin Entry decisions and validation, adopt the
   canonical tournament ranking authority, field and draw, then install the
   real Slot schedule.
3. Execute the actual match/rally engine and Week Transition, Save, close the
   API and reopen against the same SQLite file.
4. Attempt a deliberately injected transaction-time audit-installer failure
   and prove no partial Branch remains.
5. Create the Saved Revision Branch, verify target-owned tournament/ranking,
   paired Week Transition receipts/World Events and independent Branch identity.
6. Complete the next event-free week on the fork, Save, and verify the original
   ranking and position have not moved.

`tests/infrastructure/test_week_transition_fork_audit.py` supplies short
reconstruction and forgery tests, including missing/wrong tournament target
and damaged receipt data. Existing event-free PR-critical regressions remain
mandatory.

**Evidence status (9 Oct 2026):** First real HTTP/SQLite integration passed in
Fast CI workflow `37895207678` at commit `b9904863a45696a4d79a5e160600da8c07384c04`
(26 PR-critical tests passed; 3478 intentionally deselected). That run includes
one completed tournament, fork, independent continuation and rollback injection.
Follow-up changes still require green checks on their final PR head. This
proves only the narrow four-player standard-tournament scenario, not a
50-season or multi-tournament pre-alpha gate.

## Explicitly unsupported

- Multiple completed tournaments, tournament corrections and disciplinary zeros
  in confirmed Week Transition history.
- Season Transition, Season Closing and final season rollover.
- Tournament-group/hybrid ranking remaps lacking dedicated nested provenance.
- A complete 50-season FAX pre-alpha or a realism calibration certificate.

The current `application_validation_policy_unresolved` gate remains in place.
An explicitly audited Admin validation in this fixture does **not** implement
automatic player application eligibility/deadline policy. Product conflict,
if any, must be reconciled against the current Master independently; this
acceptance changes no entry, scoring or ranking policy.
