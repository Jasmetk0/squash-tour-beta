# Saved ATP squash sporting profiles V1

## 2024 Finals and source coverage audit

Setup source v7 / sporting Category v6 append two independent 2024 group profiles: ATP Finals (10–17 November, 200 per group win, 400 semifinal win, 500 final win) and Next Gen ATP Finals (18–22 December, unranked). Both retain the existing eight-player, two-group, crossover semifinal and squash BO5 adaptation with Admin-selected entrants. No automatic Race or age selection and no historical player identities or results. The 2024 dates match the existing canonical Calendar. Source links are stored on each profile. Existing v5 profiles remain identical.

Run `python scripts/audit_atp_sporting_coverage.py --year 2024 --year 2025` for deterministic source coverage by year/category and per-occurrence missing/profiled status. This read-only tool checks identity, category and Main dates against the canonical Calendar. Undated and known-not-held memberships are separately reported. The audit validates the complete yearly membership partition regardless of selected years. Each dated row includes the original source URL, source state, inclusive duration and occupied ISO weeks; missing events spanning at least three ISO weeks are flagged for chronology research (not an execution decision). A profile is not a claim of native execution readiness or full-season acceptance. It does not verify live external sources or change Run data.

## Munich and Vienna 2025

Setup source v6 and sporting Category source v5 append two profiles without
changing the four earlier payloads. The Main windows match the existing historical
Calendar occurrences. The official draw PDFs supply the ATP 500 scheduled geometry
(32 Main places, eight seeds, three wild cards, 16 Q entrants in four independent
four-player sections, four Q winners, zero byes). The points are Main
500/330/200/100/50/0 and Q 25/13/0. Historical lucky losers, withdrawals and
results are not imported as scheduled slots.

| Occurrence | Qualification | Main | W52 (start 2025, offset 1) Q/Main | W52 (start 2024, offset 37) Q/Main |
|---|---|---|---|---|
| Munich | Apr 12–13 | Apr 14–20 | S0 W15/W16 | S0 W31/W32 |
| Vienna | Oct 18–19 | Oct 20–26 | S0 W42/W43 | S1 W06/W07 |

