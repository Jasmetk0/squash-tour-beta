# Turn Pro lifecycle kernel (Master v87) — slices 1–4

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

## Slice 3 — pre-alpha player-AI model (`turn_pro_model.v1`)

Owner decisions (Master v87, pre-alpha): Turn Pro = joining the Run's professional
association; no age condition; a weekly chance driven by age, strength relative
to Tour Players and opportunity.

- `TurnProModelPolicy` is versioned and fingerprinted. The provisional default
  `pre-alpha-turn-pro.v1` uses annual bases by completed age 15→22+ of
  0.05/0.20/0.40/0.55/0.65/0.75/0.85/0.95, a readiness hazard multiplier
  `exp(2.0 × (readiness − 0.3))` and ×1.5 for a home opportunity.
- `weekly_turn_pro_chance` converts the annual chance with the Run's W, so W52 and
  W61 produce the same rate per year of age.
- `turn_pro_draw` is one hash-derived uniform per (seed, Run, Branch, player,
  week): order-independent and unaffected by which other players are evaluated.
- `decide_turn_pro` validates candidates against the completed week's lifecycle
  and returns `PlayerTurnProDecision`s ready for `advance_calendar_lifecycle`.

Synthetic-cohort calibration with the default (3,000 players, W52; W61 matches):

| Readiness | Median age | Before 16 | Before 19 | Before 22 | Latest |
|---|---|---|---|---|---|
| 0.0 (weak) | 18.6 | 3 % | 58 % | 96.2 % | 24.6 |
| 0.3 (neutral) | 17.8 | 6 % | 79 % | 99.7 % | 23.0 |
| 0.9 (strong) | 16.7 | 18 % | 99 % | 100 % | 20.0 |

The caller must still supply `readiness` and `home_opportunity` from information
known through the end of the completed week; that wiring is the next slice.

## Slice 4 — native Week Transition runs and records Turn Pro

- Under the v87 policy, the native Week Transition preview (`_turn_pro_week`)
  runs `decide_turn_pro` on the completed week's lifecycle and sporting
  checkpoint with the transition command seed. Strength is the current
  provisional OVR; readiness compares a prospect with active Tour Players and,
  while a Run has none, with the rest of the active population (never itself).
  `home_opportunity` is always false for now: native Editions carry no host
  country yet.
- `CalendarTourTransition` records `turn_pro_decisions` and the exact
  `turn_pro_model` policy. Both are omitted when absent, so historical
  transitions keep their bytes; decisions must be effective at the transition's
  own target week, in canonical player order, and require the model policy.
- `_lifecycle_history`, the Saved lifecycle-history check and `verify_tour`'s
  ranking replay rebuild the v87 lifecycle from the original World, actual
  applications and the recorded decisions. Recorded decisions in a Run without
  the v87 World policy are rejected.
- Not yet supported under v87, and rejected explicitly instead of silently
  skipping Turn Pro: the native birth (prospect intake) Week Transition and
  native fork continuation.
- **Limitation:** replay checks that the recorded decisions are consistent with
  the lifecycle, but does not re-run the model to prove that each decision came
  from the stored inputs.

## Slice 5: selecting v87 and opening professionals

- A new Run selects the rule through the existing calendar population adoption
  request: `lifecycle_policy.tour_entry_rule = "turn_pro.v87"` (HTTP
  `POST .../initial-world/calendar-adoption/preview` and confirm). Requests
  without it keep the historical policy and identical bytes.
- Under v87 the adopted `CalendarInitialWorldState` must carry
  `initial_turn_pro` (`initial_turn_pro.v1`): the exact model policy, the
  generation seed and the canonical ids of players who had already turned pro
  before opening Week 1. It is omitted for every other policy and is
  recomputed and compared on every load, so a stored opening set cannot drift.
- **PROVISIONAL retrospective model:** the opening population has a simulated
  history before Run start, so the same pre-alpha model is integrated from age
  15 to opening Week 1. With constant readiness, `W` weekly chances compound to
  exactly `1 - exp(-cumulative annual hazard)`. Readiness compares the player's
  current ability with the rest of the opening population (no earlier Tour
  Players exist); home opportunities are not modelled before the Run.
- The draw and the opening tie-break token are keyed by Run and player, not by
  Branch: pre-Run history is shared by every fork, which keeps exactly the same
  opening professionals.
- The bootstrap lifecycle represents them with
  `CalendarInitialProfessionalIdentity` (Tour entry = opening Week 1, Run-keyed
  token, v87 policy only). Every other identity keeps its population-only bytes.
  Opening professionals may apply from Week 1, are the readiness reference for
  the first Week Transition and enter the ranking roster published at Week 2.

## Not implemented (next slices)

- The public World Event and Viewer news for Turn Pro.
- Host country on native Editions, so the home opportunity can be derived.
- Turn Pro in the birth transition and native forks; model re-run in replay.
- HTTP/SQLite proof of the full v87 path (adoption → sporting initialization →
  applications → Week Transition with Turn Pro → Save/verify). Adoption, Save,
  restart and fork of the opening professionals are proven over HTTP/SQLite.
- `verify_tour` Turn Pro replay with the lifecycle as input.
