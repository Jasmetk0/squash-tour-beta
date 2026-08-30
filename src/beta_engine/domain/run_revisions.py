"""Pure contracts for canonical Run Saved Revisions and Working Drafts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

INITIAL_SAVED_REVISION_SEQUENCE = 1
INITIAL_SAVED_REVISION_KIND = "initial_run_creation"
INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION = "empty_run_saved_revision_v1"
# This schema names only the clean draft created with an empty Run. It does not
# choose the still-open representation of future logical change bundles.
WORKING_DRAFT_SCHEMA_VERSION = "empty_run_working_draft_v1"
# A new Branch initially shares its selected immutable source revision and owns
# only this clean draft. Future general draft schemas remain a separate concern.
SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION = (
    "saved_revision_fork_working_draft_v1"
)
RUN_WORKING_DRAFT_SCHEMA_VERSION = "run_working_draft_v1"
RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION = "run_saved_revision_v1"
VIEWER_BRANCH_SELECTION_CHANGE_KIND = "set_viewer_branch"
VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND = "viewer_branch_selection"
SAVED_REVISION_AUDIT_EVENT_KIND = "saved_revision_created"
BRANCH_RESTORE_SAVED_REVISION_KIND = "branch_restore"
BRANCH_RESTORE_AUDIT_EVENT_KIND = "branch_restored"
PRE_RESTORE_CHECKPOINT_KIND = "pre_restore_saved_revision"
CLEAN_WORKING_DRAFT_STATUS = "clean"
DIRTY_WORKING_DRAFT_STATUS = "dirty"
CONTENT_HASH_ALGORITHM = "sha256"


def canonical_json(payload: object) -> str:
    """Serialize persisted revision content in a stable, hashable form."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def initial_saved_revision_payload(
    *,
    run_id: str,
    display_name: str,
    run_status: str,
    timeline_start_season: int,
    timeline_end_season: int,
    branch_id: str,
    branch_display_name: str,
    branch_status: str,
) -> dict[str, object]:
    """Return the smallest complete restorable snapshot of an empty Run root."""

    return {
        "run": {
            "run_id": run_id,
            "display_name": display_name,
            "status": run_status,
            "timeline_start_season": timeline_start_season,
            "timeline_end_season": timeline_end_season,
            "viewer_branch_id": branch_id,
        },
        "branch": {
            "branch_id": branch_id,
            "display_name": branch_display_name,
            "status": branch_status,
            "forked_from_branch_id": None,
            "forked_from_saved_revision_id": None,
        },
        "content": {},
    }


def initial_saved_revision_change_summary(*, display_name: str) -> dict[str, object]:
    """Describe the implicit first save without inventing sporting content."""

    return {
        "kind": INITIAL_SAVED_REVISION_KIND,
        "summary": f"Created empty Run {display_name}",
    }


def viewer_branch_selection_change(*, viewer_branch_id: str) -> dict[str, object]:
    """Return the canonical logical change stored in a Working Draft."""

    return {
        "kind": VIEWER_BRANCH_SELECTION_CHANGE_KIND,
        "viewer_branch_id": viewer_branch_id,
    }


def viewer_branch_id_from_changes(changes: list[object]) -> str:
    """Validate and read the one change bundle supported by this first slice."""

    if len(changes) != 1 or not isinstance(changes[0], dict):
        raise ValueError("Working Draft must contain exactly one Viewer Branch change")
    change = changes[0]
    if set(change) != {"kind", "viewer_branch_id"}:
        raise ValueError("Viewer Branch change contains unsupported fields")
    if change.get("kind") != VIEWER_BRANCH_SELECTION_CHANGE_KIND:
        raise ValueError("Working Draft contains an unsupported change kind")
    viewer_branch_id = change.get("viewer_branch_id")
    if not isinstance(viewer_branch_id, str) or not viewer_branch_id.strip():
        raise ValueError("Viewer Branch change contains a blank Branch id")
    if viewer_branch_id != viewer_branch_id.strip() or len(viewer_branch_id) > 128:
        raise ValueError("Viewer Branch change contains an invalid Branch id")
    return viewer_branch_id


def saved_viewer_branch_id(payload: dict[str, object]) -> str:
    """Read the Viewer Branch identity protected by a Saved Revision hash."""

    run_payload = payload.get("run")
    if not isinstance(run_payload, dict):
        raise ValueError("Saved Revision contains no Run snapshot")
    viewer_branch_id = run_payload.get("viewer_branch_id")
    if not isinstance(viewer_branch_id, str) or not viewer_branch_id.strip():
        raise ValueError("Saved Revision contains no valid Viewer Branch")
    return viewer_branch_id


