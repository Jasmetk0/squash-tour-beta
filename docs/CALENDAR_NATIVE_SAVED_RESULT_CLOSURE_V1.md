# Native Saved tournament result closure (v1, sporting-only)

Master v85 continuation after owner-merged #1538. This is a **new write
boundary**, not a read-only ranking wrapper. It closes an actual signed seven
MatchEngine-game tournament into authoritative *native sporting facts* about
eight entrants. It does **not** create a canonical Tour Edition, validate Tour
Entry, publish Official Ranking, award Race points or change public time.

## Command / confirmation

After playing the existing 8-player **scored** v4 later-week knockout, the
Admin must manually review and Save the entire terminal state. In the same
sporting week, while that tournament is the most recent event, the operator
may POST `/calendar-continuation/knockouts/close-result`, supplying exact
Run/Branch, Saved HEAD, checkpoint fingerprint, unique command identity,
played tournament identity, operator/reason and literal
`explicit_result_confirmation:true`.

The action uses one `BEGIN IMMEDIATE` SQLite transaction and existing Saved
world/player/match owners. It verifies all seven winner-fed results and the
previously prepared v2 eight-player point policy (not Official), and persists
**eight player result records** with exact match-ID participation, wins,
losses, reached round and prepared points. Their tournament and complete
award-source fingerprints must match the signed played event. Results are
player-ID sorted; seven wins, seven losses, correct finalist/champion and four
quarterfinal/two semifinal exits are enforced.

A new `calendar_native_tournament_closure.v1` result envelope upgrades
`calendar_sporting_checkpoint.v7` to `v8` **without changing the original
matches, source events, 57-attribute population, sporting week or their old
hashes**. The closure is a separate additive field, omitted by all older
checkpoint serializers. The operator must review and manually Save again.
Identical exact retries, including after later Save and Week 3, return the
original receipt and checkpoint hash. Changed evidence or reused identity
fails closed; completed closure cannot be replayed as a second write.

Historical replay reconstructs all actual matches/weekly advances then
applies each closure at the stored exact week-event boundary. It validates
the original full sporting fingerprint and independently rebuilds each
player's win/loss/award ledger; a modified outer checkpoint hash cannot
legitimate tampered results. Cold restart, immutable Save/restore, later
individual matches/knockouts and W52/W80 sporting advances retain v8.

The Admin CS/EN UI shows closure status, a separate explicit confirmation
and signed player results in History. No read of Working Draft counts as
Saved authority. Old v1–v7 run history still parses and retains original
serialization/fingerprints.

## Not yet claimed

The result is not a configured Official Tour Edition or approved Entry. It
does not activate an Official Ranking writer, public Viewer score, Tour
career/lifecycle trigger, Prize/Race point authority, nine-stage Week
Transition, Season Transition or Full Simulation. Integration to canonical
Edition/Entry and Official publication remains a follow-up.

## Targeted regression

W52/W80 production HTTP/SQLite, a played signed 8-player scored tournament
with seven match logs; wrong Saved HEAD/consent/Edition identity; closure
with 7 wins/7 losses; rollback on failure; unchanged player records; manual
Saved v8; all seven exact replays; Week 3 and retry; immutable earlier Saved
Revisions; tampered award/wins/origin/sequence/schema even with recomputed
outer checksum; restart and historical backward/forward restore; CS/EN
consent and client result validation. Final-HEAD CI and applicable browser
checks before stating merge-ready; owner alone merges.
