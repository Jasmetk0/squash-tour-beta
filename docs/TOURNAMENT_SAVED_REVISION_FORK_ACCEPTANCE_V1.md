# Completed standard-tournament Saved Revision Branch fork — acceptance boundary

## Scope

A materialized Branch created from a Saved Revision after Week Transition may
inherit a fully evidenced history of **canonical standard Run-owned tournaments
without an arbitrary count limit**, across different weeks or multiple events
in a Week Transition. Each independent edition must have unique identity and
complete matching player/entry, draw, Slot, result, award, ranking and audit
history. This removes only the artificial count cap: no Season Transition,
ranking correction, disciplinary-zero version or unsupported tournament format
is implicitly enabled.

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

`tests/application/test_single_tournament_saved_revision_fork.py` now runs
four real HTTP/SQLite variants: one completed tournament, two across two
weeks, two simultaneous in Week 1, and **three tournaments** (two Week-1
events plus an independently completed Week-2 event). These use the
full-season acceptance's real Run-owned World/Calendar infrastructure,
without running a 61-week or 50-season campaign:

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
7. In the parallel Week-1 variant, adopt both Calendar events into the Run,
   generate eight players, review two disjoint four-player entrant fields
   (so Week Tournament Lock requires no selection), create both Run-owned
   canonical draws, execute both real tournament match schedules and close
   them in **one** Week Transition before Save/reopen/fork.
8. The three-tournament variant clones a distinct source Calendar/MatchPackage
   **before** Run adoption to keep the separate Week-2 event; after adoption,
   every entry, tournament Draw, rally, result and Week Transition comes from
   production Run-owned HTTP/SQLite authority. The two Week-1 fields remain
   disjoint; Week 2 uses explicitly revalidated players.
9. Verify every canonical tournament/result/point authority survives the
   target fork with identical sporting outcomes and new Branch-owned
   fingerprints, then complete the next event-free week on the fork and
   Save. Confirm the original ranking and position do not move.

`tests/infrastructure/test_week_transition_fork_audit.py` supplies short
reconstruction and forgery tests, including 3, 7 and 12 fully bound tournaments
across two historical receipts. Negative tests cover missing/foreign bindings,
duplicate editions or same-week events, forged publication weeks, and surplus
target sources. Existing event-free PR-critical regressions remain mandatory.

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

**Same-week checkpoint (9 Oct 2026):** The final #1320 Fast CI
workflow `37899754724` passed **44 focused tests** on
`ab6a82a8434c985962a199549ceed335b5d2f266`, including the genuine
two-simultaneous-tournament HTTP/SQLite fork and independent continuation.
This does not establish 50-season support, overlapping entrant arbitration,
hybrid tournaments or general multi-tournament capacity.

**Unbounded standard-history checkpoint (9 Oct 2026):** initial
Fast CI workflow `37901923845` on `cb944da3920d94a43370ce695c8444bc72e173b0`
reported **55 passed / 3,478 deselected / one unrelated deprecation warning**,
including the real three-tournament fork, rollback and independent continuation,
plus pure 3/7/12-event audit remapping. This is provisional checkpoint evidence
until the final PR head (including these documentation changes) passes all
required checks. It is **not** a universal-load, full-season or 50-season release
certificate.

## Explicitly unsupported

- A claim of arbitrary-scale performance or all possible tournament formats
  from the existing tests: 12-event source/audit rebind is a pure test, while
  the full production Run path has exercised three authentic tournaments.
- Overlapping accepted tournament entries still require separate verified
  Week Tournament Lock resolution; this acceptance intentionally uses disjoint
  four-player Week-1 fields rather than overriding that policy.
- Tournament corrections and disciplinary zeros in confirmed history.
- Season Transition, Season Closing and final season rollover.
- Tournament-group/hybrid ranking remaps lacking dedicated nested provenance.
- A complete 50-season FAX pre-alpha or a realism calibration certificate.

The current `application_validation_policy_unresolved` gate remains in place.
An explicitly audited Admin validation in this fixture does **not** implement
automatic player application eligibility/deadline policy. Product conflict,
if any, must be reconciled against the current Master independently; this
acceptance changes no entry, scoring or ranking policy.
