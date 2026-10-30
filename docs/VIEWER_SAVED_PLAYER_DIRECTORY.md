# Viewer complete Saved player directory — CS/EN, source-safe read-only UX

## Scope

The top-level \`/viewer/players\` used to display only five sample players from
the Saved-Revision \`viewer_players.v1\` API response. It now browses the full
saved player population from one **verified Product Run / Viewer Branch**:
name, public ID, country, age, active/retired, public current OVR and the
source of player identity (\`initial_world\` vs \`run_prospect\`).

This PR touches no Admin, backend/domain, API clients, routes, or shared
localization modules. It does not invent rankings, simulate matches, write
Saved Revision, or infer private attributes.

## Source-of-truth and privacy

The top-level page resolves the current saved Viewer Branch from the existing
\`useViewerOfficialRunContext\`; \`official_branch_id\` is a **legacy API
field naming the Viewer Branch**, not a special privileged sporting branch.
Only after the context matches the active Product Run does it issue
\`getViewerPlayers(productRunId)\`. Its React Query key contains **both**
Product Run and Viewer Branch. While the context refetches, the old child is
not rendered; a source change remounts the child so old queries and filter
state cannot be displayed under the new identity.

The frontend requires \`viewer_players.v1\` and exact source IDs, a valid
saved season index/week and exact \`player_count\`, \`active_player_count\`
and \`retired_player_count\`. Every player must have one unique nonblank
ID, nonblank name, a three-letter country code, valid age/status/origin
and valid nullable projected numeric attributes. Malformed responses
fail closed, with a GET-only retry and no partial roster. Legitimate zero
players, filtered zero matches and failures are distinguished.

Although legacy DTO types still define \`potential_ovr\`, \`current_form\`,
\`match_sharpness\` and \`long_term_fatigue\`, the normal Saved public
projection deliberately withholds these internals. **Do not show them**
or infer replacements from overall, age or future career. \`current_ovr\`
is public in this existing DTO and may be null. A local sort by known
public OVR is **not** an Official Ranking. The legacy V1 \`week\` range
1–61 is a versioned read-model constraint, not a limit on calendar-native
W52/W61/W80 Runs.

## Read-only browsing

- Complete CS/EN text and accessibility names with source player/country
  data unchanged.
- Search full population by name, ID or country, case-insensitive.
- Filter active vs retired, initial-world vs Run prospect and actual
  country codes in the loaded population.
- Deterministic sort by name, public current OVR (unknown last) or age,
  with stable player-ID tie-breaking.
- 50 players per page with first/previous/next/last and validated numeric
  page jumps. A change of filters resets pagination; language toggles do not
  refetch data or reset filters.
- Player names link to the existing canonical Player career page using
  exact encoded player IDs; countries link to their Saved country detail.
- Display the source's saved season index and week **as metadata**, not
  the unrelated manually selected ViewerContext calendar.

## Tests and limits

Local pure validation/filter unit tests and mocked-GET React tests cover
count/identity integrity, private-field suppression, empty population,
filters, page bounds, source/missing context failures, Run/Branch switching,
late old-Run replies, and CS/EN state. These are **not** browser or
HTTP/SQLite integration acceptance. Require matching final-head Fast CI,
changed frontend tests and production TypeScript/Vite build, CodeQL and
SonarCloud. Irrelevant skipped CI jobs are not passes. Only the owner merges.
