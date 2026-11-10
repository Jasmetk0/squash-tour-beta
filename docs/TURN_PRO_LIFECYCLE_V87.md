# Turn Pro lifecycle kernel (Master v87) — domain slice 1

Master v87 (9.2) replaces the v57 Tour-entry trigger: a prospect becomes a
`Tour Player` through a separate **Turn Pro** event chosen by its player AI, and
only from that week may make a first MSA Tour application or receive a definitive
wild card. This slice implements the pure, deterministic domain kernel only.

## Implemented

- `PlayerLifecyclePolicy.tour_entry_rule`: `None` (historical v57 rule) or
  `"turn_pro.v87"`. `None` is omitted from serialization, so every existing
  policy, lifecycle snapshot and fingerprint keeps its exact bytes.
- `PlayerTurnProDecision` (`player_turn_pro_decision.v1`): Run/Branch, player,
  `effective_week` (RunWeekPosition), `decision_source="player_ai"`, the
  fingerprint of the pre-transition inputs it was made from, and provenance. Its
  NR tie-break token is domain-separated from application tokens.
- `advance_calendar_lifecycle(..., turn_pro=())` and `calendar_lifecycle_history`:
  under v87 the decision effective at the target week sets `tour_entry_week` to
  that week (effective from the week start, so a same-week application is valid).
  Applications never create Entry; an application before the player's Turn Pro
  week is rejected. Under the historical rule any Turn Pro decision is rejected.
- Fail-closed validation: one decision per player, own Run/Branch, compatible Run
  clock, player present in the predecessor lifecycle (a newborn cannot turn pro in
  its birth week), not retired, never rewrites a recorded entry, never applied late.
- `require_professional_for_entry(lifecycle, player_id, week)`: the v87 gate for a
  first application or definitive wild card; a no-op under the historical rule.
- The legacy 61-week `PlayerLifecycleWeekState` refuses a v87 policy rather than
  silently following the old trigger.

## Not implemented (next slices)

- No runtime can select the v87 policy yet: every production constructor builds
  the historical policy. Nothing changes for existing or new Runs.
- Persistence and Saved capture/restore of Turn Pro decisions, and the public
  World Event.
- Player-AI decision model (the formula is an open Master item).
- Native Tour ranking roster: `calendar_tour.ranking_players` still derives
  entrants from applications; under v87 it must come from Turn Pro (0 points,
  `NR` until the next snapshot, provisional Master 9.2).
- Calling `require_professional_for_entry` from application validation and
  definitive wild-card assignment.
- Initial-world players who are already professional at Run start (the native v2
  bootstrap creates no Tour entry; a Turn Pro decision cannot be effective at the
  opening week).
