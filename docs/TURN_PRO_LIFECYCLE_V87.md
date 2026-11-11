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

## Slice 6: first full v87 HTTP/SQLite path

- `tests/api/test_calendar_tour_turn_pro_v87_flow.py` (smoke) runs the real
  production stack: v87 population adoption with opening professionals →
  health → sporting checkpoint → Tour initialize → Edition → Week Transitions
  that run and record the model → a prospect turns pro, applies in its Turn Pro
  week, plays real matches and is ranked → a remaining prospect's application is
  refused without writes → Save, exact replay, Saved hash, restart and an
  idempotent retry verified from the recorded decisions.
- The test injects a recorded, test-only eager calibration for two transitions
  so a weekly decision happens within the fixture's few weeks; the following
  transition records the default calibration.
- Fix: a Tour without a stored native lifecycle (pre-v4 authority) no longer
  refuses every v87 application; the gate uses the same derived lifecycle
  (World + applications + recorded Turn Pro) as the ranking roster, at the
  application week.
- **Known gap:** weeks advanced before Tour initialization (the pre-Tour
  sporting continuation) record no Turn Pro decisions, so the model does not
  run in those preparation weeks. Native competition and birth weeks still
  reject v87 explicitly.

## Slice 7: host country and home opportunity

- `CalendarTourEdition.host_country_code` (optional ISO-3 style uppercase code)
  is accepted by `create-edition`; it is omitted when absent, so every earlier
  Edition keeps its bytes and fingerprint.
- At a v87 Week Transition into `target`, a prospect has a home opportunity when
  some Edition hosted in the prospect's country was announced before `target`
  (an announcement that becomes public at this very transition is not yet known)
  and is played at or after `target`. The player's country comes from the
  original InitialWorld. Opportunity multiplies the annual hazard by the
  recorded model's `home_opportunity_multiplier`.
- **PROVISIONAL:** any public upcoming home Edition counts, regardless of its
  size, level or distance in weeks; "small event" and look-ahead windows are
  calibration for later versions.
- Newborn prospects are not in the InitialWorld; birth weeks still reject v87.

## Slice 8: public Turn Pro World Event

- When a v87 Week Transition records decisions, its public event gains
  `turned_pro_player_ids` (sorted). It is omitted when nobody turned pro, so
  every earlier public event keeps its bytes. The model's chance, draw and
  source fingerprint stay Admin-only evidence in the transition.
- `verify_tour` recomputes the expected public event from the recorded
  decisions. Viewer's existing `public_events` exposes the news from the
  transition's target week only (no earlier historical week shows it).
- Not yet: names or richer news text in the Viewer UI; Notification Center
  items for followed players (Master v85) are a separate system.

## Slice 9: native birth/competition weeks, model re-run on replay

- `prepare_native_tour_week` (shared by execution and Signed replay) runs the
  model under v87 from the Signed lifecycle and sporting checkpoint of the
  completed week, with home opportunities from the InitialWorld countries and
  earlier signed birth events. Decisions feed the lifecycle advance (births are
  added afterwards, so a newborn cannot turn pro in its own birth week). The
  impact records `turn_pro_decisions` and `turn_pro_model` only under v87.
- Signed replay (`verify_native_tour` and native competition verification)
  passes the *recorded* model back in, so every native v87 decision is
  re-derived and must match; a later change of the default calibration cannot
  rewrite or break history. This closes the "model re-run" gap for native weeks.
- `verify_calendar_native_birth_history` accepts Signed Turn Pro entries under
  v87 (entry at that week, Turn Pro token, not previously entered) and still
  rebuilds every other lifecycle fact; the receipt replay above proves them.
- The service no longer rejects v87 in native birth weeks. Native forks still
  reject v87 explicitly.

## Slice 10: native fork continuation

- The native fork reducer runs the same pure `native_turn_pro_decisions` step
  as an original native week: countries from the InitialWorld and the Signed
  prospect source, strength from the fork's competition view of the completed
  week. Decisions belong to the fork Branch, are recorded with the model in the
  transition and impact, and appear in its public event.
- Fork replay sets `turn_pro_model` from each confirmed command's recorded
  result, so the fork's decisions are re-derived exactly after a restart even
  when the default calibration differs.
- Pre-fork Turn Pro entries are copied into the fork baseline with their
  original Branch tokens; the fork never re-verifies them as its own.

## Slice 11: v87 as the Admin default for new Runs

- Owner direction (11 November 2026, recommended option accepted by "continue"):
  new Runs created in Admin use the Master v87 Turn Pro rule by default. The
  population adoption controls show a "Tour entry" choice defaulting to Turn Pro
  (v87) and keep the historical first-application rule as an explicit option.
- The Admin request then carries `admin-calendar-population-turn-pro.v87`
  (`tour_entry_rule = "turn_pro.v87"`, retirement age 46). The historical
  choice omits the policy, exactly as before. The HTTP API default is unchanged,
  so existing Runs, scripts and tests keep their behavior and bytes.
- The review response adds `opening_professional_count` only under v87; the UI
  requires it exactly for a v87 review and shows "professionals already at Run
  start: N / total".
- Reversible: changing the UI default does not reinterpret any adopted World.

## Slice 12: Saved FAX Draw admits only professionals

- Owner decision (11 November 2026): the FAX reference path follows Master v87
  too. A player must first turn pro; only then may they apply or receive a wild
  card. An application, wild card, seeding or a Saved Draw slot never makes
  anyone a professional. The earlier "first valid application" bridge (option 1)
  is intentionally not implemented for this path.
- Under a v87 World, `adopt-saved-draw` (Ranked or Unranked, because Turn Pro is
  what allows playing association events) requires every Main, Qualification and
  wild-card participant to be a professional in the current lifecycle at the
  adoption week, which precedes announcement and play. Otherwise the command
  fails closed without writes and names the players who have not turned pro.
- The historical policy keeps its existing Ranked-only prior Tour Entry check.
- **Limitation:** the Saved Entry Field records no application week, so the
  check uses the adoption week (the native consumption of the Saved entries).
  The legacy copied-FAX acceptance materializer still builds a legacy 61-week
  InitialWorld whose lifecycle cannot represent v87; moving that acceptance Run
  to the native calendar population is a separate, larger step.

## Not implemented (next slices)

- Viewer UI text and followed-player notifications for Turn Pro.
- Model re-run for the non-native (pre-v4) Tour replay.
- Turn Pro in the pre-Tour sporting continuation weeks.
- `verify_tour` Turn Pro replay with the lifecycle as input.
