# Authoritative Player Lifecycle Week State V1

This is an implemented technical contract, not a new product decision. For the
supported ordinary same-season Week Transition, roster/lifecycle authority is
Run/Branch-owned and server-derived. Canonical weekly development, Form
regression, Sharpness decay and Fatigue recovery now live in the separate
sporting-state contract. Match-derived updates and health healing remain separate/open sporting concerns.
The same lifecycle progression is also used by the canonical Season Transition.

`player_lifecycle_week_state.v1` is an immutable Run/Branch/week snapshot. It
preserves player and birth identity, current age, status, retirement effective
week, authoritative Tour-entry week, tie-break identity/provenance, origin,
initial-world fingerprint, predecessor fingerprint and a stable fingerprint. It
does not duplicate sporting attributes.
Each snapshot also embeds the effective `PlayerLifecyclePolicy` identity,
automatic-retirement age and provenance. Age 46 is the Official Run default;
custom Runs may author another age, and validation/progression always use the
stored historical policy rather than a global engine constant.

Initial Week 1 is bootstrapped during initial-world adoption solely from owned
`InitialWorldState`, never live global player JSON. Later pregenerated Run prospects
are not part of that initial bootstrap; they are consumed only when their exact birth
week opens. Missing authoritative owned lifecycle input still fails closed.
An exact adoption retry atomically verifies or backfills Week 1 solely from its
already-owned `InitialWorldState`, so deletion or change of the global pool is
irrelevant. Restore of a legacy revision similarly backfills when its owned
Initial World and Week-1 ranking boundary make reconstruction unambiguous;
post-transition legacy state without lifecycle fails closed.

Birthdays compare `birth_year_week` with the canonical FAX Year Week obtained
from the target Season Week through `season_week_to_year_week`; the two week
coordinates are never treated as interchangeable. Initial age is the number of
completed FAX years at the Week-1 calendar position (2000 / Year Week 37 for the
first season), derived from birth year and birth Year Week rather than the legacy
coarse season-start age. Initial-pool generation preserves its sampled starting
age by deriving birth year after its branch-scoped birth-week draw.
Country allocation preserves `populationYear = birthYear` before individual
birth-week draws by aggregating each age bucket uniformly over all 61 possible
birth Year Weeks and resolving population for the resulting birth years. Absolute
season-start age weeks use the same calendar coordinates rather than completed
years, so birthdays after YW37 do not lose a FAX year.

Existing `run_prospects` are Run-scoped pregeneration records rather than
Branch-owned historical visibility. When a row matches the exact target
calendar/season birth week, Week/Season Transition validates its age/birth identity
and copies that stable player identity into the target branch lifecycle. The
resulting player is a pre-Tour Draft with `tour_entry_week=None`; its deterministic
ranking tie-break token is derived from stored prospect identity provenance. Earlier
lifecycle snapshots do not contain it. Once any branch lifecycle contains that
prospect identity, its Run-scoped pregeneration metadata becomes immutable through
the persistence/materialization boundary: idempotent identical writes remain valid,
but normal overwrite/delete cannot retroactively change public identity metadata.

Lifecycle remains the authority for identity, age, retirement and Tour-entry status,
while sporting state owns the simulation-valid sports core. For an ordinary supported
Week Transition, a birth-week Run prospect now enters **both** target lifecycle and
target sporting history atomically, but through separate validated projections of the
same Run-scoped source row. The sporting projection is accepted only when the
persisted canonical 57-attribute profile/development/potential evidence is internally
consistent; an older placeholder profile blocks that affected Week Transition instead
of inventing sporting values.

The target-week prospect still has `tour_entry_week=None`, so birth-week creation
does not create MSA Tour status, Official Ranking membership or tournament entry.
Completed-week sporting context remains exact over the predecessor sporting roster:
the newly created prospect did not exist during that completed week and therefore
receives no retroactive development or match count. Its first ordinary weekly
development can be evaluated only after it has existed through a completed week.
Season Transition parity for Week 61 → next-season Week 1 remains a separate follow-up.

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


## Branch-fork identity

Materialized ranking-bearing Branch forks now support the complete saved lifecycle
history. Source snapshots are validated first, then rebuilt with the target Branch id
and a newly chained target predecessor fingerprint. Sporting-independent lifecycle
facts and policy evidence are preserved exactly. The rebuilt chain is installed into
the target Branch and embedded in its target-owned materialized Saved Revision in the
same fork transaction.

The shared `source_initial_world_fingerprint` remains historical provenance to the
fork's shared origin; it is not rewritten into a fabricated target InitialWorld.
