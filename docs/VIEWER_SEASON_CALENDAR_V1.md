# Viewer Season Calendar v1

## Purpose

The top-level Viewer Season Calendar is a canonical read-only projection of the selected
Viewer Branch's immutable Saved Revision. It reuses `viewer_tournament_history.v1`
instead of reading the legacy SimulationRun season plan or event registry.

## Authority

The schedule comes from applied Calendar Packages stored in the Saved Revision Run Package
component. Result publication, champion and other already-public tournament outcome fields
come from the canonical Saved Ranking component joined by Tournament History.

The page never reads live Run Package state and never uses `getRun()` or `listEvents()`
as its schedule authority.

## Public presentation

The Calendar page shows:

- every saved season represented by Calendar Packages;
- canonical event name and ID;
- Season Week;
- Tour/category/template;
- host;
- deterministic position in the saved multi-season timeline;
- canonical result-publication state and champion when published;
- links to Planned Event, Week Detail and Tournament Detail routes.

It does not attempt to infer a new current/upcoming status from legacy `next_event_index`.
That status remains a separate migration concern until Planned Event/Week views move to
canonical Position/time authority.

## Publication boundary

A Calendar Package applied only in the live Working Draft remains invisible until the
normal Working Draft Save creates a new Saved Revision. Tournament result changes remain
invisible until their Ranking Save boundary.

## Remaining compatibility

The following routes remain separate follow-up work:

- Planned Event detail (`/calendar/:eventId`);
- Week Detail (`/weeks/:week`);
- their legacy Ranking/Race snapshot links and persisted-event compatibility metadata.

The canonical top-level Calendar does not promote those compatibility readers to authority.
