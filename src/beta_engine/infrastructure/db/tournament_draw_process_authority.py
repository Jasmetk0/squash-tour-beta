"""Persistence for canonical Qualification/Main Draw process-window authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessAuthority,
    TournamentDrawProcessAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentDrawProcessAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)


class TournamentDrawProcessAuthorityConflict(ValueError):
    """Draw process configuration conflicts with persisted authority."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentDrawProcessAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Draw process Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Draw process scope is not writable")

    @staticmethod
    def _request(
        *,
        draw_authority_fingerprint: str,
        main_process_window_count: int,
        qualification_process_window_count: int | None,
    ) -> dict:
        return {
            "draw_authority_fingerprint": draw_authority_fingerprint,
            "main_process_window_count": main_process_window_count,
            "qualification_process_window_count": qualification_process_window_count,
        }

    def _command_row(
        self, *, run_id: str, branch_id: str, command_id: str
    ) -> TournamentDrawProcessAuthorityModel | None:
        return self.session.scalar(
            select(TournamentDrawProcessAuthorityModel).where(
                TournamentDrawProcessAuthorityModel.run_id == run_id,
                TournamentDrawProcessAuthorityModel.branch_id == branch_id,
                TournamentDrawProcessAuthorityModel.command_id == command_id,
            )
        )

    @classmethod
    def validate_row(
        cls,
        row: TournamentDrawProcessAuthorityModel,
        *,
        draw,
    ) -> TournamentDrawProcessAuthority:
        authority = TournamentDrawProcessAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.configured_by_command_id,
            authority.draw_authority_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.draw_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament Draw process authority is corrupt")
        if draw.fingerprint != row.draw_authority_fingerprint:
            raise ValueError(
                "Tournament Draw process authority references a different Draw authority"
            )

        rebuilt = TournamentDrawProcessAuthorityBuilder.build(
            draw=draw,
            command_id=row.command_id,
            main_process_window_count=authority.main.process_window_count,
            qualification_process_window_count=(
                authority.qualification.process_window_count
                if authority.qualification is not None
                else None
            ),
        )
        if rebuilt != authority:
            raise ValueError(
                "Tournament Draw process authority does not replay from frozen Draw"
            )
        expected_request = cls._request(
            draw_authority_fingerprint=draw.fingerprint,
            main_process_window_count=authority.main.process_window_count,
            qualification_process_window_count=(
                authority.qualification.process_window_count
                if authority.qualification is not None
                else None
            ),
        )
        if row.request_fingerprint != _fingerprint(expected_request):
            raise ValueError(
                "Tournament Draw process authority request fingerprint is corrupt"
            )
        return authority

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawProcessAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentDrawProcessAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        draw = TournamentDrawAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None:
            raise ValueError(
                "Tournament Draw process authority references missing Draw authority"
            )
        return self.validate_row(row, draw=draw)

    def configure(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        main_process_window_count: int,
        qualification_process_window_count: int | None = None,
    ) -> TournamentDrawProcessAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament Draw process requires a valid command ID")

        draw = TournamentDrawAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None:
            raise ValueError(
                "Tournament Draw process requires canonical Draw authority"
            )

        request = self._request(
            draw_authority_fingerprint=draw.fingerprint,
            main_process_window_count=main_process_window_count,
            qualification_process_window_count=qualification_process_window_count,
        )
        request_fp = _fingerprint(request)

        retry = self._command_row(
            run_id=run_id,
            branch_id=branch_id,
            command_id=command_id,
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentDrawProcessAuthorityConflict(
                    "Tournament Draw process command ID already has a different request"
                )
            return self.validate_row(retry, draw=draw)

        if self.session.get(
            TournamentDrawProcessAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentDrawProcessAuthorityConflict(
                "Tournament event already has Draw process authority"
            )

        authority = TournamentDrawProcessAuthorityBuilder.build(
            draw=draw,
            command_id=command_id,
            main_process_window_count=main_process_window_count,
            qualification_process_window_count=qualification_process_window_count,
        )
        self.session.add(
            TournamentDrawProcessAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=authority.fingerprint,
                draw_authority_fingerprint=draw.fingerprint,
                payload_json=authority.model_dump_json(),
            )
        )
        self.session.flush()
        return authority
