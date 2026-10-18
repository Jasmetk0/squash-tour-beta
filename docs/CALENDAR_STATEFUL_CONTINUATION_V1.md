# Stateful native calendar continuation V1

Implementation contract under Master v85; no new growth/Health calibration.

## Usable behavior

After a real v5 opening knockout and explicit Save of its full-population native
checkpoint, Admin can select any two distinct population players and play another
real BO5 exhibition (11 points, win by two). The actual MatchEngine consumes their
**current stored 57 attributes, form, sharpness and fatigue** through the existing
versioned projection. An original finalist therefore keeps its played load;
a previous nonparticipant starts from its untouched bootstrap record.

The existing provisional match-effect calculation changes only those two players.
All 57 attributes, potential identity/provenance, form norm and every unaffected
player record remain unchanged. Each new exhibition is sequential; simultaneous
knockout semifinals retain their original frozen inputs. There is no recovery,
training, development, ageing, point award or implicit Week Transition. These are
operator-created same-week exhibitions, not a full Tour scheduler.

## Authority, commands and Save

The existing `calendar_player_sporting_checkpoint` component gains explicit
`calendar_sporting_checkpoint.v2`, phase `opening_week_continued`, with an ordered
append-only `CalendarContinuationMatch.v1` ledger and the current population.
V1 serialization omits the new ledger field and retains its exact old shape/hash;
v1 cannot be silently populated with continuation facts. No database migration or
second sporting owner is introduced; the existing native row is transactionally
replaced. Immutable Saved Revisions retain every previous version.

Each ledger entry freezes exact Run/Branch, native clock, sequence, command and
match IDs, source Saved HEAD, source checkpoint fingerprint, seed, operator/reason,
projection/effect policies, both 57-attribute projections, actual MatchContext and
MatchResult/logs, participant-ordered descriptive Health input/source fingerprint,
and match effects. A new log anchor authenticates the frozen inputs. The input
source is the real previous checkpoint, never a newly bootstrapped four-player
operation. The entire final population is verified by rebuilding the original
v5 checkpoint, then folding the exact ordered ledger. Missing/reordered/rehashed
false history, reset state or detached inputs fails closed.

A new command requires an exact **Saved** current checkpoint and clean Working
Draft/Saved Health. Its transaction holds `BEGIN IMMEDIATE`. A competing new
command cannot consume the same predecessor twice: the first leaves an unsaved
successor and the other fails. Exact response-loss retries return the original
entry and original successor fingerprint, including after subsequent Saves,
additional matches and compatible horizon extension. Conflicting reused IDs fail.

`POST …/calendar-continuation/save` uses a distinct reviewed checkpoint fingerprint
and existing draft-version fence. Existing immutable Save captures the complete
state and audit summary. The UI requires a fresh review and separate confirmation;
no new match is available until Save. The knockout and its prepared points remain
unchanged. Their Saved status is separate from an unsaved continued population.
General established component Saves still capture the complete live state.

Restore atomically restores/removes the owner together with its original knockout,
and can return from v2 to original v1 or forward to v2. Cold restart reads stored
history. Horizon extension preserves original frozen bytes; subsequent exhibitions
may freeze the new compatible horizon. No entry may exceed the containing Saved
Run horizon. Native match-containing fork and legacy sporting writers retain their
ownership guards.

## Health and replay

Current fully Saved Health facts are projected into the actual match in participant
order. Numeric limitation effects, recovery, start/retirement decisions and medical
mutation remain unsupported and are labelled explicitly. Later medical correction
or horizon extension never changes a prior match's frozen Health input.

`GET …/calendar-continuation/{match_id}/replay` reruns the real MatchEngine with
its original seed, context, log anchor and Health facts and compares the complete
result. It does not mutate population or history. Replay selection uses an explicit
UI action distinct from the event ID (including IDs named `save` or `play`).

## Admin and verification

CS/EN controls are inside the existing native knockout panel after initial Save:
participant selection, seed/reason, play consent, consumed fatigue, ordered match
history, fresh Save review/confirmation and exact replay. Run/Branch/HEAD changes,
unmount and A→B→A invalidate old reads/consent. Current population record inspection
reflects subsequent played state; original knockout checkpoints remain frozen.

Focused production HTTP/SQLite tests cover W52/W80 two successive real matches,
untouched-player equality, stale-source rejection, exact retries/replays, separate
Save, restart, restore backward/forward, rehashed ledger corruption, concurrent
commands and rollback after an injected write failure. Saved Health correction and
horizon extension are covered through actual services. Historical domain hashes
and old checkpoint behavior remain regression obligations. UI tests mock only HTTP
and verify consent/source fences and action/ID separation. Actual Chromium gate
adds a continued match to the 1,000-player Run, consumes original finalist fatigue,
then manually Saves, reloads and replays while preserving the original knockout.

Next: actual native weekly ownership/development/Week Transition and configured
competition authority; this slice does not claim Full Simulation or realism release.
