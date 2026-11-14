"""Recorded v87 decisions at the actual pre-Tour weekly command, replayed from own inputs."""
from beta_engine.domain.players.calendar_lifecycle import (
    advance_calendar_lifecycle, bootstrap_calendar_lifecycle, calendar_lifecycle_history,
)
from beta_engine.domain.players.turn_pro_model import decide_turn_pro, turn_pro_candidates_for, traits_from_world

EXHIBITION_TURN_PRO_VERSION = 'calendar_sporting_week_advance.v4'


def exhibition_turn_pro_impact(world, checkpoint, *, model, seed, target):
    decisions = tuple(d for e in checkpoint.weekly_advances for d in e.turn_pro_decisions)
    previous_models = [e.turn_pro_model for e in checkpoint.weekly_advances if e.turn_pro_model is not None]
    if previous_models and any(recorded != model for recorded in previous_models):
        raise ValueError('Exhibition Turn Pro must retain its recorded model policy')
    lifecycle = calendar_lifecycle_history(
        bootstrap_calendar_lifecycle(world), checkpoint.week, (), turn_pro=decisions,
    )[-1]
    plain = advance_calendar_lifecycle(lifecycle, target, (), decisions)
    decided = decide_turn_pro(
        predecessor=lifecycle, target=target, policy=model, seed=seed,
        candidates=turn_pro_candidates_for(
            model, lifecycle, plain, checkpoint.players, seed=seed, target=target,
            traits_by_player=traits_from_world(world), home_opportunity_by_player={},
        ),
    )
    future = advance_calendar_lifecycle(lifecycle, target, (), (*decisions, *decided))
    active = {p.player_id for p in lifecycle.players if p.status == "active"}
    retired = tuple(p.player_id for p in future.players if p.status == "retired" and p.player_id in active)
    without_pro = tuple(p.player_id for p in future.players if p.player_id in retired and p.tour_entry_week is None)
    return dict(turn_pro_model=model, turn_pro_decisions=decided,
                source_lifecycle_fingerprint=lifecycle.fingerprint,
                target_lifecycle_fingerprint=future.fingerprint,
                retired_player_ids=retired, retired_without_turn_pro_player_ids=without_pro)
