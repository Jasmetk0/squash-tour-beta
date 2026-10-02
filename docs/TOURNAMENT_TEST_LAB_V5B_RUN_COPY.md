# Tournament Test Lab V5B — verified Saved Revision Tournament copy

## Scope

This slice adds one explicit Run → Lab boundary: copy a historical Tournament Edition from an immutable Saved Revision into a new isolated Tournament Lab Session.

The copy is read-only with respect to Product Run/Branch history. No live link is retained and no source state is mutated.

## Source validation

The copy resolves the requested Saved Revision through the canonical revision-history service and validates its saved simulation-slot tournament component with the restore-grade loader.

A copy requires:

- the latest saved Tournament Entry Field for the event,
- exactly one saved Tournament Format authority bound to that field,
- a saved Draw Input for knockout formats, or a saved Topology authority for group-based formats,
- a validated Saved Revision Initial World,
- a validated saved player sporting head.

Every copied player is projected through the same CanonicalMatchInputProjectionPolicy used by authoritative Match simulation. Players that cannot be reconstructed from the saved Initial World + sporting state fail closed.

## Frozen copy provenance

The Lab scenario uses source_kind `run_snapshot_copy` and freezes:

- Product Run, Branch, Saved Revision and event identities,
- Saved Revision content hash,
- Entry Field / Format / Draw Input / Topology fingerprints,
- sporting-state fingerprint and week ordinal,
- the canonical projection fingerprint of every copied participant.

The provenance object has its own fingerprint and that fingerprint is stored as the Scenario source fingerprint.

## Supported formats

- classic knockout, including canonical Qualification geometry when represented directly by the saved Draw Input,
- groups,
- groups → knockout.

Group geometry, seed placements, BO3/BO5, topology seed, advancement and crossings are copied from the frozen Format/Topology authorities rather than recomputed from current defaults.

## Deliberate fail-closed boundary

Historical WC, Lucky Loser and replacement/repair evidence is not flattened into a simpler Lab field. Those events are rejected until the dedicated Tournament Lab replacement/ranking-consequence slices exist.

Prospect players without a reconstructable historical Initial World profile are also rejected by this slice rather than receiving invented profile data.

## Next

Add the separate Lab → Run compatibility-preview draft bridge. After that, continue with withdrawals/WC/LL/replacements and ranking consequences through shared authorities.