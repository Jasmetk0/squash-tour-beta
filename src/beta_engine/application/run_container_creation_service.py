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
from beta_engine.infrastructure.db import (
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
        )
        return self.repository.create_empty_run_container_atomically(
            run=run, branch=branch
        )
