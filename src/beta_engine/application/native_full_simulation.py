"""Versioned server-task orchestration over the real calendar-native Tour.

V1 commands and RankingWeek keep their historical meaning. V2 freezes the
original Saved calendar, target and seed; each child is durably reviewed before
calling the existing sporting writer. No child approves Entry/results or Saves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select, text

from beta_engine.application.calendar_tour_service import (
    CalendarTourCommand,
    CalendarTourCommit,
    CalendarTourService,
)
from beta_engine.application.run_calendar_read_authority import (
    resolve_revision_run_calendar,
    resolve_saved_run_calendar,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.full_simulation_execution_guard import (
    ACTIVE_FULL_SIMULATION_GUARD,
    FullSimulationExecutionGuard,
    FullSimulationPauseRequested,
    FullSimulationStopped,
)
from beta_engine.infrastructure.db.full_simulation_invocation_lease import (
    require_invocation_lease_owner,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)

COMMAND_SCHEMA = "authoritative_full_simulation_command.v2"
OPERATION_SCHEMA = "authoritative_full_simulation_operation.v2"


class NativeWeek(FrozenInput):
    season_index: int = Field(strict=True, ge=0)
    week: int = Field(strict=True, ge=1)

    def ordinal(self, calendar):
        return calendar.ordinal(self.season_index, self.week)


class NativeFullSimulationPreview(FrozenInput):
    schema_version: Literal["authoritative_full_simulation_command.v2"] = COMMAND_SCHEMA
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_week: NativeWeek | None = None
    seed: int = Field(strict=True, ge=0, le=2**53 - 1)
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def audit(self):
        if not self.operator_label.strip() or not self.audit_reason.strip():
            raise ValueError("An operator and audit reason are required")
        if self.operator_label != self.operator_label.strip() or self.audit_reason != self.audit_reason.strip():
            raise ValueError("Audit fields must be trimmed")
        return self


class NativeFullSimulationCommand(NativeFullSimulationPreview):
    execution_calendar: dict
    expected_start_week: NativeWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def clock_and_target(self):
        clock = RunCalendar.from_metadata(self.execution_calendar)
        start = self.expected_start_week.ordinal(clock)
        if self.target_week is not None and self.target_week.ordinal(clock) < start:
            raise ValueError("Target precedes the reviewed start")
        return self


def parse_full_simulation_command(value):
    if value.get("schema_version") == COMMAND_SCHEMA:
        return NativeFullSimulationCommand.model_validate(value)
    from beta_engine.application.authoritative_run_simulation_driver import (
        AuthoritativeFullSimulationCommand,
    )
    return AuthoritativeFullSimulationCommand.model_validate(value)


def native_context(repository, session, run_id, branch_id):
    """Authenticate actual Saved/live sources within the caller's transaction."""
    branch = session.get(RunBranchModel, branch_id)
    run = session.get(RunContainerModel, run_id)
    if not branch or not run or branch.run_id != run_id:
        raise ValueError("Native simulation requires the exact Run/Branch")
    revision = repository._validated_branch_revision_state_in_session(session=session, branch=branch)
    draft = session.get(BranchWorkingDraftModel, revision.working_draft.draft_id)
    clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
    if revision.saved_revision.payload_schema_version == "native_fork_saved_root.v2":
        from beta_engine.application.native_fork_runtime_service import (
            NativeForkRuntimeService,
        )
        service = NativeForkRuntimeService(repository)
        ctx = service._context(session, run_id, branch_id)
        _run, _branch, rev, working, signed, current, _original, sources = ctx
        view = service._inspection(rev, working, signed, current, sources)
        state = current.tour
        cp_fingerprint = current.checkpoint_fingerprint
        saved = view["saved"]
        tour_fingerprint = view["tour_fingerprint"]
        blockers = view["season_transition_blockers"] if state.week.week == clock.weeks_per_year else view["transition_blockers"]
    else:
        service = CalendarTourService(repository)
        ctx, state, signed = service._context(session, run_id, branch_id)
        checkpoint = ctx[4]
        if state is None or checkpoint is None:
            raise ValueError("Native Full Simulation requires an initialized Saved Tour and sporting population")
        cp_fingerprint = checkpoint.fingerprint
        saved = checkpoint == ctx[5] and state == signed and draft.status == "clean"
        tour_fingerprint = state.fingerprint
        blockers = service._transition_blockers(state, ctx, session, season=state.week.week == clock.weeks_per_year)
    week = NativeWeek(season_index=state.week.season_index, week=state.week.week)
    # A strict extension may change the current envelope; time scale stays fixed.
    week.ordinal(clock)
    body = {
        "week": week.model_dump(mode="json"), "saved_head_revision_id": branch.saved_head_revision_id,
        "draft_version": draft.draft_version, "checkpoint_fingerprint": cp_fingerprint,
        "tour_fingerprint": tour_fingerprint,
    }
    return {
        **body, "position_fingerprint": fingerprint(body), "calendar": clock,
        "state": state, "saved": saved, "blockers": sorted(set(blockers)),
        "draft": draft, "revision": revision.saved_revision, "run": run, "branch": branch,
    }


