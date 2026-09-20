# Canonical prospect sporting-profile kernel v1

## Purpose

This slice introduces the first canonical hidden sporting-profile kernel for generated
prospects. It converts already-owned deterministic prospect seeds into a complete
57-attribute `0..200` profile plus potential identity and development timing.

The kernel is deliberately pure and does **not** itself mutate a Run or Branch.

## Authority boundary

Birth-week visibility and sporting readiness remain separate concepts.

- `player_lifecycle_week_state` remains the authority for whether a prospect exists
  historically and is visible as a pre-Tour Draft.
- A generated prospect may have hidden canonical profile truth without belonging to
  `player_sporting_week_state`.
- Merely becoming visible at the 15th-birthday week does not opt the prospect into
  normal weekly player development, junior match simulation, Official Ranking or Tour
  competition.
- A later explicit operation must adopt the prepared profile into authoritative
  sporting state before an operation that requires simulation-valid sporting truth.
- Formal Tour entry remains a separate later lifecycle mutation.

This preserves the post-#848 rule that public visibility comes from lifecycle history,
not from pregeneration storage.

## Profile contract

`prospect_sporting_profile.v1` stores:

- all 57 canonical attributes in catalogue order;
- one hidden `potential_ovr`, never lower than generated current OVR;
- a deterministic potential identity and provenance;
- development timing (`Early Bloomer`, `Standard`, or `Late Bloomer`);
- the exact versioned profile policy identity/fingerprint;
- SHA-256 digests of the hidden source seeds rather than the raw seeds.

The raw prospect seeds are therefore not copied into the materialized profile payload.

## Calibration

`prospect-sporting-profile.provisional.v1` is a **technical pre-alpha calibration**,
not new product canon. It intentionally uses bounded deterministic generation with a
shared base ability, group-level variation and attribute-level variation so a player
profile is internally correlated rather than 57 unrelated random numbers.

All numeric ranges remain tuneable. Changing them later requires a new policy identity;
old materialized profile fingerprints must keep their historical meaning.

## Persistence integration

New `weekly_15yo_cohort_v1` materialization now derives this profile at the same
deterministic boundary as the prospect seeds and persists the complete canonical
payload inside the Run-scoped prospect metadata before lifecycle activation.

The stored `profile_json` keeps the full `prospect_sporting_profile.v1` payload
and its fingerprint. `development_json` and `potential_json` carry redundant
fingerprint-bound summaries so a later consumer can fail closed if the persisted
sections disagree. The materialization-policy fingerprint now also binds the exact
sporting-profile policy id and fingerprint.

Existing historical placeholder rows are not silently rewritten. Re-materializing a
different unused row remains an explicit conflict/overwrite operation, while #848's
lifecycle-activated metadata immutability prevents overwrite once the identity is
historically visible.

## Still deferred

Persistence alone intentionally does not yet:

- place the new birth-week prospect into the target `player_sporting_week_state`;
- create a formal Tour-entry event or Official Ranking membership;
- expose hidden attributes, potential or seeds to Viewer;
- invent the still-placeholder broader hidden trait/profile systems;
- add junior competition or Next Gen ranking systems.

This missing sporting insertion is not a decision to keep visible prospects outside
sporting history. Master Week Transition performs completed-week development first
and only then creates the new 15-year-old prospect. The next implementation boundary
must therefore append the persisted canonical profile to the **target-week** sporting
snapshot after predecessor development/between-week updates. The prospect remains
pre-Tour (`tour_entry_week=None`); its first ordinary weekly development can only be
evaluated after it has actually existed through a completed week.
