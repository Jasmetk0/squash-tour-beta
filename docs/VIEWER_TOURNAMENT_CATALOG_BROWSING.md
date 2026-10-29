# Viewer Tournament Catalog — complete CS/EN saved tournament browser

## Purpose and scope

The existing top-level \`/viewer/tournaments\` page previously exposed only the
first eight calendar events and a count of published results. It is now a
source-verified read-only browser of the entire Saved-Revision calendar, with
a matched tournament result publication index.

No backend, API client, domain scoring, Admin, shared i18n or routing changes.
Only the existing GET operations are used:

1. \`getViewerOfficialRunContext(productRunId)\` resolves the current saved
   Viewer Branch. The legacy context field \`official_branch_id\` is **technical
   source identity**, not a privileged simulation branch.
2. \`getViewerRunCalendar(productRunId)\` supplies scheduled event evidence.
3. \`getViewerTournamentHistory(productRunId)\` supplies publication status and
   champion IDs from saved Canonical Tournament Results.

The calendar and history queries are independently keyed by
\`[productRunId, viewerBranchId]\`; their joined child remounts whenever either
source changes. During a fresh context GET, previous source data is hidden.
All retries are GET only, not a Save, simulation or repair.

## Source-integrity boundary

The UI rejects an unknown schema version; foreign Run/Branch; mismatched
\`season_count\`, \`event_count\`, \`tournament_count\` or
\`published_result_count\`; duplicated season or event IDs; missing calendar
events from history; orphan result events; and mismatched identity/season/week,
name, category, tour level, template or host-country information.
A missing or failed source hides the joined catalog: the page does **not**
combine partial data from different branches or infer sporting outcomes.

Both existing legacy projection DTOs use 1–61 season weeks; this validation
applies to **these versioned V1 readers only**. It is not a constraint on
the separately supported native W52/W61/W80 calendar configurations.
A future native-aware schema needs a distinct adapter, not guessed calendar
mapping. No past tournament is presumed to have a result merely because its
calendar status is \`completed\`.

## Usability

- Actual tournaments from all available saved seasons, with newest season first
  when filtering across seasons. No eight-item cap.
- Search by published event name/ID and saved host country/city, case-insensitive.
- Filter by saved season and **actual** published/not-published result status.
- Original saved event name, category, calendar status, location and week.
  Calendar status is translated CS/EN *as a label*, without altering source data.
- Link to existing canonical event detail using event ID. Published champion
  is shown only when supplied by the saved result authority, linking to the
  current player career route (not a historical reconstructed player profile).
- Local pagination (25 per page) with first/previous/next/last, bounded numeric
  page jump, accessible labels and distinct zero-catalog vs no-match messages.
- Filters/page are reset on source switch; language switch only changes UI
  copy and preserves the loaded source and filter state.

**Historical weeks:** A cross-season \`/viewer/runs/:runId/weeks/:week\` link
would not encode which season a past week belongs to, so the catalog labels
the stored week but links to the exact event ID instead. No artificial
historic week navigation is introduced.

## Test evidence and limitations

Colocated pure Vitest tests and mocked-GET React component tests cover
source tampering/mismatch, true zero state, complete search and filtering,
pagination bounds, published champions, source switching, late old-source
replies, context retry, safe encoded links and CS/EN stability.

These tests do **not** prove real HTTP/SQLite or a Chromium browser session.
Require final-head Fast CI, frontend critical baseline, new changed tests,
TypeScript/Vite build, CodeQL and SonarCloud. Appropriate deeper pre-alpha
release gates remain separate. Skipped unrelated jobs are not successful
integration. The repository owner alone chooses the merge.
