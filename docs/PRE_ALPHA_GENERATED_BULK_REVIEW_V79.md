# F79-05 — separate action selection, bulk preview and one session Undo

**Product authority:** Master v79 §9.7. Follow-up to #1389 configurable source
columns; the first independent bulk action slice, **not** a subset Add or a
new authoritative player-edition API.

## User workflow

1. Generate a first-season InitialWorld preview from a saved Run World.
2. Select individual players for **Action** independently from the **Keep**
   column. Select current 50-player page, all current search/country/tier
   matches, remove current page or clear. Sorting and pagination never discard
   selection; the count distinguishes selected from total and filtered rows.
   The selection resets on a different actual reviewed preview.
3. Choose one of the **nine supported real numeric source fields**, and enter
   one integer value in `1..99`. A pure browser-side "before/after"
   table compares values for all affected IDs, with unchanged-count and
   conflict diagnostics. This is a *proposal*, not authoritative player state.
4. Explicitly **Stage reviewed bulk locks**. The staged field-lock list is
   local/pending, sorted and bounded, and disables Adopt through the existing
   `locksDirty` gate. A rejected or mismatched value does not change any
   server or local verified review. Staged edits can be discarded.
5. Explicitly **Verify staged bulk changes on server**, using the existing
   production Run-scoped preview endpoint and authenticated Keep/V2 edit
   lineage. The browser sends only the typed source request/field locks; the
   server generates and validates all changed players. The client rechecks
   provenance, target and every approved lock via `verifiedInitialWorldPreview`.
6. A **one-step session Undo** is available after successful bulk verification.
   It restores the exact preceding *already server-verified* preview and its
   previously approved lock list, within unchanged Run/Branch/HEAD/Draft/World,
   without writing to the Run or sending trusted player values to the backend.
   Undo is not persistent and is invalidated by another preview/edit/reload.
   Re-approval for Adopt is always required.

## Safety

- Action selection is never synonymous with Keep, display filters, input group
  constraints, preview field locks or the final Adopt selection.
- Current initial-world Adopt remains **whole-batch**, requires clean current
  Saved HEAD / Draft / World snapshot and user approval; manual Save remains
  independent. This slice does **not** expose Add Selected or mutate a saved
  world by replacing a subset.
- A missing field, identity collision, stale selected ID, malformed value,
  contradictory current/potential relationship or lock-budget overflow is a
  conflict. The production generator may reject additional constraints that
  cannot be inferred from the displayed legacy subset; its decision wins.
- No new database schema or stored source-model fields; table preferences
  remain browser-only under #1389.
- This is session UI state. Exact historical proposal read/revalidate from
  #1387 remains separate and no migration of historical fingerprinted requests
  is needed.

## Acceptance evidence

Unit tests cover batch plan source facts, sorting, identity validity, missing
fields, conflict bounds and nonmutation. Inspector component tests cover
selection crossing pages and filters, Keep independence, and 50-row paging.
Run Admin component tests cover before/after, staging, new server preview,
exact lock values, Undo and unchanged Adopt/Save boundaries. The existing
1,000-player production-browser acceptance checks that this frontend change
does not regress the established whole-cohort, SQLite and ranking flow; it is
not a dedicated end-to-end browser simulation of every bulk action. Backend
PR-critical tests may be skipped for frontend-only changes per test policy.

**Not yet built:** multi-field batch operations, arbitrary overlapping
population groups, a persistent multi-step Undo history, and safely appending
selected individuals to a *saved* InitialWorld. Append requires its own
authoritative Run-owned operation and collision rules rather than an alternate
meaning for existing Adopt.
