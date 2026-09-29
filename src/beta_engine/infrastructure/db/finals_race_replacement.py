"""Append-only persistence for frozen-Race Finals replacement authority."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.finals import (
    WorldTourFinalsEffectiveParticipantState,
    WorldTourFinalsReplacementAuthority,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    WorldTourFinalsEffectiveParticipantStateModel,
    WorldTourFinalsReplacementAuthorityModel,
)


class WorldTourFinalsReplacementConflict(ValueError):
    pass


class WorldTourFinalsReplacementStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Finals replacement Run/Branch scope does not exist")
        if writing and (
            run.read_only or branch.read_only or branch.status == "archived"
        ):
            raise ValueError("Finals replacement scope is not writable")

    def state_history(
        self, *, run_id: str, branch_id: str, target_season_index: int
    ) -> tuple[WorldTourFinalsEffectiveParticipantState, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(WorldTourFinalsEffectiveParticipantStateModel)
            .where(
                WorldTourFinalsEffectiveParticipantStateModel.run_id == run_id,
                WorldTourFinalsEffectiveParticipantStateModel.branch_id == branch_id,
                WorldTourFinalsEffectiveParticipantStateModel.target_season_index
                == target_season_index,
            )
            .order_by(WorldTourFinalsEffectiveParticipantStateModel.sequence)
        ).all()
        states = tuple(
            WorldTourFinalsEffectiveParticipantState.model_validate_json(
                row.payload_json
            )
            for row in rows
        )
        previous = None
        for sequence, (row, state) in enumerate(zip(rows, states), 1):
            if (
                row.sequence,
                row.state_fingerprint,
                row.predecessor_fingerprint,
                row.command_id,
            ) != (
                sequence,
                state.fingerprint,
                state.predecessor_fingerprint,
                state.created_by_command_id,
            ):
                raise ValueError(
                    "Stored effective Finals participant state identity mismatch"
                )
            if state.predecessor_fingerprint != previous:
                raise ValueError("Effective Finals participant state lineage is broken")
            previous = state.fingerprint
        return states

    def latest_state(self, **scope) -> WorldTourFinalsEffectiveParticipantState | None:
        history = self.state_history(**scope)
        return history[-1] if history else None

    def put_state(
        self, state: WorldTourFinalsEffectiveParticipantState
    ) -> WorldTourFinalsEffectiveParticipantState:
        self._scope(state.run_id, state.branch_id, writing=True)
        rows = self.state_history(
            run_id=state.run_id,
            branch_id=state.branch_id,
            target_season_index=state.target_season_index,
        )
        by_command = next(
            (
                item
                for item in rows
                if item.created_by_command_id == state.created_by_command_id
            ),
            None,
        )
        if by_command is not None:
            if by_command != state:
                raise WorldTourFinalsReplacementConflict(
                    "Effective Finals state command ID has a different request"
                )
            return by_command
        expected = rows[-1].fingerprint if rows else None
        if state.predecessor_fingerprint != expected:
            raise WorldTourFinalsReplacementConflict(
                "Effective Finals state predecessor is stale"
            )
        self.session.add(
            WorldTourFinalsEffectiveParticipantStateModel(
                run_id=state.run_id,
                branch_id=state.branch_id,
                target_season_index=state.target_season_index,
                finals_event_id=state.finals_event_id,
                sequence=len(rows) + 1,
                state_fingerprint=state.fingerprint,
                predecessor_fingerprint=state.predecessor_fingerprint,
                command_id=state.created_by_command_id,
                payload_json=state.model_dump_json(),
            )
        )
        self.session.flush()
        return state

    def authority_history(
        self, *, run_id: str, branch_id: str, vacancy_id: str
    ) -> tuple[WorldTourFinalsReplacementAuthority, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(WorldTourFinalsReplacementAuthorityModel)
            .where(
                WorldTourFinalsReplacementAuthorityModel.run_id == run_id,
                WorldTourFinalsReplacementAuthorityModel.branch_id == branch_id,
                WorldTourFinalsReplacementAuthorityModel.vacancy_id == vacancy_id,
            )
            .order_by(WorldTourFinalsReplacementAuthorityModel.sequence)
        ).all()
        values = tuple(
            WorldTourFinalsReplacementAuthority.model_validate_json(row.payload_json)
            for row in rows
        )
        previous = None
        for sequence, (row, value) in enumerate(zip(rows, values), 1):
            if (
                row.sequence,
                row.authority_fingerprint,
                row.predecessor_fingerprint,
                row.command_id,
            ) != (
                sequence,
                value.fingerprint,
                value.predecessor_authority_fingerprint,
                value.command_id,
            ):
                raise ValueError(
                    "Stored Finals replacement authority identity mismatch"
                )
            if value.predecessor_authority_fingerprint != previous:
                raise ValueError("Finals replacement authority lineage is broken")
            previous = value.fingerprint
        return values

    def put_authority(
        self, value: WorldTourFinalsReplacementAuthority
    ) -> WorldTourFinalsReplacementAuthority:
        self._scope(value.run_id, value.branch_id, writing=True)
        rows = self.authority_history(
            run_id=value.run_id, branch_id=value.branch_id, vacancy_id=value.vacancy_id
        )
        by_command = next(
            (item for item in rows if item.command_id == value.command_id), None
        )
        if by_command is not None:
            if by_command != value:
                raise WorldTourFinalsReplacementConflict(
                    "Finals replacement command ID has a different request"
                )
            return by_command
        expected = rows[-1].fingerprint if rows else None
        if value.predecessor_authority_fingerprint != expected:
            raise WorldTourFinalsReplacementConflict(
                "Finals replacement authority predecessor is stale"
            )
        self.session.add(
            WorldTourFinalsReplacementAuthorityModel(
                run_id=value.run_id,
                branch_id=value.branch_id,
                target_season_index=value.target_season_index,
                finals_event_id=value.finals_event_id,
                vacancy_id=value.vacancy_id,
                sequence=len(rows) + 1,
                authority_fingerprint=value.fingerprint,
                predecessor_fingerprint=value.predecessor_authority_fingerprint,
                command_id=value.command_id,
                payload_json=value.model_dump_json(),
            )
        )
        self.session.flush()
        return value
