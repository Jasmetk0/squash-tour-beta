# Saved ATP squash sporting profiles V1

## Completed results and calendar ranking inputs

`assemble_knockout_result_facts` is shared clock-free sporting assembly. The
existing legacy result wrapper retains its schema/date representation and JSON
bytes. `build_knockout_player_point_awards` shares existing exact Q+Main and
BYE/W/O unlock semantics; the legacy award wrapper retains its serialized shape.

`complete_scheduled_knockout_result` validates the full accepted schedule/feeder
history and returns a separate `scheduled_knockout_result.v1` projection using
the real Run clock. It snapshots the plan before calculating. It has no result
store or publication authority. `scheduled_knockout_ranking_results` derives
one `CalendarRankingResult` per player, with Q/Main points counted once, the
following Run week's publication eligibility and W-week validity. All point
values come from the copied profile, never current server defaults. Distinct
deep-Q values cannot be silently collapsed into an incompatible shared stage.

This path never converts a W52 result through legacy `RankingWeek`. Its tests
exercise 43 actual matches, independent points for all 44 players, zero-point
stages, duplicate rejection, no future publication and expiry at 52 weeks. A
generic explicitly proposed W80/season55 schedule also works; that is not an
automatic Earth-to-W80 calendar import.

A completed terminal-horizon result remains valid, but this publication adapter
requires a following week. An explicit compatible horizon extension can supply
it without changing the original result/clock/fingerprint. Rebase or shrink is
rejected. Native terminal closing remains a separate consumer; no phantom week
or implicit extension is created. These are pure candidate calculations, not
signed Official publication, Week Transition, result Save or Viewer release.

A separate committed-baseline comparison confirmed byte-identical legacy result
and award JSON/fingerprints for the same 43-match facts. Existing historical
point, BYE and feeder regressions remain separate from new calendar acceptance.

## Physical Saved source preparation

`SavedATPScheduledFeederService.prepare` authenticates the current Saved Run
clock, full Saved envelope, copied profile/Calendar bindings and the canonical
Draw Input/Draw snapshot. Live tables and subsequently changed server files are
not substitutes. The exact profile, Draw, full field and proposed schedule must
agree. A source Draw revision/replacement or implicitly inherited foreign owner
is rejected until its own consumer is supported.

`POST .../calendar-tour/atp-source-editions/{occurrence_id}/feeder-preview`
uses the same Saved-head/profile/schedule request as schedule preview. It reports
source hash, plan/Draw/schedule fingerprints, executable-node count and initial
Qualification dependencies. It is read-only; scope is `scheduled_feeder_only`,
with sporting execution and real Q-date verification explicitly false.

The source Package must be saved, then canonical Draw Input/Draw saved using the
existing explicit simulation Save flow. Merely staging a live Draw is insufficient.
`reload` resolves the original reachable Saved revision after later Saves. It
requires both selected Run/Branch and the consuming owner's expected reviewed
plan fingerprint, then rebuilds and compares the full plan. The round schedule
is an explicit proposal outside the source Package; the eventual native owner
must persist its confirmed binding. The physical source alone cannot approve it.

The HTTP/SQLite test stages disposable eligible Entry/Draw subsystem inputs,
performs real manual Saves, authenticates 43 nodes/eight initial Q matches, adds
another Saved Draw, ignores a corrupt live Draw, and cold-reopens the original
plan. Wrong owner, stale head, altered reviewed binding, unreachable revision,
wrong source hash and physical Saved-payload corruption are rejected. Fixture
ranking/Entry authorities do not certify native W52 eligibility or publication.
Actual slot ownership, Health, Week Transition, result Save and Official ranking
integration remain the next boundary; no public knockout simulation is enabled.

## Scheduled match consumption

