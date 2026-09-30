# Viewer Tournament History v1

## Purpose

The top-level Viewer tournament list is a canonical, multi-season read model built only
from the selected Viewer Branch's immutable Saved Revision. It does not use the legacy
SimulationRun event registry or live Run Package state as public authority.

## Saved authorities

Tournament identity and schedule metadata come from every applied Calendar Package stored
inside the Saved Revision Run Package component. Each Calendar Package is projected through
the existing Run-owned Calendar adapter, so later source-calendar edits cannot change Viewer
history.

Published sporting outcomes come from canonical Tournament Result authorities stored in the
same Saved Revision Ranking component. A result is considered public only when its event
identity is present in the saved Calendar history and the canonical result has crossed the
normal Ranking Save boundary.

## Public projection

`viewer_tournament_history.v1` exposes, per tournament:

- event identity and name;
- season and Season Week;
- template, category and Tour level;
- host country/city/region;
- Main/Qualification geometry, seeds, qualifier spots, Wild Cards and BYEs;
- ranking status;
- whether a canonical result has been published;
- champion and finalist IDs when that result is public.

The list is deterministic across all Calendar Packages retained by the Run Package state and
is ordered by season, Season Week and event ID.

## Fail-closed rules

Viewer history fails closed when:

- the selected Saved Revision has no Run Package state or no Calendar Package;
- Run/Branch scope differs between Saved components;
- the same event identity appears more than once in saved Calendar history;
- canonical result identity is duplicated;
- a saved canonical Tournament Result has no matching saved Calendar event.

It never fills these gaps from the legacy event registry.

## Deliberately hidden

The public list does not expose:

- Run Package fingerprints, Run-local IDs or source-package provenance;
- command IDs;
- canonical authority fingerprints;
- point/prize authority internals;
- live Working Draft Package or result state.

## Remaining compatibility surfaces

Tournament Detail still reads the legacy persisted event record for some descriptive/technical
compatibility metadata and legacy Ranking/Race publication links. The top-level Season Calendar
now reuses this canonical history projection, while Planned Event and Week Detail still retain
legacy season/event readers. Those are separate migration slices and do not make Tournament
History or the top-level Calendar legacy-backed again.
