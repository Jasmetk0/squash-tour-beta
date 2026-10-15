# Full Simulation unresolved group-phase operator checkpoint (v81)

**October 15, 2026.** PR #1477 is already merged. The canonical Next Week
preflight deliberately refuses to freeze a group-to-knockout schedule whose
post-group bracket cannot be known before real group matches finish. Previously
the nested Next Season / Full Simulation returned a generic
`week_preparation_required`, making its safe next action unclear.

This slice introduces typed `GroupPostphaseBoundaryRequired`, emitted only
from the actual Next Week guard. Both ordinary Next Season and final-season
Full Simulation propagate `group_phase_review_required` to a durable server
task `awaiting_operator` checkpoint. When canonical position blockers identify
completed-group standings, tie, hybrid entrants, bracket or closure requirements,
the separate `group_postphase_review_required` checkpoint provides actionable
review context. Exact current blockers remain authoritative; unrelated failures,
including Entry/WC, continue to use ordinary conservative handling.

Run Admin should perform the **real** group Match Days and explicit standings,
entrant/bracket and ranking review; then a user may explicitly resume the
**same original server task**. No group match, authority, Save, seed, preview
or execution is automatically created or approved by this change. The previous
#1477 append-only re-review remains separately guarded and cannot be
circumvented. CS/EN Global Task Center gives specific instructions.

Proof: Fast CI production HTTP/file-SQLite server task with a *typed error
adapter*, read-only Task Center inventory and Saved/sport immutability;
focused negative classifier and React CS/EN tests. A fully organic browser
group-to-knockout through the same running Full Simulation remains an
independent acceptance gap. This slice is not full 50-season completion.