`ScheduledKnockoutFeederPlan` is a separate v1 source adapter for a copied ATP
knockout profile, initial Draw Input/Draw and Run schedule. It reconstructs the
Draw from its committed input, preserves the profile's capacities/Main seed
count, and binds the copied payload fingerprint. It does not mark an ATP event
as a FAX fixture. The old FAX feeder adapter delegates to the same pure graph
rules while retaining its historical source validation, seed algorithm and hashes.

`scheduled_knockout_progress` reads ordinary accepted match DTOs and their
positions from the caller's frozen slot ledger. It validates recorded week/slot,
source, seed, exact feeder opponents and chronology. Missing earlier rounds,
future evidence, wrong/duplicate records and altered source payloads fail closed.
It returns only due matches; it owns no second result store. New match seed
schema is explicit and does not alter the old native seed path.

The caller still owns physical Saved-envelope authentication, Entry eligibility,
Health/player projection, frozen-slot input integrity, replay, transitions,
Save and publication. No new public execution route is enabled by this kernel.
The schedule remains an explicit proposal while real Q dates are unverified.

Component tests play all 43 actual squash matches for Main32/Q16 with 44
explicitly eligible synthetic players, apply existing match effects from frozen
round inputs, and feed actual Q winners to Main in the following proposed week.
They round-trip the frozen plan and ordinary match DTOs between phases, compare
opposite acceptance order and reject provenance/scheduling corruption. This is
not a real HTTP/SQLite cross-week native lifecycle or ranking publication proof.

## Run-owned round chronology

`KnockoutRunSchedule` stores explicit Run week + slot for each physical
Qualification/Main round. It supports different weeks, positive variable Run W,
and calendar-year rollover within one offset season. All rounds share the same
exact Run calendar and season; Qualification finishes before Main starts. There
is no implicit seven-slot week or civil-day/rest interpretation. The geometry
must have exactly the scheduled physical rounds. BYE nodes retain advancement
identity and never become executable matches.

The existing native same-week planner reads its old schedule through
`on_one_week`, so its stored schema and outputs stay unchanged. This does not
remove its existing native source/Ranked/W61 integration guards.

`POST .../calendar-tour/atp-source-editions/{occurrence_id}/schedule-preview`
takes the expected Saved head, profile fingerprint and an explicit proposed
round schedule. It checks the exact Saved clock, bracket sizes and Main source
weeks. It returns a deterministic, non-mutating planning review with
`sporting_execution_ready=false` and `qualification_dates_verified=false`.
Proposing Q in the preceding Run week is an Admin proposal, not evidence of
the source's real Q dates. The result cannot confirm or start simulation.

Tests use actual canonical Draw nodes with W52/W61/W80 clocks, same-week slots,
offset year rollover, invalid season/horizon/round chronology and real HTTP/
SQLite Saved-source reads. They are planning/contract evidence, not a played
cross-week tournament or publication acceptance pass.

## Scheduled continuation after an explicit Run extension

The consuming owner supplies the current Run calendar with its current slot.
The frozen schedule and original Saved plan remain unchanged. The consumer
accepts only the identical clock or a legal horizon extension through the Run
calendar's existing extension rules. W, offset, start year and schema cannot be
rebased. Each accepted match must retain the exact clock of its frozen slot;
that clock cannot exceed the current Run horizon or precede the frozen source.
A round cannot mix clocks, and later rounds cannot shrink the Run horizon.

The same pending slot may finish with its original frozen clock after extension.
Later newly frozen rounds can use the extended clock while consuming actual Q
winners. The completed result retains the actual final match's clock; a later
extension can make publication possible without rewriting that result. Seeds,
scores, physical match effects and the copied source schedule are preserved.

Component tests play all 43 matches with extension between Q/Main and compare
sporting outcomes to the unextended control. A separate real HTTP/SQLite test
extends the Run after source Save, retains the exact original source envelope
and reloads the same plan after a cold restart. These are separate proofs, not a
public native cross-week Run Save/Week Transition/Official-publication pass.

## Knockout configuration extension

