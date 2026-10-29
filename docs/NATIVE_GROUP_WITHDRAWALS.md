# Native group withdrawal and non-played W/O

Candidate based on `buuk` e4d0dd3b7da9f8767d19ece2cf194919a9bf864d,
after owner merges #1647 and #1651. Master 15.14 and 16.3 remain authority.

## Supported operation

`withdraw-group` reviews one current-week, drawn pure-group Edition participant
who has already played and still has unresolved group matches. It requires the
exact current Saved HEAD/checkpoint/Tour, player ID, explicit reason category,
operator and audit reason; a detail note is optional. Review is read-only;
execution changes the Working Draft and manual Save is separate. Retrying the
same confirmed request does not append a second withdrawal.

The immutable group topology, schedule and already played results remain.
Subsequent ordinary Next Match/Next Slot operations resolve each remaining
pairing involving that player through the existing TournamentWalkoverResult
and group standings receipt authority. Opponents receive a group-only win and
the effective format's maximum table points. There is no fabricated game/ball
ratio, MatchEngine call for that pairing, rally, duration, physical effect,
played career win/loss or H2H. Other matches still use actual MatchEngine and
the original common pre-slot input. A W/O does not occupy the withdrawn player's
physical match slot in another simultaneous Edition.

## Deliberate boundaries

This slice supports pure groups with zero Official group-win reward. Existing
nonzero phase rewards do not contain a decided W/O reward policy; hybrid
withdrawn-player advancement eligibility is also not inferred. Such commands
fail before writing. A second withdrawal in the same group is rejected because
the mutual non-played result needs an explicit outcome policy. Withdrawal before
the player's first real match belongs to the separate Entry/replacement flow.
The operation is not retirement during a rally and adds no automatic medical
diagnosis, sanctions, DQ, ABN, replacement, reseeding or new sporting defaults.

## Evidence and versioning

New `native_group_withdrawal.v1` audit records and `native_group_walkover.v1`
results live in `calendar_global_slot.v3`. They are separate from the slot's
actual accepted MatchEngine results. Old v1/v2 slots omit both new empty fields
and reject acquiring nonplayed data. The v13 checkpoint/v5 Tour containers retain
their original authority and physical validation gates. Strict JSON dispatch
recognizes the new slot version. A derived `calendar_group_tournament_result.v2`
has separate played `matches` and `walkovers`; old v1 result bytes stay unchanged.

Forks retain source-owned played/W/O evidence as inherited references, append
target-owned decisions, and leave the source branch untouched. Independent
command replay reconstructs withdrawal and W/O data; declared rehashed columns
cannot replace that proof. The original transactional Save and rollback gates
remain. Full Simulation uses the same slot operations and explicit review/Save
pauses rather than a second W/O executor.

## Local validation (29 October 2026)

- Real HTTP/SQLite: actual first-day matches, read-only review, injected
  post-write rollback, exact retry, manual Save, physical reopen, two nonplayed
  results, unchanged player state for W/O, preserved actual rally logs, result
  confirmation and next-week publication passed.
- Real nested forks from a partially resolved W/O slot, source isolation,
  completion and independent reopen passed. The same actual worker task reaches
  its target after separate slot Saves and result confirmation. These three
  cases took 319.84 seconds together, including a fresh production fixture.
- The real stale/foreign/missing-reason/duplicate/rehashed-evidence rejection
  case passed in 96.22 seconds, including another fresh fixture.
- Actual Admin Chromium: pure groups created through the UI, explicit withdrawal,
  10 actual matches plus two W/O, separate confirmations/Saves, week publication,
  cold SQLite restart and CS/EN passed without browser errors. Local runtime:
  Python 3.12, Playwright 1.51 and Chromium Headless Shell 134. Hosted acceptance
  on the final head remains mandatory; this is not a hosted pass.
- A fifth real HTTP/SQLite case compares whole-slot execution with reverse
  individual W/O/real-match acceptance, including a partial Save and physical
  restart. Their complete sporting checkpoints are equal (117.14 seconds).
- All 68 focused domain/CI-policy checks, 41 mocked frontend component tests and
  the TypeScript/Vite production build passed. Component tests mock HTTP and are
  separate from the genuine browser and API proof above.

The existing hybrid browser remains its own unchanged sporting scenario; a
separate withdrawal browser matrix entry exercises this slice. Final-head
W52/W61/W80 and applicable legacy/native/fork/browser acceptance must actually
pass before owner merge. Draft skips are not passes. This is not full pre-alpha
or 50-season release certification. Owner alone merges; no auto-merge.

## Hosted candidate follow-up

On candidate `dc1832330f`, both real group browser scenarios passed. The
W52/W61/W80 HTTP jobs each passed all eight existing group cases, then rejected
the withdrawal test's first review. The retained W52 source contains 12 Saved
Revisions, but its filesystem-only test copy contains only 11: a pooled SQLite
connection can retain the latest committed Save in WAL. All withdrawal fixture
clones now use the existing SQLite backup helper so their snapshot includes
committed WAL contents. The actual failed source, cloned with that helper,
returns HTTP 200 for withdrawal preview; the old incomplete copy returns 409.
Production Saved/source validation is preserved.

