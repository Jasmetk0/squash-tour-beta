# Native Signed Health v3: first durable replay schema for 15yo Tour birth

## Production gap closed on the reader side

Saved Health previously accepted only initial calendar v1 and edited v2. It
required EVERY calendar Health profile to belong to the original InitialWorld,
even after the separately authenticated lifecycle added a genuine 15yo player.
This meant a correct real Tour birth would be rejected by Saved/restore.

This change defines `player_health_calendar_state.v3`, a complete immutable
**natural weekly carry**. Each successor binds the exact verified lifecycle
fingerprint, previous Health fingerprint, opening Health origin and retained
Admin edits. A birth-week successor additionally embeds the exact
`player_lifecycle_calendar_state.v4` signed birth event. Old players retain
all injury/illness/recovery/consequence records without alteration; each
new 15yo begins with empty injury and consequence history. An ordinary
non-birth Week after the first birth carries the full population forward,
using the same versioned schema. Newborns never receive fake prior-week
Health.

The real Saved Health component loader now parses v3 and:
- preserves existing v1/v2 JSON forms, source and original player validation;
- verifies the entire v3 week chain against the **original Signed Saved
  lifecycle** already authenticated using real Run-prospect source and
  actual Tour Entry;
- re-executes `advance_native_health_week` for every v3 state, checking
  players, whole existing health history, admission, Health origin, Admin
  provenance and source lifecycle hash, not merely the stored component hash;
- refuses a v4 life birth without matching v3 Health on the exact birth week;
- permits a strictly extended horizon to retain earlier immutable clock
  fingerprints;
- refuses a v3-to-v2 Admin downgrade until a versioned correction preserves the natural lifecycle/birth proof;
- checks predecessor Health calendar identity as well as the week ordinal;
- refuses old-style branch remapping of v3 because Signed birth events
  bind original Branch identities.

## Limitations

This is a **read/write-state schema plus strictly verified Saved reader**,
not a Tour writer or a promise of final activated births. The existing
Tour transition refusal on a nonempty native source remains enabled. A
future atomic executor must backfill any consecutive missing naturally
carried Health weeks and write Sporting checkpoint + full Health history +
lifecycle v4 + ranking + signed Tour in the same guarded transaction, then
test real rollback, restart and fork re-signing. The Health schema itself
does not perform healing, publish Entry or award ranking points.

## Test evidence

The focused PR-critical suite uses the actual Saved Health loader and
the #1558 Signed birth/Tour fixture (its InitialWorld lookup is stubbed; this
is a Saved parser/replay test, not a complete Tour writer integration) for W52, W61 and W80;
it checks exact JSON replay, byte-stable source, unsafe fork rejection,
fake newborn or dropped original, forged birth hash, wrong original
Health, wrong lifecycle owner and fake predecessor. It also covers later
natural weekly carries for previously born players.
