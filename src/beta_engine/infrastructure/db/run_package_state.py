"""Strict persistence and Saved Revision projection for Run Package state."""

from __future__ import annotations

import json
from sqlalchemy.orm import Session

from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.models import RunPackageStateModel

RUN_PACKAGE_COMPONENT_KEY = "run_package_state"


def get_run_package_state(
    session: Session, *, run_id: str, branch_id: str
) -> RunPackageState | None:
    row = session.get(RunPackageStateModel, (run_id, branch_id))
    if row is None:
        return None
    state = RunPackageState.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        row.fingerprint,
    ):
        raise ValueError("Run Package state identity or fingerprint mismatch")
    return state


def put_run_package_state(session: Session, state: RunPackageState) -> None:
    row = session.get(RunPackageStateModel, (state.run_id, state.branch_id))
    if row is None:
        row = RunPackageStateModel(run_id=state.run_id, branch_id=state.branch_id)
        session.add(row)
    row.fingerprint = state.fingerprint
    row.payload_json = state.model_dump_json()
    session.flush()
    if (
        get_run_package_state(session, run_id=state.run_id, branch_id=state.branch_id)
        != state
    ):
        raise ValueError("Run Package state write could not be verified")


def capture_saved_run_package_state(
    session: Session, payload: dict, *, run_id: str, branch_id: str
) -> None:
    state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
    if state is not None:
        payload["content"][RUN_PACKAGE_COMPONENT_KEY] = {
            "fingerprint": state.fingerprint,
            "state": state.model_dump(mode="json"),
        }


def load_saved_run_package_state(
    payload: dict, *, run_id: str, branch_id: str
) -> RunPackageState | None:
    component = payload.get("content", {}).get(RUN_PACKAGE_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved Revision Run Package component")
    state = RunPackageState.model_validate_json(json.dumps(component["state"]))
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id,
        branch_id,
        component["fingerprint"],
    ):
        raise ValueError("Saved Run Package state identity or fingerprint mismatch")
    return state


def remap_saved_run_package_state(
    payload: dict, *, run_id: str, source_branch_id: str, target_branch_id: str
) -> RunPackageState:
    source = load_saved_run_package_state(
        payload, run_id=run_id, branch_id=source_branch_id
    )
    if source is None:
        raise ValueError("Saved Revision Run Package component is missing")
    if source_branch_id == target_branch_id:
        raise ValueError("Run Package fork target must differ from source")
    return source.model_copy(update={"branch_id": target_branch_id})


def restore_saved_run_package_state(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_run_package_state(
        current_payload, run_id=run_id, branch_id=branch_id
    )
    target = load_saved_run_package_state(
        target_payload, run_id=run_id, branch_id=branch_id
    )
    live = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
    if (live.fingerprint if live else None) != (
        expected.fingerprint if expected else None
    ):
        raise ValueError("Live Run Package state differs from the saved head")
    row = session.get(RunPackageStateModel, (run_id, branch_id))
    if row is not None:
        session.delete(row)
        session.flush()
    if target is not None:
        put_run_package_state(session, target)
