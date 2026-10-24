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
from beta_engine.domain.run_packages import canonical_hash
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


def _fault_injection_point(name):
    """Crash/retry seam; never supplies or changes sporting outcomes."""


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
    audit_reason: str = Field(min_length=1, max_length=1000)

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
        if clock.schema_version != "run_calendar.v1":
            raise ValueError("Native Full Simulation requires an explicit Saved Run calendar")
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
    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        native_read_proof_scope,
    )
    with native_read_proof_scope():
        return _native_context(repository, session, run_id, branch_id)


def _native_context(repository, session, run_id, branch_id):
    branch = session.get(RunBranchModel, branch_id)
    run = session.get(RunContainerModel, run_id)
    if not branch or not run or branch.run_id != run_id:
        raise ValueError("Native simulation requires the exact Run/Branch")
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
    head = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
    if head is None:
        raise ValueError("Native Full Simulation requires its immutable Saved HEAD")
    if head.payload_schema_version == "native_fork_saved_root.v2":
        from beta_engine.application.native_fork_runtime_service import (
            NativeForkRuntimeService,
        )
        service = NativeForkRuntimeService(repository)
        ctx = service._context(session, run_id, branch_id)
        _run, _branch, rev, working, signed, current, _original, sources = ctx
        # The production native authority authenticates the complete physical
        # dependency graph. A second generic lineage walk and player/table
        # projection would re-prove the same history for every worker poll.
        from beta_engine.application.native_fork_runtime_reducer import (
            tour_fingerprint as native_tour_fingerprint,
        )
        from beta_engine.application.native_fork_runtime_reducer import (
            transition_blockers,
        )
        draft, revision = working, rev
        clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
        state = current.tour
        from beta_engine.domain.native_fork_runtime import ForkCompetitionView
        competition = ForkCompetitionView(current, sources.checkpoint)
        lifecycle = current.lifecycle
        cp_fingerprint = current.checkpoint_fingerprint
        saved = current == signed and draft.status == "clean"
        tour_fingerprint = native_tour_fingerprint(current, draft.draft_version)
        blockers = transition_blockers(current, season=state.week.week == clock.weeks_per_year, calendar=clock)
    else:
        service = CalendarTourService(repository)
        ctx, state, signed = service._context(session, run_id, branch_id)
        clock, revision_state = ctx[:2]
        revision = revision_state.saved_revision
        draft = session.get(BranchWorkingDraftModel, revision_state.working_draft.draft_id)
        checkpoint = ctx[4]
        if state is None or checkpoint is None:
            raise ValueError("Native Full Simulation requires an initialized Saved Tour and sporting population")
        cp_fingerprint = checkpoint.fingerprint
        competition = checkpoint
        from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
        lifecycle = get_lifecycle(session, run_id=run_id, branch_id=branch_id, week=state.week)
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
        "draft": draft, "revision": revision, "run": run, "branch": branch,
        "competition": competition, "lifecycle": lifecycle,
    }


