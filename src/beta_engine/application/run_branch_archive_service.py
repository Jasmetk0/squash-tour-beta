"""Reviewed export and explicit, durable, identity-preserving cold restore."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from beta_engine.domain.run_branch_archive import Archive, decode, digest, encode, fail
from beta_engine.infrastructure.db.run_branch_archive import (
    RunBranchArchiveReceiptModel,
    collect_archive,
    conflicts,
    install_archive,
    validate_in_isolated_database,
)


def inventory(archive):
    unresolved = []
    for revision in archive.revisions:
        state = (
            decode(revision.payload_json)["content"]
            .get("run_package_state", {})
            .get("state", {})
        )
        if not isinstance(state, dict) or not isinstance(
            state.get("entities", []), list
        ):
            fail(
                "invalid_package_component",
                "Package state/entities have an invalid archive shape",
            )
        entities = state.get("entities", [])
        if any(not isinstance(e, dict) for e in entities):
            fail("invalid_package_component", "Package entities must be objects")
        available = {(e["source_package_id"], e["source_entity_id"]) for e in entities}
        for entity in entities:
            references = entity.get("references", [])
            if not isinstance(references, list) or any(
                not isinstance(r, dict) for r in references
            ):
                fail(
                    "invalid_package_component",
                    "Package references must be object lists",
                )
            for reference in references:
                if (
                    reference["source_package_id"],
                    reference["source_entity_id"],
                ) not in available:
                    unresolved.append(
                        {
                            "revision_id": revision.revision_id,
                            "branch_id": revision.branch_id,
                            "run_local_id": entity["run_local_id"],
                            "reference": reference,
                        }
                    )
    selected = next(
        r
        for r in archive.revisions
        if r.revision_id == archive.envelope.selected_head_revision_id
    )
    components = sorted(
        {key for r in archive.revisions for key in decode(r.payload_json)["content"]}
    )
    return {
        "schema_version": "run_branch_archive_preview.v1",
        "archive_digest": archive.raw_digest,
        "archive_size_bytes": archive.size,
        "format": archive.envelope.format,
        "minimum_engine": archive.envelope.minimum_engine,
        "scope": archive.envelope.scope,
        "run_id": archive.run.run_id,
        "display_name": archive.run.display_name,
        "selected_branch_id": archive.envelope.selected_branch_id,
        "selected_head_revision_id": archive.envelope.selected_head_revision_id,
        "viewer_branch_id": archive.run.viewer_branch_id,
        "run_activation_revision_id": archive.run.activation_revision_id,
        "branches": [
            b.model_dump(exclude={"metadata_json", "branch_seed"})
            for b in archive.branches
        ],
        "history": [
            {
                "revision_id": r.revision_id,
                "original_owner_branch_id": r.branch_id,
                "sequence": r.sequence,
                "parent_revision_id": r.parent_revision_id,
                "content_hash_algorithm": r.content_hash_algorithm,
                "content_hash": r.content_hash,
                "payload_schema_version": r.payload_schema_version,
            }
            for r in archive.revisions
        ],
        "included_components": components,
        "selected_head_components": sorted(decode(selected.payload_json)["content"]),
        "unresolved_package_references": unresolved,
        "continuation": "Use the existing operation-scoped preview/replay; import never grants new sporting readiness",
        "audit_event_count": len(archive.audits),
        "checkpoint_count": len(archive.checkpoints),
        "omitted_branch_ids": archive.envelope.omitted_branch_ids,
        "omitted_areas": archive.envelope.omitted_areas,
        "capabilities": {
            "cold_restore_original_identity": True,
            "read_saved_history": True,
            "activate_existing_component_adapters": True,
            "automatic_simulation": False,
            "copy_with_new_run_id": False,
            "overwrite_existing_run": False,
            "other_export_modes": False,
        },
    }


def reviewed_import(session, archive):
    result = {**inventory(archive), "conflicts": conflicts(session, archive)}
    result["can_restore"] = not result["conflicts"]
    result["preview_fingerprint"] = digest(encode(result))
    return result


def _restore_result(archive, command_id, preview_fingerprint):
    return {
        "schema_version": "run_branch_archive_restore_receipt.v1",
        "command_id": command_id,
        "archive_digest": archive.raw_digest,
        "preview_fingerprint": preview_fingerprint,
        "run_id": archive.run.run_id,
        "display_name": archive.run.display_name,
        "selected_branch_id": archive.envelope.selected_branch_id,
        "saved_head_revision_id": archive.envelope.selected_head_revision_id,
        "viewer_branch_id": archive.run.viewer_branch_id,
        "restored_branch_ids": [b.branch_id for b in archive.branches],
        "restored_revision_ids": [r.revision_id for r in archive.revisions],
    }


def _prior_result(session, command_id, fingerprint, archive, request):
    prior = session.get(RunBranchArchiveReceiptModel, command_id)
    if prior is None:
        return None
    if prior.request_fingerprint != fingerprint:
        fail(
            "command_id_reused",
            "Import command ID was already used with different archive/review/audit bytes",
        )
    result = decode(prior.result_json)
    if (
        result != _restore_result(archive, command_id, request["preview_fingerprint"])
        or prior.archive_digest != request["archive_digest"]
        or prior.preview_fingerprint != request["preview_fingerprint"]
        or prior.operator_label != request["operator_label"]
        or prior.audit_reason != request["audit_reason"]
    ):
        fail(
            "invalid_import_receipt",
            "Stored restore receipt does not match its original archive and audited command",
        )
    return result


def _guard_review(session, archive, expected):
    review = reviewed_import(session, archive)
    if review["preview_fingerprint"] != expected:
        fail(
            "stale_import_preview",
            "Archive or target identities/names changed since import preview",
        )
    if not review["can_restore"]:
        fail(
            "identity_conflict",
            "Cold restore cannot overwrite/merge existing identities or Run names; copy/backup restore is a separate mode",
        )


@dataclass
class RunBranchArchiveService:
    repository: object

    def export_preview(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            raw = collect_archive(
                self.repository, session, run_id=run_id, branch_id=branch_id
            )
        archive = Archive(raw)
        # Prove the archive can stand alone; source-DB verification alone is not
        # evidence that an adapter has included every physical dependency.
        validate_in_isolated_database(archive)
        return inventory(archive)

    def export(
        self, *, run_id, branch_id, expected_head_revision_id, expected_archive_digest
    ):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            raw = collect_archive(
                self.repository,
                session,
                run_id=run_id,
                branch_id=branch_id,
                expected_head=expected_head_revision_id,
            )
        if digest(raw) != expected_archive_digest:
            fail(
                "stale_export_preview",
                "Export scope or dependency bytes changed since preview; review again",
            )
        validate_in_isolated_database(Archive(raw))
        return raw

    def import_preview(self, raw):
        archive = Archive(raw)
        validate_in_isolated_database(archive)
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            return reviewed_import(session, archive)

    def confirm(
        self,
        raw,
        *,
        command_id,
        expected_preview_fingerprint,
        explicit_confirmation,
        operator_label,
        audit_reason,
    ):
        if explicit_confirmation is not True:
            fail(
                "confirmation_required",
                "Cold restore requires explicit confirmation of the exact reviewed archive",
            )
        if (
            not isinstance(command_id, str)
            or not command_id.strip()
            or len(command_id) > 128
        ):
            fail(
                "invalid_command_id",
                "Import command ID must be nonblank and at most 128 characters",
            )
        if (
            not operator_label.strip()
            or len(operator_label) > 160
            or not audit_reason.strip()
            or len(audit_reason) > 1000
        ):
            fail(
                "invalid_import_audit",
                "Import requires an operator label and an audit reason",
            )
        archive = Archive(raw)
        request = {
            "archive_digest": archive.raw_digest,
            "preview_fingerprint": expected_preview_fingerprint,
            "operator_label": operator_label,
            "audit_reason": audit_reason,
            "explicit_confirmation": True,
        }
        fingerprint = digest(encode(request))
        # Original hashes always run. A completed receipt is immutable and can
        # answer exact retry without reconstructing already-activated state.
        try:
            with self.repository._session_factory() as session:
                session.execute(text("BEGIN"))
                prior = _prior_result(
                    session, command_id, fingerprint, archive, request
                )
                if prior is not None:
                    return prior
                _guard_review(session, archive, expected_preview_fingerprint)
            # Full independent source/owner/replay/activation validation occurs
            # BEFORE the first target write, even for a client that computes a
            # fingerprint itself and skips preview. No preview token is authority.
            validate_in_isolated_database(archive)
            with self.repository._session_factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                prior = _prior_result(
                    session, command_id, fingerprint, archive, request
                )
                if prior is not None:
                    return prior
                _guard_review(session, archive, expected_preview_fingerprint)
                database = self.repository._engine.url.database
                if (
                    database
                    and database != ":memory:"
                    and shutil.disk_usage(Path(database).resolve().parent).free
                    < archive.size * 3
                ):
                    fail(
                        "insufficient_target_space",
                        "Insufficient free space for this atomic cold restore",
                    )
                # Same independent validation/activation kernel used in preview,
                # repeated against the actual target's production transaction.
                install_archive(self.repository, session, archive)
                result = _restore_result(
                    archive, command_id, expected_preview_fingerprint
                )
                session.add(
                    RunBranchArchiveReceiptModel(
                        command_id=command_id,
                        request_fingerprint=fingerprint,
                        archive_digest=archive.raw_digest,
                        preview_fingerprint=expected_preview_fingerprint,
                        operator_label=operator_label,
                        audit_reason=audit_reason,
                        result_json=encode(result).decode(),
                    )
                )
                session.flush()  # deliberately last; even this failure rolls back activation/allocators
                return result
        except IntegrityError:
            fail(
                "identity_conflict",
                "An archive identity or name is already reserved; no rows were restored",
            )

        except OperationalError as exc:
            message = str(exc.orig).lower()
            if "locked" in message or "busy" in message:
                fail(
                    "target_busy",
                    "Target writer is busy; retry this exact command and archive after it finishes",
                )
            if "full" in message:
                fail(
                    "insufficient_target_space",
                    "SQLite could not finish this atomic import; no partial Run was activated",
                )
            raise
