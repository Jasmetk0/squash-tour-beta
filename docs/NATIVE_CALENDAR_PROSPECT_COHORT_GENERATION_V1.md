# Saved World native Run-calendar prospect cohort generation v1

This slice creates a complete **deterministic generation pipeline** for future
native prospect intake. It does not migrate old 61-week seeds or change a
legacy Saved Revision.

### Source and calendar authority

`POST /admin/players/runs/{run_id}/branches/{branch_id}/intake/native-calendar/preview`
loads the Run's hash-verified Saved clock, the immutable Saved HEAD's World Package
and the exact live Package state, rejecting mismatches before deriving country
population/rating inputs. A branch with an unsaved World edit cannot produce
an authoritative cohort review. The package id is bound to the Run's world.

The review is deterministic for the same source, Run, input and W/O. It uses
the Run's exact W weeks, season start, start year and horizon, including seasons
with Season Week 1 in the following calendar year. Each individual is born in
the target Run Year Week **15 calendar years earlier**. Weighted weekly allocation
conserves the full season target; country weights use historical population,
squash popularity and access through the existing country model.

### Prepared, non-authoritative player profiles

Every planned prospect receives a deterministic Run-scoped identity and all 57
canonical initial attributes, potential/development seed evidence and source
provenance; each profile is verified against the existing canonical sporting
profile model. The review returns only counts, sample IDs and fingerprints,
not the hidden attributes. Seed/policy identifiers are distinct from historical
`weekly_15yo_cohort_v1` to avoid interpreting 61-week historical records as W52/W80.

The source record digest binds the exact complete `RunProspectRecord` rows.
World-country content fingerprint excludes Branch identity so multiple
branches can see the same underlying world-derived deterministic source.

### Limitations and safety

The preview **does not write** the Run-scoped prospect source, mutate a
Working Draft, Save or activate a player. The review explicitly returns
`materialization_supported=false` and `native_tour_activation_supported=false`.

Future explicit commit needs revalidation of the review within one SQLite writer
transaction (Run clock, Saved HEAD, live Package source, conflicting shared
prospects and any activated lifecycle identities), followed by an explicit
manual source Save. Subsequent native target-week lifecycle + 57-attribute
sporting + Health + ranking + Entry + replay is still required; no existing
Tour intake guard was removed.

Fast CI tests exercise full real HTTP/SQLite Saved World W52/O1, W52/O35,
W61/O37 and W80/O15 generation, 57-attribute cross-section evidence,
preview idempotence/restart, zero read-side writes, forged Saved clock and
foreign source rejection, plus separation from historical seed versions.
