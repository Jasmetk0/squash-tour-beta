# Safe Full Simulation checkpoint on frozen Next Week schedule drift (v81)

After a genuine Next Week child has been reviewed and frozen, a later approved hybrid group-to-knockout handoff can extend the authoritative week schedule. The Next Week child correctly rejects the changed schedule fingerprint with `Week Schedule changed during Next Week`, but an uncaught exception used to turn its encompassing server task into a generic failure.

This change catches **only that exact guard error** at the two legitimate parent delegation points:

- Next Season → Next Week (normal 2000/01–2048/49 season).
- Full Simulation → Next Week (final 2049/50 season, Weeks 1–60).

The parent now returns the usual blocked progress payload with `checkpoint = week_schedule_review_required`, an equally named blocker, the genuine current Position and clear operator-facing detail. A server-owned task transitions to `awaiting_operator` rather than `failed`; Task Center GET is still read-only. All other ValueError conditions propagate and fail closed.

**Safety boundary:** neither parent changes the original Next Week command ID, expected Saved Revision, Position fingerprint, reviewed schedule, ranking authority, already committed groups/slots, or global lease. No automatic new schedule adoption, child replay, new Saved Revision, implicit continuation or operator approval. Until an explicit safe re-review/extension is implemented, the operator may Stop the original parent and start a newly reviewed operation. Future integration must prove monotonic frozen schedule extension and child-prefix equality under SQLite writer lock before replacing that workflow.

**Evidence:** a focused production FastAPI-over-TCP/file-backed SQLite test starts a genuine durable worker on an initialized Run, replaces only the exact Next Week fingerprint guard result with the documented exception, then checks the operator checkpoint, Task Center stability, pending original command and unchanged authoritative sporting and Saved rows. This is a controlled guard integration test, **not** proof of an actual mid-flight hybrid bracket expansion. Full hybrid live acceptance remains outstanding.
