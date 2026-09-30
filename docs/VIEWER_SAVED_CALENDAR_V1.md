# Viewer Saved Calendar v1

## Purpose

Viewer calendar routes read schedule data from the selected Viewer Branch's immutable
Saved Revision, not from the legacy SimulationRun season/event registry and not from
the live Working Draft.

The Saved Revision already captures the complete Run Package state. Viewer loads that
saved package state and projects applied Calendar packages through the same canonical
Calendar Package adapter used by authoritative simulation.

## Publication boundary

A Calendar package applied to a Working Draft is not public. It becomes visible only
after an explicit Save creates the Viewer Branch Saved Revision.

Later unsaved Run Package edits do not affect Viewer output.

The source Calendar library is never reloaded at Viewer read time.

## Public projection

`viewer_run_calendar.v1` exposes:

- Product Run and selected Viewer Branch identity;
- deterministic saved seasons;
- deterministic events ordered by Season Week and event ID;
- event identity, season/week and optional calendar-year/year-week;
- event name, template, category and tour level;
- host country/city and region;
- duration/start/end Season Week;
- public event status;
- draw geometry: Main/Q sizes, seed count, qualifier spots, WC slots and BYEs;
- prestige.

Multiple applied Calendar packages are allowed when they describe distinct seasons.
Duplicate public season identities or duplicate event IDs across seasons fail closed.

## Deliberately hidden

Viewer Calendar does not expose:

- package IDs or source versions;
- package/source/content fingerprints;
- package provenance or Run-local entity IDs;
- source-template/calendar fingerprints;
- ranking point tables/distribution internals;
- prize-money tables/configuration;
- live Working Draft changes.

## Viewer integration

The main Season Calendar, Planned Event schedule metadata, Week schedule and tournament
list consume this Saved Calendar projection.

Canonical completed Tournament Result history remains a separate Saved Ranking
projection and is joined by stable event ID. Ranking/Race publication lists on Week
Detail still use their existing read-only compatibility sources until their dedicated
Viewer migration is completed.
