# Separate adversarial review — native post-admission competition

This pass followed implementation and the first complete real HTTP/SQLite and
Chromium flows. It inspected production reducers, live/Saved source loading,
origin validation, command/receipt replay, rollback, restore/extension, current
Health versus frozen replay, and frontend HEAD/input/generation guards.
It is a correctness/integrity review, not a full repository security scan.

## Findings addressed

- Merely allowing new commands on v3/v11 would reinterpret an immutable root.
  New v4/v12 wrappers preserve those exact objects; v6 explicitly distinguishes
  the simultaneous-round semantics. Old reducers refuse v6. Full replay is still
  required after decoding; an outer recomputed hash does not authorize a ledger.
- InitialWorld-only identity/projection would exclude admitted players or require
  fake profiles. Entry now uses actual current lifecycle. Match projection uses
  real current sporting records and actual Health; missing legacy-only biography
  remains explicitly unspecified/null rather than fabricated or borrowed.
- A plausible command could name a calendar horizon absent from its claimed
  Saved source. Origin verification now checks the actual Saved Run calendar for
  creation and natural transition, as well as reachable Run/Branch identity,
  preceding checkpoint and genuine Saved Tour where required.
- Shared semifinal inputs were initially displayed as consecutive slots by the
  old evidence projection. v6 now binds the shared actual slot and Edition into
  the round fingerprint; the Admin evidence shows the same slot for both matches.
  Actual winners and terminal effects feed the next round; no hidden recovery.
- A list-shaped first command could raise AttributeError before replay. The
  v4 model now rejects it as invalid authority, exercised by rehashed live-row
  corruption in the real HTTP scenario.
- New nested command/match IDs must not collide with historical played evidence.
  The native reducer checks the actual old opening and continuation/tournament
  identities rather than trusting only new Edition IDs.
- Sporting verification and Tour verification initially replayed the same v12
  chain twice in one Saved-source fold, and replay rebuilt each played event
  twice. The exact authenticated result is shared only within that fold. Physical
  hashes, complete native dependencies, Run/Branch scope and the full reconstructed
  result comparison remain mandatory; no process-wide unverified prefix is added.
- Tuple/list differences in reconstructed receipt dictionaries caused a false
  inequality after JSON persistence. Canonical result/preview equality is checked
  first, then the authenticated stored receipt retains its exact historical shape.
- The extended HTTP fixture used its frozen pre-extension clock for a new Edition.
  It now uses the actual current Run calendar, matching the existing Admin form.

## Evidence and residual risk

The initial full production lifecycle/restart/restore passed locally (402.09 s).
Expanded Earth and FAX cases passed locally (415.15 s and 401.34 s total pytest
runs); the FAX case includes three late rollback seams and exact SQLite dump
comparisons. Actual Chromium completed every new Admin operation and separate
Save with unchanged pre-Save Viewer; its screenshot was inspected. Focused
existing domain/history/proof/summary checks, new actual-MatchEngine reducer
checks, 38 mocked-HTTP frontend component tests and production web build passed.
These local runs precede the final review fixes; same-latest-head CI, including
all original native API/season/browser gates plus the new matrix/browser, is
required and recorded in the PR. No pending check is called green.

The retained immutable root and full authenticated replay have payload/cold-read
cost. New browser artifacts record preview, commit/inspection and Save/inspection
phases; original timeouts/assertions remain. No post-admission thousand-player
or full multi-season performance/release claim is made. Existing W80/1000 and
long native API gates continue to exercise their original bounded pre-birth path.
Historical source epochs, numeric Health/healing, protected forks, policy edits
and full Master release certification remain explicit limits. No merge performed.
