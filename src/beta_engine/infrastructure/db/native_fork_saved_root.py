"""Persisted native fork roots, with original history kept at its actual owner.

This is a staging format, not a simulation checkpoint. Only the installation
kernel writes it; pending Branches cannot execute, Save, restore or become Viewer.
"""

from beta_engine.domain.native_fork_baseline import NativeForkBaseline
from beta_engine.domain.run_revisions import (
    BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND,
    canonical_json,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.native_fork_baseline import (
    verify_native_fork_baseline_in_session,
)

COMPONENT_KEY = "native_fork_baseline"
PAYLOAD_SCHEMA = "native_fork_saved_root.v1"
PENDING_STATUS = "preparing_native_fork"


def load_native_fork_saved_root(revision):
    """Structural checks only; the session verifier supplies source authority."""
    if (
        revision.payload_schema_version == "native_fork_saved_root.v2"
        or "native_fork_runtime" in revision.payload.get("content", {})
    ):
        return _load_runtime_root(revision)
    content = revision.payload.get("content")
    branch = revision.payload.get("branch")
    present = isinstance(content, dict) and COMPONENT_KEY in content
    pending = isinstance(branch, dict) and branch.get("status") == PENDING_STATUS
    if (
        not present
        and revision.payload_schema_version != PAYLOAD_SCHEMA
        and not pending
    ):
        return None
    if not present or set(content) != {COMPONENT_KEY}:
        raise ValueError("Native fork root must contain exactly its baseline")
    component = content[COMPONENT_KEY]
    if not isinstance(component, dict) or set(component) != {"state", "fingerprint"}:
        raise ValueError("Native fork root component is malformed")
    baseline = NativeForkBaseline.model_validate_json(
        canonical_json(component["state"])
    )
    run = revision.payload.get("run")
    if (
        revision.payload_schema_version != PAYLOAD_SCHEMA
        or revision.kind != BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND
        or (baseline.run_id, baseline.branch_id)
        != (revision.run_id, revision.branch_id)
        or component["fingerprint"] != baseline.fingerprint
        or revision.parent_revision_id != baseline.source_binding.source.revision_id
        or not isinstance(branch, dict)
        or branch.get("status") != PENDING_STATUS
        or branch.get("forked_from_branch_id") != baseline.selected_source_branch_id
        or branch.get("forked_from_saved_revision_id") != revision.parent_revision_id
        or not isinstance(run, dict)
        or run.get("run_calendar") != baseline.week.calendar.to_metadata()
    ):
        raise ValueError("Native fork root has inconsistent scope or source")
    return baseline


def verify_native_fork_saved_root(repository, session, *, revision, baseline):
    if revision.payload_schema_version == "native_fork_saved_root.v2":
        from beta_engine.infrastructure.db.native_fork_runtime_state import (
            verify_with_actual_dependencies,
        )
        verify_with_actual_dependencies(repository, session, revision,
            lambda: _verify_runtime_root(repository, session, revision, baseline))
        return baseline
    source = session.get(BranchSavedRevisionModel, revision.parent_revision_id)
    if source is None or revision.sequence != source.sequence + 1:
        raise ValueError("Native fork root has a missing or non-contiguous source")
    return verify_native_fork_baseline_in_session(
        repository,
        session,
        baseline=baseline,
        run_id=revision.run_id,
        source_branch_id=baseline.selected_source_branch_id,
        source_revision_id=revision.parent_revision_id,
        target_branch_id=revision.branch_id,
    )


def _load_runtime_root(revision):
    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        SAVED_SCHEMA,
        load_runtime,
    )

    runtime = load_runtime(revision.payload)
    baseline = runtime.baseline
    content = revision.payload["content"]
    if set(content) - {
        COMPONENT_KEY,
        "native_fork_runtime",
        "run_prospect_source",
    } or content.get(COMPONENT_KEY) != {
        "state": baseline.model_dump(mode="json"),
        "fingerprint": baseline.fingerprint,
    }:
        raise ValueError("Native runtime root has foreign or detached components")
    branch = revision.payload.get("branch", {})
    from beta_engine.domain.calendar.run_calendar import RunCalendar

    envelope = RunCalendar.from_metadata(
        revision.payload.get("run", {}).get("run_calendar", {})
    )
    clock = runtime.week.calendar
    compatible = (
        envelope.weeks_per_year,
        envelope.season_start_year_week,
        envelope.start_year,
    ) == (
        clock.weeks_per_year,
        clock.season_start_year_week,
        clock.start_year,
    ) and envelope.season_count >= clock.season_count
    if (
        revision.payload_schema_version != SAVED_SCHEMA
        or (revision.run_id, revision.branch_id) != (runtime.run_id, runtime.branch_id)
        or branch.get("status") != "active"
        or branch.get("forked_from_branch_id") != baseline.selected_source_branch_id
        or branch.get("forked_from_saved_revision_id")
        != baseline.source_binding.source.revision_id
        or not compatible
    ):
        raise ValueError("Native runtime root has inconsistent scope or calendar")
    if runtime.root_saved_revision_id == revision.revision_id:
        if (
            revision.kind != BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND
            or runtime.journal
            or revision.parent_revision_id != baseline.source_binding.source.revision_id
        ):
            raise ValueError(
                "Native runtime root has inconsistent installation history"
            )
    elif revision.kind not in {
        "native_fork_save",
        "native_final_run_closure",
        "branch_restore",
        "run_calendar_horizon_extension",
    }:
        raise ValueError("Native runtime descendant has an unsupported kind")
    return baseline


def _verify_runtime_root(repository, session, revision, baseline):
    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        load_runtime,
        verify_runtime,
    )

    verify_native_fork_baseline_in_session(
        repository,
        session,
        baseline=baseline,
        run_id=revision.run_id,
        source_branch_id=baseline.selected_source_branch_id,
        source_revision_id=baseline.source_binding.source.revision_id,
        target_branch_id=revision.branch_id,
    )
    parent = session.get(BranchSavedRevisionModel, revision.parent_revision_id)
    root_id = load_runtime(revision.payload).root_saved_revision_id
    if parent is None or parent.run_id != revision.run_id or parent.sequence != revision.sequence - 1 or (root_id != revision.revision_id and parent.branch_id != revision.branch_id):
        raise ValueError("Native Saved descendant lacks a contiguous target-owned parent")
    source = repository._validated_saved_revision_in_session(
        session=session,
        model=session.get(
            BranchSavedRevisionModel, baseline.source_binding.source.revision_id
        ),
    )
    if revision.payload["content"].get("run_prospect_source") != source.payload[
        "content"
    ].get("run_prospect_source"):
        raise ValueError(
            "Fork prospect source differs from its actual original Saved catalog"
        )
    if (
        revision.revision_id == load_runtime(revision.payload).root_saved_revision_id
        and revision.sequence != source.sequence + 1
    ):
        raise ValueError("Native runtime root is not contiguous with its source")
    verify_runtime(
        repository,
        session,
        runtime=load_runtime(revision.payload),
        revision=revision,
        original=source,
    )
    return baseline
