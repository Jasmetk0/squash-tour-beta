# F79-04 (first UI slice) — configurable generated-player columns

**Authority:** Master v79 §9.7. Implement the inspectable table-column layer
without changing the authoritative initial-world generation, session Keep,
field edit validation or Adopt/Save behavior.

## What the Admin can do

- Pick any supported real source-model columns from the table's "Choose table
  columns" panel; player name and stable player ID stay pinned, and session Keep
  is a separate checkbox/control, not a display column choice.
- Display country, initial age, source current ability 1–99, source potential
  ability 1–99, potential tier, career stage when available, and each of the
  seven source attributes when present in the actual returned player records.
- Show a visible `✎` marker for a value matching an approved field lock in
  the **reviewed server request**; show `✎ pending` when a local pending
  field edit differs from that approved lock. Expand a player's name-row
  details to see each field and its exact verified vs unsubmitted values.
- Remember the selection in the local browser `localStorage` under
  `squash-engine:generated-player-columns:v1`. An invalid/inaccessible
  preference falls back safely. The display preference is intentionally not
  part of the Saved Revision, Run/Branch data, proposal, player model, world
  package, fingerprint or server request. Other browsers do not share it.

The default columns are Name/ID, Country, Age, current/potential source ability,
Potential tier and Career stage (when available). OVR 0–200, Player Height and
Handedness are NOT displayed when absent from this engine/model. Session Keep,
pagination (50 rows), sort/search filters, overall full-cohort stats and Adopt
continue to apply to the full verified player batch regardless of visibility.
Changing a table column cannot select, edit or adopt a player.

## Exact limits

This PR implements the bounded **column configuration and verified/pending
field indicator** slice only. The separate Master v79 needs for selection
independent of Keep, before/after bulk diff, one-session Undo, safe subset Add
and an explicitly verified append contract are not implemented here. No
source-model attribute mutation is smuggled into the UI.

Test categories: component tests validate browser preference persistence,
invalid storage, full-cohort immutability, 1,000-player page stability and
markers; existing genuine browser acceptance ensures the original full-cohort
first-season flow still operates after the component change. Component tests
mock API boundaries and do not themselves establish a production backend
integration claim.
