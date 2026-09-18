"""Persistence for canonical Run/Branch Wild Card / Reserve Wild Card authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentDrawInputAuthorityModel,
    TournamentWildCardAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore


class TournamentWildCardAuthorityConflict(ValueError):
    """A WC/RWC command or event authority conflicts with persisted state."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentWildCardAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament WC Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament WC scope is not writable")

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentWildCardAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentWildCardAuthorityModel,
            (run_id, branch_id, event_id),
        )
        return None if row is None else self._load(row)

    def _load(
        self, row: TournamentWildCardAuthorityModel
    ) -> TournamentWildCardAuthority:
        history = TournamentEntryFieldStore(self.session).history(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
        )
        if not history:
            raise ValueError("Tournament WC authority references missing Entry Field")
        if len(history) != row.field_sequence:
            raise ValueError("Tournament WC authority no longer references terminal Entry Field")
        field = history[-1]
        authority = TournamentWildCardAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.resolved_by_command_id,
            authority.entry_field_fingerprint,
            authority.field_sequence,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.entry_field_fingerprint,
            row.field_sequence,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament WC authority is corrupt")
        if field.fingerprint != row.entry_field_fingerprint:
            raise ValueError("Tournament WC authority Entry Field fingerprint is stale")
        rebuilt = TournamentWildCardAuthorityBuilder.build(
            field=field,
            field_sequence=row.field_sequence,
            command_id=row.command_id,
            original_wild_card_player_ids=authority.original_wild_card_player_ids,
            reserve_wild_card_player_ids=authority.reserve_wild_card_player_ids,
            unavailable_player_ids=authority.unavailable_player_ids,
        )
        if rebuilt != authority:
            raise ValueError("Tournament WC authority does not replay from frozen field")
        return authority

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        original_wild_card_player_ids: tuple[str | None, ...],
        reserve_wild_card_player_ids: tuple[str, ...] = (),
        unavailable_player_ids: tuple[str, ...] = (),
    ) -> TournamentWildCardAuthority:
        self._scope(run_id, branch_id, writing=True)
        if self.session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentWildCardAuthorityConflict(
                "Tournament WC authority is locked after Draw Input commitment"
            )

        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError("Tournament WC authority requires Tournament Entry Field")
        field = history[-1]
        field_sequence = len(history)

        request = {
            "entry_field_fingerprint": field.fingerprint,
            "field_sequence": field_sequence,
            "original_wild_card_player_ids": list(original_wild_card_player_ids),
            "reserve_wild_card_player_ids": list(reserve_wild_card_player_ids),
            "unavailable_player_ids": sorted(set(unavailable_player_ids)),
        }
        request_fp = _fingerprint(request)

        retry = self.session.scalar(
            select(TournamentWildCardAuthorityModel).where(
                TournamentWildCardAuthorityModel.run_id == run_id,
                TournamentWildCardAuthorityModel.branch_id == branch_id,
                TournamentWildCardAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentWildCardAuthorityConflict(
                    "Tournament WC command ID already has a different request"
                )
            return self._load(retry)

        if self.session.get(
            TournamentWildCardAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentWildCardAuthorityConflict(
                "Tournament event already has WC authority"
            )

        authority = TournamentWildCardAuthorityBuilder.build(
            field=field,
            field_sequence=field_sequence,
            command_id=command_id,
            original_wild_card_player_ids=original_wild_card_player_ids,
            reserve_wild_card_player_ids=reserve_wild_card_player_ids,
            unavailable_player_ids=unavailable_player_ids,
        )
        self.session.add(
            TournamentWildCardAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                payload_json=authority.model_dump_json(),
            )
        )
        self.session.flush()
        return authority
