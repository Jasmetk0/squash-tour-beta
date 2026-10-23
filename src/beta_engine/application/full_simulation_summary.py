"""Frozen terminal-operation evidence, never a projection of today's Branch."""
from __future__ import annotations

import json

from sqlalchemy import select

from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel, OwnedTournamentRankingSourceModel,
    RunBranchModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore

CHILD_MAPS = (
    "season_children", "final_week_children", "week_children", "child_commands",
    "week61_slot_children", "final_week61_slot_children", "empty_week_children",
    "final_empty_week_children",
)


def _children(payload, run_id, branch_id):
    for field in CHILD_MAPS:
        values = payload.get(field, {})
        if not isinstance(values, dict):
            raise ValueError("Full Simulation summary child scope is corrupt")
        for value in values.values():
            if value is None:
                continue  # A future slot is a placeholder until its review exists.
            command = value.get("command", value) if isinstance(value, dict) else value
            if isinstance(command, dict):
                if (command.get("run_id", run_id) != run_id
                        or command.get("branch_id", branch_id) != branch_id):
                    raise ValueError("Full Simulation summary child scope is corrupt")
                command = command.get("command_id")
            if not isinstance(command, str) or not command:
                raise ValueError("Full Simulation summary child identity is corrupt")
            yield command
    for field in ("slot_child_command_ids", "week_child_command_ids", "season_child_command_ids",
                  "child_command_ids", "empty_week_child_command_ids", "week61_slot_child_command_ids"):
        values = payload.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError("Full Simulation summary completed child identities are corrupt")
        yield from values


def capture_terminal_summary(session, receipt, frozen, position):
    """Called under the terminal writer lock; persist this in the parent atomically."""
    run_id, branch_id = receipt.run_id, receipt.branch_id
    seen, observed = {receipt.command_id}, set()
    pending = list(_children(frozen, run_id, branch_id))
    while pending:
        command_id = pending.pop()
        if command_id in seen:
            raise ValueError("Full Simulation summary child graph is cyclic or duplicated")
        seen.add(command_id)
        row = session.get(AuthoritativeSimulationCommandModel, (run_id, branch_id, command_id))
        if row is None:
            continue  # A frozen child command may not have executed yet.
        payload = json.loads(row.result_json)
        if (payload.get("run_id", run_id) != run_id
                or payload.get("branch_id", branch_id) != branch_id):
            raise ValueError("Full Simulation summary child receipt scope is corrupt")
        observed.add(command_id)
        pending.extend(_children(payload, run_id, branch_id))

    tournaments = []
    rows = session.scalars(select(OwnedTournamentRankingSourceModel).where(
        OwnedTournamentRankingSourceModel.run_id == run_id,
        OwnedTournamentRankingSourceModel.branch_id == branch_id,
    ).order_by(OwnedTournamentRankingSourceModel.edition_id)).all()
    for row in rows:
        if row.adopted_by_command_id not in observed:
            continue
        source = OwnedTournamentRankingSourceStore(session).get(
            run_id=run_id, branch_id=branch_id, edition_id=row.edition_id)
        if source.adopted_by_command_id != row.adopted_by_command_id:
            raise ValueError("Full Simulation summary tournament owner is corrupt")
        result = source.canonical_result or (source.result.summary if source.result else None)
        if result is None:
            raise ValueError("Full Simulation summary tournament result is unavailable")
        tournaments.append({
            "event_id": row.event_id, "edition_id": row.edition_id,
            "completed_week": source.binding.completed_week.model_dump(mode="json"),
            "champion_player_id": result.champion_player_id,
            "finalist_player_id": result.finalist_player_id,
            "source_fingerprint": row.source_fingerprint,
            "source_command_id": row.adopted_by_command_id,
        })
    events = frozen.get("control_events", []) if receipt.status == "stopped" else frozen.get("target_events", [])
    terminal_event = next((event for event in reversed(events)
        if receipt.status != "stopped" or event.get("action") == "stop"), None)
    if terminal_event is None:
        raise ValueError("Full Simulation terminal audit is missing")
    from beta_engine.application.full_simulation_boundary_targets import effective_boundary, validate_trigger
    boundary = effective_boundary(frozen)
    trigger = validate_trigger(frozen, frozen.get("target_trigger_evidence")) if boundary and receipt.status == "target_reached" else None
    summary = {
        "schema_version": "full_simulation_terminal_summary.v2" if boundary else "full_simulation_terminal_summary.v1",
        "run_id": run_id, "branch_id": branch_id, "command_id": receipt.command_id,
        "receipt_request_fingerprint": receipt.request_fingerprint,
        "status": receipt.status,
        "start_week": frozen["start_week"],
        "end_week": position.current_week.model_dump(mode="json"),
        "original_final_week": frozen["final_week"],
        "effective_target_week": frozen.get("effective_target_week", frozen["final_week"]),
        "target_revision": frozen.get("target_revision", 0),
        "reason": "operator_stop" if receipt.status == "stopped" else ("boundary_target_reached" if boundary else "week_target_reached"),
        "target_reached": receipt.status == "target_reached",
        "terminal_control_command_id": terminal_event["command_id"],
        "terminal_operator_label": terminal_event["operator_label"],
        "terminal_audit_reason": terminal_event["audit_reason"],
        "initial_saved_revision_id": frozen["initial_saved_revision_id"],
        "terminal_saved_revision_id": session.get(RunBranchModel, branch_id).saved_head_revision_id,
        "persisted_child_command_count": len(observed),
        "completed_tournaments": tournaments,
        "position": position.model_dump(mode="json"),
        "unavailable_sections": ["ranking_changes", "watched_events", "notifications"],
    }
    if boundary:
        summary["effective_boundary_target"] = boundary.model_dump(mode="json")
        summary["target_trigger_evidence"] = trigger
    return {**summary, "summary_fingerprint": fingerprint(summary)}


