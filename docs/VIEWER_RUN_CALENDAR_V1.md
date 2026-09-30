# Viewer Run Calendar v1

## Purpose

Run-scoped Viewer Tournament list/detail metadata now comes from the selected Viewer
Branch's immutable Saved Revision Calendar Package state rather than the legacy
SimulationRun event registry.

This is an authority migration only. It preserves the tournament schedule visibility
already exposed by the existing Viewer and does not define or infer the still-separate
`announcement_week` / public `Public Stage` policy.

## Authority and publication boundary

The endpoint loads `run_package_state` from the selected Viewer Branch's Saved Revision
and projects every applied Calendar Package with the canonical
`CalendarPackageRunAdapter`.

Live Run Package changes are not public. Applying or editing a Calendar Package in the
Working Draft does not change Viewer output until normal explicit Save creates the next
immutable Saved Revision.

Canonical completed-result summaries are joined only from the same Saved Revision's
Ranking component and its `OwnedTournamentRankingSource.canonical_result` values.

## Public projection

`viewer_run_calendar.v1` exposes sporting/public catalog fields only:

- Product Run and Viewer Branch identity;
- event identity, season/week and calendar position;
- template, event name, category and tour;
- host country/city and region;
- Main/Qualification capacities, qualifier spots, Wild Card slots and BYEs;
- ranking/source status;
- optional canonical champion/finalist/match-count summary when the saved canonical
  Tournament Result exists.

The projection excludes Run-local IDs, Package/source fingerprints, Package provenance,
command IDs, ranking/result authority fingerprints and Admin review metadata.

## Validation

The read fails closed when:

- the Viewer Saved Revision has no Run Package state or no Calendar Package;
- Saved Package scope differs from the Viewer Branch;
- a Calendar Package cannot be reconstructed through the canonical adapter;
- an event identity is duplicated across applied Saved Calendar Packages;
- a season is outside the fixed 2000/01–2049/50 Run timeline;
- Saved Ranking scope is incoherent or the same event has ambiguous canonical result
  authority.

## Current web scope

The run-scoped Viewer **Tournaments list** and **Tournament Detail metadata** consume this
projection.

Still separate migrations:

- run-scoped Calendar/Week pages still have legacy progress and publication joins;
- ranking/race source-publication links on Tournament Detail still use their historical
  compatibility readers;
- top-level `/viewer/tour/tournaments` remains compatibility-backed;
- Race and Finals remain separate Viewer authority migrations;
- `announcement_week` / derived public `Public Stage` is not implemented by this
  change and must not be inferred from Calendar Package presence.
