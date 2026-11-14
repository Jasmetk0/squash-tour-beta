"""Master v87 Turn Pro for the exhibition weeks that precede Tour initialization.

The exhibition writer (``CalendarSportingWeekService``) advances only the sporting
owner. A v87 Run still needs its prospects to have the chance to turn pro in each of
those Week Transitions. At Tour initialization this module replays the *signed*
exhibition history week by week: it rebuilds the sporting checkpoint of each
completed week from the real events, lets the same player-AI model decide from what
each prospect then knew about itself, and returns one record for the Tour authority.

Nothing here reads a later week, another Branch or hidden opponent strength, and
nothing is invented for the Tour path: the seed of each week is the recorded seed of
that week's real sporting advance command.
"""

from __future__ import annotations

from beta_engine.domain.players.calendar_continuation_match import append_continuation
from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
from beta_engine.domain.players.calendar_followup_knockout import (
    CalendarFollowupKnockout,
    append_followup_knockout,
)
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_sporting_checkpoint import (
    build_calendar_sporting_checkpoint,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarSportingWeekAdvance,
    append_sporting_week,
)
from beta_engine.domain.players.calendar_tournament_closure import (
    append_native_tournament_closure,
)
from beta_engine.domain.players.turn_pro_model import (
    decide_turn_pro,
    default_turn_pro_model_policy,
    traits_from_world,
    turn_pro_candidates_for,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarPreTourTurnPro,
    CalendarPreTourTurnProWeek,
)

EXHIBITION_ADVANCE = "calendar_sporting_week_advance.v1"


def derive_pre_tour_turn_pro(world, checkpoint, evidence) -> CalendarPreTourTurnPro | None:
    """Turn Pro record for every exhibition week of ``checkpoint``; None if not v87."""
    from beta_engine.application.calendar_initial_world import (
        derive_calendar_bootstrap_lifecycle,
    )

    lifecycle = derive_calendar_bootstrap_lifecycle(world)
    if not lifecycle.policy.requires_turn_pro:
        return None
    models = [e.turn_pro_model for e in checkpoint.weekly_advances if e.turn_pro_model is not None]
    # New v4 weeks record the actual model and decisions at the weekly command.
    # The old v1 reconstruction remains a compatibility reader for older worlds.
    model = models[0] if models else default_turn_pro_model_policy()
    traits = traits_from_world(world)
    knockout = getattr(evidence, "knockout", evidence)
    prefix = build_calendar_sporting_checkpoint(world, knockout, calendar_engine_player)
    recorded: list = []
    weeks: list[CalendarPreTourTurnProWeek] = []
    for event in (*checkpoint.continuations, *checkpoint.week_events):
        if isinstance(event, CalendarSportingWeekAdvance):
            if event.schema_version not in {EXHIBITION_ADVANCE, "calendar_sporting_week_advance.v4"}:
                raise ValueError("Tour initialization found a non-exhibition weekly advance")
            if event.completed_week.ordinal != lifecycle.week.ordinal:
                raise ValueError("Exhibition weeks are not consecutive with the lifecycle")
            target = event.target_week
            plain = advance_calendar_lifecycle(lifecycle, target, (), tuple(recorded))
            # ``prefix`` is exactly the completed week's sporting record.
            decisions = decide_turn_pro(
                predecessor=lifecycle,
                target=target,
                policy=model,
                seed=event.seed,
                candidates=turn_pro_candidates_for(
                    model,
                    lifecycle,
                    plain,
                    prefix.players,
                    seed=event.seed,
                    target=target,
                    traits_by_player=traits,
                    # No Edition exists before the Tour, hence no home opportunity.
                    home_opportunity_by_player={},
                ),
            )
            if event.turn_pro_model is not None and (event.turn_pro_model != model or event.turn_pro_decisions != decisions):
                raise ValueError("Pre-Tour evaluation differs from its recorded weekly decision")
            recorded.extend(decisions)
            lifecycle = advance_calendar_lifecycle(lifecycle, target, (), tuple(recorded))
            weeks.append(
                CalendarPreTourTurnProWeek(
                    command_id=event.command_id,
                    completed_week=event.completed_week,
                    target_week=target,
                    seed=event.seed,
                    decisions=decisions,
                    **(dict(sporting_advance_fingerprint=event.fingerprint,
                            retired_player_ids=event.retired_player_ids,
                            retired_without_turn_pro_player_ids=event.retired_without_turn_pro_player_ids)
                       if event.turn_pro_model is not None else {}),
                )
            )
            prefix = append_sporting_week(prefix, world, knockout, event)
        elif isinstance(event, CalendarFollowupKnockout):
            prefix = append_followup_knockout(prefix, world, event)
        else:
            prefix = append_continuation(prefix, world, event)
        for closure in checkpoint.closures:
            if closure.source_week_event_count == len(prefix.week_events) and closure not in prefix.closures:
                prefix = append_native_tournament_closure(prefix, closure)
    if not weeks:
        return None
    return CalendarPreTourTurnPro(model=model, weeks=tuple(weeks))
