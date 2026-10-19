# Native Tour complete Health preparation

## Concrete gap

The bounded configured Tour currently retains opening Saved Health while its
lifecycle advances. A birthday proposal cannot create a durable Health v3 target
by jumping directly from that opening baseline to the target week: v3 requires
consecutive predecessor fingerprints and the matching lifecycle for each week.

`prepare_native_health_history` keeps the complete verified Saved Health prefix
and prepares each missing natural weekly state against its own Signed lifecycle.
It then prepares the target week's exact v3 Health state, including its genuine
v4 birthday event. An earlier birth belongs only to its historical birthday;
the next birthday never appears in a backfilled earlier week. Existing injury,
illness, consequences, baseline origin and Admin evidence are preserved. There
is no stochastic healing or retrospective health generation.

The caller authenticates the full Saved lifecycle/Health/source first. The pure
preparation also refuses gaps, foreign identities/calendars, contracting horizons,
future Health, rewritten predecessors and forged v3 carry states. A partial Saved
prefix can be resumed without replacing any earlier objects or serialized bytes.

## Production boundary

The real Admin `POST .../calendar-tour/prospect-intake/sporting-preflight` now uses
this preparation after verifying Saved HEAD, checkpoint, Tour, exact source and
completed-week play counts. `sporting_week_projection.durable_health` reports:

- original Health head fingerprint/week and saved state count;
- full prepared state count and number of backfilled weeks;
- target `player_health_calendar_state.v3` schema and fingerprint;
- canonical fingerprint of the complete prospective Health component;
- `prepared_transition_fingerprint` binding the Saved HEAD, prior complete
  admission/sporting proposal and full Health chain.

The response returns compact hashes/counts rather than copying every player in
every historical week into HTTP. Changing the development seed changes the
combined transition proof while leaving deterministic Health carry unchanged.
The existing read-only API schema remains backward compatible. Strict Run
horizon extensions use the current Run calendar for the target while retaining
the exact frozen completed checkpoint/lifecycle calendar. Admin validates both
clocks separately; extending the horizon never rewrites old Saved bytes.

This is **preparation exposed through the production read-only route**, not the
native Tour's atomic writer. It never inserts Health/lifecycle/players, modifies
a Working Draft, Saves a Revision, creates Entry or publishes rankings. The
existing native-intake refusal remains in effect. A sporting checkpoint capable
of replaying births and the coupled atomic executor are the immediate next step;
protected fork re-signing and versioned v3 Admin correction also remain blocked.

## Verification

Pure tests cover W52/O1, W52/O35, W61/O37, W80/O15 and W80/O80, two distinct
birthdays, exact prefix resumption, retained active injury/Admin facts, and
adversarial inputs. The production HTTP/SQLite test exercises real opening
matches, Signed source Save, seed changes, stale proof rejection, non-mutation,
SQLite process restart and rejection of recomputed but unsaved live Health.
Its final matrix uses W52/O1, W61/O37 and W80/O80 with eight original players;
the W80 case extends the Run from three to five seasons after actual matches.
These tests do not claim an end-to-end persisted birth transition.
