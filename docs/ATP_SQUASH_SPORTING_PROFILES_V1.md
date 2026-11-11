# Saved ATP squash sporting profiles V1

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
