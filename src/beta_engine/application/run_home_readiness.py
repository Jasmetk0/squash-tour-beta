"""Honest, Saved-Revision-backed Run Home guidance (Master v83).

One SQLite read transaction owns the entire selected-Branch snapshot. This is an
operator guide, NEVER a replacement for operation-scoped sporting preflight.
Historical viewing does not query this current-state endpoint.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import PackageType
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
from beta_engine.infrastructure.db.models import (
    FullSimulationTaskModel, RunBranchModel, RunContainerModel,
)
from beta_engine.infrastructure.db.player_health_state import load_saved_health
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state
from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component

ItemStatus = Literal["saved", "missing", "candidate_only", "unsaved", "optional"]
ItemCode = Literal["world", "calendar_package", "population", "health", "official_ranking", "working_draft"]
TASK_FINAL_STATES = {"stopped", "target_reached", "complete"}


class RunReadinessItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    code: ItemCode
    status: ItemStatus
    evidence_count: int = Field(ge=0)


class RunHomeReadiness(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["run_home_readiness.v1"] = "run_home_readiness.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    saved_revision_content_hash: str
    draft_version: int = Field(ge=0)
    run_status: str
    source: Literal["validated_selected_branch_saved_head"] = "validated_selected_branch_saved_head"
    current_calendar: dict
    phase: Literal["preparation", "sporting_history", "completed"]
    items: tuple[RunReadinessItem, ...]
    saved_transition_count: int = Field(ge=0)
    saved_published_ranking_count: int = Field(ge=0)
    active_full_simulation_task_count: int = Field(ge=0)
    historical_full_simulation_task_count: int = Field(ge=0)
    sporting_calendar_supported_by_legacy_writers: bool
    requires_operation_preflight: Literal[True] = True
    simulation_started: Literal[False] = False


def inspect_run_home_readiness(
    session: Session, repository, *, run_id: str, branch_id: str,
) -> RunHomeReadiness:
    """Validated current read; the caller MUST begin a coherent DB read snapshot."""
    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise KeyError("Run/Branch was not found")

    state = repository._validated_branch_revision_state_in_session(
        session=session, branch=branch,
    )
    revision = state.saved_revision
    if state.run_id != run_id or state.branch_id != branch_id:
        raise ValueError("Run/Branch Saved Revision scope mismatch")
    if branch.saved_head_revision_id != revision.revision_id:
        raise ValueError("Run/Branch HEAD changed within readiness inspection")
    calendar = resolve_saved_run_calendar(
        session, run_id=run_id, branch_id=branch_id,
    )
    # An ancestor owned by another Branch is valid *history*, but not an
    # independent present-day Saved content projection for this Branch.
    if revision.branch_id != branch_id and revision.payload.get("content"):
        raise ValueError("This Branch still refers to unmaterialized inherited content")

    payload = revision.payload
    saved_calendar_match = load_saved_calendar_match(
        payload, run_id=run_id, branch_id=branch_id,
    ) if revision.branch_id == branch_id else None
    packages = load_saved_run_package_state(
        payload, run_id=run_id, branch_id=branch_id,
    ) if revision.branch_id == branch_id else None
    population = load_saved_initial_world(
        payload, run_id=run_id, branch_id=branch_id,
    ) if revision.branch_id == branch_id else None
    health = load_saved_health(
        payload, run_id=run_id, branch_id=branch_id,
    ) if revision.branch_id == branch_id else None
    ranking = load_saved_ranking_component(
        payload, run_id=run_id, branch_id=branch_id,
    ) if revision.branch_id == branch_id else None

    version_types = set(v.package_type for v in packages.package_versions) if packages else set()
    # A saved Package version without any Run-owned entity is not sufficient
    # evidence of usable World/Calendar content.
    owned_types = {
        v.package_type
        for v in packages.package_versions
        if any(e.source_package_id == v.package_id for e in packages.entities)
    } if packages else set()
    del version_types
    population_count = len(population.players) if population else 0
    publication = (ranking.authoritative_transition_state or {}).get("publications", []) if ranking else []
    events = (ranking.authoritative_transition_state or {}).get("events", []) if ranking else []
    from beta_engine.infrastructure.db.calendar_tour import saved_tour
    native_tour=saved_tour(payload,run_id=run_id,branch_id=branch_id)
    if native_tour:
        publication=list(native_tour.rankings)
        events=list(native_tour.transitions)
    # A candidate Ranking is NOT an adopted/published initial Ranking.
    draft = state.working_draft
    items = (
        RunReadinessItem(code="world", status="saved" if PackageType.WORLD in owned_types else "missing",
                         evidence_count=sum(e.source_package_id in {
                            v.package_id for v in (packages.package_versions if packages else ())
                            if v.package_type == PackageType.WORLD
                         } for e in (packages.entities if packages else ()))),
        RunReadinessItem(code="calendar_package", status="saved" if PackageType.CALENDAR in owned_types else "missing",
                         evidence_count=sum(e.source_package_id in {
                            v.package_id for v in (packages.package_versions if packages else ())
                            if v.package_type == PackageType.CALENDAR
                         } for e in (packages.entities if packages else ()))),
        RunReadinessItem(code="population", status="saved" if population_count else "missing",
                         evidence_count=population_count),
        RunReadinessItem(code="health", status="saved" if health else (
            "missing" if population and population.schema_version == "initial_world_state.v2" else "optional"
        ), evidence_count=len(health) if health else 0),
        RunReadinessItem(code="official_ranking", status="saved" if publication else (
            "candidate_only" if ranking and ranking.entries else "missing"
        ), evidence_count=len(publication)),
        RunReadinessItem(code="working_draft", status="saved" if draft.status == "clean" else "unsaved",
                         evidence_count=draft.change_count),
    )

    # Frozen evidence is read from the durable task contract, not a browser
    # local store or an unreliable worker-process memory view.
    from beta_engine.application.full_simulation_tasks import _read as read_task
    tasks = session.scalars(
        select(FullSimulationTaskModel).where(
            FullSimulationTaskModel.run_id == run_id,
            FullSimulationTaskModel.branch_id == branch_id,
        ).order_by(FullSimulationTaskModel.task_id)
    ).all()
    statuses = [read_task(row)["state"] for row in tasks]
    supported = calendar == RunCalendar.fax_default()
    phase = "completed" if run.status == "completed" else (
        "sporting_history" if events or saved_calendar_match is not None else "preparation"
    )
    return RunHomeReadiness(
        run_id=run_id, branch_id=branch_id,
        saved_revision_id=revision.revision_id,
        saved_revision_content_hash=revision.content_hash,
        draft_version=draft.draft_version, run_status=run.status,
        current_calendar=calendar.to_metadata(), phase=phase,
        items=items, saved_transition_count=len(events),
        saved_published_ranking_count=len(publication),
        active_full_simulation_task_count=sum(v not in TASK_FINAL_STATES for v in statuses),
        historical_full_simulation_task_count=len(tasks),
        sporting_calendar_supported_by_legacy_writers=supported,
    )
