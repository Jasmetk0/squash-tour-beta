"""Persistence/replay for immutable group Match + Match Day schedule authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
    TournamentGroupMatchScheduleBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentGroupMatchScheduleAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityStore,
)


class TournamentGroupMatchScheduleAuthorityConflict(ValueError):
    """A group match/schedule command conflicts with immutable event history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupMatchScheduleAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Group Match Schedule Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Group Match Schedule scope is not writable")

    @staticmethod
    def _request(*, format_fp: str, topology_fp: str) -> dict:
        return {
            "format_authority_fingerprint": format_fp,
            "topology_authority_fingerprint": topology_fp,
            "schedule_policy_id": "round_robin_circle.v1",
        }

    def validate_row(
        self,
        row: TournamentGroupMatchScheduleAuthorityModel,
        *,
        format_authority,
        topology_authority,
    ) -> TournamentGroupMatchScheduleAuthority:
        authority = TournamentGroupMatchScheduleAuthority.model_validate_json(
            row.payload_json
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.format_authority_fingerprint,
            authority.topology_authority_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.format_authority_fingerprint,
            row.topology_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored group Match Schedule authority is corrupt")
        if authority.format_authority_fingerprint != format_authority.fingerprint:
            raise ValueError("Group Match Schedule references stale Format authority")
        if authority.topology_authority_fingerprint != topology_authority.fingerprint:
            raise ValueError("Group Match Schedule references stale Topology authority")

        rebuilt = TournamentGroupMatchScheduleBuilder.build(
            format_authority=format_authority,
            topology_authority=topology_authority,
            command_id=row.command_id,
        )
        if rebuilt != authority:
            raise ValueError(
                "Group Match Schedule does not replay from frozen Format/Topology"
            )
        request = self._request(
            format_fp=format_authority.fingerprint,
            topology_fp=topology_authority.fingerprint,
        )
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Group Match Schedule request fingerprint is corrupt")
        return authority

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentGroupMatchScheduleAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentGroupMatchScheduleAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        format_authority = TournamentFormatAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        topology_authority = TournamentTopologyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if format_authority is None or topology_authority is None:
            raise ValueError(
                "Group Match Schedule references missing Format/Topology authority"
            )
        return self.validate_row(
            row,
            format_authority=format_authority,
            topology_authority=topology_authority,
        )

    def generate(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> TournamentGroupMatchScheduleAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Group Match Schedule requires a valid command ID")

        format_authority = TournamentFormatAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        topology_authority = TournamentTopologyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if format_authority is None or topology_authority is None:
            raise ValueError(
                "Group Match Schedule requires frozen Format and Topology authorities"
            )
        if format_authority.format_kind not in {"groups", "groups_knockout"}:
            raise ValueError("Group Match Schedule requires group-based Tournament Format")

        proposed = TournamentGroupMatchScheduleBuilder.build(
            format_authority=format_authority,
            topology_authority=topology_authority,
            command_id=command_id,
        )
        request = self._request(
            format_fp=format_authority.fingerprint,
            topology_fp=topology_authority.fingerprint,
        )
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentGroupMatchScheduleAuthorityModel).where(
                TournamentGroupMatchScheduleAuthorityModel.run_id == run_id,
                TournamentGroupMatchScheduleAuthorityModel.branch_id == branch_id,
                TournamentGroupMatchScheduleAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentGroupMatchScheduleAuthorityConflict(
                    "Group Match Schedule command ID already has a different request"
                )
            return self.validate_row(
                retry,
                format_authority=format_authority,
                topology_authority=topology_authority,
            )

        existing = self.session.get(
            TournamentGroupMatchScheduleAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentGroupMatchScheduleAuthorityConflict(
                "Tournament Edition already has immutable group Match Schedule authority"
            )

        self.session.add(
            TournamentGroupMatchScheduleAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                format_authority_fingerprint=format_authority.fingerprint,
                topology_authority_fingerprint=topology_authority.fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
