"""Persistence for explicit hybrid Tournament Edition ranking phase policy."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthority,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentHybridRankingPolicyAuthorityModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityStore,
)


class TournamentHybridRankingPolicyAuthorityConflict(ValueError):
    """A hybrid ranking policy command conflicts with immutable event history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentHybridRankingPolicyAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Hybrid Ranking Policy Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Hybrid Ranking Policy scope is not writable")

    @staticmethod
    def _request(
        *,
        played_group_win_points: int,
        knockout_stage_points: tuple[tuple[str, int], ...],
    ) -> dict:
        return {
            "group_component_policy_id": "played_group_match_win_only.v1",
            "played_group_win_points": played_group_win_points,
            "knockout_stage_points": [list(item) for item in knockout_stage_points],
            "composition_policy_id": (
                "single_tournament_sum_group_plus_knockout_no_double_count.v1"
            ),
        }

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentHybridRankingPolicyAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentHybridRankingPolicyAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        authority = TournamentHybridRankingPolicyAuthority.model_validate_json(
            row.payload_json
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.configured_by_command_id,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Hybrid Ranking Policy authority is corrupt")
        request = self._request(
            played_group_win_points=authority.played_group_win_points,
            knockout_stage_points=authority.knockout_stage_points,
        )
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Hybrid Ranking Policy request fingerprint is corrupt")
        return authority

    def configure(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        played_group_win_points: int,
        knockout_stage_points: tuple[tuple[str, int], ...],
    ) -> TournamentHybridRankingPolicyAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Hybrid Ranking Policy requires a valid command ID")
        topology = TournamentTopologyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if topology is None or topology.format_kind != "groups_knockout":
            raise ValueError(
                "Hybrid Ranking Policy requires frozen groups+knockout Tournament Topology"
            )

        canonical_stage_points = tuple(sorted(knockout_stage_points))
        proposed = TournamentHybridRankingPolicyAuthority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            configured_by_command_id=command_id,
            played_group_win_points=played_group_win_points,
            knockout_stage_points=canonical_stage_points,
        )
        request = self._request(
            played_group_win_points=proposed.played_group_win_points,
            knockout_stage_points=proposed.knockout_stage_points,
        )
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentHybridRankingPolicyAuthorityModel).where(
                TournamentHybridRankingPolicyAuthorityModel.run_id == run_id,
                TournamentHybridRankingPolicyAuthorityModel.branch_id == branch_id,
                TournamentHybridRankingPolicyAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentHybridRankingPolicyAuthorityConflict(
                    "Hybrid Ranking Policy command ID already has a different request"
                )
            value = self.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
            assert value is not None
            return value

        source = OwnedTournamentRankingSourceStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            edition_id=event_id,
        )
        if source is not None:
            raise TournamentHybridRankingPolicyAuthorityConflict(
                "Tournament Edition ranking source is already frozen"
            )

        existing = self.session.get(
            TournamentHybridRankingPolicyAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentHybridRankingPolicyAuthorityConflict(
                "Tournament Edition already has immutable Hybrid Ranking Policy"
            )

        self.session.add(
            TournamentHybridRankingPolicyAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