Setup source v3 adds sporting Category v2 with a separate knockout entity kind.
The earlier group entity schemas/payloads remain unchanged. The original
historical Category/Series/Calendar documents remain v1. Saved v1/v2 Setups
continue to use their copied content; updates require explicit Package review.

Rotterdam 2025 is sourced from official Main and Qualification draw PDFs:

- https://www.protennislive.com/posting/2025/407/mds.pdf
- https://www.protennislive.com/posting/2025/407/qs.pdf

The data records both PDF hashes, 32 Main places (24 other direct places,
4 WC and 4 Q placeholders), 16 Q entrants in four sections of four, 8 seeds,
no BYEs and 43 actual match nodes (31 Main + 12 Q). Main stage points are
500/330/200/100/50/0; Q winner/Q final loss/Q first-round loss are 25/13/0.
These are source awards, not a new phase-composition or eligibility policy.
The PDF's 3–9 February event header is not treated as evidence of Q dates.
Real names, results, withdrawals, Lucky Loser and Special Exempt decisions
from those PDFs are not imported into simulation.

Shared bracket-part construction supplies the ATP geometry without labelling
it as a FAX release fixture. The original FAX wrapper retains its source guard
and serialized shape. A distinct baseline comparison confirms identical dumps
and fingerprints for all 80 original FAX Editions.

The Saved catalog includes the geometry and explicit execution blockers;
Admin can inspect the capacities but cannot confirm a fake playable Edition.
The generic preview rejects unsupported knockout execution without mutation.
Qualification chronology and native Ranked W52 adoption/Entry/awards still need
integration. Merely removing the historical Main4/8 or W61 guards is not a fix.

## Original group-profile slice

The ATP Calendar Setup **source version 2** retains the original Category,
Series and Calendar v1 documents unchanged and adds a separate Category Package
`atp_squash_sporting_profiles` v1. Its two entities are explicit squash adaptations
of sourced 2025 ATP formats. Applying the Setup copies independent Run data and
does not create an Edition or simulate matches. Existing v1 Saved sources retain
their historical bytes; importing the updated Setup is an explicit Package operation.

| Occurrence | Source window | Field | Group win | Knockout component |
| --- | --- | --- | --- | --- |
| ATP Finals 2025 | 9–16 November | Two groups of four, crossover semifinals and final | 200 | Champion 900, finalist 400, semifinal loser 0 |
| Next Gen ATP Finals 2025 | 17–21 December | Two groups of four, crossover semifinals and final | 0 | Unranked, no points |

Finals points are one tournament result: group wins × 200 plus the knockout
component. The champion's 900 includes the semifinal win (400) and final win
(500). An undefeated champion receives 1,500, never 1,500 plus group points.
The official 2025 programme provides the format and awards:
https://www.nittoatpfinals.com/-/media/sites/finals-new/programme/nitto-atp-finals-2025-official-programme.pdf

Both profiles explicitly store squash BO5, the existing versioned squash group
table/tie-break/walkover policies, and the native one-week announcement lead.
These are adaptation policies, not claims about tennis scoring or original ATP
announcement dates. Admin selects participants. Automatic Race/age eligibility,
ATP seed-layer placement, replacement rules, prize money and ATP-specific Best N
exceptions are not implemented by these profiles. Ranking uses the configured
Run policy and its normal W-week validity. Other historical occurrences still
need independently sourced sport configuration; this is not a complete ATP world.

## Ordinary Run workflow

1. Apply the ATP Calendar Setup through Packages preview/confirmation.
2. Save manually.
3. In Calendar Tour, load ATP tournaments from the Saved Package.
4. Review a selected occurrence, confirm the ordinary create-edition command,
   and Save manually. Then use ordinary announcement, Entry, draw, Next Slot,
   result confirmation and weekly ranking publication.

