# Actual canonical 57-attribute knockout inputs — implementation contract

Base `buuk`: `dd1cc6ecb8a9ef348c843b0b461d62fc0c2c7416`, after owner merge #1528.
No open PR at task start. Master remains v85; no new product calibration is decided.

## Usable behavior

New plays use `calendar_opening_knockout.v4`. Before play, Admin may preview four
57-attribute records from the exact Saved population and inspect every value in
CS/EN controls. Preview is read-only, checks HEAD/population/entrant scope and
creates no sporting state, Saved revision or match. Changing selection/HEAD clears
it; late A→B→A responses and unmounted results are ignored. During play, the server
recreates exactly the same deterministic source, which is stored with the result.
After Save/reload, Admin shows the frozen played source instead of recomputing it.

Each source retains the original population player facts, source generation
fingerprint, potential, exact `PlayerSportingRecord` catalogue and historically
frozen bootstrap/projection policies. This reuses the existing deterministic
7→57 bootstrap coefficients/jitter; no extra random calls, country DNA or fake
prestart/annual development are introduced. The conversion was extracted into a
pure domain function without changing legacy bootstrap JSON or fingerprints.

Every actual MatchEngine context is built using the existing
`CanonicalMatchInputProjectionPolicy` and `project_player`. All 57 values are
retained in each participant projection; projected engine values and independent
form/sharpness/fatigue modifiers are consumed by the engine. A new v3 match anchor
binds the full canonical projection, optional Health snapshot and actual context
to the rally log. The parser rebuilds source records, projections and context,
rejecting altered catalogue values, calibration, source scope or detached anchors.

Both semifinals still read one frozen slot checkpoint. Finalists use their
post-semifinal form/load with unchanged attributes. Initial canonical source and
terminal form/load are distinct facts, not a claim that every player remains at
initial form. Existing points/Save, Health corrections, horizon extension,
restore and restart retain the whole evidence atomically in the existing match
component. No parallel mutable canonical store is introduced.

## Boundaries

This is operation-owned input for the four entrants. It does **not** create a
world-wide weekly sporting owner or automatically initialize all other players.
The current population generator still starts with seven calibrated values; the
canonical bootstrap is provisional, not the final historical-cohort generator or
an empirical realism result. The rally engine still uses its explicit 57→seven
compatibility projection, not a new native 57-dimensional strength formula.
Numeric Health, recovery, annual development, actual Tour entry, Official ranking
publication and calendar Week/Season/Full Simulation remain incomplete. Existing
legacy and native fork guards remain. No legacy RankingWeek is manufactured.

Historical v1/v2/v3 omit all new optional fields and keep original schemas, bytes,
hashes and replay semantics. Their frozen players are not retroactively upgraded.
Shared legacy bootstrap retains its original guard against calendar population;
only the explicit versioned knockout input adopts current source facts here.
Owner alone merges; this is not a completed pre-alpha release.

## Verification

- Real W52/W80 preview→play→manual Save→cold restart verifies that the preview
  source is byte-identical to the played source and all six participant inputs
  carry 57 attributes. Database dumps prove preview/repeat are read-only.
- Pure checks cover actual engine projection (changing canonical Technical values
  changes projected technique), simultaneity/order independence and semantic
  corruption even after outer rehash. Existing v1/v2/v3 replay tests remain.
- Legacy bootstrap JSON/hash were directly compared to the original merged
  function and pinned as regression evidence; v3 payload/hash were compared with
  the original parser. No persisted history was rewritten/re-signed.
- Real Health/point/correction/extension/restore flows exercise v4 with Health;
  direct existing knockout API regression also checks v4 without Health.
- Frontend tests mock HTTP only and cover preview display, stale HEAD/A→B→A,
  frozen source and response contracts. Build and the existing real Chromium
  acceptance are separate required gates. Chromium opens 57-row tables, proves
  no play/Save on preview, and verifies actual played/frozen source through the
  existing Health/points/extension/reload flow.
- Exact final-head CI and final local results are recorded in the PR body.
