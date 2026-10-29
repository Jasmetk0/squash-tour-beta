# Viewer Week route and source-bound publication guard — 29 October 2026

Scope: read-only canonical Viewer Calendar, Planned Event and Week Detail in `web/src/pages/ViewerRunCalendarPage.tsx`, with focused Vitest regressions.

## Behavior

- Week route coordinates accept any **positive safe integer** rather than assuming a universal 61-week season. The Run's Saved Calendar determines its real events; a week without public content has an empty state. Malformed, zero, negative, fractional and overflow route values never start the canonical readers.
- The selected Product Run, together with the selected Viewer Branch when supplied by the route, bounds each calendar/history/ranking/Finals source. In legacy/test routes without an explicit Viewer Branch, the independently checked Saved Calendar establishes the branch identity used to join public publications.
- Foreign Run/Branch responses are withheld and reported rather than displayed as this Run. A tournament result also must match its Saved Calendar event's **event ID, season and week** before it can be shown as published.
- Query keys include Viewer Branch identity, avoiding reusing an old branch's cached public data after a branch change.

No API/backend/SQLite/command/write/revision or sporting logic is changed, and empty calendars do not invent sporting events.

## Test evidence and limitations

Focused mocked-HTTP Vitest cases cover week 80, invalid/overflow week coordinates, foreign Run calendar, foreign Viewer Branch tournament/ranking sources, and reused event ID at a different week. These are component contracts, not genuine backend, persistence or browser integration.

The connected GitHub environment did not provide a local runnable repo; **do not present this PR as ready for merge** without reviewing actual latest-head CI/frontend tests and applicable acceptance gates. This is a Draft PR for owner review and merge decision.
