# Authoritative Player Lifecycle Week State V1

This is an implemented technical contract, not a new product decision. For the
supported ordinary same-season Week Transition, roster/lifecycle authority is
Run/Branch-owned and server-derived. Weekly development, Form regression,
fatigue recovery and health healing remain **OPEN blockers**. Season Transition
is unsupported here.

`player_lifecycle_week_state.v1` is an immutable Run/Branch/week snapshot. It
preserves player and birth identity, current age, status, retirement effective
week, authoritative Tour-entry week, tie-break identity/provenance, origin,
initial-world fingerprint, predecessor fingerprint and a stable fingerprint. It
does not duplicate sporting attributes.

Week 1 is bootstrapped during initial-world adoption solely from owned
`InitialWorldState`, never live global player JSON. Prospects are not generated;
missing authoritative owned lifecycle input fails closed.

Birthdays compare `birth_year_week` with the canonical FAX Year Week obtained
from the target Season Week through `season_week_to_year_week`; the two week
coordinates are never treated as interchangeable. Initial age is the number of
completed FAX years at the Week-1 calendar position (2000 / Year Week 37 for the
first season), derived from birth year and birth Year Week rather than the legacy
coarse season-start age. Initial-pool generation preserves its sampled starting
age by deriving birth year after its branch-scoped birth-week draw.

Existing `run_prospects` are Run-scoped rather than Branch-owned. A row matching
the target calendar/season week therefore blocks transition before lifecycle
staging with an explicit missing-source-bridge error; this slice neither consumes
that row nor invents prospect generation or Tour-entry AI.

The existing `AuthoritativeWeekTransitionRunner` remains the sole
`BEGIN IMMEDIATE` owner. It validates predecessor lifecycle, stages target state,
applies target-week birthdays and age-46 retirement, derives the ranking roster,
and exactly compares the temporary `RankingTransitionAuthority.players` copy.
Ranking staging/publication, world clock, event, receipt and lifecycle commit or
roll back together. Preview uses this writer and rolls back. Retry validates the
persisted lifecycle fingerprint, preventing double aging.

Lifecycle history is stored in its own `player_lifecycle` Saved Revision
component, not `ranking_revision_state`. Restore compares the live history with
the current saved component before replacing it. Older revisions without this
component remain compatible, but cannot silently discard live uncaptured state.
