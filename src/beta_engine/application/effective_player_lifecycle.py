"""Current-world lifecycle projection over immutable week snapshots and entry events."""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.players.tour_entry_projection import (
    project_lifecycle_tour_entries,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import AuthoritativeWorldStateModel
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)


def current_authoritative_week(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> RankingWeek:
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if world is None:
        raise ValueError("Effective lifecycle requires an authoritative world head")
    if world.current_ordinal < 0:
        raise ValueError("Authoritative world ordinal is invalid")
    return RankingWeek(
        season_index=world.current_ordinal // 61,
        week=world.current_ordinal % 61 + 1,
    )


def resolve_current_effective_lifecycle(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> PlayerLifecycleWeekState:
    """Return current career status without rewriting the stored week snapshot."""

    week = current_authoritative_week(
        session,
        run_id=run_id,
        branch_id=branch_id,
    )
    stored = get_lifecycle(
        session,
        run_id=run_id,
        branch_id=branch_id,
        week=week,
    )
    if stored is None:
        raise ValueError("Effective lifecycle requires current lifecycle history")
    triggers = PlayerTourEntryTriggerStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    return project_lifecycle_tour_entries(stored, triggers)
