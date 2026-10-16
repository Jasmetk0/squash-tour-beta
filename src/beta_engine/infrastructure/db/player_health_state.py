"""Persistence, Saved Revision, restore, and fork support for legacy Health V1 and calendar-owned initial health."""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_health import CalendarHealthState
from beta_engine.domain.players.calendar_initial_health import (
    CalendarInitialHealthState,
)
from beta_engine.domain.players.health import (
    PlayerHealthWeekState,
    bootstrap_health_state,
    carry_health_state_forward,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import PlayerHealthWeekStateModel

PLAYER_HEALTH_COMPONENT_KEY = "player_health_state"


def _parse_health_json(raw):
    value = json.loads(raw)
    if (
        isinstance(value, dict)
        and value.get("schema_version") == "calendar_initial_health_state.v1"
    ):
        return CalendarInitialHealthState.model_validate_json(raw)
    if (
        isinstance(value, dict)
        and value.get("schema_version") == "player_health_calendar_state.v2"
    ):
        return CalendarHealthState.model_validate_json(raw)
    return PlayerHealthWeekState.model_validate_json(raw)


def _load(
    row: PlayerHealthWeekStateModel,
    run_id: str,
    branch_id: str,
    week_ordinal: int,
) -> PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState:
    state = _parse_health_json(row.payload_json)
    if (state.run_id, state.branch_id, state.week.ordinal, state.fingerprint) != (
        run_id,
        branch_id,
        week_ordinal,
        row.fingerprint,
    ):
        raise ValueError("Player health identity, week, or fingerprint mismatch")
    return state


def get_health(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek | RunWeekPosition,
) -> PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState | None:
    row = session.get(PlayerHealthWeekStateModel, (run_id, branch_id, week.ordinal))
    if row is None:
        return None
    state = _load(row, run_id, branch_id, week.ordinal)
    if isinstance(state, (CalendarInitialHealthState, CalendarHealthState)):
        if not isinstance(week, RunWeekPosition) or state.week != week:
            raise ValueError("Calendar health requires its matching Run-owned position")
    elif not isinstance(week, RankingWeek):
        raise ValueError("Legacy health requires its historical RankingWeek")
    return state


def put_health(
    session: Session,
    state: PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState,
) -> PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState:
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
    if getattr(world, "schema_version", None) == "initial_world_state.v2":
        raise ValueError(
            "Calendar population requires a versioned Health bootstrap before sporting use"
        )
    state = bootstrap_health_state(
        run_id=world.run_id,
        branch_id=world.branch_id,
        source_initial_world_fingerprint=world.fingerprint,
        player_ids=tuple(player.player_id for player in world.players),
    )
    return put_health(session, state)


def bootstrap_health_from_week_one_identity(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    source_initial_world_fingerprint: str,
    player_ids: tuple[str, ...],
) -> PlayerHealthWeekState:
    """Compatibility bootstrap for explicit Week-1 identity without fake pre-history."""

    return put_health(
        session,
        bootstrap_health_state(
            run_id=run_id,
            branch_id=branch_id,
            source_initial_world_fingerprint=source_initial_world_fingerprint,
            player_ids=player_ids,
        ),
    )


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


def replace_health_head(
    session: Session,
    state: PlayerHealthWeekState | CalendarHealthState,
    *,
    expected_fingerprint: str,
) -> PlayerHealthWeekState | CalendarHealthState:
    """Replace only the current Health head through an explicit audited Admin path."""

    rows = session.scalars(
        select(PlayerHealthWeekStateModel)
        .where(
            PlayerHealthWeekStateModel.run_id == state.run_id,
            PlayerHealthWeekStateModel.branch_id == state.branch_id,
        )
        .order_by(PlayerHealthWeekStateModel.week_ordinal)
    ).all()
    if not rows:
        raise ValueError("Player health history is missing")
    head = rows[-1]
    if head.week_ordinal != state.week.ordinal:
        raise ValueError("Admin Health edit may replace only the current health head")
    current = _load(head, state.run_id, state.branch_id, state.week.ordinal)
    calendar_current = isinstance(
        current, (CalendarInitialHealthState, CalendarHealthState)
    )
    if calendar_current != isinstance(state, CalendarHealthState):
        raise ValueError("Health writer cannot change calendar schema authority")
    if current.week != state.week:
        raise ValueError("Health writer cannot reinterpret the current time basis")
    if isinstance(current, CalendarInitialHealthState):
        if (
            state.origin.baseline_fingerprint != current.fingerprint
            or len(state.admin_edits) != 1
        ):
            raise ValueError(
                "Calendar Health conversion must retain baseline provenance"
            )
    elif isinstance(current, CalendarHealthState):
        if (
            state.origin != current.origin
            or state.admin_edits[:-1] != current.admin_edits
        ):
            raise ValueError("Calendar Health writer cannot rewrite edit provenance")
    if current.fingerprint != expected_fingerprint:
        raise ValueError("Player health head changed since preview")
    if current.predecessor_fingerprint != state.predecessor_fingerprint:
        raise ValueError("Admin Health edit cannot rewrite predecessor history")
    if (
        current.source_initial_world_fingerprint
        != state.source_initial_world_fingerprint
    ):
        raise ValueError("Admin Health edit cannot rewrite InitialWorld provenance")

    head.fingerprint = state.fingerprint
    head.payload_json = state.model_dump_json()
    session.flush()
    installed = get_health(
        session,
        run_id=state.run_id,
        branch_id=state.branch_id,
        week=state.week,
    )
    if installed is None or installed.fingerprint != state.fingerprint:
        raise ValueError("Admin Health edit write could not be verified")
    return installed


def health_component(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> dict | None:
    """Return the canonical Saved Revision Health component for live state."""

    rows = session.scalars(
        select(PlayerHealthWeekStateModel)
        .where(
            PlayerHealthWeekStateModel.run_id == run_id,
            PlayerHealthWeekStateModel.branch_id == branch_id,
        )
        .order_by(PlayerHealthWeekStateModel.week_ordinal)
    ).all()
    if not rows:
        return None
    states = tuple(
        _load(
            row,
            run_id,
            branch_id,
            row.week_ordinal,
        )
        for row in rows
    )
    _validate_chain(states)
    return _component(states)


def _component(
    states: tuple[
        PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState, ...
    ]
    | list[PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState],
):
    body = [state.model_dump(mode="json") for state in states]
    return {
        "fingerprint": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "states": body,
    }


def _validate_chain(
    states: tuple[
        PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState, ...
    ],
) -> None:
    calendar_states = [
        s
        for s in states
        if isinstance(s, (CalendarInitialHealthState, CalendarHealthState))
    ]
    if calendar_states and len(calendar_states) != len(states):
        raise ValueError("Calendar health cannot contain mixed legacy history")
    if any(isinstance(s, CalendarInitialHealthState) for s in states[1:]):
        raise ValueError("Initial health baseline must be the opening state")
    if calendar_states and any(
        s.week.calendar != states[0].week.calendar for s in states
    ):
        raise ValueError("Calendar Health chain cannot alias foreign calendars")
    if calendar_states and (
        states[0].week.ordinal != 0 or states[0].predecessor_fingerprint is not None
    ):
        raise ValueError("Calendar Health history requires its opening state")
    for predecessor, target in pairwise(calendar_states):
        if (
            isinstance(target, CalendarHealthState)
            and isinstance(predecessor, CalendarHealthState)
            and (
                target.origin != predecessor.origin
                or target.admin_edits[: len(predecessor.admin_edits)]
                != predecessor.admin_edits
            )
        ):
            raise ValueError("Calendar Health history cannot rewrite edit provenance")
    ordinals = tuple(state.week.ordinal for state in states)
    if ordinals != tuple(sorted(set(ordinals))):
        raise ValueError("Player health state weeks are not unique and canonical")
    for predecessor, target in pairwise(states):
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
    component = health_component(session, run_id=run_id, branch_id=branch_id)
    if component is not None:
        payload["content"][PLAYER_HEALTH_COMPONENT_KEY] = component


def load_saved_health(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> (
    tuple[PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState, ...]
    | None
):
    component = payload.get("content", {}).get(PLAYER_HEALTH_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "states"}:
        raise ValueError("Invalid Saved Revision player-health component")
    states = tuple(
        _parse_health_json(json.dumps(state)) for state in component["states"]
    )
    _validate_chain(states)
    if _component(states)["fingerprint"] != component["fingerprint"] or any(
        (state.run_id, state.branch_id) != (run_id, branch_id) for state in states
    ):
        raise ValueError("Saved player-health identity or fingerprint mismatch")
    if any(
        isinstance(state, (CalendarInitialHealthState, CalendarHealthState))
        for state in states
    ):
        from beta_engine.infrastructure.db.initial_world_state import (
            load_saved_initial_world,
        )
        from beta_engine.infrastructure.db.player_lifecycle_state import (
            load_saved_lifecycle,
        )

        world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id)
        life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
        if (
            world is None
            or world.schema_version != "initial_world_state.v2"
            or not life
        ):
            raise ValueError("Saved calendar health requires its population/lifecycle")
        for state in states:
            owned_life = next((item for item in life if item.week == state.week), None)
            if (
                state.week.calendar != world.run_calendar
                or owned_life is None
                or state.source_initial_world_fingerprint
                != owned_life.source_initial_world_fingerprint
                or tuple(p.player_id for p in state.players)
                != tuple(p.player_id for p in owned_life.players)
                or tuple(p.player_id for p in state.players)
                != tuple(sorted(p.player_id for p in world.players))
            ):
                raise ValueError(
                    "Saved calendar health differs from its population/calendar"
                )
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

    remapped: list[
        PlayerHealthWeekState | CalendarInitialHealthState | CalendarHealthState
    ] = []
    previous = None
    for state in source:
        target = _parse_health_json(
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
    target_lifecycle = None
    if target is None:
        from beta_engine.infrastructure.db.initial_world_state import (
            load_saved_initial_world,
        )
        from beta_engine.infrastructure.db.player_lifecycle_state import (
            load_saved_lifecycle,
        )
        from beta_engine.infrastructure.db.saved_revision_rankings import (
            load_saved_ranking_component,
        )

        target_world = load_saved_initial_world(
            target_payload,
            run_id=run_id,
            branch_id=branch_id,
        )
        target_lifecycle = load_saved_lifecycle(
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
        opening_lifecycle = (
            target_lifecycle is not None
            and len(target_lifecycle) == 1
            and target_lifecycle[0].week.ordinal == 0
        )
        if (world_clock is not None and world_clock["current_ordinal"] > 0) or (
            target_world is None
            and target_ranking is not None
            and not opening_lifecycle
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
            row.week_ordinal,
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

    calendar_population = (
        target_world is not None
        and target_world.schema_version == "initial_world_state.v2"
    )
    if target is None and target_lifecycle is not None and not calendar_population:
        opening = target_lifecycle[0]
        put_health(
            session,
            bootstrap_health_state(
                run_id=run_id,
                branch_id=branch_id,
                source_initial_world_fingerprint=(
                    opening.source_initial_world_fingerprint
                ),
                player_ids=tuple(player.player_id for player in opening.players),
            ),
        )
    elif target is None and target_world is not None and not calendar_population:
        from beta_engine.infrastructure.db.initial_world_state import get_initial_world

        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        if world is None:
            raise ValueError(
                "Target InitialWorldState is unavailable for health backfill"
            )
        bootstrap_health(session, world)
