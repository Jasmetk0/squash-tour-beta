"""Reviewed v2 population adoption. Save and sporting execution remain separate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import Field

from beta_engine.application.calendar_initial_world import (
    CalendarInitialWorldState,
    bootstrap_calendar_player,
    derive_calendar_bootstrap_lifecycle,
)
from beta_engine.application.run_calendar_initial_pool_preview_service import (
    RunCalendarInitialPoolPreviewRequest,
    RunCalendarInitialPoolPreviewService,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash

if TYPE_CHECKING:
    from beta_engine.infrastructure.db import SimulationPersistenceRepository


class CalendarInitialWorldReviewRequest(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_draft_version: int = Field(ge=0)
    expected_package_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation: RunCalendarInitialPoolPreviewRequest
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    lifecycle_policy: PlayerLifecyclePolicy = PlayerLifecyclePolicy(
        policy_id="calendar-initial-population.v2",
        automatic_retirement_age=46,
        provenance="Initial population default; Tour entry and sporting initialization pending",
    )

    def fingerprint(self, run_id: str, branch_id: str) -> str:
        return canonical_hash(
            {
                "run_id": run_id,
                "branch_id": branch_id,
                "request": self.model_dump(mode="json"),
            }
        )


class CalendarInitialWorldConfirmation(FrozenInput):
    review: CalendarInitialWorldReviewRequest
    expected_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class CalendarInitialWorldAdoptionService:
    repository: SimulationPersistenceRepository
    adapter: WorldPackageRunAdapter

    def _prove_target(self, session, *, run_id, branch_id, request):
        from beta_engine.application.run_calendar_read_authority import (
            resolve_saved_run_calendar,
        )
        from beta_engine.infrastructure.db.models import (
            RunBranchModel,
            RunContainerModel,
        )
        from beta_engine.infrastructure.db.run_package_state import (
            get_run_package_state,
            load_saved_run_package_state,
        )

        run, branch = (
            session.get(RunContainerModel, run_id),
            session.get(RunBranchModel, branch_id),
        )
        if (
            run is None
            or branch is None
            or branch.run_id != run_id
            or run.read_only
            or run.storage_kind != "custom_local"
            or run.status != "working"
            or branch.read_only
            or branch.status != "active"
        ):
            raise ValueError(
                "Population adoption requires a writable unstarted custom Run/Branch"
            )
        calendar = resolve_saved_run_calendar(
            session, run_id=run_id, branch_id=branch_id
        )
        if (
            calendar.weeks_per_year,
            calendar.season_start_year_week,
            calendar.start_year,
            calendar.season_count,
        ) == (61, 37, 2000, 50):
            raise ValueError(
                "Use the existing FAX player setup for the legacy sporting calendar"
            )
        state = self.repository._validated_branch_revision_state_in_session(
            session=session, branch=branch
        )
        draft = state.working_draft
        if (
            branch.saved_head_revision_id != request.expected_saved_head
            or state.saved_revision.branch_id != branch_id
            or draft.base_revision_id != request.expected_saved_head
            or draft.draft_version != request.expected_draft_version
            or draft.status != "clean"
        ):
            raise ValueError(
                "Population review is stale; Saved head or Working Draft changed"
            )
        package = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
        saved_package = load_saved_run_package_state(
            state.saved_revision.payload, run_id=run_id, branch_id=branch_id
        )
        if (
            package is None
            or saved_package is None
            or package.fingerprint != request.expected_package_fingerprint
            or saved_package.fingerprint != package.fingerprint
        ):
            raise ValueError(
                "Save the reviewed Run World copy before population adoption"
            )
        return calendar

    def _candidate(self, *, run_id, branch_id, request):
        # No writer lock is held during potentially expensive Earth generation.
        # The transaction below rechecks every source/target proof before writes.
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            self._prove_target(
                session, run_id=run_id, branch_id=branch_id, request=request
            )
            from beta_engine.infrastructure.db.initial_world_state import (
                get_initial_world,
            )

            if (
                get_initial_world(session, run_id=run_id, branch_id=branch_id)
                is not None
            ):
                raise ValueError(
                    "An initial population already exists; it cannot be overwritten"
                )
        pool = RunCalendarInitialPoolPreviewService(
            self.repository, self.adapter
        ).preview(
            run_id=run_id,
            branch_id=branch_id,
            request=request.generation,
        )
        if (
            pool.calendar_saved_revision_id != request.expected_saved_head
            or pool.run_package_state_fingerprint
            != request.expected_package_fingerprint
        ):
            raise ValueError(
                "Population source changed during generation; generate a new review"
            )
        calendar = RunCalendar.from_metadata(pool.run_calendar)
        bootstrap_fp = canonical_hash(
            {
                "algorithm": "calendar_initial_world_bootstrap.v2",
                "pool_preview_fingerprint": pool.preview_fingerprint,
                "lifecycle_policy": request.lifecycle_policy.model_dump(mode="json"),
            }
        )
        world = CalendarInitialWorldState(
            run_id=run_id,
            branch_id=branch_id,
            run_calendar=calendar,
            season=calendar.label(0),
            players=tuple(
                sorted(
                    (
                        bootstrap_calendar_player(
                            p,
                            seed=request.generation.seed,
                            bootstrap_fingerprint=bootstrap_fp,
                        )
                        for p in pool.result.players
                    ),
                    key=lambda p: p.player_id,
                )
            ),
            source_season=calendar.label(0),
            source_fingerprint=pool.preview_fingerprint,
            world_package_id=request.generation.world_package_id,
            world_country_content_fingerprint=pool.world_country_content_fingerprint,
            world_generation_content_fingerprint=pool.world_generation_content_fingerprint,
            run_world_pool_preview_fingerprint=pool.preview_fingerprint,
            bootstrap_seed=request.generation.seed,
            bootstrap_fingerprint=bootstrap_fp,
            adopted_by_command_id=request.command_id,
            audit_label=request.audit_label,
            audit_reason=request.audit_reason,
            adoption_request_fingerprint=request.fingerprint(run_id, branch_id),
            lifecycle_policy=request.lifecycle_policy,
        )
        return world, pool

    def review(self, *, run_id, branch_id, request):
        world, pool = self._candidate(
            run_id=run_id, branch_id=branch_id, request=request
        )
        return {
            "schema_version": "calendar_initial_world_review.v2",
            "preview_only": True,
            "request": request.model_dump(mode="json"),
            "pool_preview": {
                **pool.model_dump(mode="json"),
                "preview_fingerprint": pool.preview_fingerprint,
            },
            "initial_world_fingerprint": world.fingerprint,
            "lifecycle_fingerprint": derive_calendar_bootstrap_lifecycle(
                world
            ).fingerprint,
            "player_count_before": 0,
            "player_count_after": len(world.players),
        }

    def _installed(self, session, *, run_id, branch_id):
        from beta_engine.application.run_calendar_read_authority import (
            resolve_saved_run_calendar,
        )
        from beta_engine.infrastructure.db.initial_world_state import get_initial_world
        from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle

        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        if world is None:
            return None
        if world.schema_version != "initial_world_state.v2":
            raise ValueError("This Branch uses the existing legacy InitialWorld format")
        if (
            resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
            != world.run_calendar
        ):
            raise ValueError("Installed population differs from the saved Run clock")
        expected = derive_calendar_bootstrap_lifecycle(world)
        lifecycle = get_lifecycle(
            session, run_id=run_id, branch_id=branch_id, week=expected.week
        )
        # A fork preserves historical source provenance; its new current world
        # hash may differ. Compare actual player/policy/clock facts separately.
        if (
            lifecycle is None
            or lifecycle.players != expected.players
            or lifecycle.policy != expected.policy
            or lifecycle.week != expected.week
        ):
            raise ValueError("Installed calendar population has no matching lifecycle")
        return {
            "state": world.model_dump(mode="json"),
            "fingerprint": world.fingerprint,
            "lifecycle_fingerprint": lifecycle.fingerprint,
            "sporting_execution_supported": False,
        }

    def read(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            installed = self._installed(session, run_id=run_id, branch_id=branch_id)
            if installed is None:
                raise KeyError("Calendar initial population not found")
            return installed

    def confirm(self, *, run_id, branch_id, confirmation):
        from beta_engine.infrastructure.db.initial_world_state import put_initial_world
        from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle

        request = confirmation.review
        # Exact committed replay is resolved before regeneration or stale-head
        # checks. It also works after a subsequent explicit Save or lost response.
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            current = self._installed(session, run_id=run_id, branch_id=branch_id)
            if current is not None:
                if (
                    current["state"]["adopted_by_command_id"] == request.command_id
                    and current["state"]["adoption_request_fingerprint"]
                    == request.fingerprint(run_id, branch_id)
                    and current["fingerprint"]
                    == confirmation.expected_initial_world_fingerprint
                ):
                    return current
                raise ValueError(
                    "An initial population already exists; command or content differs"
                )
        world, _ = self._candidate(run_id=run_id, branch_id=branch_id, request=request)
        if world.fingerprint != confirmation.expected_initial_world_fingerprint:
            raise ValueError("Population review changed; confirm a fresh review")
        with self.repository._session_factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            current = self._installed(session, run_id=run_id, branch_id=branch_id)
            if current is not None:
                if current["fingerprint"] == world.fingerprint:
                    return current
                raise ValueError("Another population adoption won this target")
            calendar = self._prove_target(
                session, run_id=run_id, branch_id=branch_id, request=request
            )
            if calendar != world.run_calendar:
                raise ValueError("Run clock changed during population review")
            self._require_empty_player_state(
                session, run_id=run_id, branch_id=branch_id
            )
            put_initial_world(session, world)
            put_lifecycle(session, derive_calendar_bootstrap_lifecycle(world))
            return self._installed(session, run_id=run_id, branch_id=branch_id)

    @staticmethod
    def _require_empty_player_state(session, *, run_id, branch_id):
        from sqlalchemy import select

        from beta_engine.infrastructure.db.models import (
            OfficialRankingCandidateModel,
            PlayerHealthWeekStateModel,
            PlayerLifecycleWeekStateModel,
            PlayerSportingWeekStateModel,
            SimulationSlotModel,
        )

        for model in (
            PlayerLifecycleWeekStateModel,
            PlayerHealthWeekStateModel,
            PlayerSportingWeekStateModel,
            SimulationSlotModel,
            OfficialRankingCandidateModel,
        ):
            if (
                session.scalar(
                    select(model)
                    .where(model.run_id == run_id, model.branch_id == branch_id)
                    .limit(1)
                )
                is not None
            ):
                raise ValueError(
                    "Population adoption requires an empty player/ranking/simulation workspace"
                )
