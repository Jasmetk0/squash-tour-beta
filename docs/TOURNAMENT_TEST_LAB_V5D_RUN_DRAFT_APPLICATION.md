# Tournament Test Lab V5D — reviewed Lab → Run draft application

## Scope

V5D completes the explicit reviewed bridge from an isolated Tournament Lab Session into a Product Run Working Draft.

The bridge deliberately stages a **Run-owned tournament draft proposal**. It does not create or replace Tournament Ranking, Entry, Wild Card, Draw, Result, Point Award, prize-money or ranking authorities. Those production authorities keep their existing provenance and adoption rules.

## Review → apply contract

Admin first builds the V5C compatibility preview. Apply then requires the exact reviewed:

- Tournament Lab Session fingerprint,
- target Product Run / Branch / event,
- target Saved Head revision,
- target Working Draft version,
- preview fingerprint,
- candidate fingerprint,
- unique command ID.

Apply re-reads and recomputes all of that under a database write lock. Any drift fails closed before the Working Draft is changed.

## Atomicity and retry

Application uses the same safety shape as other reviewed Run mutations:

- `BEGIN IMMEDIATE` write serialization,
- exact Saved Head + Working Draft CAS,
- target Working Draft must start clean,
- idempotent command receipt,
- command-ID reuse with a different request is rejected,
- proposal persistence and Working Draft mutation are one transaction,
- stale preview/candidate evidence leaves no partial proposal behind.

An exact retry returns the original proposal evidence and does not append a second Working Draft change.

## Run-owned proposal state

Each target event has one current reviewed proposal with monotonically increasing proposal version. Its fingerprint binds:

- Run / Branch / event identity,
- source Lab Session identity and fingerprint,
- source Scenario fingerprint,
- reviewed preview fingerprint,
- exact candidate payload and candidate fingerprint.

Multiple event proposals are captured as one deterministic Run-owned component.

## Saved Revision / restore / fork

The proposal component is included in ordinary Saved Revision capture and Season Transition revision capture.

The normal Working Draft Save path recognizes the reviewed proposal change and saves it as revision kind `tournament_lab_run_draft`. Save requires the exact proposal-component fingerprint and exact Working Draft evidence.

Restore treats the proposal table as a covered authoritative component and restores the exact target snapshot.

Materialized Branch forks remap proposal ownership to the new Branch, recompute target-owned proposal/state fingerprints and preserve the reviewed Lab/candidate provenance.

## UI

Tournament Test Lab exposes a reviewed target workflow:

1. enter Product Run ID, Branch ID and event ID,
2. preview compatibility,
3. inspect Saved Head, Working Draft version, blockers and fingerprints,
4. explicitly Apply to the target Working Draft,
5. use the normal Run Save workflow to create the immutable Saved Revision.

Lab Inspect/Run execution remains isolated and never mutates a Run. Only the separate explicit Apply action stages a proposal.

## Remaining boundary

V5D is not an authority-adoption shortcut. A later production slice may consume a saved proposal only through explicit normal tournament-authority review/adoption rules.

Tournament Lab still does not model every withdrawal/WC/LL/replacement/ranking-consequence case. Those remain shared-authority work where required by the copied-FAX acceptance flow.

After V5D, the highest-value pre-alpha work moves back to the mandatory copied-FAX full-season + next-season acceptance and closes only Lab gaps that block that run.
