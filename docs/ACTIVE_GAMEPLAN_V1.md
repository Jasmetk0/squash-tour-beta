# Active Gameplan V1

## Status and boundary

This document describes the implemented pre-alpha contract. It follows the
Master decision that active style and gameplan use four simultaneous axes:

- `Risk`: low-risk construction to aggressive risk taking,
- `Tempo`: patient to fast play,
- `Court Positioning`: deeper/reactive to higher/front-seeking positioning,
- `Variation`: repeated patterns to high variation.

The axes, separation of player knowledge from engine truth, imperfect
countering, and the ability to stick or adapt are product behavior. Numeric
weights and thresholds are only the versioned `pre_alpha_gameplan_v1`
calibration. They may be replaced without reinterpreting already stored
matches.

## Match input truth

`EffectiveMatchGameplanSnapshot` is created before the first rally and included
in hash-protected `match_input_snapshot.v8`. It stores, in participant order:

1. the materialized Natural Style Profile of each player;
2. a player-specific familiarity baseline and temporary adaptability proxy;
3. each player's noisy estimate of the opponent;
4. the initial active plan and its four axes;
5. intended mechanism, time horizon, confidence, reassessment threshold, and
   anticipated payoff horizon;
6. the deterministic seed used to make each choice.

The current player record still has a legacy categorical `play_style`. V1
deterministically materializes that category into stable, player-specific axes.
This is explicit migration debt, recorded as
`persistent_authored_style_profiles` in `unsupported_components`; it is not a
claim that the final career style model should be reconstructed forever.

Likewise, the current lighter player model does not yet expose the final
`Adaptability` attribute or Match Preparation state. V1 uses a logged
mental/consistency proxy and lists Match Preparation, scouting history, and
mental-bar coupling as unsupported. No hidden value is invented and presented
as if those systems already existed.

## Decision layer versus physical execution

The player AI and Match Engine are separate layers:

- AI selects `OWN_STRENGTH`, `COUNTER_ESTIMATE`, or `DELAYED_PAYOFF` from its
  own profile and a noisy opponent estimate.
- A counter plan is aimed at that estimate, so a reasonable decision can still
  target the wrong pattern.
- The Match Engine evaluates the chosen plan against the opponent's actual
  active plan and the player's real current physical reserve.
- Familiarity and available abilities limit execution. A tactically sensible
  idea therefore does not grant a direct point bonus.

The old categorical style matchup modifier is disabled when Active Gameplan V1
is running. This prevents the natural-style label and its materialized
four-axis effect from being counted twice. The separate archetype interaction
remains as legacy engine behavior.

## Rally-by-rally reassessment

Before each rally, each player sees only evidence that already exists. The
decision log contains the number of observed rallies, their point differential,
and the player's imperfect performance signal. It never contains the future
rally result.

At the stored reassessment threshold the AI may:

- keep a plan because the observed result is acceptable;
- intentionally wait for a later expected payoff;
- keep it because of high confidence or low adaptability;
- mistakenly keep it after misreading the evidence; or
- adapt after a negative reassessment.

An adaptation creates the next exact plan revision. Both players evaluate the
same pre-rally state before either new plan is applied, so simultaneous
decisions do not become execution-order dependent.

## Causal sporting effects

The active plan affects four physical parts of the existing rally pipeline:

- quality of acquiring or retaining hidden control;
- shared phase pace;
- closure pressure, meaning how readily the phase reaches a terminal incident;
- individual workload, including the cost of unfamiliar execution.

Risk or a purported counter never awards a point directly. The winner still
emerges from the opening, hidden control transitions, terminal probability,
and deterministic rally RNG already used by the engine. This also means a plan
can be well chosen but poorly executed, or well executed and still lose.

## Authoritative log and replay

Every current rally uses `rally_event.v5` inside `match_rally_log.v5`. Its
`gameplan_context` stores the exact plan decision and derived causal effects for
both players. The event hash protects that data. Log validation additionally
requires:

- both players in match participant order;
- `START` only on rally one;
- `ADAPT` to select a plan at the current rally;
- an adaptation to increment the player's plan revision exactly once;
- a `STICK` decision to retain the same revision;
- internally consistent observed-rally and point-differential evidence.

Stored Replay continues to read these events and snapshots and never reruns the
current AI or random generator.

## Deliberately deferred

- authored and career-evolving continuous style profiles;
- a full 57-attribute Style Execution mapping;
- first-class `Adaptability` and personality/stubbornness inputs;
- Match Preparation, scouting quality, H2H memory, and video availability;
- mental-bar coupling;
- final strategy probabilities, weights, and reassessment distributions;
- detailed shot patterns or shot-by-shot tactics.

Those additions should create a new historical calibration/schema generation,
not mutate the meaning of `pre_alpha_gameplan_v1`.