def read_native_task_progress(session, *, run_id, branch_id, parent):
    """Hash-checked read projection, never a sporting execution/Save authority.

    Like legacy task progress, this counts actual persisted Branch receipts.
    Polling must not replay MatchEngine or re-prove every historical match. The
    production native context still performs that proof before every writer.
    Sporting components use their canonical UTF-8 hash; the task control/audit
    keeps its existing fingerprint contract. Unicode must not mix the two.
    """
    from beta_engine.infrastructure.db.models import (
        BranchSavedRevisionModel,
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError("Native task progress Branch is unavailable")
    available_clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
    head = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
    if head.payload_schema_version == "native_fork_saved_root.v2":
        saved = json.loads(head.payload_json)["content"]["native_fork_runtime"]
        component = saved
        draft = session.scalar(select(BranchWorkingDraftModel).where(BranchWorkingDraftModel.branch_id == branch_id))
        if draft is None or draft.base_revision_id != head.revision_id:
            raise ValueError("Native task progress Working Draft source is corrupt")
        if draft.status == "dirty" and draft.draft_schema_version == "native_fork_runtime_draft.v1":
            changes = json.loads(draft.changes_json)
            if len(changes) != 1 or changes[0].get("kind") != "native_fork_runtime" or draft.change_count != 1:
                raise ValueError("Native task progress Working Draft is malformed")
            component = changes[0]["component"]
            if component["state"]["baseline"] != saved["state"]["baseline"] or component["state"]["root_saved_revision_id"] != saved["state"]["root_saved_revision_id"]:
                raise ValueError("Native task progress Working Draft changed its original source")
        state = component["state"]
        if set(component) != {"state", "fingerprint"} or component["fingerprint"] != canonical_hash(state) or state["schema_version"] not in {"native_fork_runtime.v1", "native_fork_runtime.v2"}:
            raise ValueError("Native task progress runtime hash/schema is corrupt")
        tour = state["tour"]
        if state["lifecycle"]["week"] != tour["week"] or tour["schema_version"] != "native_fork_tour.v1":
            raise ValueError("Native task progress aggregate has inconsistent current time")
        source_fingerprint = component["fingerprint"]
    else:
        checkpoint_row = session.get(CalendarPlayerSportingCheckpointModel, (run_id, branch_id))
        tour_row = session.get(CalendarTourAuthorityModel, (run_id, branch_id))
        if checkpoint_row is None or tour_row is None:
            raise ValueError("Native task progress lacks its sporting/Tour owner")
        state, tour = json.loads(checkpoint_row.payload_json), json.loads(tour_row.payload_json)
        if state.get("schema_version") not in {f"calendar_sporting_checkpoint.v{i}" for i in range(1, 14)} or tour.get("schema_version") not in {f"calendar_tour_authority.v{i}" for i in range(1, 6)}:
            raise ValueError("Native task progress sporting/Tour schema is unsupported")
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import parse_checkpoint_json
        from beta_engine.domain.tournaments.calendar_tour import parse_tour_json
        parse_tour_json(tour_row.payload_json)
        actual_week = parse_checkpoint_json(checkpoint_row.payload_json).week.model_dump(mode="json") if state["schema_version"] in {"calendar_sporting_checkpoint.v11", "calendar_sporting_checkpoint.v12", "calendar_sporting_checkpoint.v13"} else state["week"]
        if canonical_hash(state) != checkpoint_row.fingerprint or canonical_hash(tour) != tour_row.fingerprint or tour["checkpoint_fingerprint"] != checkpoint_row.fingerprint or actual_week != tour["week"]:
            raise ValueError("Native task progress sporting/Tour hash or position is corrupt")
        source_fingerprint = fingerprint({"checkpoint": checkpoint_row.fingerprint, "tour": tour_row.fingerprint})
    owner = state.get("baseline", state)
    if (owner.get("run_id"), owner.get("branch_id"), tour.get("run_id"), tour.get("branch_id")) != (run_id, branch_id, run_id, branch_id):
        raise ValueError("Native task progress has a foreign owner")
    receipts = {r["command_id"]: r for r in tour["receipts"]}
    for child in parent["children"]:
        actual = receipts.get(child["request"]["command"]["command_id"])
        if actual is None or actual["request"] != child["request"] or fingerprint(actual["result"]) != child["result_fingerprint"]:
            raise ValueError("Native task progress child differs from persisted sporting receipts")
    clock = RunCalendar.from_metadata(parent["resume_command"]["execution_calendar"])
    source_clock = RunCalendar.from_metadata(tour["week"]["calendar"])
    if (source_clock.weeks_per_year, source_clock.season_start_year_week, source_clock.start_year) != (clock.weeks_per_year, clock.season_start_year_week, clock.start_year) or source_clock.season_count > available_clock.season_count:
        raise ValueError("Native task progress clock is foreign to the original Run basis")
    week = NativeWeek.model_validate({k: tour["week"][k] for k in ("season_index", "week")})
    ordinal = week.ordinal(clock)
    editions = {a["edition"]["edition_id"]: a for a in tour["editions"]
        if (a["edition"]["week"]["season_index"], a["edition"]["week"]["week"]) == (week.season_index, week.week)}
    match_ids = []
    for receipt in receipts.values():
        action = receipt["request"]["command"]
        if action["action"] in {"next-slot", "next-match"} and receipt["result"]["week"]["season_index"] == week.season_index and receipt["result"]["week"]["week"] == week.week:
            match_ids.extend(receipt["result"]["match_ids"])
        if action["action"] == "play" and action.get("edition_id") in editions:
            ids = receipt["result"]["played"]["match_ids"]
            if not isinstance(ids, list) or any(not isinstance(i, str) or not i for i in ids):
                raise ValueError("Native task progress match receipt is corrupt")
            match_ids.extend(ids)
    if len(match_ids) != len(set(match_ids)):
        raise ValueError("Native task progress has duplicate played match receipts")
    count = len(match_ids)
    return ordinal, count, source_fingerprint


def _write(row, payload):
    payload["state_fingerprint"] = fingerprint({k: v for k, v in payload.items() if k != "state_fingerprint"})
    row.result_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))


