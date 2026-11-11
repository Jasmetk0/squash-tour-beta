# Saved ATP squash sporting profiles V1

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
