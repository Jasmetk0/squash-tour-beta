"""Validated read authority for the calendar of one Saved Revision-backed Run.

Reads within the caller's SQLite transaction. The live Run row selects the current
clock; the Branch's immutable Saved head proves that it was actually saved.
Absent historical fields are legacy FAX, never a migration write or new default.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import CONTENT_HASH_ALGORITHM, saved_revision_content_hash


def _json_object(raw: str, *, label: str) -> dict:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} JSON is corrupt") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def resolve_saved_run_calendar(
    session: Session, *, run_id: str, branch_id: str
) -> RunCalendar:
    """Return the verified calendar without modifying Run or Saved history.

    A fork may legitimately point to a hash-verified Saved Revision owned by
    another Branch of the same Run. Hashes are verified from the ORIGINAL
    payload/schema/identity, not reconstructed from current defaults.
    """

    # Loading db.models executes db.__init__, which imports sporting writers.
    # Defer this boundary until the authority module has finished initializing.
    from beta_engine.infrastructure.db.models import (
        BranchSavedRevisionModel, RunBranchModel, RunContainerModel,
    )

    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise ValueError("Run calendar requires an existing matching Run/Branch")

    metadata = _json_object(run.metadata_json, label="Run metadata")
    current_calendar = (
        RunCalendar.from_metadata(metadata["run_calendar"])
        if "run_calendar" in metadata else RunCalendar.legacy_fax()
    )

    if branch.saved_head_revision_id is None:
        if "run_calendar" in metadata:
            raise ValueError("Versioned Run calendar has no immutable Saved head")
        # Older legacy Run records did not necessarily have Saved Revisions.
        return current_calendar

    revision = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
    if revision is None or revision.run_id != run_id:
        raise ValueError("Run calendar Saved head is missing or outside this Run")
    payload = _json_object(revision.payload_json, label="Saved Revision payload")
    changes = _json_object(revision.change_summary_json, label="Saved Revision change summary")
    if (
        revision.content_hash_algorithm != CONTENT_HASH_ALGORITHM
        or saved_revision_content_hash(
            revision_id=revision.revision_id,
            run_id=revision.run_id,
            branch_id=revision.branch_id,
            sequence=revision.sequence,
            parent_revision_id=revision.parent_revision_id,
            kind=revision.kind,
            payload_schema_version=revision.payload_schema_version,
            payload=payload,
            change_summary=changes,
        ) != revision.content_hash
    ):
        raise ValueError("Run calendar Saved Revision failed content-hash validation")

    saved_run = payload.get("run")
    if not isinstance(saved_run, dict) or saved_run.get("run_id") != run_id:
        raise ValueError("Saved Revision Run identity is corrupt")

    if "run_calendar" in saved_run:
        saved_calendar = RunCalendar.from_metadata(saved_run["run_calendar"])
    else:
        saved_calendar = RunCalendar.legacy_fax()

    if saved_calendar != current_calendar:
        raise ValueError("Run calendar differs from the Branch Saved head")

    if current_calendar.schema_version == "run_calendar.v1":
        if (
            run.timeline_start_season != current_calendar.start_year
            or run.timeline_end_season
            != current_calendar.start_year + current_calendar.season_count - 1
        ):
            raise ValueError("Run timeline columns disagree with its saved calendar")

    return current_calendar


def require_supported_legacy_sporting_calendar(
    session: Session, *, run_id: str, branch_id: str, operation: str
) -> RunCalendar:
    """Protect 61-based authoritative writers from an unsupported Saved clock.

    Use inside the SAME transaction as any subsequent authoritative write. The
    existing historical FAX ordinal/replay semantics must not be reinterpreted
    by a Run-local W52 planning clock before the writer migration is complete.
    """

    calendar = resolve_saved_run_calendar(
        session, run_id=run_id, branch_id=branch_id
    )
    if (
        calendar.weeks_per_year != 61
        or calendar.season_start_year_week != 37
        or calendar.start_year != 2000
        or calendar.season_count != 50
    ):
        raise ValueError(
            f"{operation} cannot execute this Run calendar yet: "
            "the authoritative sporting/ranking writers still require "
            "the historical FAX 61-week, 50-season calendar"
        )
    # Numeric equality with reference FAX never grants legacy ownership of a
    # native checkpoint. A later native transition must consume it explicitly.
    from sqlalchemy import select
    from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel
    if session.scalar(select(CalendarPlayerSportingCheckpointModel.run_id).where(
            CalendarPlayerSportingCheckpointModel.run_id == run_id,
            CalendarPlayerSportingCheckpointModel.branch_id == branch_id).limit(1)) is not None:
        raise ValueError(f"{operation} cannot reinterpret a native population sporting checkpoint as legacy FAX state")
    return calendar


def require_supported_full_simulation_calendar(calendar: RunCalendar) -> None:
    """Fail closed until the sporting writer is truly W/horizon aware.

    No UI/preview may imply that changing the stored Run calendar makes
    legacy 61-week ranking ordinals, transitions and final closure executable.
    """

    if (
        calendar.weeks_per_year != 61
        or calendar.season_start_year_week != 37
        or calendar.start_year != 2000
        or calendar.season_count != 50
    ):
        raise ValueError(
            "Full Simulation cannot execute this Run calendar yet: "
            "variable weeks, offset, start year or horizon require the "
            "authoritative transition and target migration"
        )


def guard_versioned_sporting_write(
    session: Session, *, run_id: str, branch_id: str, operation: str
) -> None:
    """Fence new explicit-clock Runs at the lower sporting write boundaries.

    Legacy callers retain their existing validation and receipt contracts. New
    v82 roots must prove a supported Saved clock before installing initial
    sports, ranking candidates or match work. Data/package planning stays free
    of this gate. Call after exact historical replay, before new writes.
    """

    # Loading db.models executes db.__init__, which imports sporting writers.
    # Defer this boundary until the authority module has finished initializing.
    from beta_engine.infrastructure.db.models import RunContainerModel

    run = session.get(RunContainerModel, run_id)
    if run is not None and "run_calendar" in _json_object(run.metadata_json, label="Run metadata"):
        require_supported_legacy_sporting_calendar(
            session, run_id=run_id, branch_id=branch_id, operation=operation
        )
