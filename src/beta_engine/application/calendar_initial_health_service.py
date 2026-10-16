"""Reviewed initial health for an already saved calendar-owned population."""

from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import select

from beta_engine.application.calendar_initial_world import (
    derive_calendar_bootstrap_lifecycle,
)
from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar,
)
from beta_engine.domain.players.calendar_health import CalendarHealthState
from beta_engine.domain.players.calendar_initial_health import (
    CalendarInitialHealthState,
)
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.initial_world_state import (
    get_initial_world,
    load_saved_initial_world,
)
from beta_engine.infrastructure.db.models import (
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_health_state import (
    get_health,
    health_component,
    put_health,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle


class CalendarInitialHealthRequest(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    expected_saved_head: str = Field(min_length=1)
    expected_draft_version: int = Field(ge=0)
    expected_population_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    initialization_policy: Literal["fresh_without_history.v1"] = (
        "fresh_without_history.v1"
    )
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)

    def fingerprint(self, run_id, branch_id):
        return canonical_hash(
            {
                "run_id": run_id,
                "branch_id": branch_id,
                "request": self.model_dump(mode="json"),
            }
        )


class CalendarInitialHealthConfirmation(FrozenInput):
    review: CalendarInitialHealthRequest
    expected_health_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass
class CalendarInitialHealthService:
    repository: object

    def _context(self, session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Initial health Run/Branch not found")
        clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
        revision = self.repository._validated_branch_revision_state_in_session(
            session=session, branch=branch
        )
        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        saved_world = load_saved_initial_world(
            revision.saved_revision.payload, run_id=run_id, branch_id=branch_id
        )
        if (
            world is None
            or world.schema_version != "initial_world_state.v2"
            or saved_world is None
            or saved_world.fingerprint != world.fingerprint
            or world.run_calendar != clock
        ):
            raise ValueError(
                "Save the calendar-owned population before preparing initial health"
            )
        expected = derive_calendar_bootstrap_lifecycle(world)
        life = get_lifecycle(
            session, run_id=run_id, branch_id=branch_id, week=expected.week
        )
        if (
            life is None
            or life.players != expected.players
            or life.policy != expected.policy
        ):
            raise ValueError("Initial health population lifecycle is inconsistent")
        health = get_health(
            session, run_id=run_id, branch_id=branch_id, week=expected.week
        )
        if health is not None and (
            not isinstance(health, (CalendarInitialHealthState, CalendarHealthState))
            or tuple(p.player_id for p in health.players)
            != tuple(p.player_id for p in life.players)
        ):
            raise ValueError("Initial health differs from its population")
        return run, branch, revision, world, life, health

    def _view(self, session, context):
        _, branch, revision, world, life, health = context
        component = health_component(
            session, run_id=world.run_id, branch_id=world.branch_id
        )
        saved_component = revision.saved_revision.payload.get("content", {}).get(
            "player_health_state"
        )
        return {
            "schema_version": "calendar_initial_health_view.v1",
            "run_id": world.run_id,
            "branch_id": world.branch_id,
            "saved_head_revision_id": branch.saved_head_revision_id,
            "population_fingerprint": world.fingerprint,
            "run_calendar": world.run_calendar.to_metadata(),
            "player_count": len(life.players),
            "state": health.model_dump(mode="json") if health else None,
            "health_fingerprint": health.fingerprint if health else None,
            "health_component_fingerprint": component["fingerprint"]
            if component
            else None,
            "saved": health is not None and component == saved_component,
            "draft_version": revision.working_draft.draft_version,
            "draft_status": revision.working_draft.status,
        }

    def inspect(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            return self._view(session, self._context(session, run_id, branch_id))

    def _candidate(self, context, request):
        run, branch, revision, world, life, health = context
        if (
            run.read_only
            or branch.read_only
            or run.storage_kind != "custom_local"
            or run.status != "working"
            or branch.status != "active"
        ):
            raise ValueError("Initial health requires a writable unstarted Run/Branch")
        draft = revision.working_draft
        if (
            health is not None
            or branch.saved_head_revision_id != request.expected_saved_head
            or revision.saved_revision.branch_id != branch.branch_id
            or draft.base_revision_id != request.expected_saved_head
            or draft.status != "clean"
            or draft.draft_version != request.expected_draft_version
            or world.fingerprint != request.expected_population_fingerprint
        ):
            raise ValueError("Initial health review is stale or health already exists")
        return CalendarInitialHealthState(
            run_id=world.run_id,
            branch_id=world.branch_id,
            week=life.week,
            players=tuple(
                PlayerHealthProfile(player_id=p.player_id) for p in life.players
            ),
            source_initial_world_fingerprint=world.fingerprint,
            command_id=request.command_id,
            request_fingerprint=request.fingerprint(world.run_id, world.branch_id),
            audit_label=request.audit_label,
            audit_reason=request.audit_reason,
        )

    def preview(self, *, run_id, branch_id, request):
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            state = self._candidate(self._context(session, run_id, branch_id), request)
            return {
                "schema_version": "calendar_initial_health_review.v1",
                "request": request.model_dump(mode="json"),
                "state": state.model_dump(mode="json"),
                "health_fingerprint": state.fingerprint,
            }

    def confirm(self, *, run_id, branch_id, confirmation):
        import json

        with self.repository._session_factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            context = self._context(session, run_id, branch_id)
            current = context[-1]
            request = confirmation.review
            if current is not None:
                if (
                    not isinstance(current, CalendarInitialHealthState)
                    or current.fingerprint != confirmation.expected_health_fingerprint
                    or current.request_fingerprint
                    != request.fingerprint(run_id, branch_id)
                ):
                    raise ValueError(
                        "Initial health command differs from the installed baseline"
                    )
                return self._view(session, context)
            state = self._candidate(context, request)
            if state.fingerprint != confirmation.expected_health_fingerprint:
                raise ValueError("Initial health differs from the reviewed baseline")
            put_health(session, state)
            component = health_component(session, run_id=run_id, branch_id=branch_id)
            draft = session.scalar(
                select(BranchWorkingDraftModel).where(
                    BranchWorkingDraftModel.run_id == run_id,
                    BranchWorkingDraftModel.branch_id == branch_id,
                )
            )
            if draft is None or draft.draft_version != request.expected_draft_version:
                raise ValueError("Initial health Working Draft changed concurrently")
            # The existing Health Save command validates this exact component proof.
            draft.status = "dirty"
            draft.change_count = 1
            draft.draft_version += 1
            draft.changes_json = json.dumps(
                [
                    {
                        "kind": "player_health_state",
                        "fingerprint": component["fingerprint"],
                        "command_id": request.command_id,
                    }
                ],
                sort_keys=True,
                separators=(",", ":"),
            )
            session.flush()
            return self._view(session, self._context(session, run_id, branch_id))
