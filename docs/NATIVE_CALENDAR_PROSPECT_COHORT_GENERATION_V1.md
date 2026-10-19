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

The preview **does not write** any source, Working Draft, Saved history
or Tour state. The separate
`POST .../intake/native-calendar/materialize` command requires the exact
review fingerprint, current Saved HEAD, explicit confirmation and audit reason.
Inside one `BEGIN IMMEDIATE` SQLite transaction it rechecks the full
Saved Run clock, Branch permission/HEAD, saved-versus-live World Package,
original shared prospect-source fingerprint, InitialWorld identities and
existing/activated prospect conflicts before inserting the exact reviewed
57-attribute records. This is an atomic Run-scoped source write, **not**
lifecycle activation, and it never automatically saves a revision.

A later manual `prospect-source/save` creates immutable Saved evidence.
Until then a further preview/confirmation on the same Branch fails closed
because its shared live source no longer matches Saved HEAD. Retry with an
outdated review cannot duplicate, rewrite or silently mix generations.
After Save an identical confirmed review is idempotent, while incompatible
review policies/conflicts require a separate explicit resolution.

A shared Run prospect source could otherwise invalidate a different Branch's
immutable Saved HEAD. Until coordinated multi-Branch confirmation is
implemented, materialization refuses a Run that has **any sibling Branch**
inside the same SQLite transaction. Preview remains read-only and explicitly
returns `materialization_supported=false` with the exact blocker code.
The restriction applies equally to every Branch; it does not invent an
Official/Main Branch privilege. A real two-Branch HTTP/SQLite regression
proves that the rejected command changes no rows or Saved history.

The response still declares `native_tour_activation_supported=false`.
Subsequent native target-week lifecycle + 57-attribute sporting + Health +
ranking + Entry + replay is required; no Tour intake guard was removed.

Fast CI tests exercise full real HTTP/SQLite Saved World W52/O1, W52/O35,
W61/O37 and W80/O15 generation, 57-attribute cross-section evidence,
preview idempotence/restart, zero read-side writes, forged Saved clock and
foreign source rejection, plus separation from historical seed versions.