`GET .../calendar-tour/atp-source-editions` reads only hash-verified Saved
profiles, Category/Series bindings and the original Saved Calendar. It reports
out-of-horizon occurrences separately without moving or clipping them.
`POST .../atp-source-editions/{occurrence_id}/preview` takes the ordinary stale-head,
checkpoint and Tour guards. It constructs the native v3 Edition from that profile,
then delegates to the shared Tour service. The command's audit reason identifies
the exact profile content fingerprint. Confirming that reviewed command is the
existing explicit mutation boundary; Save remains separate.

No per-event preview endpoint or runtime lookup in current server source files
is required for a new compatible group profile. Unsupported multiweek formats,
missing sporting profiles, source drift, edited reference baselines and dates
outside the Run horizon fail closed at the affected operation. The older
Next Gen-only endpoint remains compatible with previously Saved v1 Setups.

## Evidence boundary

The HTTP/SQLite lifecycle test exercises legacy Next Gen and the generic ranked
ATP Finals import, 15 actual squash matches each, manual Saves, weekly points
and cold restart. The catalog integration test verifies Save-first reads,
independence from current server files and non-mutating horizon rejection.
Frontend tests mock HTTP and are component evidence. Required hosted acceptance
and browser gates remain separate; skipped Draft gates are not executed passes.


## Sourced Qualification dates — 11 November 2026

New imports use Setup source v4, sporting Category source v3 and Rotterdam
knockout profile v2. The historical v1 profile / Category v2 remains readable
with exactly its original JSON and fingerprints; it still says `not_verified`.
A new server source never upgrades an existing Run snapshot automatically.
Main dates, capacities, points, Draw seeds and the two group profiles are unchanged.

Rotterdam Qualification was **1–2 February 2025**, Main **3–9 February**.
The organiser's dated articles independently identify both Qualification days:

- 15 January 2025: https://www.abnamro-open.nl/nieuws/headlines/52ste-editie/-goffin-en-de-jong-blikvangers-op-kwalificatielijst
- 29 January 2025: https://www.abnamro-open.nl/nieuws/headlines/52ste-editie/vier-nederlanders-in-actie-kwalificatie-abn-amro-open

The ATP overview at https://www.atptour.com/en/news/rotterdam-2025-history-draw-schedule
contains a duplicated date in its Sunday Qualification line and unrelated stale
final-day text. The exact Qualification window comes from the two consistent
organiser articles, not an inferred correction of that ATP page or the Main-only
PDF header. Only the date facts/URLs/publication dates are copied.

| Phase | Original dates | ISO week labels | W52 with offset 1 / start 2025 |
| --- | --- | --- | --- |
| Qualification | 1–2 February 2025 | 2025 W5 | S1W5 |
| Main | 3–9 February 2025 | 2025 W6 | S1W6 |

The new evidence is versioned independently of the old PDF hashes. A v2 profile
requires real ordered dates, distinct dated HTTPS sources published by the first
Qualification date and a window consistent with Main. V1 cannot acquire v2
verification fields. Week projection preserves original dates, the Run's actual
offset and every touched ISO label. A partial horizon or ISO week 53 yields
explicit conflicts, without a clipped whole-phase schedule or proportional
conversion to W61/W80.

The ordinary Saved catalog now reports the Qualification window independently
of Main. Schedule/feeder previews use that exact copied evidence: new v2 rounds
outside the sourced Q week are rejected, just as Main rounds outside their
source weeks are rejected. V1 retains its previous explicit-proposal boundary.
A real HTTP/SQLite copy, manual Save, changed-default and cold-restart proof
covers both versions, preserving the physical Saved payload/hash. The old
Category/profile fingerprints are pinned in a compatibility fixture.

Admin shows sourced Q dates in CS/EN and keeps the unsupported knockout import
disabled. This closes the source-date blocker, not the native cross-week Run
execution blocker. Slots remain explicitly proposed and reviewed; dates do not
prove Entry, create a Draw, run MatchEngine, Save or publish ranking. The next
consumer must retain the original binding across Q Save/restart, ordinary Week
Transition and Main in the existing global-slot ledger, then confirm/publish
results through the actual Run commands. No legacy calendar guard is removed.
