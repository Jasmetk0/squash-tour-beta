# Saved Native Tour Season Summaries V1 — bounded implementation candidate

## Scope and data provenance

Parent `buuk` is owner-merged PR #1546
(`bb38e5a17e6a9b667c8f47287fb992d8e00ee3be`). This candidate
does **not** alter any Saved Revision, MatchEngine outcome, sporting
checkpoint, ranking policy, calendar or replay hash.

A season is publicly **complete only after** its real versioned
`season_transition_completed` event has reached the **Saved** Tour
authority. Reaching last Week W, having a Working-only Season Transition
or having a planned future Edition does not qualify. Older completed
seasons remain navigable from later signed revisions.

The new on-demand:
- `GET /admin/runs/{run_id}/branches/{branch_id}/calendar-tour/seasons/{index}?compare_to={other_index}`
- `GET /viewer/runs/{run_id}/calendar-tour/seasons/{index}?compare_to={other_index}`

always authenticate the persisted Saved lineage and Run/Branch identity.
Viewer resolves the one current Saved Viewer Branch and never reads a Working
Draft. Admin shows only the exact selected Branch's Saved tour even if the
Branch has newer uncommitted Working changes. Both reject an incomplete,
negative, future or out-of-horizon season without attempting a summary.

## Historical facts in the response

The compact national summary groups **confirmed** real Tour Editions by
actual participant Saved nationality, using the same played MatchEngine
`play` receipts whose bracket, awarded placements and signed point policy
are already verified against the actual sporting event by
`saved_tour/verify_tour`. It counts authentic champion/finalist/
semifinal/quarterfinal outcomes, sum of *original Edition awarded points*,
distinct participating players and count of Editions represented.

The response also exposes per-Edition champion/finalist and provenance hash,
per-player titles and awarded points, and the **last ranking published inside
the completed Season's Week W** with its source fingerprint. The latter is
not mislabeled as a final end-of-season ranking: results from Week W enter
the Official Ranking at the next Season Week 1. Historical award totals
are **not** current ranking points because Best N and time expiry apply.
This derived report is not a persisted Records authority and adds no
imaginary athletic/national performance indicators.

Choose any two already completed Saved seasons. Comparison deltas are
`selected - compared`, including nations only represented in either
season. The CS/EN Admin table and optional detailed editions/players expose
these exact signed facts; all reads are explicitly requested, not recurring
or automatically published World Events.

## Proof boundary

Fast pr-critical synthetic-contract tests reject forged champion, malformed
field, unknown identity and foreign Run/Branch; cover empty/incomplete years
and two-season comparisons. The real HTTP/SQLite acceptance extends the
existing prior-season announcement and post-season authentic tournament
through another actual Season Transition: 0 confirmed S1 Editions vs one
S2 Edition, actual winner/runner-up/national points, Admin/Viewer parity,
negative incomplete S3, restart and immutable source authenticity.
The existing Native Tour browser W52/W61/W80, complete Tour HTTP/SQLite
replay/rollback and original signed Season Transition tests still run
in their dedicated CI workflows on the same final commit.

**Remaining:** this is the compact bounded native Tour summary only. Full
Master v85 notifications, record catalog/holder history, arbitrary Saved
Views, intake, numeric Health, correction authority, Full Simulation and the
reference 50×61 internal-release gate remain unsupported. Do not claim
pre-alpha release from this PR.
