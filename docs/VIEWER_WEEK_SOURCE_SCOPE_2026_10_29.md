# Viewer Week route and source-bound publication guard — 29 October 2026

Scope: read-only canonical Viewer Calendar, Planned Event and Week Detail in `web/src/pages/ViewerRunCalendarPage.tsx`, with focused Vitest regressions.

## Behavior

- Week route coordinates accept any **positive safe integer** rather than assuming a universal 61-week season. The Run's Saved Calendar determines its real events; a week without public content has an empty state. Malformed, zero, negative, fractional and overflow route values never start the canonical readers.
- The selected Product Run, together with the selected Viewer Branch when supplied by the route, bounds each calendar/history/ranking/Finals source. In legacy/test routes without an explicit Viewer Branch, the independently checked Saved Calendar establishes the branch identity used to join public publications.
- Foreign Run/Branch responses are withheld and reported rather than displayed as this Run. A tournament result also must match its Saved Calendar event's **event ID, season and week** before it can be shown as published.
- Query keys include Viewer Branch identity, avoiding reusing an old branch's cached public data after a branch change.
- Week navigation from the season timeline and planned event preserves the exact Saved season in an encoded `?season=` URL. When no active season is known and W occurs in multiple Saved seasons, the Viewer offers exact season links instead of combining historical events and ranking/Finals publications. A nonexistent explicit season fails closed; unknown/malformed calendar years are not inferred from a numeric prefix.
- Within an otherwise matching Finals Race history response, a publication with a foreign Run or Branch identity is rejected individually. Legacy published ranking indices are interpreted against their original 2000-based season system only when the displayed calendar year is resolved.

No API/backend/SQLite/command/write/revision or sporting logic is changed, and empty calendars do not invent sporting events.

## Test evidence and limitations

Focused mocked-HTTP Vitest cases cover week 80, invalid/overflow week coordinates, foreign Run calendar, foreign Viewer Branch tournament/ranking sources, a reused event ID at a different week, season-specific Week links, overlapping season/week entries, invalid season query, and a foreign nested Finals Race publication. These are component contracts, not genuine backend, persistence or browser integration.

The connected GitHub environment did not provide a local runnable repo; **do not present this PR as ready for merge** without reviewing actual latest-head CI/frontend tests and applicable acceptance gates. This is a Draft PR for owner review and merge decision.

**Important authority limit:** the existing `viewer_run_calendar.v1` backend schema still constrains its historical calendar event weeks to 1–61. Accepting W80 in the Viewer route does **not** upgrade that backend reader or prove native W80 calendar integration. The W80 UI case is mocked only; the broader Run calendar migration remains separate.
