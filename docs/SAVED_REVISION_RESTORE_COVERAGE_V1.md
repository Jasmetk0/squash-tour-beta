# Saved Revision restore coverage registry v1

Saved Revision restore is a historical state replacement boundary. It must never
silently combine the selected historical revision with live Run/Branch state created
after that revision.

## Central coverage registry

`saved_revision_restore_coverage.py` is the single restore-preflight registry for
authoritative row families captured by Saved Revision components. Each entry binds:

- the Saved Revision component key;
- a human-readable recovery label;
- every live Run/Branch table whose rows are owned by that component.

Before restore mutation begins, the repository checks the current saved head. If live
rows exist for a registered family but that component is absent from the current Saved
Revision, restore fails closed.

The registry currently covers ranking, InitialWorld, lifecycle, entry chronology,
application validation/submission, definitive WC assignments, Tour-entry triggers,
sporting history and authoritative simulation/tournament state.

The ranking family explicitly includes Season Closing Ranking history. The simulation
family explicitly includes WC authority, Draw Process authority and append-only Draw
revision history.

## Transient restore blockers

Some Run/Branch state is intentionally not Saved Revision content. It must not be
silently carried through a historical restore.

The first registered transient blocker is the standalone-match authoring workspace.
The minimum Master §31.3 standalone flow intentionally persists only the completed
canonical match, not a partially authored workspace. Restore therefore requires that
workspace to be finished/discarded first.

A transient blocker is not converted into Saved Revision content by this registry. It
only prevents an unsafe restore.

## Embedded-only components

`season_closure` is valid Saved Revision content but has no independent live table.
Its marker is revision-bound evidence embedded directly in the revision. Restore
validates the historical component and rebinds the marker to the newly created restore
revision through the dedicated season-closure restore path.

## Maintenance rule

When a new canonical Run/Branch persistence table is introduced, its recovery
ownership must be explicit:

1. captured/restored by an existing Saved Revision component and added to its registry
   family;
2. introduced with a new Saved Revision component and registered here; or
3. intentionally transient and added to the transient blocker registry.

Leaving a new live table outside all three categories is a recovery-integrity gap.
This rule is technical persistence ownership only and must not invent product rules.
