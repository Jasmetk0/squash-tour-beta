# Calendar-native population sporting checkpoint V1

Implementation contract; Master v85 product/calibration decisions are unchanged.

A newly played `calendar_opening_knockout.v5` creates two coupled Run/Branch-owned
live records in **one SQLite transaction**: the actual three-match evidence and
`calendar_sporting_checkpoint.v1` in `calendar_player_sporting_checkpoints`. The
checkpoint owns all population players at the original native `RunWeekPosition`,
Season 1 Week 1, phase `opening_week_after_knockout`. It uses no `RankingWeek`,
legacy 61-week ordinal, fake world advancement or duplicate medical authority.

## Actual state

Every player receives the existing explicit provisional 7→57 bootstrap, including
potential identity/provenance, development timing and long-term form norm. The
four actual entrants retain their verified terminal form, sharpness and fatigue
from the played semifinals/final. Other players retain their exact bootstrap
records. All 57 attributes remain unchanged during this opening operation.
Actual match projection still uses the existing 57→engine adapter from #1529.

The full roster and every record must equal a rebuild from the actual Saved
InitialWorld, frozen bootstrap policy and authenticated knockout. In particular,
the four frozen canonical sources must exactly match the corresponding actual
Saved population facts. A self-consistently rehashed change to an outsider,
attribute, source fingerprint or native position is rejected.

## Save, history and recovery

Normal capture, match Save preview, explicit match Save, medical-fact Save and
all-Branch horizon extension use the same coupled capture. Saved content contains
`calendar_standalone_match` and `calendar_player_sporting_checkpoint`; the same
immutable revision hash covers both. The Save audit summary includes the native
checkpoint fingerprint. Match v5 without its checkpoint, an orphan checkpoint,
SQLite hash drift or source mismatch blocks inspection/capture/Save.

Saved revision validation checks both components, including after the event is
wrapped with prepared points. Restore removes or reinstalls both records inside
its existing atomic transaction, verifies live state against the current Saved
HEAD, and preserves historical bytes. Cold restart does not regenerate state.
Horizon extension keeps the original checkpoint and played source unchanged;
the containing revision may have a strictly longer compatible horizon.

Historical knockout v1–v4 and exhibition v1 have **no** population checkpoint and
are never silently upgraded. Their JSON, fingerprints, projection and replay
contracts remain unchanged. Forking native played history remains blocked until a
true ownership/provenance remap exists. Legacy sporting writers retain their guards;
even an exact reference FAX W61 calendar cannot reinterpret this native owner.

## Admin

The existing knockout panel shows the stored population size, 57 attributes per
player, and whether manual Save is still pending. Any population player, including
nonparticipants, can be inspected through a source-bound read-only record route:
`GET …/calendar-opening-knockout/sporting-checkpoint/players/{player_id}` with
`expected_saved_head` and `expected_checkpoint_fingerprint`. It reads the actual
checkpoint; it does not generate a candidate or install state. CS/EN UI discards
old responses on player, Run, Branch, Saved HEAD or checkpoint changes, including
A→B→A and unmount.

## Deliberate remaining limits

One opening sporting operation per Branch remains. This supplies durable native
population ownership for future continuation; it does **not** implement a second
tournament, Week/Season Transition, annual development, automatic recovery,
retirement, Health effects, Tour entry or Official Ranking. Initial attributes
still come from provisional seven-value source generation; no realism calibration
or historical-cohort simulation is claimed. Medical facts remain in Saved Health.

## Verification

- Real FastAPI/SQLite W52/W80 and W52 1,000-player coverage: full roster,
  unchanged nonparticipants, played terminal state, source-bound nonmutating read,
  retry, joint manual Save, cold restart, exact MatchEngine replay, backward and
  forward restore, historical hash integrity and guarded fork.
- Failure injection after match insertion proves rollback of both writes.
- An isolated legacy-fence unit test proves that numeric reference FAX calendar
  equality cannot bypass existing native ownership; it does not claim that the
  native-population setup supports the legacy reference clock.
- Missing/rehashed live owner corruption blocks inspection and Save preview;
  rehashed Saved component tampering and orphan/detached sources fail closed.
- Existing knockout/Health/points/horizon integration and historical domain pins
  remain relevant. Distinct adversarial review checks orphan ownership, wrong
  source population, missing restore coverage and replay/history compatibility.
- UI tests mock only HTTP; they verify source changes and malformed records.
  Real Chromium gate inspects a nonparticipant's stored 57 values before/after
  Save/reload in a 1,000-player Run and verifies extension preservation.

Final-head CI evidence belongs in the PR, not an assertion of full release readiness.
