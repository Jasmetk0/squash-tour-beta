"""Read ATP source authority from the current immutable Run/Branch revision."""

import json

from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.run_revisions import CONTENT_HASH_ALGORITHM, saved_revision_content_hash
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state


def read_saved_atp_source(session, *, run_id: str, branch_id: str):
    """Use the caller's read transaction for both Run clock and Package state."""
    clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or not branch.saved_head_revision_id:
        raise ValueError("Run Branch has no immutable Saved head")
    revision = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
    if revision is None or revision.run_id != run_id:
        raise ValueError("Saved Run Package source revision missing or foreign")
    payload = json.loads(revision.payload_json)
    changes = json.loads(revision.change_summary_json)
    if (
        not isinstance(payload, dict)
        or not isinstance(changes, dict)
        or revision.content_hash_algorithm != CONTENT_HASH_ALGORITHM
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
        raise ValueError("Saved ATP source revision failed hash verification")
    # Shared pre-fork ancestry belongs to the ORIGINAL revision Branch,
    # not necessarily the requested current Branch.
    state = load_saved_run_package_state(
        payload, run_id=run_id, branch_id=revision.branch_id
    )
    if state is None:
        raise ValueError("ATP reference Package is not in Saved Revision")
    return clock, revision, state
