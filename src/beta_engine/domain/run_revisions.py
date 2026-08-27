"""Pure contracts for canonical Run Saved Revisions and Working Drafts."""

from __future__ import annotations

import hashlib
import json

INITIAL_SAVED_REVISION_SEQUENCE = 1
INITIAL_SAVED_REVISION_KIND = "initial_run_creation"
INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION = "empty_run_saved_revision_v1"
# This schema names only the clean draft created with an empty Run. It does not
# choose the still-open representation of future logical change bundles.
WORKING_DRAFT_SCHEMA_VERSION = "empty_run_working_draft_v1"
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
