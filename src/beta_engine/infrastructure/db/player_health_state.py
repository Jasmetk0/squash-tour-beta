"""Persistence, Saved Revision, restore, and fork support for canonical Health V1."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.players.health import (
    PlayerHealthWeekState,
    bootstrap_health_state,
    carry_health_state_forward,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import PlayerHealthWeekStateModel

PLAYER_HEALTH_COMPONENT_KEY = "player_health_state"


def _load(
    row: PlayerHealthWeekStateModel,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
) -> PlayerHealthWeekState:
    state = PlayerHealthWeekState.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.week.ordinal, state.fingerprint) != (
        run_id,
        branch_id,
        week.ordinal,
        row.fingerprint,
    ):
        raise ValueError("Player health identity, week, or fingerprint mismatch")
    return state


def get_health(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
) -> PlayerHealthWeekState | None:
    row = session.get(PlayerHealthWeekStateModel, (run_id, branch_id, week.ordinal))
    return None if row is None else _load(row, run_id, branch_id, week)


def put_health(
    session: Session,
    state: PlayerHealthWeekState,
) -> PlayerHealthWeekState:
    current = get_health(
        session,
        run_id=state.run_id,
        branch_id=state.branch_id,
        week=state.week,
    )
    if current is not None:
        if current.fingerprint == state.fingerprint:
            return current
        raise ValueError(
            "Player health target week already has different authoritative state"
        )
    session.add(
        PlayerHealthWeekStateModel(
            run_id=state.run_id,
            branch_id=state.branch_id,
            week_ordinal=state.week.ordinal,
            fingerprint=state.fingerprint,
            payload_json=state.model_dump_json(),
        )
    )
    session.flush()
    installed = get_health(
        session,
        run_id=state.run_id,
        branch_id=state.branch_id,
        week=state.week,
    )
    if installed is None:  # pragma: no cover - flush/read invariant
        raise ValueError("Player health write could not be verified")
    return installed


def bootstrap_health(session: Session, world) -> PlayerHealthWeekState:
    state = bootstrap_health_state(
        run_id=world.run_id,
        branch_id=world.branch_id,
        source_initial_world_fingerprint=world.fingerprint,
        player_ids=tuple(player.player_id for player in world.players),
    )
    return put_health(session, state)


def transition_health(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed: RankingWeek,
    target: RankingWeek,
    target_player_ids: tuple[str, ...],
) -> PlayerHealthWeekState:
    predecessor = get_health(
        session,
        run_id=run_id,
        branch_id=branch_id,
        week=completed,
    )
    if predecessor is None:
        raise ValueError("Authoritative predecessor player health snapshot is missing")
    result = carry_health_state_forward(
        predecessor,
        target=target,
        target_player_ids=target_player_ids,
    )
    return put_health(session, result)


def _component(states: tuple[PlayerHealthWeekState, ...] | list[PlayerHealthWeekState]):
    body = [state.model_dump(mode="json") for state in states]
    return {
        "fingerprint": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "states": body,
    }


def _validate_chain(states: tuple[PlayerHealthWeekState, ...]) -> None:
    ordinals = tuple(state.week.ordinal for state in states)
    if ordinals != tuple(sorted(set(ordinals))):
        raise ValueError("Player health state weeks are not unique and canonical")
    for predecessor, target in zip(states, states[1:], strict=False):
        if (
            target.week.ordinal != predecessor.week.ordinal + 1
            or target.predecessor_fingerprint != predecessor.fingerprint
            or target.source_initial_world_fingerprint
            != predecessor.source_initial_world_fingerprint
        ):
            raise ValueError("Saved player-health predecessor chain is corrupt")


def capture_saved_health(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    rows = session.scalars(
        select(PlayerHealthWeekStateModel)
        .where(
            PlayerHealthWeekStateModel.run_id == run_id,
            PlayerHealthWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerHealthWeekStateModel.week_ordinal)
    ).all()
    if not rows:
        return
    states = tuple(
        _load(
            row,
            run_id,
            branch_id,
            RankingWeek(
                season_index=row.week_ordinal // 61,
                week=row.week_ordinal % 61 + 1,
            ),
        )
        for row in rows
    )
    _validate_chain(states)
    payload["content"][PLAYER_HEALTH_COMPONENT_KEY] = _component(states)


def load_saved_health(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[PlayerHealthWeekState, ...] | None:
    component = payload.get("content", {}).get(PLAYER_HEALTH_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "states"}:
        raise ValueError("Invalid Saved Revision player-health component")
    states = tuple(
        PlayerHealthWeekState.model_validate_json(json.dumps(state))
        for state in component["states"]
    )
    _validate_chain(states)
    if _component(states)["fingerprint"] != component["fingerprint"] or any(
        (state.run_id, state.branch_id) != (run_id, branch_id)
        for state in states
    ):
        raise ValueError("Saved player-health identity or fingerprint mismatch")
    return states


def remap_saved_health_component(
    payload: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
):
    """Rebuild complete Health history for a materialized Branch fork."""

    source = load_saved_health(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source is None:
        return None

    remapped: list[PlayerHealthWeekState] = []
    previous = None
    for state in source:
        target = PlayerHealthWeekState.model_validate_json(
            state.model_copy(
                update={
                    "branch_id": target_branch_id,
                    "predecessor_fingerprint": (
                        previous.fingerprint if previous is not None else None
                    ),
                }
            ).model_dump_json()
        )
        remapped.append(target)
        previous = target
    return _component(tuple(remapped))


def restore_saved_health(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_health(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_health(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target_world = None
    if target is None:
        from beta_engine.infrastructure.db.initial_world_state import (
            load_saved_initial_world,
        )
        from beta_engine.infrastructure.db.saved_revision_rankings import (
            load_saved_ranking_component,
        )

        target_world = load_saved_initial_world(
            target_payload,
            run_id=run_id,
            branch_id=branch_id,
        )
        target_ranking = load_saved_ranking_component(
            target_payload,
            run_id=run_id,
            branch_id=branch_id,
        )
        authoritative = (
            target_ranking.authoritative_transition_state if target_ranking else None
        )
        world_clock = authoritative.get("world") if authoritative else None
        if (target_world is None and target_ranking is not None) or (
            world_clock is not None and world_clock["current_ordinal"] > 0
        ):
            raise ValueError(
                "Legacy Saved Revision has no health component and cannot be "
                "reconstructed unambiguously from its owned target state"
            )

    rows = session.scalars(
        select(PlayerHealthWeekStateModel)
        .where(
            PlayerHealthWeekStateModel.run_id == run_id,
            PlayerHealthWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerHealthWeekStateModel.week_ordinal)
    ).all()
    live = tuple(
        _load(
            row,
            run_id,
            branch_id,
            RankingWeek(
                season_index=row.week_ordinal // 61,
                week=row.week_ordinal % 61 + 1,
            ),
        )
        for row in rows
    )
    if tuple(state.fingerprint for state in live) != tuple(
        state.fingerprint for state in (expected or ())
    ):
        raise ValueError("Live player health differs from saved head")

    session.execute(
        delete(PlayerHealthWeekStateModel).where(
            PlayerHealthWeekStateModel.run_id == run_id,
            PlayerHealthWeekStateModel.branch_id == branch_id,
        )
    )
    for state in target or ():
        put_health(session, state)

    if target is None and target_world is not None:
        from beta_engine.infrastructure.db.initial_world_state import get_initial_world

        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        if world is None:
            raise ValueError(
                "Target InitialWorldState is unavailable for health backfill"
            )
        bootstrap_health(session, world)