def validate_native_parent(session, row, payload, command=None):
    if not isinstance(payload, dict) or not isinstance(payload.get("review"), dict) or not isinstance(payload.get("children"), list) or not isinstance(payload.get("control_events"), list):
        raise TypeError("Native Full Simulation parent shape is corrupt")
    command = command or NativeFullSimulationCommand.model_validate(payload["resume_command"])
    clock = resolve_revision_run_calendar(session, run_id=row.run_id, revision_id=command.expected_revision_id)
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
    source = session.get(BranchSavedRevisionModel, command.expected_revision_id)
    review = payload.get("review", {})
    if (
        payload.get("schema_version") != OPERATION_SCHEMA
        or payload.get("state_fingerprint") != fingerprint({k: v for k, v in payload.items() if k != "state_fingerprint"})
        or (command.run_id, command.branch_id, command.command_id) != (row.run_id, row.branch_id, row.command_id)
        or row.request_fingerprint != fingerprint({"mode": "full_simulation", "command": command.model_dump(mode="json")})
        or clock.to_metadata() != command.execution_calendar
        or source.content_hash != review.get("source_content_hash")
        or review.get("preview_fingerprint") != command.expected_preview_fingerprint
        or fingerprint({k: v for k, v in review.items() if k != "preview_fingerprint"}) != command.expected_preview_fingerprint
        or review.get("expected_revision_id") != command.expected_revision_id
        or review.get("expected_position_fingerprint") != command.expected_position_fingerprint
        or review.get("start_week") != command.expected_start_week.model_dump(mode="json")
        or review.get("execution_calendar") != command.execution_calendar
        or review.get("final_week") != {"season_index": clock.season_count - 1, "week": clock.weeks_per_year}
        or review.get("request") != {k: v for k, v in command.model_dump(mode="json").items() if k in NativeFullSimulationPreview.model_fields}
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
        request = validate_native_child(command, index, child["request"])
        if request.command.action == "season-transition":
            approval = child.get("operator_approval")
            if not isinstance(approval, dict) or approval.get("review_fingerprint") != request.expected_preview_fingerprint or approval.get("explicit_confirmation") is not True or not approval.get("operator_label") or not approval.get("audit_reason"):
                raise ValueError("Native Season Transition lost its explicit operator approval")
            closure = child.get("season_closure", {})
            if closure.get("source_revision_id") != request.command.expected_saved_head or closure.get("checkpoint_fingerprint") != request.command.expected_checkpoint_fingerprint:
                raise ValueError("Native Season Transition lost its exact outgoing closing authority")
        previous = child["fingerprint"]
    if payload.get("pending_child") is not None:
        validate_native_child(command, len(payload["children"]), payload["pending_child"])
    if payload.get("terminal_summary"):
        summary = payload["terminal_summary"]
        if summary["summary_fingerprint"] != fingerprint({k: v for k, v in summary.items() if k != "summary_fingerprint"}):
            raise ValueError("Native terminal summary is corrupt")
        if summary["status"] != row.status or summary["command_id"] != command.command_id:
            raise ValueError("Native terminal summary scope is corrupt")
        end = NativeWeek.model_validate(summary["end_week"]).ordinal(clock)
        start = command.expected_start_week.ordinal(clock)
        if (summary.get("run_id"), summary.get("branch_id"), summary.get("start_week"), summary.get("execution_calendar"), summary.get("original_final_week"), summary.get("effective_target_week")) != (
            row.run_id, row.branch_id, payload["start_week"], command.execution_calendar, payload["final_week"], payload["effective_target_week"]
        ) or end < start or summary.get("persisted_child_command_count") != len(payload["children"]):
            raise ValueError("Native terminal summary chronology/source is corrupt")
        if row.status == "target_reached" and (command.target_week is None or end != command.target_week.ordinal(clock)):
            raise ValueError("Native terminal summary does not reach its exact frozen target")
        if row.status == "complete" and (command.target_week is not None or end != clock.season_count * clock.weeks_per_year - 1 or "closure_save" not in payload):
            raise ValueError("Native completed parent has no original final Saved closure")
        if row.status == "complete":
            from beta_engine.application.native_full_simulation_closure import (
                saved_native_closure,
            )
            saved_id = payload["closure_save"]["revision_id"]
            closing_clock = resolve_revision_run_calendar(session, run_id=row.run_id, revision_id=saved_id)
            saved_row = session.get(BranchSavedRevisionModel, saved_id)
            marker = saved_native_closure(json.loads(saved_row.payload_json), branch_id=row.branch_id, calendar=clock)
            if marker is None or closing_clock != clock or marker["fingerprint"] != payload["closure_save"]["marker_fingerprint"] or summary["terminal_saved_revision_id"] != saved_id:
                raise ValueError("Native completion lost its exact immutable final Saved marker")
            resolve_revision_run_calendar(session, run_id=row.run_id, revision_id=marker["source_revision_id"])
            terminal_source = session.get(BranchSavedRevisionModel, marker["source_revision_id"])
            if terminal_source.content_hash != marker["source_content_hash"]:
                raise ValueError("Native completion source changed after final Save")
    elif row.status != "pending":
        raise ValueError("Native terminal parent is missing its frozen summary")
    return command, clock


def child_id(command, index):
    return "nfs-" + fingerprint({"parent": command.model_dump(mode="json"), "child_index": index})[:56]


def child_seed(command, index):
    return int(fingerprint({"root_seed": command.seed, "child": child_id(command, index)})[:12], 16)


def validate_native_child(command, index, value):
    request = CalendarTourCommit.model_validate(value)
    child = request.command
    if child.action not in {"play", "next-slot", "transition", "season-transition"} or child.data:
        raise ValueError("Native task child is not a supported sporting action")
    if (child.command_id, child.seed, child.operator_label, child.audit_reason) != (
        child_id(command, index), child_seed(command, index), command.operator_label, command.audit_reason
    ):
        raise ValueError("Native child differs from its immutable parent seed/audit identity")
    return request


def append_child(payload, request, result):
    child = {"index": len(payload["children"]), "previous": payload["children"][-1]["fingerprint"] if payload["children"] else None,
        "request": request, "result_fingerprint": fingerprint(result)}
    if request["command"]["action"] == "season-transition":
        child["operator_approval"] = payload.get("pending_child_approval")
        child["season_closure"] = payload.get("pending_child_season_closure")
    payload["children"].append({**child, "fingerprint": fingerprint(child)})
    payload["pending_child"] = None
    payload.pop("pending_child_approval", None)
    payload.pop("pending_child_season_closure", None)


def authenticate_children(payload, ctx):
    receipts = {r.command_id: r for r in ctx["state"].receipts}
    for child in payload["children"]:
        receipt = receipts.get(child["request"]["command"]["command_id"])
        if receipt is None or receipt.request != child["request"] or fingerprint(receipt.result) != child["result_fingerprint"]:
            raise ValueError("Native task child differs from actual sporting receipts")


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
        from beta_engine.application.native_full_simulation_closure import (
            saved_native_closure,
        )
        if saved_native_closure(ctx["revision"].payload, branch_id=request.branch_id, calendar=ctx["calendar"]):
            raise ValueError("This Branch has a Saved final Run closure; extend the Run before new simulation")
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
            "source_content_hash": ctx["revision"].content_hash,
            "initial_transition_blockers": ctx["blockers"],
            "manual_save_required_after_each_sporting_child": True,
            "season_transition_requires_separate_review": True,
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
            "review": plan,
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
        if payload["pending_child"]:
            request = payload["pending_child"]
            receipt = next((r for r in ctx["state"].receipts if r.command_id == request["command"]["command_id"]), None)
            if receipt:
                if receipt.request != request:
                    raise ValueError("Native terminal pending child conflicts with actual receipt")
                append_child(payload, request, receipt.result)
        authenticate_children(payload, ctx)
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
            "completed_tournaments": [a.edition.edition_id for a in ctx["state"].editions if a.result_confirmed and any(
                (c["request"]["command"]["action"] == "play" and c["request"]["command"]["edition_id"] == a.edition.edition_id)
                or (c["request"]["command"]["action"] in {"next-slot", "next-match"} and any(
                    mid.startswith(a.edition.edition_id + ":") for r in ctx["state"].receipts if r.command_id == c["request"]["command"]["command_id"] for mid in r.result.get("match_ids", [])))
                for c in payload["children"])],
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
            authenticate_children(payload, ctx)
            if row.status != "pending":
                return _progress(command, ctx, row.status)
            if payload["control_state"] in {"paused", "pause_requested"}:
                payload["control_state"] = "paused"
                _write(row, payload)
                return _progress(command, ctx, "operator_paused")
            if payload["pending_child"] is None and not ctx["saved"]:
                return _progress(command, ctx, "native_manual_save_required", detail="Explicitly Save the sporting/Tour draft, then resume this same task.")
            current = NativeWeek.model_validate(ctx["week"]).ordinal(RunCalendar.from_metadata(command.execution_calendar))
            target = command.target_week
            if target is not None and current > target.ordinal(RunCalendar.from_metadata(command.execution_calendar)):
                raise ValueError("The Branch passed this task's frozen target outside its execution; inspect the original task")
            if target is not None and current == target.ordinal(RunCalendar.from_metadata(command.execution_calendar)):
                return self._terminal(row, payload, command, ctx, "target_reached")
            if payload["pending_child"] is None:
                state = ctx["state"]
                pending = sorted((a for a in state.editions if a.edition.week.ordinal <= state.week.ordinal and not a.result_confirmed), key=lambda a: (a.edition.week.ordinal, a.edition.start_slot, a.edition.edition_id))
                authority = pending[0] if pending else None
                if authority:
                    if not authority.draw:
                        return _progress(command, ctx, "native_entry_review_required", blockers=["entry_draw_required:" + authority.edition.edition_id], detail="Review Entry, approve the field/draw and manually Save in Run Admin.")
                    if authority.tournament_fingerprint:
                        return _progress(command, ctx, "native_result_review_required", blockers=["result_confirmation_required:" + authority.edition.edition_id], detail="Review and explicitly confirm the played results, then manually Save.")
                    if authority.edition.schema_version == "calendar_tournament_edition.v2":
                        current_due = [a for a in pending if a.edition.week.ordinal == state.week.ordinal and a.edition.schema_version == "calendar_tournament_edition.v2" and not a.tournament_fingerprint]
                        missing = [a.edition.edition_id for a in current_due if not a.draw]
                        if missing:
                            return _progress(command, ctx, "native_entry_review_required", blockers=["entry_draw_required:" + eid for eid in missing])
                        action = "next-slot"
                    else:
                        action = "play"
                else:
                    clock = RunCalendar.from_metadata(command.execution_calendar)
                    if current == clock.season_count * clock.weeks_per_year - 1:
                        from beta_engine.application.native_full_simulation_closure import (
                            saved_native_closure,
                        )
                        if saved_native_closure(ctx["revision"].payload, branch_id=command.branch_id, calendar=clock):
                            return self._terminal(row, payload, command, ctx, "complete")
                        return _progress(command, ctx, "native_final_closure_review_required", detail="Review final native Run closure; confirmation and manual final Save are separate operator actions.")
                    action = "season-transition" if state.week.week == clock.weeks_per_year else "transition"
                    if ctx["blockers"]:
                        return _progress(command, ctx, "native_transition_review_required", blockers=ctx["blockers"])
                child = CalendarTourCommand(action=action, command_id=child_id(command, len(payload["children"])),
                    expected_saved_head=ctx["saved_head_revision_id"], expected_checkpoint_fingerprint=ctx["checkpoint_fingerprint"],
                    expected_tour_fingerprint=ctx["tour_fingerprint"], edition_id=authority.edition.edition_id if authority and action != "next-slot" else None,
                    seed=child_seed(command, len(payload["children"])),
                    operator_label=command.operator_label, audit_reason=command.audit_reason)
            else:
                child = CalendarTourCommit.model_validate(payload["pending_child"]).command
                if child.action == "season-transition" and not payload.get("pending_child_approval"):
                    return _progress(command, ctx, "native_season_transition_review_required", detail="Review and explicitly approve this exact Season Transition, then continue the same task.")
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
                if child.action == "season-transition":
                    from beta_engine.application.native_full_simulation_closure import (
                        closure_facts,
                    )
                    payload["pending_child_season_closure"] = closure_facts(self.repository, session, ctx["revision"], final=False)
                _write(row, payload)
                if child.action == "season-transition":
                    return _progress(command, ctx, "native_season_transition_review_required", detail="Review and explicitly approve this exact Season Transition, then continue the same task.")
        else:
            request = CalendarTourCommit.model_validate(payload["pending_child"])
        guard = FullSimulationExecutionGuard(command.run_id, command.branch_id, command.command_id,
            fingerprint({"mode": "full_simulation", "command": command.model_dump(mode="json")}), execution_lease_token,
            self.full_simulation_before_transaction_check)
        token = ACTIVE_FULL_SIMULATION_GUARD.set(guard)
        interrupted = False
        try:
            result = service.execute(run_id=command.run_id, branch_id=command.branch_id, request=request)
        except (FullSimulationPauseRequested, FullSimulationStopped):
            interrupted = True
        finally:
            ACTIVE_FULL_SIMULATION_GUARD.reset(token)
        if interrupted:
            return self.simulate_full_simulation(command, execution_lease_token=execution_lease_token)
        _fault_injection_point("after_native_child_commit")
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            require_invocation_lease_owner(session, token=execution_lease_token)
            row, payload = self._parent(session, command)
            if payload["pending_child"] != request.model_dump(mode="json"):
                raise ValueError("Native pending child identity changed")
            append_child(payload, request.model_dump(mode="json"), result)
            # The sporting service already authenticated and committed this
            # exact result. Reconcile its actual receipt/hash here; do not run
            # MatchEngine a second time merely to acknowledge the child.
            ordinal, _count, _source = read_native_task_progress(session, run_id=command.run_id, branch_id=command.branch_id, parent=payload)
            clock = RunCalendar.from_metadata(command.execution_calendar)
            position = clock.position_at_ordinal(ordinal)
            ctx = {"week": {"season_index": position.season_index, "week": position.season_week}}
            _write(row, payload)
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
            result = self.control_full_simulation_in_session(session, command)
            return {"schema_version": "native_full_simulation_control_result.v1", "run_id": command.run_id,
                "branch_id": command.branch_id, "command_id": command.target_command_id,
                "control_command_id": command.control_command_id, "result": result}

    def _season_review(self, session, command):
        row, payload = self._parent(session, command)
        if row.status != "pending" or payload.get("pending_child") is None:
            raise ValueError("There is no frozen native Season Transition awaiting review")
        request = CalendarTourCommit.model_validate(payload["pending_child"])
        if request.command.action != "season-transition":
            raise ValueError("This pending child is not a Season Transition")
        preview = CalendarTourService(self.repository).preview(run_id=command.run_id, branch_id=command.branch_id, command=request.command)
        if preview["preview_fingerprint"] != request.expected_preview_fingerprint:
            raise ValueError("Native Season Transition inputs changed; its original reviewed child cannot execute")
        from beta_engine.application.native_full_simulation_closure import closure_facts
        from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
        source = self.repository._validated_saved_revision_in_session(session=session,
            model=session.get(BranchSavedRevisionModel, request.command.expected_saved_head))
        closing = closure_facts(self.repository, session, source, final=False)
        if closing != payload.get("pending_child_season_closure"):
            raise ValueError("Native outgoing closing authority differs from actual Saved facts")
        return row, payload, {"schema_version": "native_full_simulation_season_review.v1", "run_id": command.run_id,
            "branch_id": command.branch_id, "parent_command_id": command.command_id,
            "review_fingerprint": preview["preview_fingerprint"], "preview": preview, "outgoing_season_closure": closing}

    def review_season_transition(self, command):
        with self.factory() as session:
            session.execute(text("BEGIN"))
            return self._season_review(session, command)[2]

    def approve_season_transition(self, command, request):
        from beta_engine.application.native_full_simulation_closure import (
            NativeFullSimulationClosureService,
        )
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            NativeFullSimulationClosureService._idle(session, command)
            row, payload = self._parent(session, command)
            prior = payload.get("pending_child_approval")
            if prior:
                if prior != request:
                    raise ValueError("Native Season Transition already has another explicit approval")
                return {"request": prior}
            _, _, review = self._season_review(session, command)
            if request["review_fingerprint"] != review["review_fingerprint"]:
                raise ValueError("Native Season Transition review is stale")
            payload["pending_child_approval"] = request
            _write(row, payload)
            return {"request": request}
