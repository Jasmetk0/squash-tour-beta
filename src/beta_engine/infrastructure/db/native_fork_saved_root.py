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
