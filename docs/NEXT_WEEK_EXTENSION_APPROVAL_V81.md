# Explicit Next Week extension approval (Master v81, 15 October 2026)

After merged #1476 the read-only append-only inspector can verify exact old-to-new week schedule changes. A POST `next-week/extension-approve` adds an **independent operator-signed, audited, replay-safe approval**, without executing sporting results or saving a revision. The original frozen Next Week **request fingerprint is immutable**; only its persisted *approved schedule/range* advances after an explicit yes/no checkbox.

## Transactional safety
- The approval includes immutable task ID and revision, Next Week child ID, fingerprint of the observed Next Week receipt and of the reviewed *current* schedule, operator and audit reason, and explicit confirmation that committed work remains immutable.
- An SQLite `BEGIN IMMEDIATE` writer transaction revalidates the global Full Simulation invocation lease is not active, task state is `awaiting_operator` at checkpoint `week_schedule_review_required`, child is demonstrably owned by the pending original full parent (or nested pending Next Season), original week command request fingerprint, current Run/Branch and Saved-head, exact prefix fingerprint, stable hybrid bracket ownership, all original child completion receipts, and Position precisely at the first added slot.
- No original child receipt is replaced. The only added slots are monotonically consecutive and all come from frozen hybrid knockout match authorities, with no unverified Entry/WC gap. New children are unstarted placeholders with deterministic original-week child IDs.
- Approval event includes old/new schedule hashes, appended ordinals, task revision, operator, audit reason and immutable request fingerprint. The distinct approval command receipt makes exact lost-response retry replay-safe, and conflicts reject.
- Task audit gets an explicit state event (`awaiting_operator` to itself), checkpoint becomes `week_schedule_extension_approved`. Resume remains separately audited through the same server-task control, never automatic.
- Any race with the worker, stale task revision, unexpected canonical sports state, changed original Saved head, foreign Run/Branch, fingerprint drift or rejected append fails closed.

## Evidence limits
The original #1476 inspector has scoped HTTP/SQLite and UI evidence. This slice adds approval contract/same-parent tests; browser integration with fully materialized real hybrid knockout and uninterrupted seeded parity is required before claiming that complete acceptance. No full 50-season completion or pre-alpha release claim.