The separate W80/1,000-player Tour browser reached Week 6 and completed both
result confirmations, but exceeded its unchanged 18-minute deadline during
final verification. This remains an unresolved acceptance failure, not a pass.
A cold inspection of its retained database confirms a clean Saved Week 6;
profiling attributes most inspection time to actual Saved-lineage verification.
Neither fixture scale, validation gates nor deadlines have been reduced.

After the backup correction, all five genuine withdrawal HTTP/SQLite cases
passed together in 321.59 seconds with a fresh W52 fixture, including rollback,
exact retry, nested forks, the real worker and reverse-order restart equality.
All five focused withdrawal domain cases, scoped Ruff and whitespace checks
also pass. New-head hosted acceptance is still required.

## Same-read decoded values candidate

The original Saved physical-row, complete dependency graph, ownership, lineage
and sporting replay gates still run. A completed private global replay now
retains at most eight checkpoint model values beside its existing Tour values.
The authenticated Admin context can consume them only after binding the entire
actual component value, declared fingerprint, independently computed model
fingerprint and Run/Branch scope. Original match evidence is still decoded and
checked. Missing, changed or evicted values take the ordinary strict decoder
and bounded defensive-copy cache. No cross-request source proof or new persisted
hash is introduced, and the default internal decoder contract remains unchanged.
A cache hit also avoids constructing a JSON string that its checked part decoder
would immediately discard; its actual-value and retained-model guards remain.

The same retained W80/1,000 database produced identical COMPLETE production
inspection DTOs in a paired cold-read comparison: ordinary decoding 79.102s,
same-read values 73.712s (6.81% less). This is a read measurement, not whole-Run
or hosted speed certification. The actual unchanged full Admin Chromium flow
with 1,000 real players and W80 then passed in 760.259s under its original
18-minute outer deadline, including both real tournaments, manual Saves,
confirmed results, physical backend/SQLite restart, public Week 6 and CS/EN.
The restart portion took 52.762s. No fixture, assertion or timeout was reduced.

The extended actual SQLite source-value case checks strict decoder equivalence,
foreign scope, changed/rehashed component values, declared hash changes and a
changed private model. The strict version-dispatch case still checks byte-for-
byte serialization against the original strict Union validator. Sixty-six
additional dependency/snapshot/value-isolation/history/domain cases passed.
An existing corruption fixture now preserves its source class/for_week interface
while changing its fingerprint, so it reaches the intended ValueError rather
than an unrelated AttributeError; the original failure was reproduced on buuk.

On preceding head b6d90e4d, all three W52/W61/W80 group HTTP jobs passed. The
W80/1,000 browser still timed out, and the final-week W80 job ended without
available logs or its artifact; GitHub left its execution step in progress in
the failed job record. Its cause is not established. The same unchanged runtime
passed that final-week job on dc1832330f. Neither missing evidence nor an older
pass substitutes for successful final-head hosted acceptance.

Final local physical-source/Save verification also passed all four selected
production HTTP/SQLite cases in 170.03s: actual append/late-write gates and changed
ancestor rejection, metadata-only histories with complete physical gates,
concurrent/stale/retry/rollback/rehashed slot rejection, and cached final replay
with unchanged real-engine and read-only boundaries. No negative case was removed.

## Component decode follow-up (29 October 2026)

On head `238639cfb3176b95d563f19b6a05db771b6839ec`, the real group/W-O
browser and HTTP matrices and the W80 final-week closing gate passed. The
W80/1,000-player native Tour browser still exceeded its original 18-minute
budget during the final Week Transition. That remains a failed gate.

Profiling its retained actual database showed a subsequent Saved inspection
spending 6.58 seconds strictly decoding the same checkpoint again and 3.37
seconds in defensive-copy work (instrumented total: 17.42 seconds). The former
same-read handoff did not seed the cross-read decode cache, whose whole-payload
key also changed after a Tour-only Save even when the sporting owner did not.

The internal authenticated-context reader now keys v13 checkpoint decode data
by its complete actual component envelope plus Run/Branch scope. Strict model
parsing and scope/hash checks run on misses; hits hash the complete component
and return defensive copies. This shares the existing 64 MiB projection budget,
with at most four entries, rather than adding another model cache. An optional
same-read replay value may seed it only after its existing complete-value guard.
Original match evidence and coupled Tour checks still run independently.
Legacy schemas and the default decoder retain their original path. No cached
value authenticates a Saved row, graph, owner, sporting result or new write.

The final follow-up adds tests for changed actual data with an unchanged declared
hash, repeated failed decodes, foreign ownership, nested caller mutation, byte
and entry budgets, oversize bypass, and genuine SQLite/default-decoder equality.
The focused dependency/decode/domain set passed all 49 cases in 31.69 seconds.
Further real HTTP/SQLite withdrawal and corruption/rollback/retry cases and the
complete unchanged W80/1,000 browser are being verified on this follow-up.
Hosted checks on its final commit remain required before owner merge; the prior
local browser pass and other green jobs do not substitute for that failed gate.
