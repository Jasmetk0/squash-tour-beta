"""Persistence for immutable Run/Branch tournament draw input commitment."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentDrawInputAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


class TournamentDrawInputAuthorityConflict(ValueError):
    """A committed draw input or command identity conflicts with stored authority."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentDrawInputAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Draw Input Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Draw Input scope is not writable")

    def _command_row(
        self, *, run_id: str, branch_id: str, command_id: str
    ) -> TournamentDrawInputAuthorityModel | None:
        return self.session.scalar(
            select(TournamentDrawInputAuthorityModel).where(
                TournamentDrawInputAuthorityModel.run_id == run_id,
                TournamentDrawInputAuthorityModel.branch_id == branch_id,
                TournamentDrawInputAuthorityModel.command_id == command_id,
            )
        )

    @classmethod
    def validate_row(
        cls,
        row: TournamentDrawInputAuthorityModel,
        *,
        ranking_authority,
        field,
        field_sequence: int,
    ) -> TournamentDrawInputAuthority:
        """Validate one frozen row against already-resolved target dependencies."""

        committed = TournamentDrawInputAuthority.model_validate_json(row.payload_json)
        if (
            committed.run_id,
            committed.branch_id,
            committed.event_id,
            committed.committed_by_command_id,
            committed.field_sequence,
            committed.entry_field_fingerprint,
            committed.tournament_ranking_authority_fingerprint,
            committed.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.field_sequence,
            row.entry_field_fingerprint,
            row.ranking_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament Draw Input authority is corrupt")
        if row.field_sequence != field_sequence:
            raise ValueError(
                "Tournament Draw Input authority no longer references the terminal Entry Field"
            )
        if field.fingerprint != row.entry_field_fingerprint:
            raise ValueError(
                "Tournament Draw Input authority Entry Field fingerprint is stale"
            )
        if ranking_authority.fingerprint != row.ranking_authority_fingerprint:
            raise ValueError(
                "Tournament Draw Input authority ranking fingerprint is stale"
            )

        rebuilt = TournamentDrawInputAuthorityBuilder.build(
            authority=ranking_authority,
            field=field,
            field_sequence=field_sequence,
            command_id=row.command_id,
            draw_seed=committed.draw_seed,
            main_seed_count=committed.main_seed_count,
            qualification_seed_count=committed.qualification_seed_count,
            schema_version=committed.schema_version,
        )
        if rebuilt != committed:
            raise ValueError(
                "Tournament Draw Input authority does not replay from frozen inputs"
            )
        expected_request = cls._request(
            ranking_authority_fingerprint=ranking_authority.fingerprint,
            entry_field_fingerprint=field.fingerprint,
            field_sequence=field_sequence,
            draw_seed=committed.draw_seed,
            main_seed_count=committed.main_seed_count,
            qualification_seed_count=committed.qualification_seed_count,
        )
        if row.request_fingerprint != _request_fingerprint(expected_request):
            raise ValueError(
                "Tournament Draw Input authority request fingerprint is corrupt"
            )
        return committed

    def _load_row(
        self, row: TournamentDrawInputAuthorityModel
    ) -> TournamentDrawInputAuthority:
        ranking_authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
        )
        if ranking_authority is None:
            raise ValueError(
                "Tournament Draw Input authority references missing ranking authority"
            )
        history = TournamentEntryFieldStore(self.session).history(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
        )
        if not history:
            raise ValueError(
                "Tournament Draw Input authority references missing Entry Field history"
            )
        return self.validate_row(
            row,
            ranking_authority=ranking_authority,
            field=history[-1],
            field_sequence=len(history),
        )

    @staticmethod
    def _request(
        *,
        ranking_authority_fingerprint: str,
        entry_field_fingerprint: str,
        field_sequence: int,
        draw_seed: int,
        main_seed_count: int,
        qualification_seed_count: int,
    ) -> dict:
        return {
            "ranking_authority_fingerprint": ranking_authority_fingerprint,
            "entry_field_fingerprint": entry_field_fingerprint,
            "field_sequence": field_sequence,
            "draw_seed": draw_seed,
            "main_seed_count": main_seed_count,
            "qualification_seed_count": qualification_seed_count,
        }

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawInputAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        )
        return None if row is None else self._load_row(row)

    def commit(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        draw_seed: int,
        main_seed_count: int | None = None,
        qualification_seed_count: int | None = None,
    ) -> TournamentDrawInputAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament Draw Input requires a valid command ID")

        ranking_authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if ranking_authority is None:
            raise ValueError(
                "Tournament Draw Input requires Tournament Ranking Snapshot authority"
            )
        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError(
                "Tournament Draw Input requires a persisted Tournament Entry Field"
            )
        field = history[-1]
        field_sequence = len(history)

        # All new commitments use the Master-aligned v2 contract. Explicit seed
        # counts are accepted only as a validation assertion; the canonical counts
        # are derived from bracket capacity and actual player count.
        proposed = TournamentDrawInputAuthorityBuilder.build(
            authority=ranking_authority,
            field=field,
            field_sequence=field_sequence,
            command_id=command_id,
            draw_seed=draw_seed,
            main_seed_count=main_seed_count,
            qualification_seed_count=qualification_seed_count,
            schema_version="tournament_draw_input_authority.v2",
        )
        request = self._request(
            ranking_authority_fingerprint=ranking_authority.fingerprint,
            entry_field_fingerprint=field.fingerprint,
            field_sequence=field_sequence,
            draw_seed=draw_seed,
            main_seed_count=proposed.main_seed_count,
            qualification_seed_count=proposed.qualification_seed_count,
        )
        request_fp = _request_fingerprint(request)

        retry = self._command_row(
            run_id=run_id,
            branch_id=branch_id,
            command_id=command_id,
        )
        if retry is not None:
            if (
                retry.event_id != event_id
                or retry.request_fingerprint != request_fp
            ):
                raise TournamentDrawInputAuthorityConflict(
                    "Tournament Draw Input command ID already has a different request"
                )
            return self._load_row(retry)

        existing = self.session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentDrawInputAuthorityConflict(
                "Tournament event already has committed Draw Input authority"
            )

        committed = proposed
        self.session.add(
            TournamentDrawInputAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=committed.fingerprint,
                ranking_authority_fingerprint=ranking_authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                payload_json=committed.model_dump_json(),
            )
        )
        self.session.flush()
        return committed