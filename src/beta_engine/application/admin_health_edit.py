"""Reviewed Admin Health edits on the current Run/Branch health head."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, field_validator, model_validator
from sqlalchemy import select, text, update

from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_health import (
    CalendarHealthEditEvidence,
    CalendarHealthOrigin,
    CalendarHealthProfile,
    CalendarHealthRecord,
    CalendarHealthState,
)
from beta_engine.domain.players.calendar_initial_health import (
    CalendarInitialHealthState,
)
from beta_engine.domain.players.health import (
    PermanentHealthConsequence,
    PlayerHealthProfile,
    PlayerHealthRecord,
    PlayerHealthWeekState,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.run_containers import (
    COMPLETED_RUN_STATUS,
    LEGACY_ACTIVE_RUN_STATUS,
    WORKING_RUN_STATUS,
)
from beta_engine.domain.run_revisions import (
    DIRTY_WORKING_DRAFT_STATUS,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    BranchWorkingDraftModel,
    PlayerHealthAdminEditReceiptModel,
    PlayerHealthWeekStateModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_health_state import (
    _load,
    get_health,
    health_component,
    load_saved_health,
    replace_health_head,
)

HealthEditMode = Literal["pre_start_input", "current_state_correction"]


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class AdminHealthEditRequest(FrozenInput):
    schema_version: Literal["admin_health_edit_request.v1"] = (
        "admin_health_edit_request.v1"
    )
    command_id: str = Field(min_length=1, max_length=128)
    player_id: str = Field(min_length=1, max_length=160)
    mode: HealthEditMode
    expected_draft_version: int = Field(ge=0)
    records: tuple[PlayerHealthRecord, ...] = ()
    permanent_consequences: tuple[PermanentHealthConsequence, ...] = ()
    audit_label: str = Field(min_length=1, max_length=200)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @field_validator("records", mode="before")
    @classmethod
    def canonical_records(cls, value) -> tuple[PlayerHealthRecord, ...]:
        if value is None:
            return ()
        records = tuple(
            item
            if isinstance(item, PlayerHealthRecord)
            else PlayerHealthRecord.model_validate_json(json.dumps(item))
            for item in value
        )
        return tuple(sorted(records, key=lambda record: record.record_id))

    @field_validator("permanent_consequences", mode="before")
    @classmethod
    def canonical_consequences(cls, value) -> tuple[PermanentHealthConsequence, ...]:
        if value is None:
            return ()
        consequences = tuple(
            item
            if isinstance(item, PermanentHealthConsequence)
            else PermanentHealthConsequence.model_validate_json(json.dumps(item))
            for item in value
        )
        return tuple(
            sorted(
                consequences,
                key=lambda consequence: consequence.consequence_id,
            )
        )

    @model_validator(mode="after")
    def unique_ids(self):
        record_ids = tuple(record.record_id for record in self.records)
        consequence_ids = tuple(
            consequence.consequence_id for consequence in self.permanent_consequences
        )
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("Admin Health edit record IDs must be unique")
        if len(consequence_ids) != len(set(consequence_ids)):
            raise ValueError("Admin Health edit consequence IDs must be unique")
        return self

    def fingerprint_for_scope(self, *, run_id: str, branch_id: str) -> str:
        return _hash(
            {
                "run_id": run_id,
                "branch_id": branch_id,
                "request": self.model_dump(mode="json"),
            }
        )


class CalendarAdminHealthEditRequest(AdminHealthEditRequest):
    schema_version: Literal["admin_health_edit_request.v2"] = (
        "admin_health_edit_request.v2"
    )
    expected_saved_head: str = Field(min_length=1)
    expected_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    records: tuple[CalendarHealthRecord, ...] = ()

    @field_validator("records", mode="before")
    @classmethod
    def canonical_records(cls, value):
        records = tuple(
            item
            if isinstance(item, CalendarHealthRecord)
            else CalendarHealthRecord.model_validate_json(json.dumps(item))
            for item in (value or ())
        )
        return tuple(sorted(records, key=lambda record: record.record_id))


HealthEditRequest = Annotated[
    AdminHealthEditRequest | CalendarAdminHealthEditRequest,
    Field(discriminator="schema_version"),
    BeforeValidator(
        lambda value: (
            {"schema_version": "admin_health_edit_request.v1", **value}
            if isinstance(value, dict) and "schema_version" not in value
            else value
        )
    ),
]


class AdminHealthEditPreview(FrozenInput):
    schema_version: Literal[
        "admin_health_edit_preview.v1", "admin_health_edit_preview.v2"
    ] = "admin_health_edit_preview.v1"
    run_id: str
    branch_id: str
    week: RankingWeek | RunWeekPosition
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_draft_version: int = Field(ge=0)
    saved_head_revision_id: str | None = None
    before_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_state: PlayerHealthWeekState | CalendarHealthState
    before_component_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_component_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def preview_fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class AdminHealthCurrentView(FrozenInput):
    schema_version: Literal[
        "admin_health_current_view.v1", "admin_health_current_view.v2"
    ] = "admin_health_current_view.v1"
    run_id: str
    branch_id: str
    week: RankingWeek | RunWeekPosition
    player: PlayerHealthProfile | CalendarHealthProfile
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    health_component_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    draft_version: int = Field(ge=0)
    saved_head_revision_id: str | None = None


class AdminHealthEditResult(FrozenInput):
    schema_version: Literal[
        "admin_health_edit_result.v1", "admin_health_edit_result.v2"
    ] = "admin_health_edit_result.v1"
    run_id: str
    branch_id: str
    command_id: str
    week: RankingWeek | RunWeekPosition
    player_id: str
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    health_component_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    draft_version: int = Field(ge=0)
    already_applied: bool = False


@dataclass(slots=True)
class AdminHealthEditService:
    repository: object

    @staticmethod
    def _require_writable(run: RunContainerModel, branch: RunBranchModel) -> None:
        if (
            run.read_only
            or branch.read_only
            or branch.status != "active"
            or run.status
            not in {WORKING_RUN_STATUS, LEGACY_ACTIVE_RUN_STATUS, COMPLETED_RUN_STATUS}
        ):
            raise ValueError("Run/Branch lifecycle is not writable")

    @staticmethod
    def _draft_changes(draft: BranchWorkingDraftModel) -> list[dict]:
        try:
            raw = json.loads(draft.changes_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Working Draft change evidence is corrupt") from exc
        if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
            raise ValueError("Working Draft change evidence is corrupt")
        return raw

    @staticmethod
    def _component_after(
        component: dict,
        state: PlayerHealthWeekState,
    ) -> str:
        states = component.get("states")
        if not isinstance(states, list) or not states:
            raise ValueError("Live Health component is corrupt")
        body = list(states)
        if (
            body[-1].get("week", {}).get("season_index") != state.week.season_index
            or body[-1].get("week", {}).get("week") != state.week.week
        ):
            raise ValueError(
                "Live Health component head differs from current Health state"
            )
        body[-1] = state.model_dump(mode="json")
        return _hash(body)

    @staticmethod
    def _validate_record_weeks(
        request: AdminHealthEditRequest | CalendarAdminHealthEditRequest,
        *,
        current_week: RankingWeek | RunWeekPosition,
    ) -> None:
        for record in request.records:
            for label, week in (
                ("onset", record.onset_week),
                ("recovered", record.recovered_week),
            ):
                if (
                    isinstance(current_week, RunWeekPosition)
                    and week is not None
                    and (
                        not isinstance(week, RunWeekPosition)
                        or week.calendar != current_week.calendar
                    )
                ):
                    raise ValueError("Admin Health date belongs to a foreign calendar")
                if week is not None and week.ordinal > current_week.ordinal:
                    raise ValueError(
                        f"Admin Health edit {label} week cannot be in the future"
                    )
        if request.mode == "pre_start_input":
            if current_week.ordinal != 0:
                raise ValueError(
                    "Pre-start Health input is available only at opening Week 1"
                )
            if any(not record.started_before_run for record in request.records):
                raise ValueError(
                    "Pre-start Health input records must be explicitly marked started_before_run"
                )

    def _current_in_session(self, session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Admin Health Run/Branch scope not found")
        revision = self.repository._validated_branch_revision_state_in_session(
            session=session, branch=branch
        )
        head = session.scalar(
            select(PlayerHealthWeekStateModel)
            .where(
                PlayerHealthWeekStateModel.run_id == run_id,
                PlayerHealthWeekStateModel.branch_id == branch_id,
            )
            .order_by(PlayerHealthWeekStateModel.week_ordinal.desc())
            .limit(1)
        )
        if head is None:
            raise ValueError("Admin Health edit requires canonical Health state")
        state = _load(head, run_id, branch_id, head.week_ordinal)
        if isinstance(state, (CalendarInitialHealthState, CalendarHealthState)):
            clock = resolve_saved_run_calendar(
                session, run_id=run_id, branch_id=branch_id
            )
            if state.week.calendar != clock:
                raise ValueError("Admin Health calendar differs from Saved clock")
            # Validate the live facts against immutable population/lifecycle authority.
            component = health_component(session, run_id=run_id, branch_id=branch_id)
            payload = {
                **revision.saved_revision.payload,
                "content": {
                    **revision.saved_revision.payload["content"],
                    "player_health_state": component,
                },
            }
            load_saved_health(payload, run_id=run_id, branch_id=branch_id)
            from beta_engine.infrastructure.db.initial_world_state import (
                get_initial_world,
                load_saved_initial_world,
            )
            from beta_engine.infrastructure.db.player_lifecycle_state import (
                get_lifecycle,
                load_saved_lifecycle,
            )

            world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
            saved_world = load_saved_initial_world(
                payload, run_id=run_id, branch_id=branch_id
            )
            life = get_lifecycle(
                session, run_id=run_id, branch_id=branch_id, week=state.week
            )
            saved_life = load_saved_lifecycle(
                payload, run_id=run_id, branch_id=branch_id
            )
            if world != saved_world or life not in (saved_life or ()):
                raise ValueError("Save the population/lifecycle before editing Health")
        return run, branch, revision, state

    def _preview_in_session(
        self,
        session,
        *,
        run_id: str,
        branch_id: str,
        request: AdminHealthEditRequest | CalendarAdminHealthEditRequest,
    ) -> AdminHealthEditPreview:
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Admin Health edit Run/Branch scope not found")
        self._require_writable(run, branch)

        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.run_id == run_id,
                BranchWorkingDraftModel.branch_id == branch_id,
            )
        )
        if draft is None:
            raise ValueError("Admin Health edit Working Draft is missing")
        if draft.draft_version != request.expected_draft_version:
            raise ValueError("Admin Health edit Working Draft changed since review")
        changes = self._draft_changes(draft)
        if changes and any(
            change.get("kind") != "player_health_state" for change in changes
        ):
            raise ValueError(
                "Resolve the pending non-Health Working Draft before editing Health"
            )

        _, _, revision, current = self._current_in_session(session, run_id, branch_id)
        current_week = current.week
        calendar_owned = isinstance(
            current, (CalendarInitialHealthState, CalendarHealthState)
        )
        if calendar_owned != isinstance(request, CalendarAdminHealthEditRequest):
            raise ValueError(
                "Admin Health request schema differs from current time authority"
            )
        if calendar_owned and (
            request.expected_saved_head != branch.saved_head_revision_id
            or draft.base_revision_id != request.expected_saved_head
            or request.expected_state_fingerprint != current.fingerprint
        ):
            raise ValueError(
                "Admin Health Saved head or state proof changed since review"
            )

        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        if world is not None and world.current_ordinal != current_week.ordinal:
            raise ValueError(
                "Admin Health edit Health head differs from authoritative Week"
            )
        if world is None and current_week.ordinal != 0:
            raise ValueError(
                "Admin Health edit cannot infer an advanced authoritative Week"
            )

        self._validate_record_weeks(request, current_week=current_week)
        existing = next(
            (
                player
                for player in current.players
                if player.player_id == request.player_id
            ),
            None,
        )
        if existing is None:
            raise ValueError(
                "Admin Health edit player is absent from current Health roster"
            )

        profile_type = CalendarHealthProfile if calendar_owned else PlayerHealthProfile
        replacement = profile_type(
            player_id=request.player_id,
            records=request.records,
            permanent_consequences=request.permanent_consequences,
        )
        if replacement.model_dump(mode="json") == existing.model_dump(mode="json"):
            raise ValueError(
                "Admin Health edit makes no effective player Health change"
            )

        players = tuple(
            replacement if player.player_id == request.player_id else player
            for player in current.players
        )
        if calendar_owned:
            evidence = CalendarHealthEditEvidence(
                command_id=request.command_id,
                request_fingerprint=request.fingerprint_for_scope(
                    run_id=run_id, branch_id=branch_id
                ),
                before_state_fingerprint=current.fingerprint,
                source_run_id=run_id,
                source_branch_id=branch_id,
                player_id=request.player_id,
                mode=request.mode,
                audit_label=request.audit_label,
                audit_reason=request.audit_reason,
            )
            origin = (
                CalendarHealthOrigin.from_baseline(current)
                if isinstance(current, CalendarInitialHealthState)
                else current.origin
            )
            edits = (
                ()
                if isinstance(current, CalendarInitialHealthState)
                else current.admin_edits
            )
            after_state = CalendarHealthState(
                run_id=run_id,
                branch_id=branch_id,
                week=current_week,
                players=tuple(
                    CalendarHealthProfile.model_validate_json(p.model_dump_json())
                    for p in players
                ),
                source_initial_world_fingerprint=current.source_initial_world_fingerprint,
                predecessor_fingerprint=current.predecessor_fingerprint,
                origin=origin,
                admin_edits=edits + (evidence,),
                stage_provenance=f"admin_health_edit.v2:{request.mode}:{request.command_id}",
            )
        else:
            after_state = current.model_copy(
                update={
                    "players": players,
                    "stage_provenance": f"admin_health_edit.v1:{request.mode}:{request.command_id}",
                }
            )
        component = health_component(session, run_id=run_id, branch_id=branch_id)
        if component is None:
            raise ValueError("Admin Health edit live Health component is missing")
        return AdminHealthEditPreview(
            schema_version="admin_health_edit_preview.v2"
            if calendar_owned
            else "admin_health_edit_preview.v1",
            saved_head_revision_id=branch.saved_head_revision_id,
            run_id=run_id,
            branch_id=branch_id,
            week=current_week,
            request_fingerprint=request.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id
            ),
            expected_draft_version=request.expected_draft_version,
            before_state_fingerprint=current.fingerprint,
            after_state=after_state,
            before_component_fingerprint=component["fingerprint"],
            after_component_fingerprint=self._component_after(component, after_state),
        )

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        player_id: str,
    ) -> AdminHealthCurrentView:
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            _, branch, revision, state = self._current_in_session(
                session, run_id, branch_id
            )
            component = health_component(session, run_id=run_id, branch_id=branch_id)
            player = next((p for p in state.players if p.player_id == player_id), None)
            if player is None or component is None:
                raise ValueError("Admin Health player is absent from current roster")
            return AdminHealthCurrentView(
                schema_version="admin_health_current_view.v2"
                if isinstance(state.week, RunWeekPosition)
                else "admin_health_current_view.v1",
                run_id=run_id,
                branch_id=branch_id,
                week=state.week,
                player=player,
                state_fingerprint=state.fingerprint,
                health_component_fingerprint=component["fingerprint"],
                draft_version=revision.working_draft.draft_version,
                saved_head_revision_id=branch.saved_head_revision_id,
            )

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: AdminHealthEditRequest | CalendarAdminHealthEditRequest,
    ) -> AdminHealthEditPreview:
        with self.repository._session_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            return self._preview_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                request=request,
            )

    def commit(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: AdminHealthEditRequest | CalendarAdminHealthEditRequest,
        expected_preview_fingerprint: str,
    ) -> AdminHealthEditResult:
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            receipt = session.get(
                PlayerHealthAdminEditReceiptModel,
                (run_id, branch_id, request.command_id),
            )
            request_fingerprint = request.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id
            )
            if receipt is not None:
                try:
                    payload = json.loads(receipt.payload_json)
                    stored_preview = AdminHealthEditPreview.model_validate_json(
                        json.dumps(payload["preview"])
                    )
                    stored_result = AdminHealthEditResult.model_validate_json(
                        json.dumps(payload["result"])
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError("Admin Health edit receipt is corrupt") from exc
                if (
                    receipt.request_fingerprint != request_fingerprint
                    or stored_preview.preview_fingerprint
                    != expected_preview_fingerprint
                ):
                    raise ValueError(
                        "Admin Health edit retry differs from the stored reviewed command"
                    )
                if (
                    (
                        stored_result.run_id,
                        stored_result.branch_id,
                        stored_result.command_id,
                        stored_result.player_id,
                    )
                    != (run_id, branch_id, request.command_id, request.player_id)
                    or (stored_preview.run_id, stored_preview.branch_id)
                    != (run_id, branch_id)
                    or stored_preview.request_fingerprint != request_fingerprint
                    or stored_preview.after_state.fingerprint
                    != stored_result.state_fingerprint
                    or stored_preview.after_component_fingerprint
                    != stored_result.health_component_fingerprint
                    or stored_preview.week != stored_result.week
                    or receipt.before_state_fingerprint
                    != stored_preview.before_state_fingerprint
                    or receipt.after_state_fingerprint
                    != stored_result.state_fingerprint
                    or payload.get("request") != request.model_dump(mode="json")
                ):
                    raise ValueError(
                        "Admin Health edit receipt integrity differs from its command"
                    )
                current = get_health(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=stored_result.week,
                )
                if (
                    current is None
                    or current.fingerprint != stored_result.state_fingerprint
                ):
                    raise ValueError(
                        "Admin Health edit receipt is historical after restore or later correction; "
                        "use a new command_id"
                    )
                return stored_result.model_copy(update={"already_applied": True})

            preview = self._preview_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                request=request,
            )
            if preview.preview_fingerprint != expected_preview_fingerprint:
                raise ValueError("Admin Health edit changed since reviewed preview")

            installed = replace_health_head(
                session,
                preview.after_state,
                expected_fingerprint=preview.before_state_fingerprint,
            )
            component = health_component(session, run_id=run_id, branch_id=branch_id)
            if (
                component is None
                or component["fingerprint"] != preview.after_component_fingerprint
            ):
                raise ValueError("Admin Health edit component changed during commit")

            draft = session.scalar(
                select(BranchWorkingDraftModel).where(
                    BranchWorkingDraftModel.run_id == run_id,
                    BranchWorkingDraftModel.branch_id == branch_id,
                )
            )
            if draft is None or draft.draft_version != request.expected_draft_version:
                raise ValueError("Admin Health edit Working Draft changed concurrently")
            changes = self._draft_changes(draft)
            claimed = session.execute(
                update(BranchWorkingDraftModel)
                .where(
                    BranchWorkingDraftModel.draft_id == draft.draft_id,
                    BranchWorkingDraftModel.draft_version
                    == request.expected_draft_version,
                )
                .values(
                    status=DIRTY_WORKING_DRAFT_STATUS,
                    change_count=draft.change_count + 1,
                    draft_version=request.expected_draft_version + 1,
                    draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
                    changes_json=json.dumps(
                        changes
                        + [
                            {
                                "kind": "player_health_state",
                                "fingerprint": component["fingerprint"],
                                "command_id": request.command_id,
                                "player_id": request.player_id,
                            }
                        ],
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            ).rowcount
            if claimed != 1:
                raise ValueError("Admin Health edit Working Draft changed concurrently")

            result = AdminHealthEditResult(
                schema_version="admin_health_edit_result.v2"
                if isinstance(preview.week, RunWeekPosition)
                else "admin_health_edit_result.v1",
                run_id=run_id,
                branch_id=branch_id,
                command_id=request.command_id,
                week=preview.week,
                player_id=request.player_id,
                state_fingerprint=installed.fingerprint,
                health_component_fingerprint=component["fingerprint"],
                draft_version=request.expected_draft_version + 1,
            )
            session.add(
                PlayerHealthAdminEditReceiptModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    command_id=request.command_id,
                    week_ordinal=preview.week.ordinal,
                    player_id=request.player_id,
                    request_fingerprint=request_fingerprint,
                    before_state_fingerprint=preview.before_state_fingerprint,
                    after_state_fingerprint=installed.fingerprint,
                    payload_json=json.dumps(
                        {
                            "request": request.model_dump(mode="json"),
                            "preview": preview.model_dump(mode="json"),
                            "preview_fingerprint": preview.preview_fingerprint,
                            "audit": {
                                "label": request.audit_label,
                                "reason": request.audit_reason,
                            },
                            "result": result.model_dump(mode="json"),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            )
            session.flush()
            return result