def stored_terminal_summary(receipt, frozen):
    if frozen.get("schema_version") == "authoritative_full_simulation_operation.v2":
        from beta_engine.domain.run_packages import canonical_hash
        summary = frozen.get("terminal_summary")
        if summary is None:
            return None
        if summary.get("summary_fingerprint") != canonical_hash({k: v for k, v in summary.items() if k != "summary_fingerprint"}) or (summary.get("run_id"), summary.get("branch_id"), summary.get("command_id"), summary.get("status")) != (receipt.run_id, receipt.branch_id, receipt.command_id, receipt.status):
            raise ValueError("Native terminal summary is corrupt")
        return summary
    summary = frozen.get("terminal_summary")
    if summary is None:
        return None  # Never infer a historical endpoint from the current Branch.
    if not isinstance(summary, dict):
        raise ValueError("Full Simulation terminal summary is corrupt")
    content = {k: v for k, v in summary.items() if k != "summary_fingerprint"}
    if (summary.get("schema_version") not in ("full_simulation_terminal_summary.v1", "full_simulation_terminal_summary.v2")
            or summary.get("summary_fingerprint") != fingerprint(content)
            or summary.get("run_id") != receipt.run_id
            or summary.get("branch_id") != receipt.branch_id
            or summary.get("command_id") != receipt.command_id
            or summary.get("receipt_request_fingerprint") != receipt.request_fingerprint
            or summary.get("status") != receipt.status
            or receipt.status not in ("stopped", "target_reached")
            or summary.get("start_week") != frozen.get("start_week")
            or summary.get("effective_target_week") != frozen.get("effective_target_week", frozen.get("final_week"))):
        raise ValueError("Full Simulation terminal summary identity or fingerprint is corrupt")
    from beta_engine.application.authoritative_run_simulation_driver import AuthoritativeSimulationPosition
    from beta_engine.application.global_full_simulation_operations import _week
    start = _week(summary.get("start_week"), label="summary start")
    end = _week(summary.get("end_week"), label="summary end")
    target = _week(summary.get("effective_target_week"), label="summary target")
    ordinal = lambda v: v["season_index"] * 61 + v["week"] - 1
    position = AuthoritativeSimulationPosition.model_validate_json(json.dumps(summary.get("position")))
    reached = receipt.status == "target_reached"
    from beta_engine.application.full_simulation_boundary_targets import effective_boundary, validate_trigger
    boundary = effective_boundary(frozen)
    if boundary:
        if (summary.get("schema_version") != "full_simulation_terminal_summary.v2"
                or summary.get("effective_boundary_target") != boundary.model_dump(mode="json")):
            raise ValueError("Terminal boundary selector is corrupt")
        if reached:
            trigger = validate_trigger(frozen, summary.get("target_trigger_evidence"))
            if trigger != frozen.get("target_trigger_evidence") or end != boundary.week.model_dump(mode="json"):
                raise ValueError("Terminal boundary evidence is corrupt")
    elif summary.get("schema_version") != "full_simulation_terminal_summary.v1":
        raise ValueError("Unexpected terminal boundary schema")
    events = frozen.get("target_events", []) if reached else frozen.get("control_events", [])
    event = next((value for value in reversed(events) if reached or value.get("action") == "stop"), {})
    if (position.run_id != receipt.run_id or position.branch_id != receipt.branch_id
            or position.current_week.model_dump(mode="json") != end
            or ordinal(end) < ordinal(start) or ordinal(target) < ordinal(start)
            or summary.get("original_final_week") != frozen.get("final_week")
            or summary.get("target_revision") != frozen.get("target_revision", 0)
            or type(summary.get("target_reached")) is not bool
            or summary["target_reached"] != reached
            or summary.get("reason") != (("boundary_target_reached" if boundary else "week_target_reached") if reached else "operator_stop")
            or summary.get("terminal_control_command_id") != event.get("command_id")
            or summary.get("terminal_operator_label") != event.get("operator_label")
            or summary.get("terminal_audit_reason") != event.get("audit_reason")
            or (reached and (end != frozen.get("target_reached_week") or (not boundary and ordinal(end) < ordinal(target))))
            or type(summary.get("persisted_child_command_count")) is not int
            or summary["persisted_child_command_count"] < 0):
        raise ValueError("Full Simulation terminal summary chronology is corrupt")
    return summary


