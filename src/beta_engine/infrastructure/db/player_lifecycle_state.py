"""Persistence, bootstrap, transition and Saved Revision projection for lifecycle state."""

import hashlib
import json
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
    advance_lifecycle,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import PlayerLifecycleWeekStateModel

PLAYER_LIFECYCLE_COMPONENT_KEY = "player_lifecycle"


def _load(row, run_id, branch_id, week):
    state = PlayerLifecycleWeekState.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.week.ordinal, state.fingerprint) != (
        run_id,
        branch_id,
        week.ordinal,
        row.fingerprint,
    ):
        raise ValueError("Player lifecycle identity, week, or fingerprint mismatch")
    return state


def get_lifecycle(session: Session, *, run_id: str, branch_id: str, week: RankingWeek):
    row = session.get(PlayerLifecycleWeekStateModel, (run_id, branch_id, week.ordinal))
    return None if row is None else _load(row, run_id, branch_id, week)


def put_lifecycle(
    session: Session, state: PlayerLifecycleWeekState
) -> PlayerLifecycleWeekState:
    current = get_lifecycle(
        session, run_id=state.run_id, branch_id=state.branch_id, week=state.week
    )
    if current:
        if current.fingerprint == state.fingerprint:
            return current
        raise ValueError(
            "Player lifecycle target week already has different authoritative state"
        )
    session.add(
        PlayerLifecycleWeekStateModel(
            run_id=state.run_id,
            branch_id=state.branch_id,
            week_ordinal=state.week.ordinal,
            fingerprint=state.fingerprint,
            payload_json=state.model_dump_json(),
        )
    )
    session.flush()
    installed = get_lifecycle(
        session, run_id=state.run_id, branch_id=state.branch_id, week=state.week
    )
    if installed is None:  # pragma: no cover - flush/read invariant
        raise ValueError("Player lifecycle write could not be verified")
    return installed


def bootstrap_lifecycle(session: Session, world: InitialWorldState):
    week = RankingWeek(season_index=0, week=1)
    existing = get_lifecycle(
        session, run_id=world.run_id, branch_id=world.branch_id, week=week
    )
    if existing:
        return existing
    players = []
    for p in world.players:
        provenance = json.dumps(
            {
                "player_id": p.player_id,
                "birth_year": p.birth_year,
                "birth_year_week": p.birth_year_week,
                "source": p.source_generation_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        players.append(
            PlayerLifecycleIdentity(
                player_id=p.player_id,
                birth_year=p.birth_year,
                birth_year_week=p.birth_year_week,
                tie_break_token=hashlib.sha256(provenance.encode()).hexdigest(),
                tie_break_provenance=provenance,
                tour_entry_week=week,
                age=p.age_years_at_season_start,
                status="active",
                origin=f"initial_world:{world.fingerprint}",
            )
        )
    return put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id=world.run_id,
            branch_id=world.branch_id,
            week=week,
            players=tuple(players),
            source_initial_world_fingerprint=world.fingerprint,
        ),
    )


def transition_lifecycle(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed: RankingWeek,
    target: RankingWeek,
):
    predecessor = get_lifecycle(
        session, run_id=run_id, branch_id=branch_id, week=completed
    )
    if predecessor is None:
        raise ValueError(
            "Authoritative predecessor player lifecycle snapshot is missing"
        )
    return put_lifecycle(session, advance_lifecycle(predecessor, target))


def capture_saved_lifecycle(session, payload, *, run_id, branch_id):
    rows = session.scalars(
        select(PlayerLifecycleWeekStateModel)
        .where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerLifecycleWeekStateModel.week_ordinal)
    ).all()
    if rows:
        states = [
            _load(
                r,
                run_id,
                branch_id,
                RankingWeek(
                    season_index=r.week_ordinal // 61, week=r.week_ordinal % 61 + 1
                ),
            )
            for r in rows
        ]
        body = [s.model_dump(mode="json") for s in states]
        fingerprint = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        payload["content"][PLAYER_LIFECYCLE_COMPONENT_KEY] = {
            "fingerprint": fingerprint,
            "states": body,
        }


def load_saved_lifecycle(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(PLAYER_LIFECYCLE_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "states"}:
        raise ValueError("Invalid Saved Revision player-lifecycle component")
    states = tuple(
        PlayerLifecycleWeekState.model_validate_json(json.dumps(s))
        for s in component["states"]
    )
    body = [s.model_dump(mode="json") for s in states]
    fp = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if fp != component["fingerprint"] or any(
        (s.run_id, s.branch_id) != (run_id, branch_id) for s in states
    ):
        raise ValueError("Saved player-lifecycle identity or fingerprint mismatch")
    return states


def restore_saved_lifecycle(
    session, *, current_payload, target_payload, run_id, branch_id
):
    expected = load_saved_lifecycle(current_payload, run_id=run_id, branch_id=branch_id)
    target = load_saved_lifecycle(target_payload, run_id=run_id, branch_id=branch_id)
    rows = session.scalars(
        select(PlayerLifecycleWeekStateModel)
        .where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerLifecycleWeekStateModel.week_ordinal)
    ).all()
    live = tuple(
        _load(
            r,
            run_id,
            branch_id,
            RankingWeek(
                season_index=r.week_ordinal // 61, week=r.week_ordinal % 61 + 1
            ),
        )
        for r in rows
    )
    if tuple(s.fingerprint for s in live) != tuple(
        s.fingerprint for s in (expected or ())
    ):
        raise ValueError("Live player lifecycle differs from saved head")
    session.execute(
        delete(PlayerLifecycleWeekStateModel).where(
            PlayerLifecycleWeekStateModel.run_id == run_id,
            PlayerLifecycleWeekStateModel.branch_id == branch_id,
        )
    )
    for state in target or ():
        put_lifecycle(session, state)
