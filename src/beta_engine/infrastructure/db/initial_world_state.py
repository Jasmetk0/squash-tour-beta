"""Persistence and Saved Revision projection for initial-world state."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from beta_engine.application.initial_world import (
    InitialWorldState,
    parse_initial_world_json,
)
from beta_engine.infrastructure.db.models import InitialWorldStateModel

if TYPE_CHECKING:
    from beta_engine.application.calendar_initial_world import CalendarInitialWorldState

INITIAL_WORLD_COMPONENT_KEY = "initial_world"


def get_initial_world(
    session: Session, *, run_id: str, branch_id: str
) -> InitialWorldState | CalendarInitialWorldState | None:
    row = session.get(InitialWorldStateModel, (run_id, branch_id))
    if row is None:
        return None
    state = parse_initial_world_json(row.payload_json)
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        row.fingerprint,
    ):
        raise ValueError("Initial-world identity or fingerprint mismatch")
    return state


def put_initial_world(
    session: Session, state: InitialWorldState | CalendarInitialWorldState
) -> InitialWorldState | CalendarInitialWorldState:
    current = get_initial_world(session, run_id=state.run_id, branch_id=state.branch_id)
    if current is not None:
        if current.fingerprint == state.fingerprint:
            return current
        raise ValueError("Initial world already exists for this Run/Branch")
    session.add(
        InitialWorldStateModel(
            run_id=state.run_id,
            branch_id=state.branch_id,
            fingerprint=state.fingerprint,
            payload_json=state.model_dump_json(),
        )
    )
    session.flush()
    installed = get_initial_world(
        session, run_id=state.run_id, branch_id=state.branch_id
    )
    if installed is None:
        raise ValueError("Initial-world write could not be verified")
    return installed


def capture_saved_initial_world(
    session: Session, payload: dict, *, run_id: str, branch_id: str
) -> None:
    state = get_initial_world(session, run_id=run_id, branch_id=branch_id)
    content = payload["content"]
    if state is not None:
        content[INITIAL_WORLD_COMPONENT_KEY] = {
            "fingerprint": state.fingerprint,
            "state": state.model_dump(mode="json"),
        }


def load_saved_initial_world(
    payload: dict, *, run_id: str, branch_id: str
) -> InitialWorldState | CalendarInitialWorldState | None:
    component = payload.get("content", {}).get(INITIAL_WORLD_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved Revision initial-world component")
    state = parse_initial_world_json(json.dumps(component["state"]))
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        component["fingerprint"],
    ):
        raise ValueError("Saved initial-world identity or fingerprint mismatch")
    if state.schema_version == "initial_world_state.v2":
        run_snapshot = payload.get("run", {})
        snapshot_calendar = run_snapshot.get("run_calendar")
        population_origin = state.run_calendar.to_metadata()
        if snapshot_calendar != population_origin:
            # Run-wide horizon extension does not regenerate the original
            # population. Only a hash-signed Saved Revision with the explicit
            # *original population clock* may preserve the old component.
            # W/offset/start never change; shortening is never permitted.
            from beta_engine.domain.calendar.run_calendar import RunCalendar
            origin = run_snapshot.get("run_calendar_content_origin")
            if origin != population_origin:
                raise ValueError("Saved calendar InitialWorld disagrees with the revision's Run clock")
            current = RunCalendar.from_metadata(snapshot_calendar)
            basis = RunCalendar.from_metadata(origin)
            if (
                current.weeks_per_year != basis.weeks_per_year
                or current.season_start_year_week != basis.season_start_year_week
                or current.start_year != basis.start_year
                or current.season_count <= basis.season_count
            ):
                raise ValueError("Saved InitialWorld extension provenance has incompatible clocks")
        if payload.get("content", {}).get("player_lifecycle") is None:
            raise ValueError("Saved calendar InitialWorld has no lifecycle component")
    return state


def remap_saved_initial_world_for_branch(
    payload: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> InitialWorldState | CalendarInitialWorldState:
    """Validate and re-scope an owned InitialWorld for a materialized fork.

    Adoption fields are deliberately retained verbatim: they describe the historical
    source adoption, not a fabricated Admin command on the new Branch.  Constructing
    the frozen model again (rather than editing snapshot JSON) gives the target its
    naturally branch-scoped fingerprint while preserving all sporting source data.
    """
    source = load_saved_initial_world(
        payload, run_id=run_id, branch_id=source_branch_id
    )
    if source is None:
        raise ValueError("Saved Revision initial-world component is missing")
    if target_branch_id == source_branch_id:
        raise ValueError("Initial-world fork target must be a different Branch")
    return parse_initial_world_json(
        source.model_copy(update={"branch_id": target_branch_id}).model_dump_json()
    )


def restore_saved_initial_world(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_initial_world(
        current_payload, run_id=run_id, branch_id=branch_id
    )
    target = load_saved_initial_world(
        target_payload, run_id=run_id, branch_id=branch_id
    )
    live = get_initial_world(session, run_id=run_id, branch_id=branch_id)
    if (live.fingerprint if live else None) != (
        expected.fingerprint if expected else None
    ):
        raise ValueError("Live initial world differs from the saved head")
    if live is not None:
        session.delete(session.get(InitialWorldStateModel, (run_id, branch_id)))
        session.flush()
    if target is not None:
        session.add(
            InitialWorldStateModel(
                run_id=run_id,
                branch_id=branch_id,
                fingerprint=target.fingerprint,
                payload_json=target.model_dump_json(),
            )
        )
        session.flush()
