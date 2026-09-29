"""Persistence/replay for hybrid knockout entrants resolved from final group order."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthority,
    TournamentHybridKnockoutEntrantsBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentHybridKnockoutEntrantsAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_group_standings_authority import (
    TournamentGroupStandingsAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityStore,
)


class TournamentHybridKnockoutEntrantsAuthorityConflict(ValueError):
    """A hybrid entrants command conflicts with immutable tournament history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentHybridKnockoutEntrantsAuthorityStore:
    """Freeze configured hybrid crossings from final group positions only."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Hybrid Knockout Entrants Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Hybrid Knockout Entrants scope is not writable")

    @staticmethod
    def _request(*, topology_fingerprint: str, standings_fingerprint: str) -> dict:
        return {
            "topology_authority_fingerprint": topology_fingerprint,
            "group_standings_authority_fingerprint": standings_fingerprint,
            "source_policy_id": "configured_group_crossings_no_reseed.v1",
        }

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentHybridKnockoutEntrantsAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentHybridKnockoutEntrantsAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None

        topology = TournamentTopologyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        standings = TournamentGroupStandingsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if topology is None or standings is None:
            raise ValueError(
                "Hybrid Knockout Entrants references missing Topology/Standings authority"
            )

        authority = TournamentHybridKnockoutEntrantsAuthority.model_validate_json(
            row.payload_json
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.topology_authority_fingerprint,
            authority.group_standings_authority_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.topology_authority_fingerprint,
            row.group_standings_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Hybrid Knockout Entrants authority is corrupt")
        if (
            authority.topology_authority_fingerprint != topology.fingerprint
            or authority.group_standings_authority_fingerprint != standings.fingerprint
        ):
            raise ValueError("Hybrid Knockout Entrants dependency fingerprint is stale")

        rebuilt = TournamentHybridKnockoutEntrantsBuilder.build(
            topology=topology,
            standings=standings,
            command_id=row.command_id,
        )
        if rebuilt != authority:
            raise ValueError(
                "Hybrid Knockout Entrants does not replay from frozen Topology/Standings"
            )
        request = self._request(
            topology_fingerprint=topology.fingerprint,
            standings_fingerprint=standings.fingerprint,
        )
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Hybrid Knockout Entrants request fingerprint is corrupt")
        return authority

    def generate(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> TournamentHybridKnockoutEntrantsAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Hybrid Knockout Entrants requires a valid command ID")

        topology = TournamentTopologyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        standings = TournamentGroupStandingsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if topology is None or standings is None:
            raise ValueError(
                "Hybrid Knockout Entrants requires frozen Topology and final Group Standings"
            )

        proposed = TournamentHybridKnockoutEntrantsBuilder.build(
            topology=topology,
            standings=standings,
            command_id=command_id,
        )
        request = self._request(
            topology_fingerprint=topology.fingerprint,
            standings_fingerprint=standings.fingerprint,
        )
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentHybridKnockoutEntrantsAuthorityModel).where(
                TournamentHybridKnockoutEntrantsAuthorityModel.run_id == run_id,
                TournamentHybridKnockoutEntrantsAuthorityModel.branch_id == branch_id,
                TournamentHybridKnockoutEntrantsAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentHybridKnockoutEntrantsAuthorityConflict(
                    "Hybrid Knockout Entrants command ID already has a different request"
                )
            value = self.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
            assert value is not None
            return value

        existing = self.session.get(
            TournamentHybridKnockoutEntrantsAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentHybridKnockoutEntrantsAuthorityConflict(
                "Tournament Edition already has immutable Hybrid Knockout Entrants authority"
            )

        self.session.add(
            TournamentHybridKnockoutEntrantsAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                topology_authority_fingerprint=topology.fingerprint,
                group_standings_authority_fingerprint=standings.fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
