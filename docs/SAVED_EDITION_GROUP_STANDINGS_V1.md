# Saved Edition Group Standings & Audited Tie Decisions v1 — 13 October 2026

A read-only Master v80 group table follow-up to merged PR #1422. No tournament
simulation, Ranking, RNG, scoring, Admin decision or Save path is changed.

## Exact authority

`GET /admin/runs/{run}/branches/{selected}/tour/editions/{event}?revision_id={revision}&season_index={n}`
now optionally returns `group_standings` on `run_saved_tour_edition.v1`.

- Same existing reachable immutable Saved Revision, including *original owning
  Branch* when the selected Branch descends from a pre-fork common ancestor.
- The snapshot's `simulation_slots` component passes existing **restore-grade
  semantic validation** before this projection. The loader already validates
  original group standings by replaying the real saved group result receipts,
  Group Match Schedule, rules and any audited tie decisions. The new projection
  additionally matches saved row's Run/Branch/event/command/fingerprint,
  predecessor group Match Schedule fingerprint, group and player counts.
- Only **completed** frozen `TournamentGroupStandingsAuthority` can supply
  positions, group points, W/L, played count, W/O, games and point totals.
  A planned fixture does not create a provisional or hypothetical table.
- For v2 standings, every stored Admin tie resolution must match exactly the
  frozen decisions referenced by the standings; the audit includes case hash,
  ordered player IDs and original reason. Missing, duplicate, foreign or forged
  tie decisions fail closed. V1 tables cannot gain retroactively invented
  Admin tie decisions.
- A present standings authority without the exact original Group Match
  Schedule is a conflict; ordinary knockout and unpublished group Editions
  without final tables continue to return `null`.
- No inferred "why ordered this way" for automatic tie-breaks: only explicit
  Admin decisions are displayed as such.

## Edition UI

In **Results**, group-based Editions show one final Group table per group:
ranking, actual group points, W/L, played, W/O for and against, games for/against,
and ball points for/against. Audited Admin ties appear underneath with ordered
players, exact stored reason and shortened case fingerprint. The existing
canonical match/result evidence and links remain separate, and default
knockout Edition routes are unchanged. CS/EN labels are supported.

## Verification

New PR-critical tests exercise real immutable domain `TournamentGroupStandingsBuilder`
receipts for played matches, a walkover, and an unresolved tie requiring an
explicit Admin decision; include missing, stale, foreign, duplicated and forged
provenance cases. Frontend guard and rendering tests ensure group points,
positions and reasons cannot be fabricated client-side. Existing Chromium Saved
Replay test verifies the previously supported regular tournament is unaffected.

**Not claimed:** a real end-to-end hybrid/group browser scenario; current real
browser fixture still covers regular knockout. A dedicated group/hybrid Save →
historical Saved Edition → standings/browser/restart test is a separate future
acceptance slice. Group seed/qualifying visual bracket and automatic tie-break
explanations also remain later work.
