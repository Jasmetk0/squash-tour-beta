"""Closed, provisional transport contract for identity-preserving cold restore.

Transport hashes detect byte damage. They never replace the original Saved hash,
owner, source or replay validators. No imported path or executable data is used.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.domain.run_revisions import saved_revision_content_hash

FORMAT = "run_branch_archive.v1"
ENGINE_CAPABILITY = "run_branch_archive.v1"
MINIMUM_ENGINE_BASE = "9980628243f6ac637cb6ab803af1e4c632520849+archive.v1"
# Per-request parser budget, not a Run/history quota. No compression/extraction.
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
ID = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^\S(?:.*\S)?$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
PART_NAMES = ("run", "branches", "revisions", "audits", "checkpoints", "allocator")
OMITTED_AREAS = (
    "unselected_branch_future",
    "recovery_drafts",
    "working_changes",
    "caches",
    "temporary_calculations",
    "worker_processes_and_task_controls",
    "global_packages",
    "non_saved_authoring_receipts",
)
SUPPORTED_SCHEMAS = {
    "empty_run_saved_revision_v1",
    "run_saved_revision_v1",
    "native_fork_saved_root.v2",
}
SUPPORTED_COMPONENTS = frozenset(
    {
        "initial_world",
        "run_package_state",
        "player_lifecycle",
        "player_health_state",
        "player_sporting_state",
        "simulation_slot_match_state",
        "calendar_standalone_match",
        "calendar_player_sporting_checkpoint",
        "calendar_tour_authority",
        "native_fork_baseline",
        "native_fork_runtime",
        "run_prospect_source",
        "application_validation_slots",
        "definitive_wild_card_assignments",
        "player_tour_entry_triggers",
        "run_entry_decision_slots",
        "tournament_application_submissions",
    }
)


class ArchiveError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code, message):
    raise ArchiveError(code, message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate_json_key", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(raw: bytes | str):
    try:
        return json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_constant=lambda x: fail(
                "invalid_json", f"Nonfinite JSON number: {x}"
            ),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError(
            "invalid_json",
            "Archive contains invalid, truncated or excessively nested JSON",
        ) from exc


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RunSpec(Closed):
    run_id: ID
    display_name: Annotated[str, Field(min_length=1, max_length=256)]
    status: Literal["working", "active", "completed", "archived"]
    timeline_start_season: int
    timeline_end_season: int
    viewer_branch_id: ID
    activation_revision_id: ID
    metadata_json: str


class BranchSpec(Closed):
    branch_id: ID
    display_name: Annotated[str, Field(min_length=1, max_length=256)]
    status: Literal["active"] = "active"
    branch_seed: Annotated[int, Field(ge=-(2**63), le=2**63 - 1)] | None
    forked_from_branch_id: ID | None
    forked_from_saved_revision_id: ID | None
    saved_head_revision_id: ID
    metadata_json: str
    role: Literal["selected", "dependency"]
    # A fresh CLEAN draft is created; no source draft identity or contents travel.


class RevisionSpec(Closed):
    revision_id: ID
    run_id: ID
    branch_id: ID
    sequence: Annotated[int, Field(ge=1)]
    parent_revision_id: ID | None
    kind: Annotated[str, Field(min_length=1, max_length=64)]
    payload_schema_version: str
    content_hash_algorithm: Literal["sha256"]
    content_hash: Digest
    payload_json: str
    change_summary_json: str
    created_at: str

    def original_authority(self):
        if self.payload_schema_version not in SUPPORTED_SCHEMAS:
            fail(
                "unsupported_saved_schema",
                f"Unsupported Saved schema: {self.payload_schema_version}",
            )
        payload, summary = decode(self.payload_json), decode(self.change_summary_json)
        if not isinstance(payload, dict) or set(payload) != {
            "run",
            "branch",
            "content",
        }:
            fail(
                "invalid_saved_payload",
                "Saved payload must contain Run, Branch and content",
            )
        if (
            not isinstance(payload["run"], dict)
            or not isinstance(payload["branch"], dict)
            or not isinstance(summary, dict)
            or not isinstance(payload["content"], dict)
        ):
            fail("invalid_saved_payload", "Saved summary/content must be objects")
        run_fields = {
            "run_id",
            "display_name",
            "status",
            "timeline_start_season",
            "timeline_end_season",
            "viewer_branch_id",
            "run_calendar",
            "run_calendar_content_origin",
        }
        branch_fields = {
            "branch_id",
            "display_name",
            "status",
            "forked_from_branch_id",
            "forked_from_saved_revision_id",
        }
        if set(payload["run"]) - run_fields or set(payload["branch"]) - branch_fields:
            fail(
                "unsupported_saved_metadata",
                "Saved Run/Branch contains unsupported activation metadata; no fields may be discarded",
            )
        if any(
            not isinstance(component, dict) for component in payload["content"].values()
        ):
            fail("invalid_component", "Saved components must be objects")
        unknown = set(payload["content"]) - SUPPORTED_COMPONENTS
        if unknown:
            fail(
                "unsupported_component",
                f"Unsupported components: {', '.join(sorted(unknown))}",
            )
        if (payload["run"].get("run_id"), payload["branch"].get("branch_id")) != (
            self.run_id,
            self.branch_id,
        ):
            fail(
                "foreign_saved_owner",
                "Saved payload differs from its original Run/Branch owner",
            )
        fields = self.model_dump(
            exclude={
                "content_hash_algorithm",
                "content_hash",
                "payload_json",
                "change_summary_json",
                "created_at",
            }
        )
        if (
            saved_revision_content_hash(
                **fields, payload=payload, change_summary=summary
            )
            != self.content_hash
        ):
            fail(
                "invalid_saved_hash", f"Original Saved hash failed: {self.revision_id}"
            )
        return self


class AuditSpec(Closed):
    audit_event_id: ID
    run_id: ID
    branch_id: ID
    saved_revision_id: ID
    event_kind: str
    payload_json: str
    created_at: str


class CheckpointSpec(Closed):
    checkpoint_id: ID
    run_id: ID
    branch_id: ID
    saved_revision_id: ID
    target_saved_revision_id: ID
    restore_saved_revision_id: ID
    kind: Literal["pre_restore_saved_revision"]
    draft_id: ID
    draft_version: Annotated[int, Field(ge=0, le=2**63 - 1)]
    viewer_branch_id: ID
    content_hash_algorithm: Literal["sha256"]
    content_hash: Digest
    created_at: str


class Part(Closed):
    name: str
    size: Annotated[int, Field(ge=0)]
    sha256: Digest
    data_json: str


class Envelope(Closed):
    format: Literal["run_branch_archive.v1"]
    engine_capability: Literal["run_branch_archive.v1"]
    minimum_engine: Literal["9980628243f6ac637cb6ab803af1e4c632520849+archive.v1"]
    scope: Literal["custom_selected_saved_branch_with_dependency_history"]
    selected_branch_id: ID
    selected_head_revision_id: ID
    omitted_branch_ids: list[ID]
    omitted_areas: list[str]
    parts: list[Part]


class Archive:
    """Decoded, integrity-checked envelope; production validation still required."""

    def __init__(self, raw: bytes):
        if len(raw) > MAX_ARCHIVE_BYTES:
            fail(
                "archive_request_too_large",
                f"Archive exceeds this operation's {MAX_ARCHIVE_BYTES}-byte parser budget",
            )
        value = decode(raw)
        if not isinstance(value, dict) or value.get("format") != FORMAT:
            fail(
                "unsupported_archive_version",
                f"Requires {FORMAT}; unknown versions cannot be downgraded",
            )
        self.envelope = Envelope.model_validate(value)
        self.raw_digest, self.size = digest(raw), len(raw)
        if [p.name for p in self.envelope.parts] != list(PART_NAMES):
            fail(
                "invalid_manifest", "Archive must contain exactly the ordered v1 parts"
            )
        if self.envelope.omitted_areas != list(OMITTED_AREAS):
            fail("invalid_manifest", "Unsupported omitted-area declaration")
        parts = {}
        for part in self.envelope.parts:
            data = part.data_json.encode("utf-8")
            if len(data) != part.size or digest(data) != part.sha256:
                fail(
                    "invalid_part_integrity", f"Part size or digest failed: {part.name}"
                )
            parts[part.name] = decode(data)
        for name in ("branches", "revisions", "audits", "checkpoints"):
            if not isinstance(parts[name], list):
                fail("invalid_manifest", f"Part {name} must be a list")
        self.run = RunSpec.model_validate(parts["run"])
        self.branches = [BranchSpec.model_validate(x) for x in parts["branches"]]
        self.revisions = [RevisionSpec.model_validate(x) for x in parts["revisions"]]
        for revision in self.revisions:
            revision.original_authority()
        self.audits = [AuditSpec.model_validate(x) for x in parts["audits"]]
        self.checkpoints = [
            CheckpointSpec.model_validate(x) for x in parts["checkpoints"]
        ]
        self.allocator = parts["allocator"]
        if type(self.allocator) is not int or not 1 <= self.allocator <= 2**63 - 1:
            fail(
                "invalid_allocator",
                "Package allocator must be a positive SQLite integer",
            )
        self._graph()

    def _graph(self):
        def unique(rows, key):
            values = [getattr(x, key) for x in rows]
            if len(set(values)) != len(values):
                fail("duplicate_identity", f"Duplicate {key}")
            return {getattr(x, key): x for x in rows}

        branches = unique(self.branches, "branch_id")
        revisions = unique(self.revisions, "revision_id")
        unique(self.audits, "audit_event_id")
        unique(self.checkpoints, "checkpoint_id")
        if len({b.display_name for b in self.branches}) != len(branches):
            fail("duplicate_branch_name", "Branch names must be unique in the Run")
        selected = branches.get(self.envelope.selected_branch_id)
        if (
            selected is None
            or selected.saved_head_revision_id
            != self.envelope.selected_head_revision_id
            or [b.branch_id for b in self.branches if b.role == "selected"]
            != [selected.branch_id]
            or self.run.viewer_branch_id not in branches
        ):
            fail(
                "invalid_selection",
                "Selected HEAD or saved Viewer Branch is missing/inconsistent",
            )
        if set(
            self.envelope.omitted_branch_ids
        ) & branches.keys() or self.envelope.omitted_branch_ids != sorted(
            set(self.envelope.omitted_branch_ids)
        ):
            fail(
                "invalid_manifest",
                "Omitted Branch identities overlap or are not unique/ordered",
            )
        reached, branch_paths = set(), {}
        for branch in self.branches:
            if (
                branch.forked_from_branch_id is not None
                and branch.forked_from_branch_id not in branches
            ):
                fail("missing_owner", "Fork source Branch context is missing")
            seen, current = set(), branch.saved_head_revision_id
            while current is not None:
                if current in seen:
                    fail("lineage_cycle", "Saved lineage contains a cycle")
                seen.add(current)
                revision = revisions.get(current)
                if revision is None:
                    fail(
                        "missing_revision",
                        f"Missing required Saved Revision: {current}",
                    )
                if (
                    revision.run_id != self.run.run_id
                    or revision.branch_id not in branches
                ):
                    fail("foreign_saved_owner", "Missing/foreign original Saved owner")
                parent = revisions.get(revision.parent_revision_id)
                if (
                    revision.parent_revision_id is not None
                    and parent is None
                    or parent is not None
                    and revision.sequence != parent.sequence + 1
                    or revision.parent_revision_id is None
                    and revision.sequence != 1
                ):
                    fail(
                        "invalid_lineage",
                        "Saved lineage has missing/noncontiguous parents",
                    )
                current = revision.parent_revision_id
            reached.update(seen)
            branch_paths[branch.branch_id] = seen
        # The Branch graph is also acyclic, even when a Branch currently shares
        # another owner's HEAD and therefore has no own revision rows yet.
        for branch in self.branches:
            seen, current = set(), branch.branch_id
            while current is not None:
                if current in seen:
                    fail(
                        "branch_cycle", "Original Branch fork contexts contain a cycle"
                    )
                seen.add(current)
                current = branches[current].forked_from_branch_id
        activation = revisions.get(self.run.activation_revision_id)
        if activation is None:
            fail(
                "missing_run_activation",
                "Original Saved authority for the Run/Viewer choice is absent",
            )
        needed = {
            self.envelope.selected_branch_id,
            self.run.viewer_branch_id,
            activation.branch_id,
        }
        previous = set()
        while needed != previous:
            previous = set(needed)
            for bid in previous:
                branch = branches[bid]
                if branch.forked_from_branch_id:
                    needed.add(branch.forked_from_branch_id)
                for rid in branch_paths[bid]:
                    revision = revisions[rid]
                    payload = decode(revision.payload_json)
                    needed.add(revision.branch_id)
                    needed.add(payload["run"]["viewer_branch_id"])
                    baseline = (
                        payload["content"].get("native_fork_baseline", {}).get("state")
                    )
                    if baseline:
                        needed.add(baseline["selected_source_branch_id"])
            active_revisions = set().union(*(branch_paths[bid] for bid in previous))
            needed.update(
                c.viewer_branch_id
                for c in self.checkpoints
                if c.restore_saved_revision_id in active_revisions
            )
            if not needed <= branches.keys():
                fail(
                    "missing_owner",
                    "A required historical owner/Viewer/source context is missing",
                )
        if needed != branches.keys():
            fail(
                "unrelated_branch",
                "Archive contains a Branch outside the selected dependency closure",
            )
        if reached != revisions.keys():
            fail(
                "unreachable_revision",
                "Archive contains revisions outside declared Branch history",
            )
        audited = {a.saved_revision_id for a in self.audits}
        if len(audited) != len(self.audits):
            fail(
                "duplicate_audit",
                "Each Saved revision may have only one original revision audit",
            )
        if any(
            r.kind != "initial_run_creation" and r.revision_id not in audited
            for r in self.revisions
        ):
            fail(
                "missing_audit",
                "A noninitial Saved revision is missing its original revision audit",
            )
        for row in [*self.audits, *self.checkpoints]:
            if (
                row.run_id != self.run.run_id
                or row.branch_id not in branches
                or row.saved_revision_id not in revisions
            ):
                fail(
                    "foreign_history",
                    "Audit/checkpoint has a foreign or unreachable owner",
                )
            if isinstance(row, AuditSpec) and (
                revisions[row.saved_revision_id].branch_id != row.branch_id
                or not isinstance(decode(row.payload_json), dict)
            ):
                fail(
                    "foreign_audit", "Audit does not belong to its original Saved owner"
                )
        for row in self.checkpoints:
            from beta_engine.domain.run_revisions import (
                saved_revision_checkpoint_content_hash,
            )

            values = row.model_dump(
                exclude={"content_hash_algorithm", "content_hash", "created_at"}
            )
            if (
                row.target_saved_revision_id not in revisions
                or row.restore_saved_revision_id not in revisions
                or row.viewer_branch_id not in branches
                or saved_revision_checkpoint_content_hash(**values) != row.content_hash
            ):
                fail("invalid_checkpoint", "Checkpoint hash or dependencies failed")
        for revision in self.revisions:
            payload = decode(revision.payload_json)
            if payload["run"].get("viewer_branch_id") not in branches:
                fail("missing_viewer", "Historical Saved Viewer context is absent")
        if [a.audit_event_id for a in self.audits] != sorted(
            a.audit_event_id for a in self.audits
        ) or [c.checkpoint_id for c in self.checkpoints] != sorted(
            c.checkpoint_id for c in self.checkpoints
        ):
            fail(
                "invalid_manifest",
                "Audit/checkpoint identities must be canonically ordered",
            )
        if [b.branch_id for b in self.branches] != sorted(branches):
            fail("invalid_manifest", "Branches must be ordered by identity")
        if [(r.sequence, r.revision_id) for r in self.revisions] != sorted(
            (r.sequence, r.revision_id) for r in self.revisions
        ):
            fail("invalid_manifest", "Revisions must be ordered by sequence/identity")


def pack(
    *,
    run,
    branches,
    revisions,
    audits,
    checkpoints,
    allocator,
    selected_branch_id,
    selected_head_revision_id,
    omitted_branch_ids,
):
    values = (run, branches, revisions, audits, checkpoints, allocator)
    parts = []
    for name, value in zip(PART_NAMES, values, strict=True):
        raw = encode(value)
        parts.append(
            {
                "name": name,
                "size": len(raw),
                "sha256": digest(raw),
                "data_json": raw.decode("utf-8"),
            }
        )
    return encode(
        {
            "format": FORMAT,
            "engine_capability": ENGINE_CAPABILITY,
            "minimum_engine": MINIMUM_ENGINE_BASE,
            "scope": "custom_selected_saved_branch_with_dependency_history",
            "selected_branch_id": selected_branch_id,
            "selected_head_revision_id": selected_head_revision_id,
            "omitted_branch_ids": omitted_branch_ids,
            "omitted_areas": list(OMITTED_AREAS),
            "parts": parts,
        }
    )
