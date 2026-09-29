"""Persistence/replay for the immutable post-group hybrid knockout bracket."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
    TournamentHybridKnockoutBracketBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentHybridKnockoutBracketAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthorityStore,
)


class TournamentHybridKnockoutBracketAuthorityConflict(ValueError):
    """A hybrid bracket command conflicts with immutable tournament history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentHybridKnockoutBracketAuthorityStore:
    """Freeze the complete winner tree only from frozen hybrid entrants."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Hybrid Knockout Bracket Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Hybrid Knockout Bracket scope is not writable")

    @staticmethod
    def _request(*, entrants_fingerprint: str) -> dict:
        return {
            "entrants_authority_fingerprint": entrants_fingerprint,
            "bracket_policy_id": (
                "configured_crossings_standard_winner_tree_no_reseed.v1"
            ),
        }

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentHybridKnockoutBracketAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentHybridKnockoutBracketAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None

        entrants = TournamentHybridKnockoutEntrantsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if entrants is None:
            raise ValueError(
                "Hybrid Knockout Bracket references missing Entrants authority"
            )

        authority = TournamentHybridKnockoutBracketAuthority.model_validate_json(
            row.payload_json
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.entrants_authority_fingerprint,
            authority.terminal_match_id,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.entrants_authority_fingerprint,
            row.terminal_match_id,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Hybrid Knockout Bracket authority is corrupt")
        if authority.entrants_authority_fingerprint != entrants.fingerprint:
            raise ValueError("Hybrid Knockout Bracket Entrants fingerprint is stale")

        rebuilt = TournamentHybridKnockoutBracketBuilder.build(
            entrants=entrants,
            command_id=row.command_id,
        )
        if rebuilt != authority:
            raise ValueError(
                "Hybrid Knockout Bracket does not replay from frozen Entrants"
            )
        request = self._request(entrants_fingerprint=entrants.fingerprint)
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Hybrid Knockout Bracket request fingerprint is corrupt")
        return authority

    def generate(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> TournamentHybridKnockoutBracketAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Hybrid Knockout Bracket requires a valid command ID")

        entrants = TournamentHybridKnockoutEntrantsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if entrants is None:
            raise ValueError(
                "Hybrid Knockout Bracket requires frozen Hybrid Knockout Entrants"
            )

        proposed = TournamentHybridKnockoutBracketBuilder.build(
            entrants=entrants,
            command_id=command_id,
        )
        request = self._request(entrants_fingerprint=entrants.fingerprint)
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentHybridKnockoutBracketAuthorityModel).where(
                TournamentHybridKnockoutBracketAuthorityModel.run_id == run_id,
                TournamentHybridKnockoutBracketAuthorityModel.branch_id == branch_id,
                TournamentHybridKnockoutBracketAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentHybridKnockoutBracketAuthorityConflict(
                    "Hybrid Knockout Bracket command ID already has a different request"
                )
            value = self.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
            assert value is not None
            return value

        existing = self.session.get(
            TournamentHybridKnockoutBracketAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentHybridKnockoutBracketAuthorityConflict(
                "Tournament Edition already has immutable Hybrid Knockout Bracket authority"
            )

        self.session.add(
            TournamentHybridKnockoutBracketAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                entrants_authority_fingerprint=entrants.fingerprint,
                terminal_match_id=proposed.terminal_match_id,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
