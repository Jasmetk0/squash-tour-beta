# Calendar-owned player preview — v82

Base: `buuk` `643ee60868ee57cecfdc560e9079ac68f2bdda00`, after merged
#1496, #1497 and #1498. This is the next bounded migration slice, not a release.

## Usable outcome

The existing Run → Players → Generate page now offers a real read-only player
preview for custom saved clocks. It uses the selected Run's W, opening Year Week
and start year for birthdays, age and population cohorts. The Home link reaches
the same generator page. Default historical FAX geometry continues to use the
existing preview/Keep/edit/adopt/manual-Save flow unchanged. Explicit malformed
calendars fail closed instead of falling back to FAX.

For a custom clock, choose an already copied Run-owned World, seed, count and
optional age range. Inspect paged names, nationality, birth year/week, age,
current ability and potential. CS/EN labels explain the preview-only boundary.
Changing conditions or source context hides the old result; late responses are
discarded. There are no adoption, confirmation or Save controls in this slice.

## Version and authority

`POST /admin/players/runs/{run}/branches/{branch}/initial-pool/world-package/calendar-preview`
accepts `run_calendar_initial_pool_request.v2` (the endpoint supplies that default):

```json
{
  "world_package_id": "atp_earth",
  "seed": 802,
  "target_pool_size": 1000,
  "min_age": 18,
  "max_age": 25
}
```

The API also supports exact country quotas and independent Geographic/Travel
Region conditions. Those additional conditions are not yet exposed in the
custom-clock UI. Requests cannot supply a competing calendar, season, existing
profile, Keep session or v1 proposal. Invalid conditions are explained without
falling back to a different source.

One explicit SQLite read transaction verifies the selected Saved clock/hash and
captures the Run-owned package state from the same snapshot. Package content is
identified as `run_owned_working_state`; it is not falsely described as the exact
Saved package content. The response binds Run/Branch, calendar Saved revision,
calendar, package/country/generation fingerprints, request and preview hash.
Projection uses the copied snapshot, never current global source files.

`CalendarInitialPlayerPoolGenerator` reuses the production attribute/potential
kernel through small overridable birth/population/construction boundaries.
Legacy generator defaults, serialized fields, seeds and hash projections remain
unchanged. The separate `initial_pool_player.v2` DTO has mandatory versioned time
basis and validates the birthday/age/season relationship. It allows birth weeks
above 61 and signed birth years for a valid Run starting at year zero; no old
identity is converted. A v2 profile cannot be parsed as the old strict v1 DTO.
Its fingerprint covers its whole profile and time basis.

The initial population must have turned fifteen strictly before opening Week 1.
Opening-week fifteenth birthdays are excluded. For W=1 no age-15 birthday can
meet this condition: the default distribution begins at 16 and an explicit
age-15-only condition reports the impossibility. Birthday sampling and expected
birth-year aggregation take constant space in W, including very long valid years.
New v2 population weights condition the shared stage/age law on the actual age
range; legacy weighting remains historically unchanged.

Population resolution on the new calendar axis retains exact/nearest/default
source-year and estimated-share diagnostics. Country-rating source years and
exact/interpolated/fallback kinds are reported separately. Requests before or
after authored coverage use explicitly identified nearest observations. They do
not move the requested date, invent observations or extrapolate future ratings.
Old bounded population/rating entrypoints retain their original contracts.

## Verification and honest limits

Focused domain tests cover W1/2/7/52/61/80 and W=2,000,000,000, crossing offsets,
strict fifteenth-birthday boundaries, inverse age checks, invalid identities,
serialization, population fallback, and equal initial ability/potential for equal
age despite different year lengths. Existing v1 fixed preview/Keep hashes remain
unchanged on the tested Python 3.11 and 3.12 parent baselines.

Real HTTP/SQLite tests copy each actual FIFA Earth/ATP Earth package into W52
Runs and preview 1,000 players each. Other fixtures cover custom offset/year/
horizon, year zero, >61 birth weeks, restart, fork, damaged Saved proof, strict
requests, conditions/quotas, complete database non-mutation and preserved Saved
hashes. Component tests cover scope validation, stale async responses, paging,
CS/EN and the absence of adoption controls. The existing Shell Chromium
acceptance is extended with a real World copy/explicit Save/custom-W52
1,000-player preview, paging, invalidation and unchanged Saved revision.

The response explicitly says `preview_only=true`, `adoption_supported=false`.
v1 generation/adoption/sporting guards are NOT relaxed. v2 Keep/edit/saved
proposals, lifecycle/bootstrap, annual development, rankings and Week/Season/Full
Simulation remain migration work. This proves initial calendar-aware sampling,
not W52 sporting execution, calibrated realism or a complete pre-alpha.

Observed inherited float differences across Python versions are not silently
rounded away. The preview records the Python runtime in its hash; cross-runtime
regeneration equivalence remains explicitly unguaranteed. Stored v1 proposal
inspection/replay continues to read original data without new generation.

## Next coherent work

Version the actual player identity/bootstrap/lifecycle and Run-local position
contract before accepting these profiles into authoritative state. Inspect
`application/initial_world.py`, `domain/players/lifecycle.py`,
`infrastructure/db/player_lifecycle_state.py` and the still-legacy `RankingWeek`
contract together. Preserve old payloads/hashes and reject incompatible imported
birthdays. Annual sporting policy/versioning and ranking validity must follow
before lifting sporting execution guards. Do not simply loosen RankingWeek's
61-week bound or feed a new W into unversioned old state.
