# Viewer Canonical Tournament and Week Details v1

## Purpose

Run-scoped Tournament Detail and Week Detail now use Product Run-scoped canonical Saved-Revision/publication authorities only.

## Tournament Detail

Canonical context comes from:

- Saved Calendar;
- Tournament History;
- Official Ranking History;
- Finals Race History;
- Tournament Entry Field;
- Definitive Wild Cards;
- Tournament Draw;
- Tournament Result.

Legacy SimulationRun readers are not used for event/run context or Ranking/Race snapshot lookup.

Tournament publication context is expressed by canonical week/season publications. No legacy snapshot identity is inferred from event identity.

## Week Detail

Week Detail combines:

- Saved Calendar events;
- Tournament History result publications;
- Official Ranking publications;
- Finals Race publications whose cutoff season/week matches the selected Viewer week.

Legacy Race snapshot sequences are not used.

## Identity boundary

Official Ranking uses canonical week ordinal identity.

Finals Race uses canonical seasonal publication identity.

Legacy Race \`snapshot_sequence\` remains isolated to its dedicated compatibility detail route and is not mapped into Tournament/Week detail.