def inspect_terminal_summary(factory, *, run_id, branch_id, command_id):
    with factory() as session:
        receipt = session.get(AuthoritativeSimulationCommandModel, (run_id, branch_id, command_id))
        if receipt is None:
            raise ValueError("Full Simulation parent was not found")
        frozen = json.loads(receipt.result_json)
        if frozen.get("schema_version") == "authoritative_full_simulation_operation.v2":
            from beta_engine.application.native_full_simulation import validate_native_parent
            validate_native_parent(session, receipt, frozen)
            summary = stored_terminal_summary(receipt, frozen)
            return {"schema_version": "full_simulation_terminal_summary_response.v2", "run_id": run_id,
                "branch_id": branch_id, "command_id": command_id, "status": receipt.status,
                "available": summary is not None, "summary": summary}
        if frozen.get("schema_version") not in (
            "authoritative_full_simulation_operation.v1", "authoritative_full_simulation_result.v1",
        ):
            raise ValueError("Target command is not a Full Simulation parent")
        if frozen.get("schema_version") == "authoritative_full_simulation_operation.v1":
            from beta_engine.application.authoritative_run_simulation_driver import AuthoritativeFullSimulationCommand
            command = AuthoritativeFullSimulationCommand.model_validate(frozen["resume_command"])
            if ((command.run_id, command.branch_id, command.command_id) != (run_id, branch_id, command_id)
                    or receipt.request_fingerprint != fingerprint({"mode": "full_simulation", "command": command.model_dump(mode="json")})):
                raise ValueError("Full Simulation original command identity is corrupt")
        summary = stored_terminal_summary(receipt, frozen)
        return {
            "schema_version": "full_simulation_terminal_summary_response.v1",
            "run_id": run_id, "branch_id": branch_id, "command_id": command_id,
            "status": receipt.status, "available": summary is not None, "summary": summary,
        }
