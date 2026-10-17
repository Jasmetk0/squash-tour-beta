# Calendar-native four-player opening-week knockout (v84)

## Supported operation

This slice extends the proven #1522 calendar MatchEngine operation with one real
main-only BO5 bracket for **exactly four distinct Saved InitialWorld v2 players**
in **Season 1 Week 1**. The two semifinals resolve from an identical frozen
pre-slot roster, with distinct deterministic seed streams. The actual
semifinal winners feed the final. Every played MatchEngine result contains
authoritative rally, timeline and stamina logs, frozen match inputs, explicit
log anchors and Run-owned W/offset/year/horizon provenance. No legacy W61
ordinal conversion is performed; W52 and W80 are supported.

The operation is deliberately bounded: one opening-week sporting operation
per Run/Branch, either a v1 exhibition or a v1 opening knockout. A second
operation fails closed; there is no generic seeding, qualification, byes,
separate match scheduling, substitutions or abandoned-match resolution.
There is no official Tournament Edition/Category publication, configurable
point award, official ranking, future Week/Season Transition, persistent
sporting/Health effects or full 57-attribute population projection. The
active legacy guards are unchanged.

## Persistence and replay

The calendar sporting **Saved component key remains
`calendar_standalone_match`** for compatibility with the existing atomic
Save, immutable history and restore coverage. Its `state.schema_version`
discriminates old `calendar_standalone_match.v1` and new
`calendar_opening_knockout.v1`; both retain their exact signed bytes.
The underlying row table likewise remains unchanged; typed row decoding
fails closed on unknown schema. This is deliberately a migration bridge,
not a silent conversion of an old exhibition into a tournament.

- `GET /admin/runs/{run}/branches/{branch}/authoritative-simulation/calendar-opening-knockout` inspects the exact saved population, current clock and optional bracket.
- `POST .../calendar-opening-knockout/simulate` atomically plays all three real MatchEngine matches under `BEGIN IMMEDIATE` with exact command receipt and retry.
- `GET .../calendar-opening-knockout/{match_id}/replay` replays all three frozen inputs/seeds and compares the complete logs.
- `GET .../calendar-opening-knockout/save/preview` and `POST .../calendar-opening-knockout/save` reuse production fingerprint/draft/immutable revision Save checks.
- Historical Saved revisions are never re-signed. A same-Branch Saved restore reinstates matching row evidence; forking match-containing revisions remains blocked until valid cross-Branch provenance remapping is implemented.

CS/EN controls in Run Simulation let Admin choose four players, review the
draw, confirm execution, inspect all results and champion, verify three
replays, and explicitly preview/confirm immutable Save. The mutually exclusive
selector avoids mounting conflicting exhibition/knockout UIs together.

## Acceptance and remaining gates

`tests/api/test_calendar_opening_knockout_flow.py` checks both W52/W80
using real FastAPI/SQLite, normal population adoption and Saved writer,
winner-fed final, deterministic replay, command conflict, manual immutable
Save and cold restart; negative checks cover mismatched Saved sources,
non-roster participants, duplicate entrants and mixed exhibition commands.
The release-level populated season and actual tournament points and
transition are **not** supplied by this bounded PR. A dedicated Chromium
browser pass is a separate acceptance requirement, not established by a
backend test alone.
