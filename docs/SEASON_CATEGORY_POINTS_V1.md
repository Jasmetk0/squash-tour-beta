# Season Category Points V1 storage boundary

Season Category ranking points are authoritative persisted configuration keyed by
`(season, category)`. The current beta stores that registry at
`config/simulation/season_category_points.json`. This follows the existing
file-backed Season persistence boundary; it is not yet the future fully
Run-and-branch-scoped configuration store.

Legacy global and tournament-template points are compatibility inputs only when
initializing a Season's Category tables. New Tournament Editions copy their target
Season's table and never read those legacy sources directly. Persisted calendar
creation requires an explicitly initialized Season registry and fails without that
prerequisite; calendar building never initializes it as a side effect. Calendar
dry-run uses the identical in-memory initialization candidate and does not persist it.

Already persisted legacy Tournament Editions continue to load without migration or
snapshot rewriting. Qualification stage names are structurally valid, but this
slice supplies no Qualification values or additive scoring rules.