def viewer_branch_saved_revision_payload(
    *,
    base_payload: dict[str, object],
    run_id: str,
    display_name: str,
    run_status: str,
    timeline_start_season: int,
    timeline_end_season: int,
    branch_id: str,
    branch_display_name: str,
    branch_status: str,
    forked_from_branch_id: str | None,
    forked_from_saved_revision_id: str | None,
    viewer_branch_id: str,
) -> dict[str, object]:
    """Materialize a complete snapshot while preserving future content keys."""

    payload = deepcopy(base_payload)
    run_payload = payload.get("run")
    branch_payload = payload.get("branch")
    if not isinstance(run_payload, dict) or not isinstance(branch_payload, dict):
        raise ValueError("base Saved Revision has no restorable Run/Branch snapshot")
    run_payload.update(
        {
            "run_id": run_id,
            "display_name": display_name,
            "status": run_status,
            "timeline_start_season": timeline_start_season,
            "timeline_end_season": timeline_end_season,
            "viewer_branch_id": viewer_branch_id,
        }
    )
    branch_payload.update(
        {
            "branch_id": branch_id,
            "display_name": branch_display_name,
            "status": branch_status,
            "forked_from_branch_id": forked_from_branch_id,
            "forked_from_saved_revision_id": forked_from_saved_revision_id,
        }
    )
    return payload


def viewer_branch_saved_revision_change_summary(
    *, previous_viewer_branch_id: str, viewer_branch_id: str
) -> dict[str, object]:
    """Describe the exact logical change captured by a Save."""

    return {
        "kind": VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND,
        "summary": (
            f"Changed Viewer Branch from {previous_viewer_branch_id} "
            f"to {viewer_branch_id}"
        ),
        "changes": [
            {
                "kind": VIEWER_BRANCH_SELECTION_CHANGE_KIND,
                "previous_viewer_branch_id": previous_viewer_branch_id,
                "viewer_branch_id": viewer_branch_id,
            }
        ],
    }


def branch_restore_saved_revision_change_summary(
    *,
    previous_head_revision_id: str,
    target_saved_revision_id: str,
    previous_viewer_branch_id: str,
    restored_viewer_branch_id: str,
) -> dict[str, object]:
    """Describe a restore without pretending that old history was deleted."""

    return {
        "kind": BRANCH_RESTORE_SAVED_REVISION_KIND,
        "summary": (
            f"Restored Saved Revision {target_saved_revision_id} from "
            f"{previous_head_revision_id}"
        ),
        "previous_head_revision_id": previous_head_revision_id,
        "target_saved_revision_id": target_saved_revision_id,
        "previous_viewer_branch_id": previous_viewer_branch_id,
        "restored_viewer_branch_id": restored_viewer_branch_id,
    }


def saved_revision_checkpoint_hash_envelope(
    *,
    checkpoint_id: str,
    run_id: str,
    branch_id: str,
    saved_revision_id: str,
    target_saved_revision_id: str,
    restore_saved_revision_id: str,
    kind: str,
    draft_id: str,
    draft_version: int,
    viewer_branch_id: str,
) -> dict[str, object]:
    """Return every deterministic pre-restore checkpoint field."""

    return {
        "checkpoint_id": checkpoint_id,
        "run_id": run_id,
        "branch_id": branch_id,
        "saved_revision_id": saved_revision_id,
        "target_saved_revision_id": target_saved_revision_id,
        "restore_saved_revision_id": restore_saved_revision_id,
        "kind": kind,
        "draft_id": draft_id,
        "draft_version": draft_version,
        "viewer_branch_id": viewer_branch_id,
    }


def saved_revision_checkpoint_content_hash(
    *,
    checkpoint_id: str,
    run_id: str,
    branch_id: str,
    saved_revision_id: str,
    target_saved_revision_id: str,
    restore_saved_revision_id: str,
    kind: str,
    draft_id: str,
    draft_version: int,
    viewer_branch_id: str,
) -> str:
    """Hash the immutable bookmark protecting the exact pre-restore state."""

    envelope = saved_revision_checkpoint_hash_envelope(
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        branch_id=branch_id,
        saved_revision_id=saved_revision_id,
        target_saved_revision_id=target_saved_revision_id,
        restore_saved_revision_id=restore_saved_revision_id,
        kind=kind,
        draft_id=draft_id,
        draft_version=draft_version,
        viewer_branch_id=viewer_branch_id,
    )
    return hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()


def saved_revision_hash_envelope(
    *,
    revision_id: str,
    run_id: str,
    branch_id: str,
    sequence: int,
    parent_revision_id: str | None,
    kind: str,
    payload_schema_version: str,
    payload: dict[str, object],
    change_summary: dict[str, object],
) -> dict[str, object]:
    """Return every deterministic Saved Revision field protected by its hash."""

    return {
        "revision_id": revision_id,
        "run_id": run_id,
        "branch_id": branch_id,
        "sequence": sequence,
        "parent_revision_id": parent_revision_id,
        "kind": kind,
        "payload_schema_version": payload_schema_version,
        "payload": payload,
        "change_summary": change_summary,
    }


def saved_revision_content_hash(
    *,
    revision_id: str,
    run_id: str,
    branch_id: str,
    sequence: int,
    parent_revision_id: str | None,
    kind: str,
    payload_schema_version: str,
    payload: dict[str, object],
    change_summary: dict[str, object],
) -> str:
    """Hash the complete deterministic envelope of one immutable revision."""

    envelope = saved_revision_hash_envelope(
        revision_id=revision_id,
        run_id=run_id,
        branch_id=branch_id,
        sequence=sequence,
        parent_revision_id=parent_revision_id,
        kind=kind,
        payload_schema_version=payload_schema_version,
        payload=payload,
        change_summary=change_summary,
    )
    return hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()
