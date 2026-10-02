"""Reviewed materialization of a disposable copied-FAX pre-alpha reference Run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.application.pre_alpha_fax_acceptance_profile import (
    FAX_ACCEPTANCE_FIRST_SEASON,
    FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS,
    FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS,
    PreAlphaFaxAcceptanceProfile,
    PreAlphaFaxAcceptanceProfileService,
)
from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest,
    RunWorldInitialWorldService,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.run_packages import CanonicalPackageDocument, canonical_hash


class PreAlphaFaxReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    display_name: str = Field(min_length=1, max_length=160)
    world_package_id: str = Field(min_length=1, max_length=128)
    season: Literal["2000/2001"] = FAX_ACCEPTANCE_FIRST_SEASON
    seed: int = 200001
    target_pool_size: int = Field(
        default=FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS,
        ge=FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS,
    )
    best_n: int = Field(default=15, ge=1)
    automatic_retirement_age: int = Field(default=46, ge=16, le=120)

    @model_validator(mode="after")
    def validate_release_scale(self) -> "PreAlphaFaxReferenceRequest":
        if self.target_pool_size < FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS:
            raise ValueError(
                f"Copied-FAX release reference requires at least "
                f"{FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS} initial players"
            )
        return self


class PreAlphaFaxReferencePreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["pre_alpha_fax_reference_preview.v1"] = (
        "pre_alpha_fax_reference_preview.v1"
    )
    request: PreAlphaFaxReferenceRequest
    world_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_event_count: int = Field(ge=0)
    world_tour_edition_count: int = Field(ge=0)
    lower_tour_edition_count: int = Field(ge=0)
    required_world_tour_edition_count: int = FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS
    ready_to_materialize: bool

    @property
    def preview_fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class PreAlphaFaxReferenceMaterializeCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request: PreAlphaFaxReferenceRequest
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreAlphaFaxReferenceMaterializationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["pre_alpha_fax_reference_materialization.v1"] = (
        "pre_alpha_fax_reference_materialization.v1"
    )
    run_id: str
    branch_id: str
    saved_revision_id: str
    world_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    acceptance_profile: PreAlphaFaxAcceptanceProfile


@dataclass(slots=True)
class PreAlphaFaxReferenceMaterializationService:
    """Compose existing production boundaries into one reviewed disposable Run bootstrap.

    The source World/Calendar remain immutable inputs. The new Product Run is editable
    and owns copied Package snapshots plus an independently generated InitialWorld.
    Each component is saved through the ordinary Working Draft boundary.
    """

    repository: object
    id_factory: object
    world_adapter: WorldPackageRunAdapter
    calendar_adapter: CalendarPackageRunAdapter
    initial_world_service: RunWorldInitialWorldService

    def _documents(
        self, request: PreAlphaFaxReferenceRequest
    ) -> tuple[CanonicalPackageDocument, CanonicalPackageDocument]:
        world = self.world_adapter.build_document(request.world_package_id)
        calendar = self.calendar_adapter.build_document(request.season)
        return world, calendar

    @staticmethod
    def _calendar_counts(
        document: CanonicalPackageDocument,
    ) -> tuple[int, int, int]:
        events = tuple(
            entity
            for entity in document.entities
            if entity.entity_kind == "calendar.event.v1"
        )
        world_tour = sum(
            1 for entity in events if entity.payload.get("tour_level") == "WORLD_TOUR"
        )
        return len(events), world_tour, len(events) - world_tour

    def preview(
        self, request: PreAlphaFaxReferenceRequest
    ) -> PreAlphaFaxReferencePreview:
        world, calendar = self._documents(request)
        event_count, world_tour, lower = self._calendar_counts(calendar)
        return PreAlphaFaxReferencePreview(
            request=request,
            world_source_fingerprint=world.source_fingerprint,
            calendar_source_fingerprint=calendar.source_fingerprint,
            calendar_event_count=event_count,
            world_tour_edition_count=world_tour,
            lower_tour_edition_count=lower,
            ready_to_materialize=(
                world_tour == FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS
                and request.target_pool_size >= FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS
            ),
        )

    def materialize(
        self, command: PreAlphaFaxReferenceMaterializeCommand
    ) -> PreAlphaFaxReferenceMaterializationResult:
        preview = self.preview(command.request)
        if preview.preview_fingerprint != command.expected_preview_fingerprint:
            raise ValueError("Copied-FAX reference preview changed since review")
        if not preview.ready_to_materialize:
            raise ValueError(
                "Copied-FAX source is not ready: the reviewed calendar must contain "
                f"exactly {FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS} World Tour Editions"
            )

        create = RunContainerCreationService(
            repository=self.repository,
            id_factory=self.id_factory,
        )
        run = create.create_empty_run(display_name=command.request.display_name)
        branch_id = run.viewer_branch_id
        if branch_id is None:
            raise ValueError("Created copied-FAX Run has no initial Branch")

        package_service = RunPackageService(self.repository)
        draft_service = RunWorkingDraftService(
            repository=self.repository,
            id_factory=self.id_factory,
        )
        world_document, calendar_document = self._documents(command.request)

        world_preview = package_service.preview(
            run_id=run.run_id,
            branch_id=branch_id,
            document=world_document,
        )
        world_apply = package_service.confirm(
            run_id=run.run_id,
            branch_id=branch_id,
            document=world_document,
            command_id=self.id_factory("fax-world-package-command"),
            expected_head_revision_id=world_preview.saved_head_revision_id,
            expected_draft_version=world_preview.draft_version,
            expected_state_fingerprint=world_preview.current_state_fingerprint,
            expected_preview_fingerprint=world_preview.preview_fingerprint,
        )
        saved_world = draft_service.save(
            run_id=run.run_id,
            branch_id=branch_id,
            expected_draft_version=world_apply.draft_version,
        )

        calendar_preview = package_service.preview(
            run_id=run.run_id,
            branch_id=branch_id,
            document=calendar_document,
        )
        calendar_apply = package_service.confirm(
            run_id=run.run_id,
            branch_id=branch_id,
            document=calendar_document,
            command_id=self.id_factory("fax-calendar-package-command"),
            expected_head_revision_id=saved_world.saved_revision.revision_id,
            expected_draft_version=calendar_preview.draft_version,
            expected_state_fingerprint=calendar_preview.current_state_fingerprint,
            expected_preview_fingerprint=calendar_preview.preview_fingerprint,
        )
        draft_service.save(
            run_id=run.run_id,
            branch_id=branch_id,
            expected_draft_version=calendar_apply.draft_version,
        )

        adoption_request = RunWorldInitialWorldAdoptionRequest(
            command_id=self.id_factory("fax-initial-world-command"),
            generation=RunWorldInitialPoolPreviewRequest(
                world_package_id=command.request.world_package_id,
                season=command.request.season,
                seed=command.request.seed,
                target_pool_size=command.request.target_pool_size,
            ),
            audit_label="Pre-alpha copied-FAX reference materializer",
            audit_reason=(
                "Materialize reviewed disposable copied-FAX release-test InitialWorld"
            ),
            official_run=False,
            best_n=command.request.best_n,
            automatic_retirement_age=command.request.automatic_retirement_age,
        )
        initial_world = self.initial_world_service.preview(
            run_id=run.run_id,
            branch_id=branch_id,
            request=adoption_request,
        )
        adopted = self.repository.adopt_initial_world(
            initial_world,
            lifecycle_policy=PlayerLifecyclePolicy(
                policy_id="pre-alpha-fax-reference-lifecycle.v1",
                automatic_retirement_age=command.request.automatic_retirement_age,
                provenance=(
                    "Reviewed copied-FAX pre-alpha release-test reference policy"
                ),
            ),
        )
        state = self.repository.get_branch_revision_state(branch_id=branch_id)
        saved_initial = draft_service.save_initial_world(
            run_id=run.run_id,
            branch_id=branch_id,
            expected_draft_version=state.working_draft.draft_version,
            expected_initial_world_fingerprint=adopted.fingerprint,
        )

        acceptance = PreAlphaFaxAcceptanceProfileService(
            self.repository._session_factory
        ).inspect(run_id=run.run_id, branch_id=branch_id)
        if not acceptance.ready_for_long_acceptance:
            blockers = ", ".join(
                issue.code for issue in acceptance.issues if issue.severity == "error"
            )
            raise ValueError(
                "Materialized copied-FAX Run failed its own long-acceptance input gate: "
                + blockers
            )

        return PreAlphaFaxReferenceMaterializationResult(
            run_id=run.run_id,
            branch_id=branch_id,
            saved_revision_id=saved_initial.saved_revision.revision_id,
            world_source_fingerprint=world_document.source_fingerprint,
            calendar_source_fingerprint=calendar_document.source_fingerprint,
            initial_world_fingerprint=adopted.fingerprint,
            acceptance_profile=acceptance,
        )
