"""Preview and atomically apply independent Package snapshots to a Working Draft."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select, text, update

from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    CanonicalPackageDocument,
    PackageEntity,
    PackagePreview,
    RunPackageEntity,
    RunPackageState,
    canonical_hash,
    entity_content_fingerprint,
)
from beta_engine.domain.run_revisions import (
    DIRTY_WORKING_DRAFT_STATUS,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
)
from beta_engine.domain.run_containers import (
    COMPLETED_RUN_STATUS,
    LEGACY_ACTIVE_RUN_STATUS,
    WORKING_RUN_STATUS,
)
from beta_engine.infrastructure.db.models import (
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
    RunPackageApplicationReceiptModel,
    RunPackageIdentityAllocatorModel,
)
from beta_engine.infrastructure.db.run_package_state import (
    get_run_package_state,
    put_run_package_state,
)


class RunPackageConflictError(ValueError):
    pass


class RunPackageNotFoundError(ValueError):
    pass


def _baseline(entity: PackageEntity) -> str:
    return entity_content_fingerprint(
        entity_kind=entity.entity_kind,
        entity_schema_version=entity.entity_schema_version,
        scope=entity.scope,
        payload=entity.payload,
        references=entity.references,
    )


def _require_writable(run, branch) -> None:
    if (
        run.read_only
        or branch.read_only
        or branch.status != "active"
        or run.status
        not in {WORKING_RUN_STATUS, LEGACY_ACTIVE_RUN_STATUS, COMPLETED_RUN_STATUS}
    ):
        raise RunPackageConflictError("Run/Branch lifecycle is not writable")


def _compatible(target, reference) -> bool:
    return (
        target is not None
        and target.entity_kind == reference.expected_entity_kind
        and target.entity_schema_version >= reference.minimum_schema_version
    )


def _load_receipt_result(
    receipt, *, run_id: str, branch_id: str
) -> tuple[RunPackageState | None, int]:
    try:
        payload = json.loads(receipt.payload_json)
        if (
            not isinstance(payload, dict)
            or payload.get("command_id") != receipt.command_id
            or payload.get("request_fingerprint") != receipt.request_fingerprint
            or not isinstance(payload.get("draft_version"), int)
            or payload["draft_version"] < 0
        ):
            raise ValueError("receipt metadata mismatch")
        raw_state = payload.get("state")
        state = (
            RunPackageState.model_validate(raw_state) if raw_state is not None else None
        )
        if state is not None and (state.run_id, state.branch_id) != (run_id, branch_id):
            raise ValueError("receipt result scope mismatch")
        fingerprint = state.fingerprint if state is not None else canonical_hash(None)
        if fingerprint != receipt.result_fingerprint:
            raise ValueError("receipt result fingerprint mismatch")
        return state, payload["draft_version"]
    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise RunPackageConflictError(
            f"Package application receipt is corrupt: {exc}"
        ) from exc


@dataclass(frozen=True, slots=True)
class PackageApplyResult:
    state: RunPackageState | None
    draft_version: int
    already_applied: bool
    command_id: str


@dataclass(slots=True)
class RunPackageService:
    repository: object

    def _context(self, session, run_id: str, branch_id: str):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.run_id == run_id,
                BranchWorkingDraftModel.branch_id == branch_id,
            )
        )
        if run is None or branch is None or branch.run_id != run_id or draft is None:
            raise RunPackageNotFoundError("Run/Branch Working Draft was not found")
        return run, branch, draft

    def get(self, *, run_id: str, branch_id: str) -> RunPackageState | None:
        with self.repository._session_factory() as session:
            self._context(session, run_id, branch_id)
            return get_run_package_state(session, run_id=run_id, branch_id=branch_id)

    def _preview(
        self,
        session,
        *,
        run_id: str,
        branch_id: str,
        document: CanonicalPackageDocument,
    ) -> PackagePreview:
        _, branch, draft = self._context(session, run_id, branch_id)
        state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
        entities = state.entities if state else ()
        current = {(e.source_package_id, e.source_entity_id): e for e in entities}
        versions = {
            (v.package_id, v.source_version): v
            for v in (state.package_versions if state else ())
        }
        additions = []
        unchanged = []
        updates = []
        invalid = []
        conflicts = []
        incoming = []
        reviewed_documents = (
            (document, *document.leaf_documents())
            if document.package_type.value == "Setup"
            else document.leaf_documents()
        )
        for leaf in reviewed_documents:
            prior_same = versions.get((leaf.package_id, leaf.source_version))
            if prior_same and prior_same.source_fingerprint != leaf.source_fingerprint:
                conflicts.append(
                    f"{leaf.package_id}@{leaf.source_version}:source_history_divergence"
                )
            prior_types = {
                v.package_type
                for v in (state.package_versions if state else ())
                if v.package_id == leaf.package_id
            }
            if prior_types and leaf.package_type not in prior_types:
                conflicts.append(f"{leaf.package_id}:package_type_changed")
            latest = max(
                (
                    v
                    for v in (state.package_versions if state else ())
                    if v.package_id == leaf.package_id
                ),
                key=lambda v: v.source_version,
                default=None,
            )
            if (
                latest
                and leaf.source_version > latest.source_version
                and leaf.parent_source_fingerprint != latest.source_fingerprint
            ):
                conflicts.append(
                    f"{leaf.package_id}@{leaf.source_version}:divergent_ancestry"
                )
            for entity in leaf.entities:
                key = (leaf.package_id, entity.source_entity_id)
                incoming.append(key)
                label = f"{leaf.package_id}/{entity.source_entity_id}"
                if not entity.valid:
                    invalid.append(label)
                    continue
                old = current.get(key)
                if old is None:
                    additions.append(label)
                elif old.content_fingerprint == _baseline(entity):
                    unchanged.append(label)
                else:
                    updates.append(label)
                    if old.content_fingerprint != old.source_baseline_fingerprint:
                        conflicts.append(label + ":local_divergence")
        included = set(incoming)
        not_included = [
            f"{e.source_package_id}/{e.source_entity_id}"
            for e in entities
            if (e.source_package_id, e.source_entity_id) not in included
        ]
        incoming_targets = {
            (leaf.package_id, entity.source_entity_id): entity
            for leaf in document.leaf_documents()
            for entity in leaf.entities
            if entity.valid
        }
        available_targets = {**current, **incoming_targets}
        unresolved = []
        resolvable = []
        for e in entities:
            for ref in e.references:
                key = (ref.source_package_id, ref.source_entity_id)
                target = available_targets.get(key)
                if key not in current and _compatible(target, ref):
                    resolvable.append(
                        f"{e.source_package_id}/{e.source_entity_id}->{ref.source_package_id}/{ref.source_entity_id}"
                    )
                elif target is None:
                    unresolved.append(
                        f"{e.source_package_id}/{e.source_entity_id}->{ref.source_package_id}/{ref.source_entity_id}"
                    )
                elif not _compatible(target, ref):
                    conflicts.append(
                        f"{e.source_package_id}/{e.source_entity_id}->{ref.source_package_id}/{ref.source_entity_id}:incompatible_reference"
                    )
        for leaf in document.leaf_documents():
            for e in leaf.entities:
                for ref in e.references:
                    target = available_targets.get(
                        (ref.source_package_id, ref.source_entity_id)
                    )
                    if target is None:
                        unresolved.append(
                            f"{leaf.package_id}/{e.source_entity_id}->{ref.source_package_id}/{ref.source_entity_id}"
                        )
                    elif not _compatible(target, ref):
                        conflicts.append(
                            f"{leaf.package_id}/{e.source_entity_id}->{ref.source_package_id}/{ref.source_entity_id}:incompatible_reference"
                        )
        return PackagePreview(
            document=document,
            run_id=run_id,
            branch_id=branch_id,
            saved_head_revision_id=branch.saved_head_revision_id,
            draft_version=draft.draft_version,
            current_state_fingerprint=state.fingerprint if state else None,
            additions=tuple(sorted(set(additions))),
            unchanged=tuple(sorted(set(unchanged))),
            updates=tuple(sorted(set(updates))),
            not_included=tuple(sorted(set(not_included))),
            unresolved=tuple(sorted(set(unresolved))),
            automatically_resolvable=tuple(sorted(set(resolvable))),
            invalid=tuple(sorted(set(invalid))),
            conflicts=tuple(sorted(set(conflicts))),
        )

    def preview(
        self, *, run_id: str, branch_id: str, document: CanonicalPackageDocument
    ) -> PackagePreview:
        with self.repository._session_factory() as session:
            return self._preview(
                session, run_id=run_id, branch_id=branch_id, document=document
            )

    def confirm(
        self,
        *,
        run_id: str,
        branch_id: str,
        document: CanonicalPackageDocument,
        command_id: str,
        expected_head_revision_id: str,
        expected_draft_version: int,
        expected_state_fingerprint: str | None,
        expected_preview_fingerprint: str,
        conflict_resolutions: dict[str, Literal["keep_run", "use_source"]]
        | None = None,
        selected_entities: tuple[str, ...] | None = None,
        fault_at: str | None = None,
    ) -> PackageApplyResult:
        resolutions = conflict_resolutions or {}
        request = {
            "document": document.model_dump(mode="json"),
            "head": expected_head_revision_id,
            "draft": expected_draft_version,
            "state": expected_state_fingerprint,
            "preview": expected_preview_fingerprint,
            "resolutions": resolutions,
            "selected": selected_entities,
        }
        request_fp = canonical_hash(request)
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            receipt = session.get(
                RunPackageApplicationReceiptModel, (run_id, branch_id, command_id)
            )
            if receipt:
                if receipt.request_fingerprint != request_fp:
                    raise RunPackageConflictError(
                        "command id was reused with a different request"
                    )
                receipt_state, receipt_draft_version = _load_receipt_result(
                    receipt, run_id=run_id, branch_id=branch_id
                )
                return PackageApplyResult(
                    receipt_state,
                    receipt_draft_version,
                    True,
                    command_id,
                )
            run, branch, draft = self._context(session, run_id, branch_id)
            _require_writable(run, branch)
            preview = self._preview(
                session, run_id=run_id, branch_id=branch_id, document=document
            )
            if (
                branch.saved_head_revision_id != expected_head_revision_id
                or draft.draft_version != expected_draft_version
                or preview.current_state_fingerprint != expected_state_fingerprint
                or preview.preview_fingerprint != expected_preview_fingerprint
            ):
                raise RunPackageConflictError("Package preview is stale")
            reviewed_labels = {
                f"{d.package_id}/{e.source_entity_id}"
                for d in document.leaf_documents()
                for e in d.entities
            }
            selected = set(
                [
                    f"{d.package_id}/{e.source_entity_id}"
                    for d in document.leaf_documents()
                    for e in d.entities
                ]
                if selected_entities is None
                else selected_entities
            )
            if selected - reviewed_labels:
                raise RunPackageConflictError("Selection contains an unknown entity")
            divergence_labels = {
                conflict.removesuffix(":local_divergence")
                for conflict in preview.conflicts
                if conflict.endswith(":local_divergence")
            }
            if set(resolutions) - divergence_labels:
                raise RunPackageConflictError("Conflict resolution is not reviewed")
            if any(item in selected for item in preview.invalid):
                raise RunPackageConflictError("Selected logical bundle is invalid")
            selected_packages = {label.split("/", 1)[0] for label in selected}
            hard = []
            for conflict in preview.conflicts:
                if conflict.endswith("incompatible_reference"):
                    source_label, target_part = conflict.split("->", 1)
                    target_label = target_part.rsplit(":", 1)[0]
                    if source_label in selected or target_label in selected:
                        hard.append(conflict)
                    continue
                if not (
                    conflict.endswith("source_history_divergence")
                    or conflict.endswith("divergent_ancestry")
                    or conflict.endswith("package_type_changed")
                ):
                    continue
                package_id = conflict.split("@", 1)[0].split(":", 1)[0]
                if package_id == document.package_id or package_id in selected_packages:
                    hard.append(conflict)
            if hard:
                raise RunPackageConflictError(
                    "Selected Package scope has a hard conflict"
                )
            for conflict in preview.conflicts:
                if (
                    conflict.endswith(":local_divergence")
                    and conflict.removesuffix(":local_divergence") in selected
                    and conflict.removesuffix(":local_divergence") not in resolutions
                ):
                    raise RunPackageConflictError(
                        "Local divergence requires keep_run or use_source"
                    )
            old = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
            entity_map = {
                (e.source_package_id, e.source_entity_id): e
                for e in (old.entities if old else ())
            }
            allocator = session.get(RunPackageIdentityAllocatorModel, run_id)
            changed = False
            versions = list(old.package_versions if old else ())
            documents_to_record = (
                (document, *document.leaf_documents())
                if document.package_type.value == "Setup"
                else document.leaf_documents()
            )
            for leaf in documents_to_record:
                leaf_selected = tuple(
                    sorted(
                        entity.source_entity_id
                        for entity in leaf.entities
                        if f"{leaf.package_id}/{entity.source_entity_id}" in selected
                    )
                )
                if leaf is not document and not leaf_selected:
                    continue
                if (
                    leaf is document
                    and document.package_type.value != "Setup"
                    and not leaf_selected
                ):
                    continue
                if (
                    leaf is document
                    and document.package_type.value == "Setup"
                    and not selected
                ):
                    continue
                version = AppliedPackageVersion(
                    package_type=leaf.package_type,
                    package_id=leaf.package_id,
                    source_version=leaf.source_version,
                    source_fingerprint=leaf.source_fingerprint,
                    parent_source_fingerprint=leaf.parent_source_fingerprint,
                    document_explicit_scope=leaf.explicit_scope,
                    applied_entity_ids=(
                        tuple(sorted(selected))
                        if leaf is document and document.package_type.value == "Setup"
                        else leaf_selected
                    ),
                    conflict_resolutions={
                        key: value
                        for key, value in resolutions.items()
                        if key.startswith(f"{leaf.package_id}/")
                    },
                    frozen_child_versions=(
                        tuple(
                            f"{child.package_id}@{child.source_version}:{child.source_fingerprint}"
                            for child in document.children
                        )
                        if leaf is document and document.package_type.value == "Setup"
                        else ()
                    ),
                    provenance=leaf.provenance,
                )
                existing_version = next(
                    (
                        v
                        for v in versions
                        if (v.package_id, v.source_version)
                        == (leaf.package_id, leaf.source_version)
                    ),
                    None,
                )
                if (
                    existing_version is not None
                    and existing_version.source_fingerprint
                    == version.source_fingerprint
                ):
                    version = version.model_copy(
                        update={
                            "applied_entity_ids": tuple(
                                sorted(
                                    set(existing_version.applied_entity_ids)
                                    | set(version.applied_entity_ids)
                                )
                            ),
                            "conflict_resolutions": {
                                **existing_version.conflict_resolutions,
                                **version.conflict_resolutions,
                            },
                        }
                    )
                for entity in leaf.entities:
                    label = f"{leaf.package_id}/{entity.source_entity_id}"
                    if (
                        label not in selected
                        or not entity.valid
                        or resolutions.get(label) == "keep_run"
                    ):
                        continue
                    key = (leaf.package_id, entity.source_entity_id)
                    prior = entity_map.get(key)
                    if prior is None and allocator is None:
                        allocator = RunPackageIdentityAllocatorModel(
                            run_id=run_id, next_run_local_id=1
                        )
                        session.add(allocator)
                    candidate = RunPackageEntity(
                        run_local_id=(
                            prior.run_local_id
                            if prior is not None
                            else allocator.next_run_local_id
                        ),
                        source_package_id=leaf.package_id,
                        source_package_version=leaf.source_version,
                        source_package_fingerprint=leaf.source_fingerprint,
                        source_entity_id=entity.source_entity_id,
                        entity_kind=entity.entity_kind,
                        entity_schema_version=entity.entity_schema_version,
                        scope=entity.scope,
                        payload=entity.payload,
                        source_baseline_fingerprint=_baseline(entity),
                        references=entity.references,
                    )
                    if prior is None:
                        allocator.next_run_local_id += 1
                    if prior != candidate:
                        entity_map[key] = candidate
                        changed = True
                    if fault_at == "after_identity_allocation" and prior is None:
                        raise RuntimeError(
                            "injected failure after Package identity allocation"
                        )
                if existing_version is None:
                    versions.append(version)
                    changed = True
                elif existing_version != version:
                    versions[versions.index(existing_version)] = version
                    changed = True
            if not changed:
                evidence = {
                    "command_id": command_id,
                    "request_fingerprint": request_fp,
                    "document": document.model_dump(mode="json"),
                    "selected_entities": sorted(selected),
                    "conflict_resolutions": resolutions,
                    "preview": preview.model_dump(mode="json"),
                    "draft_version": draft.draft_version,
                    "already_applied": True,
                    "state": old.model_dump(mode="json") if old else None,
                }
                session.add(
                    RunPackageApplicationReceiptModel(
                        run_id=run_id,
                        branch_id=branch_id,
                        command_id=command_id,
                        request_fingerprint=request_fp,
                        result_fingerprint=old.fingerprint
                        if old
                        else canonical_hash(None),
                        payload_json=json.dumps(
                            evidence, sort_keys=True, separators=(",", ":")
                        ),
                    )
                )
                return PackageApplyResult(old, draft.draft_version, True, command_id)
            state = RunPackageState(
                run_id=run_id,
                branch_id=branch_id,
                entities=tuple(
                    sorted(entity_map.values(), key=lambda e: e.run_local_id)
                ),
                package_versions=tuple(
                    sorted(versions, key=lambda v: (v.package_id, v.source_version))
                ),
            )
            put_run_package_state(session, state)
            claimed = session.execute(
                update(BranchWorkingDraftModel)
                .where(
                    BranchWorkingDraftModel.draft_id == draft.draft_id,
                    BranchWorkingDraftModel.draft_version == expected_draft_version,
                )
                .values(
                    status=DIRTY_WORKING_DRAFT_STATUS,
                    change_count=draft.change_count + 1,
                    draft_version=expected_draft_version + 1,
                    draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
                    changes_json=json.dumps(
                        json.loads(draft.changes_json)
                        + [
                            {
                                "kind": "run_package_state",
                                "fingerprint": state.fingerprint,
                            }
                        ],
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            ).rowcount
            if claimed != 1:
                raise RunPackageConflictError("Working Draft changed concurrently")
            result = {
                "command_id": command_id,
                "request_fingerprint": request_fp,
                "document": document.model_dump(mode="json"),
                "selected_entities": sorted(selected),
                "conflict_resolutions": resolutions,
                "preview": preview.model_dump(mode="json"),
                "draft_version": expected_draft_version + 1,
                "state_fingerprint": state.fingerprint,
                "already_applied": False,
                "state": state.model_dump(mode="json"),
                "source_to_run_local_ids": {
                    f"{entity.source_package_id}/{entity.source_entity_id}": entity.run_local_id
                    for entity in state.entities
                    if f"{entity.source_package_id}/{entity.source_entity_id}"
                    in selected
                },
            }
            session.add(
                RunPackageApplicationReceiptModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    command_id=command_id,
                    request_fingerprint=request_fp,
                    result_fingerprint=state.fingerprint,
                    payload_json=json.dumps(
                        result, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            return PackageApplyResult(
                state, expected_draft_version + 1, False, command_id
            )

    def edit_entity(
        self,
        *,
        run_id: str,
        branch_id: str,
        run_local_id: int,
        payload: dict,
        expected_draft_version: int,
        expected_state_fingerprint: str,
    ) -> RunPackageState:
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            run, branch, draft = self._context(session, run_id, branch_id)
            state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
            if (
                state is None
                or state.fingerprint != expected_state_fingerprint
                or draft.draft_version != expected_draft_version
            ):
                raise RunPackageConflictError("Run Package edit is stale")
            _require_writable(run, branch)
            found = False
            entities = []
            for entity in state.entities:
                if entity.run_local_id == run_local_id:
                    entity = entity.model_copy(
                        update={"payload": payload, "provenance": "manual"}
                    )
                    found = True
                entities.append(entity)
            if not found:
                raise RunPackageNotFoundError("Run-local Package entity was not found")
            updated = state.model_copy(update={"entities": tuple(entities)})
            put_run_package_state(session, updated)
            session.execute(
                update(BranchWorkingDraftModel)
                .where(
                    BranchWorkingDraftModel.draft_id == draft.draft_id,
                    BranchWorkingDraftModel.draft_version == expected_draft_version,
                )
                .values(
                    status=DIRTY_WORKING_DRAFT_STATUS,
                    change_count=draft.change_count + 1,
                    draft_version=expected_draft_version + 1,
                    draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
                    changes_json=json.dumps(
                        json.loads(draft.changes_json)
                        + [
                            {
                                "kind": "run_package_state",
                                "fingerprint": updated.fingerprint,
                            }
                        ],
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            )
            return updated