def _write(row, payload):
    payload["state_fingerprint"] = fingerprint({k: v for k, v in payload.items() if k != "state_fingerprint"})
    row.result_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))


def validate_native_parent(session, row, payload, command=None):
    command = command or NativeFullSimulationCommand.model_validate(payload["resume_command"])
    clock = resolve_revision_run_calendar(session, run_id=row.run_id, revision_id=command.expected_revision_id)
    if (
        payload.get("schema_version") != OPERATION_SCHEMA
        or payload.get("state_fingerprint") != fingerprint({k: v for k, v in payload.items() if k != "state_fingerprint"})
        or (command.run_id, command.branch_id, command.command_id) != (row.run_id, row.branch_id, row.command_id)
        or row.request_fingerprint != fingerprint({"mode": "full_simulation", "command": command.model_dump(mode="json")})
        or clock.to_metadata() != command.execution_calendar
        or payload["resume_command"] != command.model_dump(mode="json")
        or payload["start_week"] != command.expected_start_week.model_dump(mode="json")
        or payload["final_week"] != {"season_index": clock.season_count - 1, "week": clock.weeks_per_year}
        or payload["effective_target_week"] != (command.target_week.model_dump(mode="json") if command.target_week else payload["final_week"])
    ):
        raise ValueError("Native Full Simulation original command/source integrity failed")
    if row.status not in {"pending", "complete", "target_reached", "stopped"}:
        raise ValueError("Native Full Simulation parent status is corrupt")
    previous = None
    for index, child in enumerate(payload["children"]):
        body = {k: v for k, v in child.items() if k != "fingerprint"}
        if child["index"] != index or child["previous"] != previous or child["fingerprint"] != fingerprint(body):
            raise ValueError("Native child audit chain is corrupt")
        request = CalendarTourCommit.model_validate(child["request"])
        if request.command.command_id != child_id(command, index):
            raise ValueError("Native child command identity is corrupt")
        previous = child["fingerprint"]
    if payload.get("terminal_summary"):
        summary = payload["terminal_summary"]
        if summary["summary_fingerprint"] != fingerprint({k: v for k, v in summary.items() if k != "summary_fingerprint"}):
            raise ValueError("Native terminal summary is corrupt")
        if summary["status"] != row.status or summary["command_id"] != command.command_id:
            raise ValueError("Native terminal summary scope is corrupt")
    return command, clock


def child_id(command, index):
    return "nfs-" + fingerprint({"parent": command.model_dump(mode="json"), "child_index": index})[:56]


def _progress(command, ctx, checkpoint, *, blockers=(), detail=None):
    return {
        "schema_version": "authoritative_full_simulation_progress.v2",
        "run_id": command.run_id, "branch_id": command.branch_id,
        "command_id": command.command_id, "checkpoint": checkpoint,
        "current_week": ctx["week"], "blockers": list(blockers), "detail": detail,
    }


