# Run Tour Saved Calendar / Edition scoped-read contract — 13 October 2026

**Implementation candidate, not yet merged.** This backend-only vertical slice
introduces two **read-only** Admin routes under the existing Run/Branch router:

- `GET /admin/runs/{run_id}/branches/{branch_id}/tour/calendar?revision_id={saved_revision_id}&season_index={0..49}`
- `GET /admin/runs/{run_id}/branches/{branch_id}/tour/editions/{event_id}?revision_id={saved_revision_id}&season_index={0..49}`

Every request requires all four context identifiers: Run, selected Branch,
reachable immutable Saved Revision and season index. The Edition additionally
requires the exact `event_id`. The existing Saved Revision history service
validates the requested Branch's **complete reachable lineage**, including
shared pre-fork ancestry and payload/hash consistency. The source component
loader retains the original owning Branch and never aliases its identities.

Calendar lists only the requested season, with 61 weeks represented explicitly
in the response, including seasons that have zero events. It reuses the **canonical**
`resolve_viewer_tournament_history` across ALL Calendar packages before
filtering, rejecting duplicate `event_id` across seasons/packages, orphan
published results, and cross-Run/Branch identity mismatch. Distinct valid
events retain their actual season/week and other source schedule metadata.

Edition detail references the exact saved Calendar edition; `published_result`
is included **only** when the existing canonical Saved Ranking result authority
exists for that event and its run/branch/event/season/week identity agrees with
the Calendar. That result contains the real immutable player/match records.
The Calendar's own planned/completed label is not a lifecycle authority; the
read contract marks the authoritative lifecycle status `unavailable`.
Entry/Draw/Groups/Settings histories are not invented by this slice.

A Saved HEAD change never changes a deep link with explicit `revision_id`;
unknown, foreign and unreachable Saved Revisions return 404, mismatched
result/event identity returns 409, missing required/invalid season yields 422,
and an event not in the exact season/revision returns 404. Reads do not touch
Working Draft, simulation, Viewer Branch, RNG, or source packages.

Focused PR gate: backend unit/application and actual FastAPI/SQLite API tests,
including multi-season, saved versus live content, shared lineage, 404/409/422
context guards, canonical published versus uncommitted results and restart.
Frontend links, six-tab Edition UI and actual Chromium journey remain the next
coherent slice; no new historical links are enabled prematurely.
