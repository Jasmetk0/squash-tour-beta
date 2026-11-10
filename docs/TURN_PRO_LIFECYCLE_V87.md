# Turn Pro lifecycle kernel (Master v87) — slices 1–2

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

## Slice 2 — ranking roster and application gate

- `professional_ranking_players(lifecycle, before=..., retired=...)`: under v87
  the native Tour roster is every player whose Turn Pro week precedes the
  published week, even without any application; its NR tie-break token is the
  lifecycle Turn Pro token. A player who turned pro in the week being published
  is not inserted into that snapshot (provisional Master 9.2). It refuses a
  historical-policy lifecycle.
- `calculate_tour_ranking(..., lifecycle=...)` uses that roster only when the
  supplied lifecycle has the v87 policy; otherwise (and without a lifecycle) it
  keeps the historical application roster byte-for-byte. The Week Transition
  preview and the native final-season closure pass their lifecycle.
- Native `submit`: under v87 every selected player must already be a Tour Player
  at the Edition week (`require_professional_for_entry`), otherwise the whole
  batch is rejected before any write.
- `verify_tour` refuses to replay a v87 Run's Official rankings when it has the
  world, because it rebuilds rosters from applications. **Limitation:** when it is
  called without a world it cannot see the policy.
- Native Tour has no definitive wild-card writer; the legacy WC writers belong to
  the 61-week lifecycle, which refuses v87.

## Not implemented (next slices)

- No runtime can select the v87 policy yet: every production constructor builds
  the historical policy. Nothing changes for existing or new Runs.
- Persistence and Saved capture/restore of Turn Pro decisions, and the public
  World Event.
- Player-AI decision model (the formula is an open Master item).
- HTTP/SQLite proof of the gate and roster: impossible until a Run can select
  v87 and persist Turn Pro decisions (the lifecycle history currently receives
  no decisions, so under v87 nobody could apply — fail-closed, not usable).
- `verify_tour` Turn Pro replay with the lifecycle as input.
- Initial-world players who are already professional at Run start (the native v2
  bootstrap creates no Tour entry; a Turn Pro decision cannot be effective at the
  opening week).