@dataclass
class NativeFullSimulationDriver:
    repository: object
    full_simulation_before_transaction_check: object = None

    @property
    def factory(self):
        return self.repository._session_factory

    @staticmethod
    def _require_writable_scope(session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if not run or not branch or branch.run_id != run_id or run.read_only or branch.read_only or branch.status != "active" or run.status not in {"working", "completed"}:
            raise ValueError("Native Full Simulation requires a writable active Run/Branch")

    def plan(self, session, request):
        self._require_writable_scope(session, request.run_id, request.branch_id)
        pending = session.scalars(select(AuthoritativeSimulationCommandModel).where(
            AuthoritativeSimulationCommandModel.run_id == request.run_id,
            AuthoritativeSimulationCommandModel.branch_id == request.branch_id,
            AuthoritativeSimulationCommandModel.status == "pending",
        )).all()
        if any(json.loads(r.result_json).get("schema_version") in {OPERATION_SCHEMA, "authoritative_full_simulation_operation.v1"} for r in pending):
            raise ValueError("This Branch already has a pending Full Simulation; continue its original task")
        ctx = native_context(self.repository, session, request.run_id, request.branch_id)
        if not ctx["saved"]:
            raise ValueError("Manual Save is required before Full Simulation review")
        clock = ctx["calendar"]
        current = NativeWeek.model_validate(ctx["week"]).ordinal(clock)
        if request.target_week is not None and request.target_week.ordinal(clock) < current:
            raise ValueError("Target precedes the current week")
        body = {
            "schema_version": "authoritative_full_simulation_preview.v2",
            "request": request.model_dump(mode="json"), "execution_calendar": clock.to_metadata(),
            "start_week": ctx["week"],
            "final_week": {"season_index": clock.season_count - 1, "week": clock.weeks_per_year},
            "target_week": request.target_week.model_dump(mode="json") if request.target_week else None,
            "target_semantics": "open_target_week" if request.target_week else "saved_final_run_closure",
            "expected_position_fingerprint": ctx["position_fingerprint"],
            "expected_revision_id": ctx["saved_head_revision_id"],
            "initial_transition_blockers": ctx["blockers"],
            "manual_save_required_after_each_sporting_child": True,
        }
        return {**body, "preview_fingerprint": fingerprint(body)}

    def preview(self, request):
        with self.factory() as session:
            session.execute(text("BEGIN"))
            return self.plan(session, request)

    def prepare_full_simulation(self, session, command, request_fp):
        row = session.get(AuthoritativeSimulationCommandModel, (command.run_id, command.branch_id, command.command_id))
        if row:
            payload = json.loads(row.result_json)
            validate_native_parent(session, row, payload, command)
            return payload.get("terminal_summary") if row.status != "pending" else None
        plan = self.plan(session, NativeFullSimulationPreview.model_validate({k: v for k, v in command.model_dump(mode="json").items() if k in NativeFullSimulationPreview.model_fields}))
        if (plan["preview_fingerprint"] != command.expected_preview_fingerprint or plan["expected_position_fingerprint"] != command.expected_position_fingerprint or plan["expected_revision_id"] != command.expected_revision_id or plan["start_week"] != command.expected_start_week.model_dump(mode="json") or plan["execution_calendar"] != command.execution_calendar):
            raise ValueError("Native Full Simulation review is stale")
        payload = {
            "schema_version": OPERATION_SCHEMA, "resume_command": command.model_dump(mode="json"),
            "run_id": command.run_id, "branch_id": command.branch_id,
            "start_week": plan["start_week"], "final_week": plan["final_week"],
            "effective_target_week": plan["target_week"] or plan["final_week"],
            "children": [], "pending_child": None, "control_events": [], "control_state": "running",
            "initial_saved_revision_id": command.expected_revision_id,
        }
        row = AuthoritativeSimulationCommandModel(run_id=command.run_id, branch_id=command.branch_id,
            command_id=command.command_id, request_fingerprint=request_fp, status="pending")
        _write(row, payload)
        session.add(row)
        return None

    def _parent(self, session, command):
        row = session.get(AuthoritativeSimulationCommandModel, (command.run_id, command.branch_id, command.command_id))
        if row is None:
            raise ValueError("Native Full Simulation parent is missing")
        payload = json.loads(row.result_json)
        validate_native_parent(session, row, payload)
        return row, payload

    def _terminal(self, row, payload, command, ctx, status):
        row.status = status
        summary = {
            "schema_version": "full_simulation_terminal_summary.v3", "status": status,
            "run_id": command.run_id, "branch_id": command.branch_id, "command_id": command.command_id,
            "start_week": payload["start_week"], "end_week": ctx["week"],
            "original_final_week": payload["final_week"], "effective_target_week": payload["effective_target_week"],
            "execution_calendar": command.execution_calendar,
            "initial_saved_revision_id": command.expected_revision_id,
            "terminal_saved_revision_id": ctx["saved_head_revision_id"],
            "persisted_child_command_count": len(payload["children"]),
            "reason": "run_completed" if status == "complete" else "week_target_reached" if status == "target_reached" else "operator_stop",
            "target_reached": status == "target_reached",
            "completed_tournaments": [a.edition.edition_id for a in ctx["state"].editions if a.result_confirmed],
        }
        payload["terminal_summary"] = {**summary, "summary_fingerprint": fingerprint(summary)}
        _write(row, payload)
        return _progress(command, ctx, status)

    def simulate_full_simulation(self, command, *, execution_lease_token):
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            require_invocation_lease_owner(session, token=execution_lease_token)
            row, payload = self._parent(session, command)
            ctx = native_context(self.repository, session, command.run_id, command.branch_id)
            if row.status != "pending":
                return _progress(command, ctx, row.status)
            if payload["control_state"] in {"paused", "pause_requested"}:
                payload["control_state"] = "paused"
                _write(row, payload)
                return _progress(command, ctx, "operator_paused")
            current = NativeWeek.model_validate(ctx["week"]).ordinal(RunCalendar.from_metadata(command.execution_calendar))
            target = command.target_week
            if target is not None and current >= target.ordinal(RunCalendar.from_metadata(command.execution_calendar)):
                return self._terminal(row, payload, command, ctx, "target_reached")
            if payload["pending_child"] is None:
                if not ctx["saved"]:
                    return _progress(command, ctx, "native_manual_save_required", detail="Explicitly Save the sporting/Tour draft, then resume this same task.")
                state = ctx["state"]
                pending = sorted((a for a in state.editions if a.edition.week.ordinal <= state.week.ordinal and not a.result_confirmed), key=lambda a: (a.edition.week.ordinal, a.edition.start_slot, a.edition.edition_id))
                authority = pending[0] if pending else None
                if authority:
                    if not authority.draw:
                        return _progress(command, ctx, "native_entry_review_required", blockers=["entry_draw_required:" + authority.edition.edition_id], detail="Review Entry, approve the field/draw and manually Save in Run Admin.")
                    if authority.tournament_fingerprint:
                        return _progress(command, ctx, "native_result_review_required", blockers=["result_confirmation_required:" + authority.edition.edition_id], detail="Review and explicitly confirm the played results, then manually Save.")
                    action = "play"
                else:
                    clock = RunCalendar.from_metadata(command.execution_calendar)
                    if current == clock.season_count * clock.weeks_per_year - 1:
                        return _progress(command, ctx, "native_final_closure_review_required", detail="Review final native Run closure; confirmation and manual final Save are separate operator actions.")
                    action = "season-transition" if state.week.week == clock.weeks_per_year else "transition"
                    if ctx["blockers"]:
                        return _progress(command, ctx, "native_transition_review_required", blockers=ctx["blockers"])
                child = CalendarTourCommand(action=action, command_id=child_id(command, len(payload["children"])),
                    expected_saved_head=ctx["saved_head_revision_id"], expected_checkpoint_fingerprint=ctx["checkpoint_fingerprint"],
                    expected_tour_fingerprint=ctx["tour_fingerprint"], edition_id=authority.edition.edition_id if authority else None,
                    seed=int(fingerprint({"root_seed": command.seed, "child": child_id(command, len(payload["children"]))})[:12], 16),
                    operator_label=command.operator_label, audit_reason=command.audit_reason)
            else:
                child = CalendarTourCommit.model_validate(payload["pending_child"]).command
        service = CalendarTourService(self.repository)
        if payload["pending_child"] is None:
            review = service.preview(run_id=command.run_id, branch_id=command.branch_id, command=child)
            request = CalendarTourCommit(command=child, expected_preview_fingerprint=review["preview_fingerprint"], explicit_confirmation=True)
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                require_invocation_lease_owner(session, token=execution_lease_token)
                row, payload = self._parent(session, command)
                if payload["control_state"] != "running":
                    return _progress(command, ctx, "operator_paused")
                if payload["pending_child"] is not None:
                    raise ValueError("Concurrent native child review")
                payload["pending_child"] = request.model_dump(mode="json")
                _write(row, payload)
        else:
            request = CalendarTourCommit.model_validate(payload["pending_child"])
        guard = FullSimulationExecutionGuard(command.run_id, command.branch_id, command.command_id,
            fingerprint({"mode": "full_simulation", "command": command.model_dump(mode="json")}), execution_lease_token,
            self.full_simulation_before_transaction_check)
        token = ACTIVE_FULL_SIMULATION_GUARD.set(guard)
        try:
            result = service.execute(run_id=command.run_id, branch_id=command.branch_id, request=request)
        except (FullSimulationPauseRequested, FullSimulationStopped):
            return self.simulate_full_simulation(command, execution_lease_token=execution_lease_token)
        finally:
            ACTIVE_FULL_SIMULATION_GUARD.reset(token)
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            require_invocation_lease_owner(session, token=execution_lease_token)
            row, payload = self._parent(session, command)
            if payload["pending_child"] != request.model_dump(mode="json"):
                raise ValueError("Native pending child identity changed")
            child = {"index": len(payload["children"]), "previous": payload["children"][-1]["fingerprint"] if payload["children"] else None,
                "request": request.model_dump(mode="json"), "result_fingerprint": fingerprint(result)}
            payload["children"].append({**child, "fingerprint": fingerprint(child)})
            payload["pending_child"] = None
            _write(row, payload)
            ctx = native_context(self.repository, session, command.run_id, command.branch_id)
            return _progress(command, ctx, "native_manual_save_required")

    def control_full_simulation_in_session(self, session, command):
        row = session.get(AuthoritativeSimulationCommandModel, (command.run_id, command.branch_id, command.target_command_id))
        if row is None:
            raise ValueError("Native parent is missing")
        payload = json.loads(row.result_json)
        original, _clock = validate_native_parent(session, row, payload)
        body = command.model_dump(mode="json")
        for event in payload["control_events"]:
            if event["control_command_id"] == command.control_command_id:
                if event != body:
                    raise ValueError("Native control retry differs")
                return {"control_state": payload["control_state"], "status": row.status}
        if row.status != "pending":
            raise ValueError("Terminal native parent cannot be controlled")
        payload["control_events"].append(body)
        payload["control_state"] = {"pause": "pause_requested", "resume": "running", "stop": "stopped"}[command.action]
        if command.action == "stop":
            ctx = native_context(self.repository, session, command.run_id, command.branch_id)
            return self._terminal(row, payload, original, ctx, "stopped")
        _write(row, payload)
        return {"control_state": payload["control_state"], "status": row.status}

    def control(self, command):
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            return self.control_full_simulation_in_session(session, command)
