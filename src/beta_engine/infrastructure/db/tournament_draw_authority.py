"""Persistence for immutable Run/Branch-owned tournament bracket authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentDrawAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)


class TournamentDrawAuthorityConflict(ValueError):
    """A draw-generation identity conflicts with already persisted authority."""


def _request_fingerprint(payload: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentDrawAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Draw Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Draw scope is not writable")

    def _command_row(
        self, *, run_id: str, branch_id: str, command_id: str
    ) -> TournamentDrawAuthorityModel | None:
        return self.session.scalar(
            select(TournamentDrawAuthorityModel).where(
                TournamentDrawAuthorityModel.run_id == run_id,
                TournamentDrawAuthorityModel.branch_id == branch_id,
                TournamentDrawAuthorityModel.command_id == command_id,
            )
        )

    @staticmethod
    def _request(*, draw_input_fingerprint: str) -> dict[str, str]:
        return {"draw_input_fingerprint": draw_input_fingerprint}

    @classmethod
    def validate_row(
        cls,
        row: TournamentDrawAuthorityModel,
        *,
        draw_input,
    ) -> TournamentDrawAuthority:
        authority = TournamentDrawAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.draw_input_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.draw_input_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament Draw authority is corrupt")
        if draw_input.fingerprint != row.draw_input_fingerprint:
            raise ValueError(
                "Tournament Draw authority references a different Draw Input authority"
            )

        rebuilt = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id=row.command_id,
            algorithm_version=authority.algorithm_version,
        )
        if rebuilt != authority:
            raise ValueError(
                "Tournament Draw authority does not replay from frozen Draw Input"
            )
        expected_request = cls._request(
            draw_input_fingerprint=draw_input.fingerprint,
        )
        if row.request_fingerprint != _request_fingerprint(expected_request):
            raise ValueError("Tournament Draw authority request fingerprint is corrupt")
        return authority

    def get_initial(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentDrawAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        draw_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw_input is None:
            raise ValueError(
                "Tournament Draw authority references missing Draw Input authority"
            )
        return self.validate_row(row, draw_input=draw_input)

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawAuthority | None:
        initial = self.get_initial(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if initial is None:
            return None
        from beta_engine.infrastructure.db.tournament_draw_revision import (
            TournamentDrawRevisionStore,
        )

        history = TournamentDrawRevisionStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        return history[-1].successor_draw if history else initial

    def generate(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> TournamentDrawAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament Draw generation requires a valid command ID")

        draw_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw_input is None:
            raise ValueError(
                "Tournament Draw generation requires committed Draw Input authority"
            )
        request = self._request(draw_input_fingerprint=draw_input.fingerprint)
        request_fp = _request_fingerprint(request)

        retry = self._command_row(
            run_id=run_id,
            branch_id=branch_id,
            command_id=command_id,
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentDrawAuthorityConflict(
                    "Tournament Draw command ID already has a different request"
                )
            return self.validate_row(retry, draw_input=draw_input)

        existing = self.session.get(
            TournamentDrawAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentDrawAuthorityConflict(
                "Tournament event already has canonical Draw authority"
            )

        authority = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id=command_id,
        )
        self.session.add(
            TournamentDrawAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=authority.fingerprint,
                draw_input_fingerprint=draw_input.fingerprint,
                payload_json=authority.model_dump_json(),
            )
        )
        self.session.flush()
        return authority