"""Canonical Admin boundary for Tournament Draw process-window authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessWindowPolicy,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)


class CanonicalDrawProcessConfigureCommand(FrozenInput):
    schema_version: Literal[
        "canonical_tournament_draw_process_configure_command.v1"
    ] = "canonical_tournament_draw_process_configure_command.v1"
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    expected_draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    main_process_window_count: int = Field(ge=2)
    qualification_process_window_count: int | None = Field(default=None, ge=2)


class CanonicalTournamentDrawProcessState(FrozenInput):
    schema_version: Literal["canonical_tournament_draw_process_state.v1"] = (
        "canonical_tournament_draw_process_state.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    has_qualification: bool
    configured: bool
    authority_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    main: TournamentDrawProcessWindowPolicy | None = None
    qualification: TournamentDrawProcessWindowPolicy | None = None


@dataclass(slots=True)
class CanonicalTournamentDrawProcessService:
    factory: sessionmaker[Session]

    def inspect(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> CanonicalTournamentDrawProcessState:
        with self.factory() as session:
            return self._state(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )

    def configure(
        self, command: CanonicalDrawProcessConfigureCommand
    ) -> CanonicalTournamentDrawProcessState:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            draw = TournamentDrawAuthorityStore(session).get_initial(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )
            if draw is None:
                raise ValueError(
                    "Tournament Draw process requires canonical initial Draw authority"
                )
            if draw.fingerprint != command.expected_draw_authority_fingerprint:
                raise ValueError(
                    "Tournament Draw authority changed since process configuration was prepared"
                )
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
                command_id=command.command_id,
                main_process_window_count=command.main_process_window_count,
                qualification_process_window_count=(
                    command.qualification_process_window_count
                ),
            )
            return self._state(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )

    @staticmethod
    def _state(
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
    ) -> CanonicalTournamentDrawProcessState:
        draw = TournamentDrawAuthorityStore(session).get_initial(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None:
            raise KeyError(
                f"Initial Tournament Draw authority does not exist for event '{event_id}'"
            )
        authority = TournamentDrawProcessAuthorityStore(session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        return CanonicalTournamentDrawProcessState(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            draw_authority_fingerprint=draw.fingerprint,
            has_qualification=bool(draw.qualification_brackets),
            configured=authority is not None,
            authority_fingerprint=(
                authority.fingerprint if authority is not None else None
            ),
            main=authority.main if authority is not None else None,
            qualification=(
                authority.qualification if authority is not None else None
            ),
        )
