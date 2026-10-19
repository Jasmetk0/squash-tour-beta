# Native sporting checkpoint v11

## Change and ownership

The prior Signed birthday preflight could propose complete sporting stages but
could not persist them as a population checkpoint. Version
`calendar_sporting_checkpoint.v11` now composes the **unchanged v1–v10 root**
with a consecutive native-week ledger. Existing models, historical serializers
and fingerprints are unchanged. Each native entry owns:

- completed/developed/recovered/target 57-attribute populations and injected seed;
- the exact Saved-source birthday event and predecessor checkpoint fingerprint;
- the matching target lifecycle, Health and complete Health-history fingerprints.

The first entry must contain a real birthday. Later natural weeks may have no
births and develop previously admitted players through the same W-aware kernel.
The ledger supports a season boundary and strictly extended target horizon while
retaining frozen historical clocks. v11 never guesses post-birth played matches:
only the historical root supplies actual match counts; later natural entries
require zero counts until a genuine post-birth match ledger is integrated.

## Actual persistence and replay

The production checkpoint decoder, SQLite load/replace/restore and Saved component
loader recognize v11. The Saved loader first authenticates the old root against
its real InitialWorld and played MatchEngine evidence. It then loads the full
Saved lifecycle, Health, prospect source and historically effective Tour policy.
Each native event and old-player development/recovery is rebuilt; all target
profiles and cross-component fingerprints must match. Recomputing an outer hash
does not authorize changed development, counts, Health, source or policy.

The real read-only Admin sporting preflight now prepares and verifies this exact
checkpoint. `durable_sporting` exposes its schema, fingerprint and source/lifecycle/
Health bindings. The combined transition proof explicitly advances to
`native_tour_prepared_birth_transition.v2`, binding the checkpoint as well as
the full Health history. HTTP remains compact; it does not ship every record.

## Explicit remaining boundary

This is a durable, replayable **component**, not an atomic live Tour birth writer.
The existing Tour verifier explicitly refuses v11 until confirmed Tour transition
receipts and all associated writers are integrated. The preflight remains read
only; it does not Save, create Entry, rank a newborn or publish public events.
Whole Signed Revision activation must not be inferred from component acceptance.

Current native lifecycle replay requires one unchanged Signed prospect-source
snapshot. Future annual source additions need immutable historical source epochs
before live multi-year intake can change that source without rewriting earlier
birth proofs. Protected branch re-signing, post-birth matches and versioned v3
Health corrections also remain separate integration work.

## Evidence

Pure tests cover W52/O1, W52/O35, W61/O37, W80/O15 and W80/O80; season rollover;
strict extension; later newborn development; unchanged root bytes; schema and
adversarial replay rejection. These pure fixtures do not prove root World history.

The HTTP/SQLite matrix uses genuine production-created World/player snapshots,
real opening matches and Signed source Save without World/MatchEngine mocks.
It independently reconstructs the same proposed checkpoint, verifies its Saved
component, rejects rehashed corruption, persists it to a disposable SQLite
component database, tests late rollback, closes/reopens the engine and restores
both old and new components. The W80 case extends three to five seasons. The
candidate Tour is not installed or presented as an authentic executed Revision;
the test separately asserts that the live Tour receipt guard still blocks it.
