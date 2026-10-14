# Full Simulation week boundary target — v81 slice

Scope: first *explicit absolute weekly* target form. This does not supersede
Master v81 §27.23 (which additionally requires within-week, relative and
event-based targets). The effective target means **arrival at the beginning of
the specified season/week**. No sporting result of that week is implied. If the selected week is
already current and contains committed matches, they stay committed; the
next safe writer boundary prevents additional sport.
Season indices are 0–49 (2000/01–2049/50), weeks 1–61.

The original Full Simulation preview and command remain fixed at 2049/50
Week 61. A different `target_week` is stored in the same durable parent as
`effective_target_week`, `target_revision` and immutable `target_events`.
Each request carries its own control command ID, operator and reason.
Identical HTTP retries replay one event (even after terminal target closure)
and do not roll back a later revision.
A different request with an existing ID is rejected.

A target may be changed while the parent is running, pause-requested or
paused; it must not precede the actual current week at the time the SQLite
writer lock is acquired. Resetting the target to 2049/50 Week 61 reinstates
the original final closure path. The weekly fence checks after acquiring
SQLite BEGIN IMMEDIATE, so a successful concurrent retarget cannot be
overtaken by a subsequent sporting transaction. A shortened reached target
is terminal `target_reached`, distinct from manual `stopped` and canonical
final Run `complete`; results and all Saved Revisions persist, with no
implicit Save. Further work requires a new, separately reviewed operation.

Evidence is limited to targeted production FastAPI/SQLite and React/client
tests plus required CI. No claim of precise in-week target, server-owned
autonomous worker, a full 50-season simulation, or complete pre-alpha.
