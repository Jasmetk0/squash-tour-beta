# Completed standard-tournament Saved Revision Branch fork — acceptance boundary

## Scope

A materialized Branch created from a Saved Revision after Week Transition may
inherit **at most two** completed, standard, canonical Run-owned tournaments
across its confirmed historical Week Transitions, one per distinct completed
week. Same-week multi-event transitions remain unsupported. No Season
Transition, ranking correction, disciplinary-zero version, unsupported
tournament format or third completed tournament is implicitly enabled.

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

`tests/application/test_single_tournament_saved_revision_fork.py` runs both
the original one-tournament and the new consecutive two-tournament cases,
using the full-season acceptance's canonical four-player setup but never
running a 61-week or 50-season campaign:

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
6. In the two-tournament variant, finish the Run-owned Week-2 tournament
   with a second audited Admin entry validation, canonical Draw, actual
   match/Slot engine, Official Ranking publication, Week Transition and Save.
7. Verify both independent canonical tournament/result/point authorities
   survive the target fork with identical sporting outcomes but distinct
   Branch-owned fingerprints, then complete the next event-free week on
   the fork and Save. Confirm the original ranking and position do not move.

`tests/infrastructure/test_week_transition_fork_audit.py` supplies short
reconstruction and forgery tests, including missing/wrong tournament target
and damaged receipt data. Existing event-free PR-critical regressions remain
mandatory.

**Evidence status (9 Oct 2026):** First real HTTP/SQLite integration passed in
Fast CI workflow `37895207678` at commit `b9904863a45696a4d79a5e160600da8c07384c04`
(26 PR-critical tests passed; 3478 intentionally deselected). That run includes
one completed tournament, fork, independent continuation and rollback injection.

**Two-tournament checkpoint (9 Oct 2026):** Fast CI workflow `37896440268`
passed at commit `8ed469bcd9369f54dbb153608430a56af453d3b8`
with **34 focused tests passing (3,478 intentionally deselected)**. Both
HTTP/SQLite Week-1 and Week-2 canonical tournaments, Save/reopen,
Branch fork and independent next-week progression executed. Follow-up
strengthened evidence assertions and documentation require their own final-head
green checks. This proves only the bounded four-player, two-tournament case,
not universal tournaments, full pre-alpha or a 50-season checkpoint.

## Explicitly unsupported

- More than two tournaments in confirmed history or more than one completed
  tournament within the same Week Transition.
- Tournament corrections and disciplinary zeros in confirmed history.
- Season Transition, Season Closing and final season rollover.
- Tournament-group/hybrid ranking remaps lacking dedicated nested provenance.
- A complete 50-season FAX pre-alpha or a realism calibration certificate.

The current `application_validation_policy_unresolved` gate remains in place.
An explicitly audited Admin validation in this fixture does **not** implement
automatic player application eligibility/deadline policy. Product conflict,
if any, must be reconciled against the current Master independently; this
acceptance changes no entry, scoring or ranking policy.
