"""Keep native v2 task control outside legacy restorable sporting snapshots."""

import json

from sqlalchemy import select

from beta_engine.infrastructure.db.models import AuthoritativeSimulationCommandModel


def native_task_parent(session, row):
    payload = json.loads(row.result_json)
    if not isinstance(payload, dict):
        raise TypeError("Simulation command payload must be an object")
    if payload.get("schema_version") != "authoritative_full_simulation_operation.v2":
        return None
    from beta_engine.application.native_full_simulation import validate_native_parent
    validate_native_parent(session, row, payload)
    return payload


def sporting_simulation_commands(session, rows):
    """V1 rows remain byte-for-byte restorable; v2 control is never rewound."""
    return [row for row in rows if native_task_parent(session, row) is None]


def pending_native_task_parents(session, *, run_id, branch_id):
    rows = session.scalars(select(AuthoritativeSimulationCommandModel).where(
        AuthoritativeSimulationCommandModel.run_id == run_id,
        AuthoritativeSimulationCommandModel.branch_id == branch_id,
        AuthoritativeSimulationCommandModel.status == "pending",
    )).all()
    return tuple(row for row in rows if native_task_parent(session, row) is not None)


def require_no_pending_native_task(session, *, run_id, branch_id):
    if pending_native_task_parents(session, run_id=run_id, branch_id=branch_id):
        raise ValueError("Stop the pending native Full Simulation before restoring this Branch")
