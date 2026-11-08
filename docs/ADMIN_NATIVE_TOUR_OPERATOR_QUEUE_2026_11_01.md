# Native Tour Admin — source-scoped operator queue (1 November 2026)

## Why

The native Tour Admin already has explicit forms for submitting actual applicants,
approving the field, reviewing a draw, playing through the MatchEngine,
confirming results and manually Saving the Run/Branch. Its original interface
enumerates every Edition sequentially. In a reference FAX setup with 80 planned
World Tour Editions, the owner needs a bounded way to **find the correct
Edition controls** without accidentally inventing eligibility or silently
approving a stage.

This PR adds a CS/EN read-only **operator queue**, not another simulation
or persisted data owner. It sits above the existing real Edition forms on
`web/src/pages/CalendarTourPanel.tsx`.

## Authoritative inputs and boundaries

- Consumes only the **already fetched and validated** current `TourView`
  of the selected Run/Branch. It makes **no additional HTTP requests**,
  does not create a global Run/Package query, and never issues a mutation.
- Fails closed if the parent Run/Branch is different, Tour has no initialized
  week, Edition IDs are missing or duplicated, or scheduled weeks/fields
  are malformed. The queue never infers missing Editions from a FAX calendar
  manifest. Empty `state.editions` means **none present**, not 80 configured.
- Describes the actual Edition field/draw/result flags, optional group
  tie-case and observed match/result evidence. A descriptive stage is **not**
  proof that a player is eligible, a field/draw is Signed, a global slot is
  available, a checkpoint is satisfied or a result was published in Official
  Rankings. Only the underlying server Preview/execute/Save can establish
  these facts. It does not derive automatic tournament participation rules.
- When the parent view reports `saved=false`, the UI explicitly warns that
  stages may include unsaved Working Draft changes. A confirmed-result
  flag in that draft is not claimed to have been Saved.
- Shows current, past and future Editions relative to the actual native
  Season/Week; search by name/ID, filter by observed result status, and
  paginate in batches of 12. Preserves every Edition (including 80+).
- The in-page links target the existing exact native Edition form by
  positional DOM anchor. There is no browser navigation to a different
  Run/Branch; no URL is constructed from a user-provided Edition ID.
- Normal native approvals, manual Saved boundaries, Game Engine and
  full-simulation tasks remain unchanged. No new sporting rules or service
  contracts. #1711's Run Management **Entry timing coverage audit** is
  a different owner and is neither consumed nor modified here.

## Tests and proof limits

Pure tests cover 80 Editions, real status derivation, group ties, cross-season
period comparison, malformed IDs/periods, wrong Run/Branch and zero
Edition. React tests cover CS/EN, searching to Edition #80, bounded
pagination, exact anchor, filters, empty state and fail-closed UI.
The existing `CalendarTourPanel.test.tsx` regressions must also remain
green on the final PR head.

Frontend tests + TypeScript/Vite build do **not** prove 1,000 actual
players/80 playing Editions, real MatchEngine execution, an entire
season, 50-season endurance or Windows release functionality.
The separate native HTTP/SQLite Draft PRs #1713 and #1718 supply
different genuine integration evidence; the full
`docs/PRE_ALPHA_TEST_POLICY.md` remains the release gate.

All changes stay on one separate Draft PR; owner alone merges.
