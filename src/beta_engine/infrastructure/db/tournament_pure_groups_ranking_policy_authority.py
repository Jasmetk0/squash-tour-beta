"""Persistence for explicit pure single-group ranking policy."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.pure_groups_ranking_policy_authority import (
    TournamentPureGroupsRankingPolicyAuthority,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentPureGroupsRankingPolicyAuthorityModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityStore,
)


class TournamentPureGroupsRankingPolicyAuthorityConflict(ValueError):
    """A pure-groups ranking policy command conflicts with immutable event history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentPureGroupsRankingPolicyAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Pure Groups Ranking Policy Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Pure Groups Ranking Policy scope is not writable")

    @staticmethod
    def _request(*, played_group_win_points: int) -> dict:
        return {
            "scope_policy_id": "single_group_only.v1",
            "group_component_policy_id": "played_group_match_win_only.v1",
            "played_group_win_points": played_group_win_points,
        }

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentPureGroupsRankingPolicyAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentPureGroupsRankingPolicyAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        authority = TournamentPureGroupsRankingPolicyAuthority.model_validate_json(
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
            raise ValueError("Stored Pure Groups Ranking Policy authority is corrupt")
        request = self._request(
            played_group_win_points=authority.played_group_win_points,
        )
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Pure Groups Ranking Policy request fingerprint is corrupt")
        return authority

    def configure(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        played_group_win_points: int,
    ) -> TournamentPureGroupsRankingPolicyAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Pure Groups Ranking Policy requires a valid command ID")

        topology = TournamentTopologyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if topology is None or topology.format_kind != "groups":
            raise ValueError(
                "Pure Groups Ranking Policy requires frozen groups Tournament Topology"
            )
        group_indexes = {slot.group_index for slot in topology.group_slots}
        if group_indexes != {1}:
            raise ValueError(
                "Pure Groups Ranking Policy is supported only for one-group topology"
            )

        proposed = TournamentPureGroupsRankingPolicyAuthority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            configured_by_command_id=command_id,
            played_group_win_points=played_group_win_points,
        )
        request_fp = _request_fingerprint(
            self._request(played_group_win_points=played_group_win_points)
        )

        retry = self.session.scalar(
            select(TournamentPureGroupsRankingPolicyAuthorityModel).where(
                TournamentPureGroupsRankingPolicyAuthorityModel.run_id == run_id,
                TournamentPureGroupsRankingPolicyAuthorityModel.branch_id == branch_id,
                TournamentPureGroupsRankingPolicyAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentPureGroupsRankingPolicyAuthorityConflict(
                    "Pure Groups Ranking Policy command ID already has a different request"
                )
            value = self.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
            assert value is not None
            return value

        if (
            OwnedTournamentRankingSourceStore(self.session).get(
                run_id=run_id,
                branch_id=branch_id,
                edition_id=event_id,
            )
            is not None
        ):
            raise TournamentPureGroupsRankingPolicyAuthorityConflict(
                "Tournament Edition ranking source is already frozen"
            )

        existing = self.session.get(
            TournamentPureGroupsRankingPolicyAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentPureGroupsRankingPolicyAuthorityConflict(
                "Tournament Edition already has immutable Pure Groups Ranking Policy"
            )

        self.session.add(
            TournamentPureGroupsRankingPolicyAuthorityModel(
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
