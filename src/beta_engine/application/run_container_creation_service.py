"""Application service for creating a canonical empty product Run."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from beta_engine.domain.run_containers import (
    INITIAL_BRANCH_DISPLAY_NAME,
    RUN_TIMELINE_END_SEASON,
    RUN_TIMELINE_START_SEASON,
    WORKING_RUN_STATUS,
    normalize_run_display_name,
)
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    INITIAL_SAVED_REVISION_KIND,
    INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    INITIAL_SAVED_REVISION_SEQUENCE,
    WORKING_DRAFT_SCHEMA_VERSION,
    initial_saved_revision_change_summary,
    initial_saved_revision_payload,
    saved_revision_content_hash,
)
from beta_engine.infrastructure.db import (
    BranchSavedRevisionRecord,
    BranchWorkingDraftRecord,
    RunBranchRecord,
    RunContainerRecord,
    SimulationPersistenceRepository,
)

EntityIdFactory = Callable[[str], str]


class RunCreationIdentityError(ValueError):
    """Raised when an injected identity factory returns an unusable id."""


def _validated_entity_id(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RunCreationIdentityError(f"{kind} id factory returned a blank id")
    normalized = value.strip()
    if len(normalized) > 128:
        raise RunCreationIdentityError(f"{kind} id must contain at most 128 characters")
    return normalized


@dataclass(slots=True)
class RunContainerCreationService:
    """Create the smallest valid durable Run root defined by the product spec.

    Identity generation is injected. It is intentionally separate from every
    simulation RNG and can be deterministic in tests.
    """

    repository: SimulationPersistenceRepository
    id_factory: EntityIdFactory

    def create_empty_run(self, *, display_name: str) -> RunContainerRecord:
        normalized_name = normalize_run_display_name(display_name)
        run_id = _validated_entity_id(self.id_factory("run"), kind="run")
        branch_id = _validated_entity_id(self.id_factory("branch"), kind="branch")
        revision_id = _validated_entity_id(
            self.id_factory("saved-revision"), kind="saved revision"
        )
        draft_id = _validated_entity_id(
            self.id_factory("working-draft"), kind="working draft"
        )

        run = RunContainerRecord(
            run_id=run_id,
            display_name=normalized_name,
            storage_kind="custom_local",
            read_only=False,
            world_id=None,
            world_package_fingerprint=None,
            config_version=None,
            config_fingerprint=None,
            global_seed=None,
            timeline_start_season=RUN_TIMELINE_START_SEASON,
            timeline_end_season=RUN_TIMELINE_END_SEASON,
            # The legacy column is the current compatibility storage for the
            # canonical Viewer Branch pointer.
            official_branch_id=branch_id,
            status=WORKING_RUN_STATUS,
            metadata={},
        )
        branch = RunBranchRecord(
            branch_id=branch_id,
            run_id=run_id,
            display_name=INITIAL_BRANCH_DISPLAY_NAME,
            status="active",
            read_only=False,
            branch_seed=None,
            forked_from_branch_id=None,
            forked_from_checkpoint_id=None,
            head_checkpoint_id=None,
            legacy_simulation_run_id=None,
            metadata={},
            saved_head_revision_id=revision_id,
        )
        revision_payload = initial_saved_revision_payload(
            run_id=run_id,
            display_name=normalized_name,
            run_status=WORKING_RUN_STATUS,
            timeline_start_season=RUN_TIMELINE_START_SEASON,
            timeline_end_season=RUN_TIMELINE_END_SEASON,
            branch_id=branch_id,
            branch_display_name=INITIAL_BRANCH_DISPLAY_NAME,
            branch_status="active",
        )
        revision_change_summary = initial_saved_revision_change_summary(
            display_name=normalized_name
        )
        revision = BranchSavedRevisionRecord(
            revision_id=revision_id,
            run_id=run_id,
            branch_id=branch_id,
            sequence=INITIAL_SAVED_REVISION_SEQUENCE,
            parent_revision_id=None,
            kind=INITIAL_SAVED_REVISION_KIND,
            payload_schema_version=INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
            content_hash_algorithm=CONTENT_HASH_ALGORITHM,
            content_hash=saved_revision_content_hash(
                revision_id=revision_id,
                run_id=run_id,
                branch_id=branch_id,
                sequence=INITIAL_SAVED_REVISION_SEQUENCE,
                parent_revision_id=None,
                kind=INITIAL_SAVED_REVISION_KIND,
                payload_schema_version=INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
                payload=revision_payload,
                change_summary=revision_change_summary,
            ),
            payload=revision_payload,
            change_summary=revision_change_summary,
        )
        working_draft = BranchWorkingDraftRecord(
            draft_id=draft_id,
            run_id=run_id,
            branch_id=branch_id,
            base_revision_id=revision_id,
            status=CLEAN_WORKING_DRAFT_STATUS,
            change_count=0,
            draft_version=0,
            draft_schema_version=WORKING_DRAFT_SCHEMA_VERSION,
            changes=[],
        )
        return self.repository.create_empty_run_container_atomically(
            run=run,
            branch=branch,
            revision=revision,
            working_draft=working_draft,
        )