Sources: [Munich official phase schedule (Apr 8)](https://www.atptour.com/en/news/munich-2025-atp-500-history-draw-schedule),
[Main draw](https://www.protennislive.com/posting/2025/308/mds.pdf),
[Q draw](https://www.protennislive.com/posting/2025/308/qs.pdf);
[Vienna official phase schedule (Oct 14)](https://www.erstebank-open.com/en/news/storys/vienna-2025-atp-500-history-draw-schedule),
[Main draw](https://www.protennislive.com/posting/2025/337/mds.pdf),
[Q draw](https://www.protennislive.com/posting/2025/337/qs.pdf).
PDF SHA-256 values were obtained from complete downloads in
[the source evidence run](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45672128407).

Both phases are calendar-projected from Saved source data; Admin proposes the
round slots. The 43 nodes describe scheduled geometry, not executed matches.
Native Ranked W52 execution remains outside this source-only change.

### Additional ATP 500 profiles (same unreleased source v6 / Setup v7)

| Event | Qualification | Main | Main/Q weeks (calendar year) | Source |
| --- | --- | --- | --- | --- |
| Doha 2025 | 15–16 Feb | 17–22 Feb | W08/W07 | [ATP](https://www.atptour.com/en/news/doha-2025-history-draw-schedule) |
| Dubai 2025 | 22–23 Feb | 24 Feb–1 Mar | W09/W08 | [ATP](https://www.atptour.com/en/news/dubai-2025-history-draw-schedule) |
| Halle 2025 | 14–15 Jun | 16–22 Jun | W25/W24 | [ATP](https://www.atptour.com/en/news/halle-2025-atp-500-history-draw-schedule) |
| Dubai 2024 | 24–25 Feb | 26 Feb–2 Mar | W09/W08 | [ATP](https://www.atptour.com/en/news/dubai-2024-history-draw-schedule) |
| Halle 2024 | 15–16 Jun | 17–23 Jun | W25/W24 | [ATP](https://www.atptour.com/en/news/halle-2024-atp-500-history-draw-schedule) |

Each has a full Main32, 8 seeds, 3 Main WC, zero BYEs, Q16 in four sections of four, four Q winners and 43 planned matches. All four actual Q winners are present in each final Main draw. The additional historical LL, PR and SE designations are not imported, and do not create additional qualification-winner spots. This is the existing nominal Admin-selected squash geometry, not a reproduction of historical selection or replacement rules. The 2025 Doha schedule article has a typo in the detailed end-date line; the canonical archive and both PDF headers agree on 17–22 February. All five Main points are 500/330/200/100/50/0 and Q points 25/13/0. The ten original PDF SHA-256 values are stored in the profiles; [evidence run 45688533510](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45688533510) downloaded and extracted the original draw files. Doha 2024 remains outside the package: the Q PDF could not be downloaded, and its Main draw has BYEs. No sporting execution claim.

### First ATP 250 profiles and Queen's 2025 (same unreleased source v6 / Setup v7)

| Event | Qualification | Main | Main/Q calendar weeks | Evidence |
| --- | --- | --- | --- | --- |
| Stuttgart 2024 | 8–9 Jun | 10–16 Jun | W24/W23 | [Organizer schedule](https://bossopen.com/en/news/packed-program-at-the-boss-open) |
| Stuttgart 2025 | 7–8 Jun | 9–15 Jun | W24/W23 | [ATP schedule](https://www.atptour.com/en/news/stuttgart-2025-atp-250-history-draw-schedule) |
| Queen's 2025 | 14–15 Jun | 16–22 Jun | W25/W24 | [ATP schedule](https://www.atptour.com/en/news/queens-2025-atp-500-history-draw-schedule) |

Stuttgart has 28 actual Main entrants in a 32-position bracket, four unplaced BYEs, eight nominal seeds, three Main WC, and 16 Q entrants in four sections producing four winners. The Main awards are 250/165/100/50/25/0 and Q 13/7/0. Exactly 27 Main + 12 Q matches if fully played, not 43. The existing source geometry describes unplaced BYEs; their placement and points unlock after a BYE belong to the native Draw/ranking authorities, not to this data change. The 2024 final draw includes a seed withdrawal and LL in that position; nominal seed count and four Q winners remain unchanged. Historical player identities, replacements and results are not imported. Queen's is Main32/Q16, 8 seeds, 3 Main WC, four Q winners, 43 matches and the existing ATP500 awards. All six original draw PDF hashes are recorded in the package; [evidence run 45690237346](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45690237346) also obtained Houston and Geneva 2025 PDFs. Geneva Q overlaps the Main source window, requiring separate schedule review. Houston is imported below. Geneva remains excluded.

### Further American ATP250 profiles

| Event | Qualification | Main | Main/Q weeks | Dated Q-window evidence |
| --- | --- | --- | --- | --- |
| Delray Beach 2024 | 10–11 Feb | 12–18 Feb | W07/W06 | [Organizer, 10 Jan 2024](https://www.delraybeachopen.com/en/tournament/news/fritz-and-paul-rankings-race) |
| Delray Beach 2025 | 8–9 Feb | 10–16 Feb | W07/W06 | [Organizer, 23 Oct 2024](https://www.delraybeachopen.com/en/tournament/news/2025-dbo-fritz-and-paul) |
| Houston 2025 | 29–30 Mar | 31 Mar–6 Apr | W14/W13 | [Contemporary Houston Chronicle report, 27 Mar 2025](https://www.houstonchronicle.com/la-voz/article/conciertos-de-emmanuel-marisela-tenis-golf-y-20244570.php) |
| Santiago 2025 | 22–23 Feb | 24 Feb–2 Mar | W09/W08 | [Organizer, 24 Jan 2025](https://www.chileopen.cl/todo-lo-que-necesitas-saber-para-el-movistar-chileopen-2025-horarios-shows-y-m%C3%A1s) |

Each uses 28 actual Main entrants, 4 unplaced BYEs, 8 nominal seeds, 3 Main WC, 16 Q entrants and four Q winners (39 matches if fully played). All four Q winners are present in the respective final Main draws; historical LL/SE/PR and personal results are not copied. Houston's dates use the contemporary newspaper's explicit dates, corroborated by the archived Q match results; its capacity and points come from the official draw PDFs, not from the newspaper. The Delray Beach 2025 Q PDF does not print points: its 13/7/0 awards are independently checked against the [2025 ATP rulebook, §9.G, p.264](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf). The same rulebook explains the zero-point first loss after BYE; native ranking adoption remains out of scope. [Evidence run 45691597086](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45691597086) downloaded eight original PDFs including Buenos Aires 2025; the Houston hashes come from run 45690237346. Buenos Aires remains excluded pending clarification of the qualified player's replacement (only three Q markers in final Main despite four qualifying winners), even though its [organizer's schedule](https://iebmasargentinaopen.com/todo-lo-que-tenes-que-saber-sobre-el-ieb-argentina-open-2025/) is complete. Source v6 / Setup v7 remain unreleased; previous v5 payloads unchanged.

### Further 2024 ATP500 profiles

| Event | Qualification | Main | Q/Main calendar weeks | Official dated source |
| --- | --- | --- | --- | --- |
| Rotterdam 2024 | 10–11 Feb | 12–18 Feb | W06/W07 | [ATP, 8 Feb](https://www.atptour.com/en/news/rotterdam-2024-history-draw-schedule) |
| Acapulco 2024 | 24–25 Feb | 26 Feb–2 Mar | W08/W09 | [ATP, 23 Feb](https://www.atptour.com/en/news/acapulco-2024-history-draw-schedule) |
| Vienna 2024 | 19–20 Oct | 21–27 Oct | W42/W43 | [ATP, 15 Oct](https://www.atptour.com/en/news/vienna-2024-atp-500-history-draw-schedule?q=ton) |

Each retains Main32/Q16, 8 seeds, 3 Main WC, four qualifying winners, no BYEs, 43 matches and ATP500 points. The original six draw PDF hashes are in the profile source. [Evidence run 45694538668](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/45694538668) obtained ten of fourteen attempted original PDFs. Acapulco 2025 and Rio 2025 require separate review of seed substitution; Rio 2025 Q points are not printed in its PDF. Rio 2024 and Queen's 2024 original PDFs were unavailable in this run. None of these four are imported. Historical replacements/identities and native execution remain out of scope.

## Dallas Open 2025

Setup source v5 and sporting Category source v4 add Dallas. On a calendar-year
W52 Run, Qualification on 1–2 February maps to W05 and Main on 3–9 February
maps to W06. The Saved catalog projects each phase separately using the Run's
actual season offset. The sourced draw has 32 Main places, eight seeds, three
Main wild cards and four places fed by a 16-player Qualification draw. The
profile records the phase points and PDF SHA-256 hashes. Historical player
identities, results and substitutions stay in the sources. The Saved schedule
preview validates the phase weeks. Native Ranked W52 execution is still pending.
Earlier Setup versions retain their explicitly Saved profiles.

- [Dallas Open phase dates and points](https://www.dallasopen.com/en/media/news/dallas-2025-history-draw-schedule)
- [Main draw PDF](https://www.protennislive.com/posting/2025/424/mds.pdf)
- [Qualification draw PDF](https://www.protennislive.com/posting/2025/424/qs.pdf)

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

Setup source v4 and sporting Category source v3 introduced Rotterdam
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
