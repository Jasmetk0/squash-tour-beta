"""Canonical pre-draw withdrawal repair over Run-owned tournament field authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.entry_field import TournamentEntryField
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)


class CanonicalPreDrawWithdrawalCommand(FrozenInput):
    """One idempotent pre-draw withdrawal command for an authoritative event field."""

    schema_version: Literal["canonical_pre_draw_withdrawal_command.v1"] = (
        "canonical_pre_draw_withdrawal_command.v1"
    )
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    expected_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    withdrawn_player_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_withdrawals(self) -> "CanonicalPreDrawWithdrawalCommand":
        if any(not player_id.strip() for player_id in self.withdrawn_player_ids):
            raise ValueError("withdrawn player identities must be non-empty")
        if len(set(self.withdrawn_player_ids)) != len(self.withdrawn_player_ids):
            raise ValueError("withdrawn player identities must be unique")
        return self


class CanonicalPreDrawWithdrawalResult(FrozenInput):
    """Audit-friendly field delta produced by one canonical withdrawal command."""

    schema_version: Literal["canonical_pre_draw_withdrawal_result.v1"] = (
        "canonical_pre_draw_withdrawal_result.v1"
    )
    command_id: str
    run_id: str
    branch_id: str
    event_id: str
    field_sequence: int = Field(ge=2)
    predecessor_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    newly_withdrawn_player_ids: tuple[str, ...]
    promoted_to_main_player_ids: tuple[str, ...]
    qualification_backfill_player_ids: tuple[str, ...]
    direct_main_player_ids: tuple[str, ...]
    qualification_player_ids: tuple[str, ...]
    below_qualification_cut_player_ids: tuple[str, ...]
    withdrawn_player_ids: tuple[str, ...]


@dataclass(slots=True)
class CanonicalPreDrawWithdrawalService:
    """Transaction owner for canonical pre-draw field rebalance.

    The service deliberately does not choose a replacement directly. It appends one
    Tournament Entry Field repair derived from the already-frozen application payload
    and Tournament Ranking Snapshot authority. Draw commitment remains the hard lock.
    """

    factory: sessionmaker[Session]

    def execute(
        self, command: CanonicalPreDrawWithdrawalCommand
    ) -> CanonicalPreDrawWithdrawalResult:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            store = TournamentEntryFieldStore(session)
            repaired = store.stage_pre_draw_repair_from_frozen_inputs(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
                expected_field_fingerprint=command.expected_field_fingerprint,
                withdrawn_player_ids=command.withdrawn_player_ids,
                command_id=command.command_id,
            )
            history = store.history(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )
            return self._build_result(command=command, history=history, repaired=repaired)

    @staticmethod
    def _build_result(
        *,
        command: CanonicalPreDrawWithdrawalCommand,
        history: tuple[TournamentEntryField, ...],
        repaired: TournamentEntryField,
    ) -> CanonicalPreDrawWithdrawalResult:
        try:
            index = next(
                index
                for index, field in enumerate(history)
                if field.fingerprint == repaired.fingerprint
            )
        except StopIteration as exc:
            raise ValueError(
                "Repaired Tournament Entry Field is missing from persisted history"
            ) from exc
        if index == 0 or repaired.base_field_fingerprint is None:
            raise ValueError(
                "Canonical pre-draw withdrawal result requires a predecessor field"
            )

        predecessor = history[index - 1]
        if predecessor.fingerprint != repaired.base_field_fingerprint:
            raise ValueError(
                "Canonical pre-draw withdrawal predecessor does not match persisted history"
            )

        newly_withdrawn = tuple(
            sorted(
                set(repaired.withdrawn_player_ids)
                - set(predecessor.withdrawn_player_ids)
            )
        )
        promoted_to_main = tuple(
            player_id
            for player_id in repaired.direct_main_player_ids
            if player_id not in predecessor.direct_main_player_ids
        )
        qualification_backfill = tuple(
            player_id
            for player_id in repaired.qualification_player_ids
            if player_id not in predecessor.qualification_player_ids
        )

        return CanonicalPreDrawWithdrawalResult(
            command_id=command.command_id,
            run_id=command.run_id,
            branch_id=command.branch_id,
            event_id=command.event_id,
            field_sequence=index + 1,
            predecessor_field_fingerprint=predecessor.fingerprint,
            field_fingerprint=repaired.fingerprint,
            newly_withdrawn_player_ids=newly_withdrawn,
            promoted_to_main_player_ids=promoted_to_main,
            qualification_backfill_player_ids=qualification_backfill,
            direct_main_player_ids=repaired.direct_main_player_ids,
            qualification_player_ids=repaired.qualification_player_ids,
            below_qualification_cut_player_ids=(
                repaired.below_qualification_cut_player_ids
            ),
            withdrawn_player_ids=repaired.withdrawn_player_ids,
        )