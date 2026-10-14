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

## Relative target extension

The same `POST /full-simulation/target` accepts **exactly one** of
`{"target_week":{"season_index":2,"week":20}}` (legacy absolute mode)
or `{"relative_target":{"unit":"weeks","count":5}}` /
`{"relative_target":{"unit":"seasons","count":1}}`. A strict positive
integer count is required; seasons permit at most 49 and weeks at most
3050. The operation rejects counts crossing the final 2049/50 Week 61.

The server resolves relative requests from **the actual current week while
holding the SQLite immediate writer lock**, never from the browser's cached
Position or from the previous effective target. A season means 61 weeks;
the week-of-season is preserved through rollover. `target_events` preserve
both the original relative request and its durable applied-at-week anchor
alongside the immutable resolved week. Replaying the same control ID returns
the original anchor/resolution (even after later retargeting or terminal
closure); a changed count or unit under that ID is rejected. Global receipt
inspection rejects corrupt relative provenance and arithmetic. The original
Full Simulation command/review still never changes. Stop and Save semantics
are unchanged.

This extension still only targets arrival at the **start of a week**. Event
and intra-week targets, autonomous background worker/reconnect, and release
acceptance remain outside this slice.
