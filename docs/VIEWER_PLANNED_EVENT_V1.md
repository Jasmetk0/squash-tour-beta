# Viewer Planned Event v1

## Purpose

Viewer Planned Event detail resolves one event directly from the selected Viewer Branch's
canonical Saved-Revision Tournament History. It no longer reads the legacy SimulationRun
season plan or persisted event registry.

## Authority

The event must exist in `viewer_tournament_history.v1`, whose schedule identity comes
from saved Run Package Calendar authority and whose published result summary comes from the
saved Ranking component.

Event identity is unique across the canonical saved Calendar history; missing event IDs fail
closed rather than falling back to a legacy event record.

## Public presentation

The page exposes:

- event identity and name;
- season and Season Week;
- Tour/category/template;
- host/region;
- Main and Qualification sizes;
- seeds, qualifier spots, Wild Cards and BYEs;
- ranking status;
- canonical result-publication state, champion and finalist;
- links back to Season Calendar, Week Detail and Tournament Detail.

The page deliberately does not recreate legacy `next_event_index`, current/upcoming status,
persisted-event sequence or technical event payloads.

## Remaining compatibility

Week Detail remains a separate compatibility-heavy route because it still combines legacy
season/event state and legacy Ranking/Race snapshot readers. Tournament Detail also retains
collapsed legacy technical metadata even though its sporting Entry/WC/Draw/Result sections
are canonical.
