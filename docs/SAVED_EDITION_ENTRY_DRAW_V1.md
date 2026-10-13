# Saved Revision Edition Entry & Draw v1 — 13 October 2026

This coherent read-only PR follows merged #1418 Calendar→Edition UI and does
not change its routing, gameplay, generation, AI, match simulation or Save flow.

## Historical authority

- The exact `/admin/runs/{run}/branches/{selected}/tour/editions/{event}`
  route still requires `revision_id` and `season_index`.
- Existing `RunSavedRevisionHistoryService.get_revision` proves Selected Branch
  reachability. All components are loaded from the SAME immutable payload;
  `load_saved_simulation_slot_component` uses the **original owning Branch**
  of shared pre-fork history, never the current Viewer official branch.
- Canonical `resolve_viewer_tournament_entry_field` returns the effective
  latest stored field version (direct main, qualification, alternates,
  withdrawals, entry capacity and BYEs).
- Canonical `resolve_viewer_tournament_draw` returns the effective draw
  revision (main first-round positions including seeds, Q/LL placeholders
  and BYEs, and independently named qualification sections).
  Compatibility preserves a genuine original v1 qualification bracket.
- Both are optional when missing. Existing pure Calendar-only Saved Editions
  remain readable; never infer historical applicants/draw from published result.
  A present wrong-owner or orphan Draw/Draw Revision fails closed with 409.
- Backend response adds nullable `entry_field` and `draw` to the existing
  versioned Edition read; published results and other endpoint behavior stay
  unchanged. TS guards verify exact origin branch, event, bracket positions,
  uniqueness and Slot integrity.

## UI behavior

- Entries & participants shows the real historical Entry Field, with four
  separate player lists, capacity, BYE and version. Published result players
  are clearly labeled as *separate result evidence*, not inferred entries.
- Draw/groups shows the initial round from the real saved effective Draw:
  slots, seeds, direct/bye/qualifier/LL placeholders. Qualification sections
  are shown only from saved authority, with the Draw-only phase switch.
- Published match results remain visibly separate from Draw; they do not
  create unrecorded placement rounds, match times or scheduling claims.
- Result/schedule sections continue to use verified existing publication,
  without invented time slots or historical lifecycle status.
- No Data→Live fallback, no modal branch activation, no implicit Save.

## Verification gates

Focused Python application tests for missing/foreign/orphan authorities,
Vitest for legitimate and forged scoped response and rendered BYE/seed
slots, backend compile & frontend build. Reuse the real 64-player Chromium
Saved Replay acceptance, now checking actual canonical saved Entry Field and
Draw both before/after SQLite backend restart.

Still not supported: a completed topological bracket for later rounds from
first-round slots alone, a full historical match-by-match schedule or a
historical commitments/audit log separate from Entry Field. Those need their
own persisted authority slices and tests.
