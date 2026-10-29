# Saved Player Career and Rally Navigation — current Saved HEAD only

## Scope and product boundary

The Admin player profile's **Career & results** tab lists only completed canonical
tournament match results for the selected Run / Branch / **current Saved HEAD**.
It is not a historical-revision reader, a lifetime records authority, a source of
new H2H/milestones, or a simulation. A W/O result is visibly distinguished from
a played match and does not contribute to played wins/losses. BYEs are excluded.
The backend's verified career totals, selected-season totals, and season availability
are never recalculated from the twenty rows of the loaded page.

No backend, saved object, sporting authority, API contract, central i18n, or
mutating endpoint is changed. GETs are read-only; UI filters, locale, and replay
position never invoke simulation, Save, or mutation.

## Career URL and local controls

* `careerSeason` is a canonical zero-based season index, 0–49. Missing means all.
* `careerPage` is a canonical zero-based 20-result page, 0–10000.
  Missing means first. The visible jump uses **one-based** numbers and checks the
  exact server `total_results`. First/previous/next/last never exceed it.
* `careerQ` (up to 160 characters), `careerOutcome` (all/win/loss), and
  `careerCompletion` (all/played/walkover) apply to **only the loaded page**.
  The UI states this explicitly. Searches check event name/ID, match ID, opponent
  ID, verified opponent display name *from the same Saved HEAD*, and scoreline.
  A missing/foreign/invalid identity lookup falls back to the opponent ID.
* Repeated URL keys are rejected, even if the first value is valid. Invalid URL parameters block the read and offer a safe reset; a valid numeric
  page beyond `total_results` offers the first and actual last page. Empty
  results never render `Page 1/0`. An in-range empty server page or
  duplicate event/match identity is rejected rather than misrepresented as an
  empty career or local filter. An empty local filter differs from no career,
  an unavailable identity, an HTTP failure, or a mismatched response.
* Match links retain valid season, page, query and local filters to restore
  them after the detail view. They also carry `replayBranch` and `replayHead`.

## Replay URL, source and neighboring-page safety

The player detail route identifies Run / player / event / match. The current
selected Admin Branch and its current Saved HEAD are required. The optional
`rally` URL parameter is **one-based**, canonical, and bounded 1–100000.
Omitted `rally` means the first rally. Every non-default rally bookmark
requires both `replayBranch` and `replayHead` to match the currently selected
Branch HEAD; an ordinary unscoped legacy route is still allowed to open the
first rally of the current source. New rally navigation writes both tokens.

Changing the Branch or Saved HEAD makes an old scoped link fail closed and offers
an explicit "Open current Saved HEAD" action. A source-changing render remounts
the local replay state before any new request can reuse a page 25/50 cursor.
The API endpoint **always reads the current Saved HEAD** and has no supported
parameter to read an arbitrary historic revision. A `replayHead` URL token is a
client-side mismatch fence, **not** permission to retrieve a historical HEAD.

Replay reads twenty-five stored frames per request. Prev/next/first/last,
validated numeric jump, refresh and the disclosure list of actual frames all
share the same validated URL position and exact source. The active frame is
marked `aria-current=step`. Existing selected frames, scores and players are
displayed only from actual stored responses, never inferred. Valid real
adjacent pages in the same archive are checked in both directions for scope,
total, complete immutable match metadata, rally index and score/game/set
continuity. Opponent names require the verified exact Saved HEAD and identity
source; otherwise raw IDs remain visible. An out-of-range empty page is
**not** considered a neighbor; after returning to the first frame the actual
last page remains accessible (regression following PR #1651).

A W/O may have no rally archive: result remains visible but no frames are
manufactured. Errors, unsupported time context, invalid URLs, foreign HEAD,
missing identity and unavailable replay are distinct.

## Verification

* Component tests under `web/src/pages/SavedPlayerMatchesPanel.test.tsx`,
  `SavedPlayerMatchDetailPage.test.tsx` and `savedPlayerCareerNavigation.test.ts`
  use **mocked API responses** and cannot establish production persistence.
  Their cases include malformed URLs, missing/empty pages, filters, return
  context, source changes, delayed replies, frame boundaries, malformed rally,
  out-of-range bookmark regression, duplicate URL tokens, foreign identities,
  cross-page match/set contradictions, CS/EN, and absent replay.
* `scripts/saved_player_replay_browser_checks.py` runs through real Chromium,
  production HTTP and SQLite under the existing Saved player replay acceptance.
  It retains the actual canonical match, Saved HEAD, fork, score, archive,
  publication and restart proofs. It additionally exercises URL replay refresh,
  page bounds, local filtering/return, first/last, direct frame selection,
  numeric jump, empty bookmark → first → last, CS/EN, invalid/duplicated
  career/replay URL recovery, and old-source rejection on a distinct fork.
  It explicitly records browser network requests during read-only UI activity
  and asserts there were **no POST/PUT/PATCH/DELETE writes** after the
  separately authorized tournament Save. No fixture, deadline, or original negative assertion is
  weakened. Its execution still needs a real hosted acceptance run.
* The separate full pre-alpha release gates remain mandatory; neither mocked
  UI tests nor this narrow real-browser flow certify a full release.
